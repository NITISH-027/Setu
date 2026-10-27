from datetime import datetime
from typing import Optional, Dict, Any
from app.models.content import ReviewRecord, ReviewStatus, Question, Lesson, HintLadder


class ReviewManager:
    """
    Enforces review attestation rules:
    1. Automated scripts/seeds cannot create 'reviewed' status.
    2. Imports claiming 'reviewed' without verified registry credentials are downgraded to 'unverified import'.
    3. Edits to an existing reviewed item reset status to 'changed since review' or 'author-drafted, unreviewed'.
    4. Only authenticated human actions can attest 'reviewed'.
    """

    def __init__(self, registered_reviewers: Optional[Dict[str, str]] = None):
        # In-memory registry of authorized human reviewers {name: role}
        self.registered_reviewers = registered_reviewers or {}

    def register_human_reviewer(self, name: str, role: str):
        self.registered_reviewers[name] = role

    def create_draft_record(self, version: int = 1) -> ReviewRecord:
        """Every draft, script-generated, or seeded item starts here."""
        return ReviewRecord(
            status=ReviewStatus.AUTHOR_DRAFTED,
            reviewer_name=None,
            reviewer_role=None,
            attestation_date=None,
            item_version=version,
            attestation_statement=None
        )

    def import_external_record(self, raw_record: Dict[str, Any]) -> ReviewRecord:
        """
        Processes incoming imported records.
        Rule: An imported record that claims 'reviewed' is ALWAYS stored as 'unverified import'
        and requires a fresh human attestation in the UI. No external import may create 'reviewed'.
        """
        claimed_status = raw_record.get("status")
        reviewer_name = raw_record.get("reviewer_name")
        version = raw_record.get("item_version", 1)

        if claimed_status in [ReviewStatus.REVIEWED.value, "reviewed"]:
            # Always downgrade imported 'reviewed' claims to unverified import
            return ReviewRecord(
                status=ReviewStatus.UNVERIFIED_IMPORT,
                reviewer_name=reviewer_name,
                reviewer_role="Unverified imported claim",
                attestation_date=None,
                item_version=version,
                attestation_statement="Downgraded on import: requires live reviewer UI attestation."
            )

        # Default for other imports
        return ReviewRecord(
            status=ReviewStatus.AUTHOR_DRAFTED,
            item_version=version
        )

    def human_attest(
        self,
        item_review_record: ReviewRecord,
        reviewer_name: str,
        reviewer_role: str,
        attestation_statement: str
    ) -> ReviewRecord:
        """
        Executed only through reviewer UI flow by a human action.
        """
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("Reviewer name cannot be empty for human attestation")
        if not attestation_statement or not attestation_statement.strip():
            raise ValueError("Attestation statement cannot be empty (e.g., 'I checked this item')")

        return ReviewRecord(
            status=ReviewStatus.REVIEWED,
            reviewer_name=reviewer_name.strip(),
            reviewer_role=f"{reviewer_role.strip()} (self-declared)",
            attestation_date=datetime.utcnow(),
            item_version=item_review_record.item_version,
            attestation_statement=attestation_statement.strip()
        )

    def on_item_modified(self, current_record: ReviewRecord) -> ReviewRecord:
        """
        Called whenever question text, options, lesson content, or hint is edited.
        Resets reviewed status.
        """
        new_version = current_record.item_version + 1
        if current_record.status == ReviewStatus.REVIEWED:
            return ReviewRecord(
                status=ReviewStatus.CHANGED_SINCE_REVIEW,
                reviewer_name=current_record.reviewer_name,
                reviewer_role=current_record.reviewer_role,
                attestation_date=current_record.attestation_date,
                item_version=new_version,
                attestation_statement="Content modified after attestation. Re-review required."
            )
        else:
            return ReviewRecord(
                status=ReviewStatus.AUTHOR_DRAFTED,
                item_version=new_version
            )
