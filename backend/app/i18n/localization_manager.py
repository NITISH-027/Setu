"""
Localization (i18n) & Language Manager.
Rules:
1. Every UI string and lesson has an explicit language attribute.
2. Per-student medium-of-instruction setting determines default view.
3. Strings are externalized.
4. Hindi (hi) and Telugu (te) texts are unreviewed drafts.
5. Missing translations trigger a visible fallback to English:
   e.g. '[English Fallback - translation not reviewed]'.
6. A language only counts as 'supported' if an item has two human attestations
   (fluent speaker + subject reviewer).
"""

from typing import Dict, Any, Optional, Tuple, List
from app.models.content import Lesson, Question, ReviewRecord, ReviewStatus


# Externalized UI string catalog
UI_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_title": "Setu Adaptive Learning",
        "solve_heading": "Practice Question",
        "submit_button": "Submit Answer",
        "next_button": "Continue",
        "hint_button": "Get a Hint",
        "bkt_label": "Mastery Estimate (uncalibrated, hand-set)",
        "evidence_label": "Hypothesis Evidence Score",
        "switch_sibling": "Switch Profile",
        "enter_pin": "Enter 4-digit PIN",
        "clinic_recommendation": "Recommended 10-Minute Clinic",
        "paper_mode_title": "Paper Mode Worksheet Entry",
        "fallback_notice": ""
    },
    "hi": {
        "app_title": "सेतु अनुकूलित शिक्षण (ड्राफ्ट - असमीक्षित)",
        "solve_heading": "अभ्यास प्रश्न",
        "submit_button": "उत्तर जमा करें",
        "next_button": "आगे बढ़ें",
        "hint_button": "संकेत देखें",
        "bkt_label": "दक्षता अनुमान (असमायोजित, हस्त-निर्धारित)",
        "evidence_label": "परिकल्पना साक्ष्य स्कोर",
        "switch_sibling": "प्रोफ़ाइल बदलें",
        "enter_pin": "4-अंकीय पिन दर्ज करें",
        "fallback_notice": "[हिंदी ड्राफ्ट - असमीक्षित]"
    },
    "te": {
        "app_title": "సేతు అడాప్టివ్ లెర్నింగ్ (డ్రాఫ్ట్ - సమీక్షించబడలేదు)",
        "solve_heading": "అభ్యాస ప్రశ్న",
        "submit_button": "సమాధానం సమర్పించండి",
        "next_button": "కొనసాగించండి",
        "hint_button": "సూచన పొందండి",
        "bkt_label": "పాండిత్య అంచనా (అంకగణితం, చేతితో అమర్చినది)",
        "evidence_label": "పరికల్పన ఆధార స్కోరు",
        "switch_sibling": "ప్రొఫైల్ మార్చండి",
        "enter_pin": "4 అంకెల పిన్ నమోదు చేయండి",
        "fallback_notice": "[తెలుగు డ్రాఫ్ట్ - సమీక్షించబడలేదు]"
    }
}


class LocalizedStringResult:
    def __init__(self, text: str, language: str, is_fallback: bool, notice: Optional[str] = None):
        self.text = text
        self.language = language
        self.is_fallback = is_fallback
        self.notice = notice

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "is_fallback": self.is_fallback,
            "notice": self.notice
        }


class LocalizationManager:
    SUPPORTED_LANGUAGES = ["en"]
    DRAFT_UNREVIEWED_LANGUAGES = ["hi", "te"]

    def __init__(self, string_catalog: Optional[Dict[str, Dict[str, str]]] = None):
        self.catalog = string_catalog or UI_STRINGS

    def get_ui_string(self, key: str, requested_lang: str = "en") -> LocalizedStringResult:
        lang_dict = self.catalog.get(requested_lang, {})
        if key in lang_dict:
            notice = None
            if requested_lang in self.DRAFT_UNREVIEWED_LANGUAGES:
                notice = f"[{requested_lang.upper()} Draft - unreviewed]"
            return LocalizedStringResult(
                text=lang_dict[key],
                language=requested_lang,
                is_fallback=False,
                notice=notice
            )

        # Fallback to English
        en_dict = self.catalog.get("en", {})
        fallback_text = en_dict.get(key, f"[{key}]")
        return LocalizedStringResult(
            text=fallback_text,
            language="en",
            is_fallback=True,
            notice=f"[English Fallback - translation missing for {requested_lang}]"
        )

    def resolve_lesson_content(self, lessons: List[Lesson], requested_lang: str = "en") -> Tuple[Lesson, bool, str]:
        """
        Finds lesson in requested language or provides visible fallback to English.
        Returns (lesson, is_fallback, notice).
        """
        # Look for matching language
        for l in lessons:
            if l.language == requested_lang:
                notice = (
                    f"[{requested_lang.upper()} Draft - unreviewed]"
                    if requested_lang in self.DRAFT_UNREVIEWED_LANGUAGES
                    else ""
                )
                return l, False, notice

        # Fallback to English lesson
        for l in lessons:
            if l.language == "en":
                return l, True, f"[English Fallback - {requested_lang.upper()} lesson unreviewed / not found]"

        # Default first
        return lessons[0], True, "[Fallback]"

    @staticmethod
    def verify_language_support_status(attestations: List[ReviewRecord]) -> bool:
        """
        A language counts as 'supported' only for items reviewed by:
        1. A fluent speaker attestation
        2. A subject reviewer attestation
        (Two distinct attestations).
        """
        has_fluent_speaker = any(
            r.is_human_reviewed() and "fluent" in (r.reviewer_role or "").lower()
            for r in attestations
        )
        has_subject_reviewer = any(
            r.is_human_reviewed() and ("math" in (r.reviewer_role or "").lower() or "subject" in (r.reviewer_role or "").lower())
            for r in attestations
        )
        return has_fluent_speaker and has_subject_reviewer
