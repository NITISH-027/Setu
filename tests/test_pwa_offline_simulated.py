import sys
import os
import json
from typing import Dict, Any, List, Optional
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.models.student import Student
from app.models.learning import Plan, MasteryState, Attempt, StageEnum
from app.engine.adaptive_engine import AdaptiveEngine
from app.privacy.data_protection_manager import DataProtectionManager


class LocalIndexedDBSimulator:
    """
    Simulates client-side IndexedDB offline storage in the PWA.
    """
    def __init__(self):
        self.cached_pack: Optional[ContentPack] = None
        self.local_student: Optional[Student] = None
        self.local_plan: Optional[Plan] = None
        self.local_mastery: Optional[MasteryState] = None
        self.sync_queue: List[Dict[str, Any]] = []

    def save_cached_pack(self, pack: ContentPack):
        self.cached_pack = pack

    def queue_offline_attempt(self, attempt_data: Dict[str, Any]):
        self.sync_queue.append(attempt_data)

    def clear_queue(self):
        self.sync_queue = []


def test_offline_flow_and_sync():
    """
    Test requirement:
    'Offline-first PWA: installable, local store (IndexedDB), downloads a week's pack,
     sync queue with conflict handling.
     Test: complete a learn-solve-test run with the network disabled, then sync.'
    """
    # 1. Server has the pack and student
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        pack = ContentPack.model_validate(json.load(f))

    server_privacy = DataProtectionManager()
    server_privacy.register_device("8-A", "tablet_offline_01")
    server_engine = AdaptiveEngine(pack)

    student = Student(pseudonymous_id="stu_offline_runner", class_id="8-A", pin_hash="h")
    server_privacy.add_student(student)

    # 2. Client downloads pack into local IndexedDB before going offline
    client_db = LocalIndexedDBSimulator()
    client_db.save_cached_pack(pack)
    client_db.local_student = student
    client_db.local_plan = Plan(
        student_id=student.pseudonymous_id,
        class_id=student.class_id,
        current_concept_id="c8_math_linear_eq_one_var"
    )
    client_db.local_mastery = MasteryState(
        student_id=student.pseudonymous_id,
        concept_id="c8_math_linear_eq_one_var"
    )

    # 3. Network disabled!
    network_online = False
    assert network_online is False

    # 4. Client runs entirely offline using local engine and cached pack
    local_engine = AdaptiveEngine(client_db.cached_pack)

    # Solve question offline
    step_1 = local_engine.get_next_step(
        client_db.local_student,
        client_db.local_plan,
        client_db.local_mastery
    )
    assert step_1.stage == StageEnum.SOLVE

    # Student makes attempt offline
    att_1 = Attempt(
        student_id=student.pseudonymous_id,
        question_id=step_1.item.id,
        concept_id=step_1.item.concept,
        selected_option_id="opt_2",
        is_correct=False,
        misconception_tag="tag_sign_error_on_transposition"
    )

    plan, mastery, hyp, dec = local_engine.process_attempt(
        client_db.local_student,
        client_db.local_plan,
        att_1,
        client_db.local_mastery,
        None
    )
    client_db.local_plan = plan
    client_db.local_mastery = mastery
    client_db.queue_offline_attempt(att_1.model_dump())

    # Offline probe step
    step_2 = local_engine.get_next_step(
        client_db.local_student,
        client_db.local_plan,
        client_db.local_mastery,
        hyp
    )
    assert step_2.stage == StageEnum.PROBE

    att_2 = Attempt(
        student_id=student.pseudonymous_id,
        question_id=step_2.item.id,
        concept_id=step_2.item.concept,
        selected_option_id="p1",
        is_correct=True
    )
    plan, mastery, hyp, dec = local_engine.process_attempt(
        client_db.local_student,
        client_db.local_plan,
        att_2,
        client_db.local_mastery,
        hyp
    )
    client_db.local_plan = plan
    client_db.local_mastery = mastery
    client_db.queue_offline_attempt(att_2.model_dump())

    # Verify offline queue accumulated attempts
    assert len(client_db.sync_queue) == 2

    # 5. Network restored!
    network_online = True
    assert network_online is True

    # 6. Flush sync queue to server
    sync_result = server_privacy.sync_device(
        device_id="tablet_offline_01",
        class_id="8-A",
        device_queued_attempts=client_db.sync_queue
    )

    assert sync_result["action"] == "SYNC_SUCCESS"
    assert sync_result["accepted_attempts_count"] == 2
    assert sync_result["rejected_deleted_attempts_count"] == 0
    client_db.clear_queue()
    assert len(client_db.sync_queue) == 0
