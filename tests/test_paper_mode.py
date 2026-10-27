import sys
import os
import json
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.models.student import Student
from app.models.learning import Plan, MasteryState
from app.engine.adaptive_engine import AdaptiveEngine
from app.paper_mode.paper_mode_generator import PaperModeManager


@pytest.fixture
def paper_env():
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pack = ContentPack.model_validate(data)
    engine = AdaptiveEngine(pack)
    manager = PaperModeManager(pack, engine)
    return manager, engine


def test_paper_mode_flow(paper_env):
    """
    Test requirement:
    'No device at home: teacher-mediated paper mode.
     Generate a printable question set from the pack, the teacher enters responses in bulk,
     and the same engine and logs are used.'
    """
    manager, engine = paper_env

    # 1. Generate printable worksheet
    sheet = manager.generate_printable_sheet("c8_math_linear_eq_one_var", limit=3)
    assert len(sheet.questions) == 3
    html = sheet.to_html()
    assert "Setu Paper Mode Worksheet" in html
    assert "Q1 [Code: q_c8_leq_01]" in html
    assert "bubble" in html

    # 2. Setup synthetic students who took the paper exam
    stu_1 = Student(pseudonymous_id="stu_paper_01", class_id="8-A", pin_hash="h")
    plan_1 = Plan(student_id="stu_paper_01", class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    mastery_1 = MasteryState(student_id="stu_paper_01", concept_id="c8_math_linear_eq_one_var", mastery_estimate=0.2)

    student_records = {
        "stu_paper_01": {
            "student": stu_1,
            "plan": plan_1,
            "mastery": mastery_1,
            "hypothesis": None
        }
    }

    # 3. Teacher bulk enters responses from physical sheets
    bulk_responses = [
        # Student 1 selected option opt_1 (correct) on Q1
        {
            "student_id": "stu_paper_01",
            "question_id": "q_c8_leq_01",
            "selected_option_id": "opt_1"
        }
    ]

    bulk_result = manager.process_bulk_paper_responses(bulk_responses, student_records)

    assert bulk_result["processed_count"] == 1
    res = bulk_result["results"][0]
    assert res["is_correct"] is True
    # Evaluated through standard engine: updated mastery > initial prior 0.2
    assert res["updated_mastery"] > 0.2
    assert student_records["stu_paper_01"]["mastery"].mastery_estimate > 0.2
