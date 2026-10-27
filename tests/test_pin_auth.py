import sys
import os
import pytest
from datetime import datetime, timedelta

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.auth.pin_manager import PinManager


def test_pin_lockout_and_no_logging():
    """
    Test requirement:
    'Per-student PIN on shared family phones: PIN stored hashed, sibling switch on one device,
     lockout after failed tries, PIN never logged.'
    """
    manager = PinManager()
    device_id = "phone_family_redmi"

    # Register two sibling profiles on one device
    manager.register_student_profile(
        device_id=device_id,
        student_id="stu_sibling_1",
        class_id="8-A",
        pin="1234",
        medium_language="en"
    )
    manager.register_student_profile(
        device_id=device_id,
        student_id="stu_sibling_2",
        class_id="6-B",
        pin="5678",
        medium_language="hi"
    )

    # 1. Sibling switcher lists both profiles
    siblings = manager.list_siblings_on_device(device_id)
    assert len(siblings) == 2
    student_ids = [s["pseudonymous_id"] for s in siblings]
    assert "stu_sibling_1" in student_ids
    assert "stu_sibling_2" in student_ids

    # 2. PIN stored hashed (never plain text)
    profile_1 = manager.device_profiles[device_id]["stu_sibling_1"]
    assert profile_1.pin_hash != "1234"
    assert len(profile_1.pin_hash) == 64  # SHA-256 hex length
    assert "1234" not in str(profile_1.model_dump())  # PIN never stored or dumped

    # 3. Successful authentication
    success, msg = manager.authenticate_sibling(device_id, "stu_sibling_1", "1234")
    assert success is True
    assert "successful" in msg

    # 4. Failed tries and Lockout test
    now = datetime(2026, 1, 1, 12, 0, 0)
    # Fail 1
    success, msg = manager.authenticate_sibling(device_id, "stu_sibling_1", "9999", current_time=now)
    assert success is False
    assert "2 attempt(s) remaining" in msg

    # Fail 2
    success, msg = manager.authenticate_sibling(device_id, "stu_sibling_1", "8888", current_time=now)
    assert success is False
    assert "1 attempt(s) remaining" in msg

    # Fail 3 -> triggers lockout!
    success, msg = manager.authenticate_sibling(device_id, "stu_sibling_1", "7777", current_time=now)
    assert success is False
    assert "locked for 60 seconds" in msg

    # Attempt during lockout window (even with correct PIN!) must be blocked
    locked_attempt, lock_msg = manager.authenticate_sibling(
        device_id, "stu_sibling_1", "1234",
        current_time=now + timedelta(seconds=20)
    )
    assert locked_attempt is False
    assert "Device locked" in lock_msg

    # After lockout duration expires, correct PIN succeeds
    unlocked_attempt, unlock_msg = manager.authenticate_sibling(
        device_id, "stu_sibling_1", "1234",
        current_time=now + timedelta(seconds=65)
    )
    assert unlocked_attempt is True
    assert "successful" in unlock_msg
