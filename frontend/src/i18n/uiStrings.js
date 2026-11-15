/**
 * UI string table (v4 language-selector fix).
 *
 * The selector previously only changed the CONTENT language (questions/lessons
 * via the backend); every UI string was hardcoded English, so the app looked
 * unchanged. Now visible chrome strings go through t().
 *
 * Fallback contract (honest): any key missing in the selected language falls
 * back to English. The selector already labels non-English languages
 * "Unreviewed Draft"; all non-English strings below are author-drafted,
 * DRAFT pending teacher review.
 */

export const UI_STRINGS = {
  en: {
    'nav.student': 'Student App (Phone)',
    'nav.teacher': 'Teacher Dashboard',
    'nav.privacy': 'Data & Privacy',
    'nav.review': 'Coverage & Review',
    'nav.paper': 'Paper Mode',
    'common.logout': 'Logout',
    'common.online': 'Online',
    'common.offline': 'Offline',
    'student.submit': 'Submit Answer',
    'student.hint': 'Need a Hint?',
    'student.chapterTest': 'Take Chapter Test (adaptive)',
    'student.queueEmpty': 'Queue Empty',
    'student.queueSync': 'Sync {n} Queued Attempt(s)',
    'student.autoSync': 'Auto-sync active',
    'student.offlineLocal': 'Offline: local IndexedDB',
    'student.mastery': 'Mastery',
    'student.queued': 'Queued',
    'student.continueLesson': 'Continue',
    'student.explainerTitle': 'Why this answer is wrong',
    'student.explainerFallback': 'Shown in English (translation not written yet).',
    'student.stage.solve': 'Standard Practice: Solve the problem below.',
    'student.stage.probe': 'Diagnostic Probe: Checking foundational prerequisite...',
    'student.stage.learn': 'Micro-Lesson: Reviewing prerequisite concept bridge.',
    'student.stage.bridge': 'Bridge Re-check: Verifying prerequisite mastery before continuing.',
    'student.stage.return': 'Returned to original topic: Solved the prerequisite gap! Back to standard practice.',
    'student.stage.ahead': 'Fast Track: Mastery achieved! Advancing ahead.',
    'student.stage.flag': 'Intervention: Teacher notified for 1-on-1 clinic support.',
    'student.flaggedTitle': 'Teacher Assistance Flagged',
    'student.flaggedBody': 'Your teacher has been notified. Please wait or ask your teacher.',
    'teacher.title': 'Teacher Control Dashboard',
    'teacher.attentionTitle': 'Who needs help now',
    'teacher.attentionEmpty': 'No student currently flagged, stuck, or with an open suspected gap.',
    'teacher.refresh': 'Refresh',
    'teacher.classView': 'Class View:',
    'teacher.urgent': 'urgent',
    'teacher.why': 'Why',
    'teacher.authorTitle': 'Add a question (no code needed)',
    'teacher.authorNote': 'Saved as an UNREVIEWED DRAFT. The checker catches structure only (one correct answer, tags on wrong options); a subject teacher must still check the maths and the tags.',
    'teacher.authorSubmit': 'Save as draft',
    'teacher.learnedFrom': 'Starting estimates refined from {n} teacher overrides',
  },
  ta: {
    'nav.student': 'மாணவர் செயலி (தொலைபேசி)',
    'nav.teacher': 'ஆசிரியர் டாஷ்போர்டு',
    'nav.privacy': 'தரவு & தனியுரிமை',
    'nav.review': 'உள்ளடக்கம் & மதிப்பாய்வு',
    'nav.paper': 'காகித முறை',
    'common.logout': 'வெளியேறு',
    'common.online': 'ஆன்லைன்',
    'common.offline': 'ஆஃப்லைன்',
    'student.submit': 'விடையைச் சமர்ப்பி',
    'student.hint': 'குறிப்பு வேண்டுமா?',
    'student.chapterTest': 'அத்தியாய தேர்வு (தகவமைப்பு)',
    'student.queueEmpty': 'வரிசை காலி',
    'student.queueSync': '{n} விடைகளை ஒத்திசை',
    'student.autoSync': 'தானியங்கு ஒத்திசைவு இயல்பில்',
    'student.offlineLocal': 'ஆஃப்லைன்: சாதன சேமிப்பு',
    'student.mastery': 'தேர்ச்சி',
    'student.queued': 'வரிசையில்',
    'student.continueLesson': 'தொடரவும்',
    'student.explainerTitle': 'இந்த விடை ஏன் தவறு',
    'student.explainerFallback': 'ஆங்கிலத்தில் காட்டப்படுகிறது (மொழிபெயர்ப்பு இன்னும் எழுதப்படவில்லை).',
    'student.stage.solve': 'வழக்கமான பயிற்சி: கீழுள்ள கணக்கைத் தீர்க்கவும்.',
    'student.stage.probe': 'கண்டறியும் கேள்வி: அடித்தள அறிவைச் சோதிக்கிறது...',
    'student.stage.learn': 'சிறு பாடம்: அடித்தளக் கருத்தை மீள்பார்வை.',
    'student.stage.bridge': 'மீள் சோதனை: அடித்தளத் தேர்ச்சியை உறுதி செய்கிறது.',
    'student.stage.return': 'அசல் பாடத்திற்குத் திரும்பினாய்! இடைவெளி நிவர்த்தி ஆனது.',
    'student.stage.ahead': 'விரைவு பாதை: தேர்ச்சி அடைந்தாய்! முன்னேறுகிறாய்.',
    'student.stage.flag': 'தலையீடு: ஆசிரியருக்கு அறிவிக்கப்பட்டது.',
    'student.flaggedTitle': 'ஆசிரியர் உதவி கோரப்பட்டது',
    'student.flaggedBody': 'உங்கள் ஆசிரியருக்கு அறிவிக்கப்பட்டது. காத்திருங்கள் அல்லது ஆசிரியரை அணுகுங்கள்.',
    'teacher.title': 'ஆசிரியர் கட்டுப்பாட்டு டாஷ்போர்டு',
    'teacher.attentionTitle': 'யாருக்கு இப்போது உதவி தேவை',
    'teacher.attentionEmpty': 'தற்போது எந்த மாணவரும் குறி, சிக்கல் அல்லது திறந்த சந்தேக இடைவெளியில் இல்லை.',
    'teacher.refresh': 'புதுப்பி',
    'teacher.classView': 'வகுப்பு:',
    'teacher.urgent': 'அவசரம்',
    'teacher.why': 'ஏன் [DRAFT]',
    'teacher.authorTitle': 'வினா சேர் (குறியீடு தேவையில்லை) [DRAFT]',
    'teacher.authorNote': 'மதிப்பாய்வு செய்யப்படாத வரைவாகச் சேமிக்கப்படும். கணிதத்தை ஒரு பாட ஆசிரியர் சரிபார்க்க வேண்டும். [DRAFT]',
    'teacher.authorSubmit': 'வரைவாகச் சேமி [DRAFT]',
    'teacher.learnedFrom': '{n} ஆசிரியர் மாற்றங்களிலிருந்து தொடக்க மதிப்பீடுகள் சீரமைக்கப்பட்டன',
  },
  hi: {
    'nav.student': 'छात्र ऐप (फ़ोन)',
    'nav.teacher': 'शिक्षक डैशबोर्ड',
    'nav.privacy': 'डेटा और गोपनीयता',
    'nav.review': 'कवरेज और समीक्षा',
    'nav.paper': 'पेपर मोड',
    'common.logout': 'लॉग आउट',
    'common.online': 'ऑनलाइन',
    'common.offline': 'ऑफ़लाइन',
    'student.submit': 'उत्तर जमा करें',
    'student.hint': 'संकेत चाहिए?',
    'student.chapterTest': 'अध्याय परीक्षा (अनुकूली)',
    'student.mastery': 'निपुणता',
    'student.queued': 'कतार में',
    'student.explainerTitle': 'यह उत्तर गलत क्यों है',
    'teacher.refresh': 'रीफ़्रेश',
    'teacher.classView': 'कक्षा:',
    'teacher.why': 'क्यों [DRAFT]',
  },
  te: {
    'nav.student': 'విద్యార్థి యాప్ (ఫోన్)',
    'nav.teacher': 'ఉపాధ్యాయ డ్యాష్‌బోర్డ్',
    'nav.privacy': 'డేటా & గోప్యత',
    'nav.review': 'కవరేజ్ & సమీక్ష',
    'nav.paper': 'పేపర్ మోడ్',
    'common.logout': 'లాగ్ అవుట్',
    'common.online': 'ఆన్‌లైన్',
    'common.offline': 'ఆఫ్‌లైన్',
    'student.submit': 'సమాధానం సమర్పించండి',
    'student.hint': 'సూచన కావాలా?',
    'student.chapterTest': 'అధ్యాయ పరీక్ష (అడాప్టివ్)',
    'student.mastery': 'ప్రావీణ్యం',
    'student.queued': 'క్యూలో',
    'student.explainerTitle': 'ఈ సమాధానం ఎందుకు తప్పు',
    'teacher.refresh': 'రిఫ్రెష్',
    'teacher.classView': 'తరగతి:',
    'teacher.why': 'ఎందుకు [DRAFT]',
  },
};

export function makeT(language) {
  const lang = UI_STRINGS[language] ? language : 'en';
  return (key, vars) => {
    let s = UI_STRINGS[lang][key] ?? UI_STRINGS.en[key] ?? key;
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => { s = s.replace(`{${k}}`, String(v)); });
    }
    return s;
  };
}
