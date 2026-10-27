from typing import Dict, List, Set, Any
from app.models.pack import ContentPack
from app.models.content import ReviewStatus


class CoverageReport:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return self.data


class CoverageReporter:
    """
    Computes content coverage metrics across concepts, probes, lessons, and review attestations.
    """

    MIN_QUESTIONS_PER_CONCEPT = 3

    def generate_report(self, pack: ContentPack) -> CoverageReport:
        concept_ids = {c.id for c in pack.concepts}
        graph_only_ids = {c.id for c in pack.concepts if c.graph_only}
        active_concept_ids = concept_ids - graph_only_ids

        # Question counts per concept
        q_count_by_concept: Dict[str, int] = {cid: 0 for cid in concept_ids}
        probe_count_by_concept: Dict[str, int] = {cid: 0 for cid in concept_ids}
        probe_for_tags: Set[str] = set()

        used_misconception_tags: Set[str] = set()
        for q in pack.questions:
            if q.concept in q_count_by_concept:
                q_count_by_concept[q.concept] += 1
            if q.probe_for_misconception:
                probe_for_tags.add(q.probe_for_misconception)
                if q.concept in probe_count_by_concept:
                    probe_count_by_concept[q.concept] += 1
            for opt in q.options:
                if not opt.is_correct and opt.misconception_tag:
                    used_misconception_tags.add(opt.misconception_tag.strip())

        # Lessons count
        lessons_by_concept: Dict[str, int] = {cid: 0 for cid in concept_ids}
        lesson_tags: Set[str] = set()
        for l in pack.lessons:
            if l.concept in lessons_by_concept:
                lessons_by_concept[l.concept] += 1
            if l.misconception:
                lesson_tags.add(l.misconception.strip())

        # Gaps
        concepts_without_lessons = [cid for cid in active_concept_ids if lessons_by_concept.get(cid, 0) == 0]
        concepts_with_insufficient_questions = [
            cid for cid in active_concept_ids
            if q_count_by_concept.get(cid, 0) < self.MIN_QUESTIONS_PER_CONCEPT
        ]
        concepts_without_probes = [cid for cid in active_concept_ids if probe_count_by_concept.get(cid, 0) == 0]
        tags_without_probes = list(used_misconception_tags - probe_for_tags)
        tags_without_lessons = list(used_misconception_tags - lesson_tags)

        # Review Attestation Breakdown
        all_review_records = []
        for q in pack.questions:
            all_review_records.append(q.review_record)
        for l in pack.lessons:
            all_review_records.append(l.review_record)
        for h in pack.hints:
            all_review_records.append(h.review_record)

        total_items = len(all_review_records)
        status_counts = {
            ReviewStatus.AUTHOR_DRAFTED.value: 0,
            ReviewStatus.FLAGGED.value: 0,
            ReviewStatus.REVIEWED.value: 0,
            ReviewStatus.UNVERIFIED_IMPORT.value: 0,
            ReviewStatus.CHANGED_SINCE_REVIEW.value: 0
        }

        human_verified_count = 0
        for rr in all_review_records:
            status_val = rr.status.value if hasattr(rr.status, "value") else str(rr.status)
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
            if rr.is_human_reviewed():
                human_verified_count += 1

        pct_human_reviewed = (human_verified_count / total_items * 100.0) if total_items > 0 else 0.0

        # Language Coverage Report
        lang_questions: Dict[str, int] = {}
        for q in pack.questions:
            lang = q.language or "en"
            lang_questions[lang] = lang_questions.get(lang, 0) + 1

        lang_lessons: Dict[str, int] = {}
        for l in pack.lessons:
            lang = l.language or "en"
            lang_lessons[lang] = lang_lessons.get(lang, 0) + 1

        language_coverage = {
            "en": {
                "questions": lang_questions.get("en", 0),
                "lessons": lang_lessons.get("en", 0),
                "status": "primary language (draft-unreviewed until human checked)"
            },
            "hi": {
                "questions": lang_questions.get("hi", 0),
                "lessons": lang_lessons.get("hi", 0),
                "status": "unreviewed draft (not supported - requires fluent speaker + subject review)"
            },
            "te": {
                "questions": lang_questions.get("te", 0),
                "lessons": lang_lessons.get("te", 0),
                "status": "unreviewed draft (not supported - requires fluent speaker + subject review)"
            }
        }

        report_data = {
            "pack_version": pack.metadata.version,
            "total_concepts": len(concept_ids),
            "active_concepts": len(active_concept_ids),
            "graph_only_concepts": len(graph_only_ids),
            "total_questions": len(pack.questions),
            "total_lessons": len(pack.lessons),
            "total_hints": len(pack.hints),
            "total_items": total_items,
            "human_reviewed_items": human_verified_count,
            "percent_human_reviewed": round(pct_human_reviewed, 2),
            "review_status_breakdown": status_counts,
            "language_coverage": language_coverage,
            "concepts_without_lessons": concepts_without_lessons,
            "concepts_with_insufficient_questions": concepts_with_insufficient_questions,
            "concepts_without_probes": concepts_without_probes,
            "tags_without_probes": tags_without_probes,
            "tags_without_lessons": tags_without_lessons,
            "disclaimer": (
                "Coverage reporting measures authored item existence and human attestation tallies. "
                "It does NOT evaluate pedagogical efficacy or curriculum compliance."
            )
        }
        return CoverageReport(report_data)
