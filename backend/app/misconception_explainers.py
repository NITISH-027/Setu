"""
Misconception explainers (Round 3 v3: richer child-side loop).

Short, child-facing explanations of WHY an option is wrong, keyed by the
misconception tag attached to that option in the pack. Served with the graded
attempt result so the student learns from the error immediately, before the
engine decides the next step.

Content status: author-drafted, UNREVIEWED (same status as all pack content).
Tamil entries are DRAFT pending teacher review; tags without a Tamil entry
fall back to English with is_fallback=True so the UI can show the same honest
label it uses for lesson fallbacks.
"""

from typing import Optional

# tag -> {"en": str, "ta": Optional[str]}
MISCONCEPTION_EXPLAINERS = {
    # Linear equations spine (Class 8 demo)
    "tag_sign_error_on_transposition": {
        "en": "When a term moves to the other side of '=', its sign flips. +5 becomes -5, not +5. Balance means doing the SAME operation on both sides.",
        "ta": "ஒரு உறுப்பு '=' இன் மறுபுறம் செல்லும்போது அதன் குறி மாறும். +5 என்பது -5 ஆகும், +5 அல்ல. [DRAFT - ஆசிரியர் மதிப்பாய்வு தேவை]",
    },
    "tag_dividing_instead_of_subtracting": {
        "en": "A number ADDED to x is removed by subtracting, not dividing. To undo '+ 5', subtract 5 from both sides.",
        "ta": None,
    },
    "tag_grouping_variables_wrong_sign": {
        "en": "When x-terms move across '=', each one flips sign. Collect all x-terms on one side first, then simplify.",
        "ta": None,
    },
    "tag_reciprocal_error_division": {
        "en": "Dividing by a fraction is the same as multiplying by its reciprocal (flip it). 1/2 becomes 2/1, not 1/2.",
        "ta": None,
    },
    # Class 6 integer bridge
    "tag_class6_integer_subtraction": {
        "en": "Subtracting a bigger number from a smaller one goes below zero. 5 - 12 = -7: count 12 steps down from 5 on the number line.",
        "ta": "சிறிய எண்ணிலிருந்து பெரிய எண்ணைக் கழித்தால் விடை பூஜ்ஜியத்திற்குக் கீழே செல்லும். 5 - 12 = -7. [DRAFT - ஆசிரியர் மதிப்பாய்வு தேவை]",
    },
    # Equivalent fractions spine (TN Class 6-8 demo concept)
    "tag_eqf_add_same_to_both": {
        "en": "Equivalent fractions are made by MULTIPLYING top and bottom by the same number, not adding. 1/2 = 2/4 because 1x2 and 2x2.",
        "ta": "சமமான பின்னங்கள் தொகுதி மற்றும் பகுதி இரண்டையும் ஒரே எண்ணால் பெருக்குவதால் கிடைக்கும், கூட்டுவதால் அல்ல. [DRAFT - ஆசிரியர் மதிப்பாய்வு தேவை]",
    },
    "tag_eqf_reciprocal_flip": {
        "en": "The top and bottom cannot be swapped: 1/2 is not the same as 2/1. Equivalent means same value, same point on the number line.",
        "ta": None,
    },
    "tag_eqf_wrong_operation": {
        "en": "Check the operation: multiply (or divide) BOTH numerator and denominator by the SAME number. Any other operation changes the value.",
        "ta": None,
    },
    "tag_eqf_change_one_side_only": {
        "en": "Changing only the top or only the bottom breaks the fraction. Whatever you do to the numerator, do the same to the denominator.",
        "ta": "மேலே அல்லது கீழே மட்டும் மாற்றினால் பின்னம் மாறிவிடும். தொகுதிக்கு செய்வதை பகுதிக்கும் செய்ய வேண்டும். [DRAFT - ஆசிரியர் மதிப்பாய்வு தேவை]",
    },
    "tag_eqf_size_confusion": {
        "en": "Bigger numbers do not mean a bigger fraction. 3/6 and 1/2 are the same size - look at the value, not the digits.",
        "ta": None,
    },
    # Other authored tags (outside the demo spine, English only)
    "tag_adding_denominators_directly": {
        "en": "Never add the bottoms of fractions. Find a common denominator first, then add only the tops.",
        "ta": None,
    },
    "tag_percent_as_raw_value": {
        "en": "A percent is out of 100: 25% means 0.25 or 25/100, not 25.",
        "ta": None,
    },
    "tag_multiplying_bases_adding_exponents_wrong": {
        "en": "When multiplying powers with the same base, keep the base and ADD the exponents: x^2 * x^3 = x^5.",
        "ta": None,
    },
    "tag_squaring_as_doubling": {
        "en": "Squaring means multiplying a number by itself: 5^2 = 5x5 = 25, not 5x2.",
        "ta": None,
    },
    "tag_missing_middle_term_identity": {
        "en": "(a+b)^2 is not a^2 + b^2. Expand it: (a+b)(a+b) = a^2 + 2ab + b^2. The middle term 2ab is missing.",
        "ta": None,
    },
}


def get_explainer(tag: Optional[str], language: str = "en") -> Optional[dict]:
    """Return {'text', 'language', 'is_fallback', 'review_status'} for a tag, or None."""
    if not tag or tag not in MISCONCEPTION_EXPLAINERS:
        return None
    entry = MISCONCEPTION_EXPLAINERS[tag]
    if language == "ta" and entry.get("ta"):
        return {
            "text": entry["ta"],
            "language": "ta",
            "is_fallback": False,
            "review_status": "author-drafted, DRAFT pending teacher review",
        }
    return {
        "text": entry["en"],
        "language": "en",
        "is_fallback": language != "en",
        "review_status": "author-drafted, unreviewed",
    }
