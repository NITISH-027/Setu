"""Small, evidence-based home-practice summaries. No public links or identifiers in share text."""
from collections import Counter

HOME_ACTIVITIES = {
    "c8_math_linear_eq_one_var": "Use a bus-fare puzzle: one ticket plus a Rs 5 booking fee costs Rs 20. Ask your child to find the ticket price, then check by adding the fee back.",
    "c8_math_linear_eq_variables_both_sides": "Compare two stationery bills: 2 identical notebooks plus Rs 10 costs the same as 1 notebook plus Rs 30. Ask what one notebook costs and check both bills.",
    "c8_math_rational_ops": "Draw two same-sized rotis. Shade half of one and a quarter of the other. Cut both drawings into quarters and ask how many quarters are shaded altogether.",
    "c7_math_equivalent_fractions": "Draw one roti split into 2 equal pieces and another same-sized roti split into 4. Shade one half and two quarters. Ask why the shaded amounts are equal.",
    "c8_math_squares_square_roots": "Draw a rangoli dot grid with 4 rows and 4 dots in each row. Ask how many dots it has, and why 4 squared is different from 4 doubled.",
    "c8_math_exponents_powers": "Draw 3 rounds of doubling seed packets: 2, then 4, then 8. Ask why 2 cubed means 2 times 2 times 2, not 2 times 3.",
    "c8_math_algebraic_identities": "Draw a square rangoli of side 10 + 2 units. Split each side into 10 and 2. Find the areas of the four pieces, including both rectangles.",
    "c8_math_comparing_quantities_percentages": "Use a pretend Rs 200 shop bill with a 10% discount. Ask your child to find 10 out of every 100 rupees, then the amount left to pay.",
    "c6_math_integers_add_sub": "Draw a number line. Start with a Rs 3 balance, then spend Rs 7 on credit. Move left 7 steps and discuss why the balance becomes minus Rs 4.",
    "c7_math_simple_eq": "Use a bus-fare puzzle: one ticket plus a Rs 5 booking fee costs Rs 20. Ask your child to find the ticket price and check the total.",
}


def build_parent_report(pack, attempts, generated_at):
    """attempts are newest first, limited by caller. Wrong answers are signals, not diagnoses."""
    concepts = {c.id: c.name for c in pack.concepts}
    known = [a for a in attempts if a.concept_id in concepts]
    missed = Counter(a.concept_id for a in known if not a.is_correct)
    focus = []
    for cid, count in missed.most_common(2):
        focus.append({
            "concept_id": cid,
            "topic": concepts[cid],
            "missed": count,
            "attempted": sum(a.concept_id == cid for a in known),
            "activity": HOME_ACTIVITIES.get(cid, "Ask your child to explain one example from this topic using a drawing. If they get stuck, note the step and ask their teacher for help."),
        })
    total = len(attempts)
    correct = sum(bool(a.is_correct) for a in attempts)
    if not total:
        summary = "No saved answers yet. Complete a short practice session before using this report."
    elif not missed:
        summary = f"Your child answered {correct} of the last {total} saved questions correctly. Keep practising and ask them to explain their steps."
    else:
        summary = f"Your child answered {correct} of the last {total} saved questions correctly. Some answers suggest a little more practice could help."
    note = "Prototype report, not a grade or a confirmed learning diagnosis. Based on up to 20 recent saved answers, which may include repeated questions. Offline answers not yet synced are not included. Content is author-drafted and has not been reviewed by a teacher."
    lines = ["Setu | Home practice note", f"Prepared: {generated_at}", "", summary]
    for item in focus:
        lines.extend(["", f"Practise: {item['topic']}", f"{item['missed']} of {item['attempted']} recent answers in this topic need another look.", f"Try at home: {item['activity']}"])
    if total:
        lines.extend(["", "Spend 5 minutes together. Let your child explain; do not rush to give the answer. If they are still stuck, ask their teacher."])
    lines.extend(["", note])
    return {"generated_at": generated_at, "attempts_used": total, "correct": correct,
            "summary": summary, "focus": focus, "note": note, "share_text": "\n".join(lines),
            "language": "en", "language_note": "Home reports are currently available in English only."}
