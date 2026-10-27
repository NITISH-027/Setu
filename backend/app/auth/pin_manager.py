"""
Student PIN Authentication & Sibling Switcher.
Enforces:
1. PINs stored as cryptographic hashes (SHA-256 with salt).
2. PIN is strictly NEVER logged or stored in plaintext.
3. Lockout after 3 failed attempts with configurable lockout duration.
4. Sibling switching on shared devices (multiple pseudonymous student profiles on one device).
"""

import hashlib
import secrets
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class DeviceStudentProfile(BaseModel):
    pseudonymous_id: str
    class_id: str
    pin_hash: str
    salt: str
    medium_language: str = "en"
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None


class PinManager:
    MAX_FAILED_ATTEMPTS = 3
    LOCKOUT_DURATION_SECONDS = 60

    def __init__(self):
        # device_id -> dict of {pseudonymous_id: DeviceStudentProfile}
        self.device_profiles: Dict[str, Dict[str, DeviceStudentProfile]] = {}

    @staticmethod
    def hash_pin(pin: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if not pin or len(pin) != 4 or not pin.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        salt = salt or secrets.token_hex(8)
        hashed = hashlib.sha256(f"{salt}{pin}".encode("utf-8")).hexdigest()
        return hashed, salt

    def register_student_profile(
        self,
        device_id: str,
        student_id: str,
        class_id: str,
        pin: str,
        medium_language: str = "en"
    ) -> DeviceStudentProfile:
        pin_hash, salt = self.hash_pin(pin)
        profile = DeviceStudentProfile(
            pseudonymous_id=student_id,
            class_id=class_id,
            pin_hash=pin_hash,
            salt=salt,
            medium_language=medium_language
        )
        self.device_profiles.setdefault(device_id, {})[student_id] = profile
        return profile

    def authenticate_sibling(
        self,
        device_id: str,
        student_id: str,
        candidate_pin: str,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Verifies PIN.
        Returns (success: bool, message: str).
        PIN is never logged.
        """
        now = current_time or datetime.utcnow()
        profiles = self.device_profiles.get(device_id, {})
        profile = profiles.get(student_id)

        if not profile:
            return False, "Student profile not found on this device."

        # Check lockout
        if profile.locked_until and now < profile.locked_until:
            remaining = int((profile.locked_until - now).total_seconds())
            return False, f"Device locked due to multiple failed tries. Please wait {remaining} seconds."

        # Compute hash
        candidate_hash, _ = self.hash_pin(candidate_pin, salt=profile.salt)

        if candidate_hash == profile.pin_hash:
            # Success: reset failed attempts
            profile.failed_attempts = 0
            profile.locked_until = None
            return True, "Authentication successful."
        else:
            profile.failed_attempts += 1
            if profile.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                profile.locked_until = now + timedelta(seconds=self.LOCKOUT_DURATION_SECONDS)
                return False, f"Incorrect PIN. Account locked for {self.LOCKOUT_DURATION_SECONDS} seconds."
            else:
                remaining_tries = self.MAX_FAILED_ATTEMPTS - profile.failed_attempts
                return False, f"Incorrect PIN. {remaining_tries} attempt(s) remaining."

    def list_siblings_on_device(self, device_id: str) -> List[Dict[str, str]]:
        """
        Lists available sibling profiles on a shared device (without sensitive credentials).
        """
        profiles = self.device_profiles.get(device_id, {})
        return [
            {
                "pseudonymous_id": p.pseudonymous_id,
                "class_id": p.class_id,
                "medium_language": p.medium_language
            }
            for p in profiles.values()
        ]
