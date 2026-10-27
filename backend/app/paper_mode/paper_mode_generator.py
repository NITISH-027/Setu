"""
Teacher-Mediated Paper Mode.
Generates printable question worksheets from content packs and processes
bulk physical response sheets using the exact same AdaptiveEngine and logging.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.pack import ContentPack
from app.models.content import Question
from app.models.student import Student
from app.models.learning import Attempt, Plan, MasteryState
from app.engine.adaptive_engine import AdaptiveEngine


class PrintableWorksheet:
    def __init__(self, sheet_id: str, title: str, class_level: int, questions: List[Dict[str, Any]]):
        self.sheet_id = sheet_id
        self.title = title
        self.class_level = class_level
        self.questions = questions

    def to_html(self) -> str:
        html = [
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{self.title}</title>",
            "<style>body{font-family:sans-serif;margin:20px;line-height:1.5;}.q-box{border:1px solid #ccc;padding:12px;margin-bottom:15px;border-radius:4px;}.bubble{display:inline-block;width:20px;height:20px;border-radius:50%;border:1px solid #333;text-align:center;margin-right:8px;font-size:12px;}</style>",
            f"</head><body><h2>Setu Paper Mode Worksheet: {self.title} (Class {self.class_level})</h2>",
            "<p><em>Instructions: Fill the circle corresponding to the chosen option. Teacher will enter responses in bulk.</em></p>"
        ]
        for idx, q in enumerate(self.questions, 1):
            html.append(f"<div class='q-box'><strong>Q{idx} [Code: {q['id']}]: {q['text']}</strong><br>")
            for opt_idx, opt in enumerate(q['options']):
                bubble_char = chr(65 + opt_idx)
                html.append(f"<div style='margin-top:6px;'><span class='bubble'>{bubble_char}</span> {opt['text']}</div>")
            html.append("</div>")
        html.append("</body></html>")
        return "".join(html)


class PaperModeManager:
    def __init__(self, pack: ContentPack, engine: AdaptiveEngine):
        self.pack = pack
        self.engine = engine

    def generate_printable_sheet(self, concept_id: str, limit: int = 5) -> PrintableWorksheet:
        qs = [q for q in self.pack.questions if q.concept == concept_id][:limit]
        sheet_questions = [
            {
                "id": q.id,
                "text": q.question_text,
                "options": [{"id": opt.id, "text": opt.text} for opt in q.options]
            }
            for q in qs
        ]
        concept_name = next((c.name for c in self.pack.concepts if c.id == concept_id), concept_id)
        return PrintableWorksheet(
            sheet_id=f"sheet_{concept_id}_{int(datetime.utcnow().timestamp())}",
            title=f"Practice - {concept_name}",
            class_level=8,
            questions=sheet_questions
        )

    def process_bulk_paper_responses(
        self,
        sheet_responses: List[Dict[str, Any]],  # [{student_id, question_id, selected_option_id}]
        student_records: Dict[str, Dict[str, Any]] # student_id -> {student, plan, mastery, hypothesis}
    ) -> Dict[str, Any]:
        """
        Processes bulk paper sheet responses through the standard AdaptiveEngine.
        """
        results = []
        for resp in sheet_responses:
            sid = resp["student_id"]
            qid = resp["question_id"]
            opt_id = resp["selected_option_id"]

            rec = student_records.get(sid)
            if not rec:
                continue

            student: Student = rec["student"]
            plan: Plan = rec["plan"]
            mastery: MasteryState = rec["mastery"]
            hyp = rec.get("hypothesis")

            question: Optional[Question] = self.engine.questions_by_id.get(qid)
            if not question:
                continue

            chosen_opt = next((o for o in question.options if o.id == opt_id), None)
            is_correct = chosen_opt.is_correct if chosen_opt else False
            misconception_tag = chosen_opt.misconception_tag if (chosen_opt and not is_correct) else None

            attempt = Attempt(
                student_id=sid,
                question_id=qid,
                concept_id=question.concept,
                selected_option_id=opt_id,
                is_correct=is_correct,
                misconception_tag=misconception_tag
            )

            plan, mastery, hyp, decision = self.engine.process_attempt(student, plan, attempt, mastery, hyp)
            rec["plan"] = plan
            rec["mastery"] = mastery
            rec["hypothesis"] = hyp

            results.append({
                "student_id": sid,
                "question_id": qid,
                "is_correct": is_correct,
                "misconception_tag": misconception_tag,
                "decision_action": decision.action,
                "updated_mastery": mastery.mastery_estimate
            })

        return {
            "processed_count": len(results),
            "results": results
        }
