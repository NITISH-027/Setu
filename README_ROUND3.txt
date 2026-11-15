SETU - ROUND 3 SUBMISSION BUILD (14 Nov 2026)
=============================================
This zip is the complete Setu repo with all Round 3 patches applied and
verified: 104/104 backend tests pass, frontend builds, engine parity OK.

WHAT IS IN HERE (on top of your last pushed code)
  Patch 1 - transfer items: after a passed re-check, the same idea is tested
            in a NEW format before returning to the topic.
  Patch 2 - teacher quick check: one tap = one BKT observation
            (POST /api/teacher/class/{id}/quick-check).
  Patch 3 - demo mode: SETU_DEMO_MODE=true gives one-tap student/teacher
            entry (no PIN/password). DEFAULT IS OFF. Demo data only.
  Patch 4 - Paathai (hill path) UI theme, now the default; Tamil added to the
            language dropdown (draft, pending teacher review).
  Patch 5 - "Watch Setu think": the visible diagnosis trail on the student
            screen + evidence trail on the teacher dashboard.
  Pack    - equivalent fractions concept (en items verified, ta items DRAFT
            for Tamil teacher review), with the 3 test updates required by
            the wider scope.
  ML      - scripts/setu_ml_benchmark.py: fits BKT on the real public
            ASSISTments 2009 dataset + trains a baseline and prints a measured
            comparison table. Run:  python scripts/setu_ml_benchmark.py
            (downloads 83 MB of public data itself, ~30 seconds, pure Python).
            Quote only YOUR run's numbers, labeled [MEASURED on my run].

HOW TO USE THIS ZIP
  1. Extract it. The top folder is "Setu".
  2. SAFEST: extract to a NEW folder and work there.
     You CAN extract over your existing Setu repo folder - the zip has no
     .git, so your git history is untouched - but any local files you edited
     and did not push will be overwritten. If you have an .env file or local
     database in your repo folder, keep a copy first (the zip has neither).
  3. Commit and push as usual.

RUN IT
  Backend:   cd backend && pip install -r requirements.txt
             SETU_DEMO_MODE=true uvicorn app.main:app --port 8000   (Linux/Mac)
             $env:SETU_DEMO_MODE="true"; uvicorn app.main:app --port 8000  (Windows PS)
  Seed demo data (first time, development only):
             python scripts/seed_demo_data.py   (prints credentials ONCE)
  Frontend:  cd frontend && npm install && npm run build
             (backend serves frontend/dist automatically)
  Judge demo: open the app -> Student App -> tap a student (no PIN).
             Teacher Dashboard -> "Judge demo: one-tap teacher entry".
  Tests:     python -m pytest tests   (expect 131 passed)

NEW IN THIS BUILD (evening fixes)
  - Paathai (light) theme contrast repair: every modal, banner, badge, notice,
    status bar, dropdown and disabled state audited by rendered-pixel
    screenshots; dark themes unchanged (scoped CSS overrides +
    var-with-fallback inline styles only).
  - Judge-demo reset: in SETU_DEMO_MODE, when a demo profile (one-tap student
    or teacher entry) logs out or its session expires, its attempts, mastery,
    hypotheses, trail, teacher decisions/overrides and queued items are
    restored to the seeded starting state, and the device's local IndexedDB
    copy for that profile is cleared on logout. Safe with two judges on the
    same profile: the reset waits until no live session remains for that
    profile. Real (PIN) accounts and non-demo deployments are never touched
    (covered by tests). Every demo-mode session is capped at 2 hours.
    Limits: the reset baseline is the DB state at server startup (on Render's
    ephemeral disk that IS the seeded state); a judge who closes the browser
    without logging out leaves the profile dirty until the 2h session expires
    and the next logout/login event triggers the sweep.

V6 FEATURES (this build)
  - Engine: prerequisite chain probing. When a wrong answer rejects the first
    hypothesis but the student PASSES its probe (no confirmed gap at that
    concept), the engine now opens a hypothesis on the next unprobed
    prerequisite and probes there, instead of falling back to SOLVE after the
    first rejection. Each gap still requires its probe evidence before any
    lesson is served. Re-run benchmark (200 synthetic students, seed 42):
    planted integer-gap NOT expressed in first errors (the v5 miss scenario):
    found 0% -> 55% within 12 questions, mean 5.6; fixed quiz mean 84.
    Planted Class 7 gap expressed in errors (main scenario): 90.5% -> 97.5%
    found, mean 4.2 -> 4.3 questions; fixed quiz mean 71. Main scenario did
    NOT get worse. Both disclosed; 45% of the miss scenario remains a limit.
    (Also fixed two latent bugs: rejected hypotheses resurrecting as open on
    reload, and 'supported' hypotheses being dropped from LEARN/BRIDGE.)
  - Teacher draft review workflow: authored questions no longer go live on
    save. New Coverage & Review tab panel lists drafts with status chips;
    a reviewer (one-tap demo entry, or reviewer account) can Approve (records
    reviewer name + attestation, item goes live into the pack) or Reject
    (reason required, item flagged and kept out of the student flow). Role
    guard: teachers get 403 on review endpoints. Reviewer name and decision
    are stored on the item. API: GET /api/review/drafts,
    POST /api/review/drafts/{id}/approve, POST /api/review/drafts/{id}/reject.
  - More draft content: 9 new English practice questions (3 each for simple
    equations, integer add/subtract, fraction basics - previously probe-only
    concepts), every wrong option tagged to a misconception that already has
    a diagnostic probe. All saved "author-drafted, unreviewed" - pack total
    130 questions. Tamil content remains DRAFT pending teacher review.
  - Cold start: /health endpoint (status + honesty notice, no DB touch) plus
    KEEP_WARM.md - a 3-minute guide for YOU to set up a free ping
    (cron-job.org or UptimeRobot) so Render's free tier stays awake. Nothing
    was signed up for on your behalf. In demo mode the backend now auto-seeds
    demo teacher/reviewer accounts on a fresh DB (is_seeded=true, blocked in
    production by the existing FIX 6 safeguard), so the one-tap entries work
    on any demo deploy.

V5 FEATURES (this build)
  - Simulated-classroom benchmark (scripts/setu_classroom_benchmark.py):
    synthetic students with a KNOWN planted gap; measures questions-to-correct-
    gap for Setu (real AdaptiveEngine) vs a fixed-order quiz (current-class
    questions first, prerequisites last). Reports mean/median/stdev/p10/p90 and
    found-rate, deterministic seed, labelled "SIMULATED STUDENTS - NOT REAL
    CHILDREN". On the measured run (200 students, seed 42): planted Class 7 gap
    expressed in errors -> Setu mean 4.2 questions, 90.5% found within 12;
    fixed quiz mean 71. Planted integer gap NOT expressed in the first errors
    -> Setu follows the expressed evidence and misses it within 12 (0%); the
    fixed quiz catches it at mean 81. Both results are reported, not cherry-
    picked.
  - Fitted override learning (scripts/setu_override_fit.py): logistic
    regression (pure stdlib) on SIMULATED override logs, held-out BY CONCEPT
    (80/20, no leakage): accuracy 0.98, AUC 0.999, majority baseline 0.86.
    Labelled SYNTHETIC OVERRIDES; the live engine stays BKT + v4 hand-set
    shrinkage - the fitted model is not wired in.
  - Teacher authoring without code: dashboard form (Teacher dashboard ->
    "Add a question") + POST/PUT/GET /api/teacher/authoring/questions.
    Validated with the same structural rules as the shipped pack (exactly one
    correct option, tags required on wrong options, numeric consistency);
    a brand-new misconception tag without a probe warns but stores. Every
    authored item is saved and served as "author-drafted, unreviewed" and an
    edit bumps its version; structural checks cannot prove the maths is right.
  - Pitch outline refresh (PITCH_OUTLINE.md): one-sentence concept, 8-slide
    flow, evidence slide with every number labelled by source, and a limits
    slide using only measured numbers (incl. the simulation miss disclosed).

V4 FEATURES (this build)
  - Language selector now works end-to-end (bug fix: it used to change only
    question content, leaving every UI string in English). New module
    frontend/src/i18n/uiStrings.js translates the core UI (nav, submit, hint,
    queue/sync, mastery, stage banners, teacher panel). Coverage, honestly:
    English = full (supported). Tamil = equivalent-fractions questions and
    explainers plus the core UI strings, all DRAFT pending teacher review.
    Hindi/Telugu = 11 authored questions each plus core UI strings, DRAFT.
    Anything missing falls back to English with a visible fallback label.
  - Override learning: teacher overrides are logged and now refine the
    STARTING estimate for the NEXT student who begins that concept
    (hand-set targets mark_cleared/close_gap 0.70, reinforce 0.30,
    assign_concept 0.20, averaged with the base prior 0.20 at strength k=4;
    new module backend/app/override_learning.py). The estimate is labelled
    "refined from N teacher overrides (hand-set)" and the teacher dashboard
    shows a visible "learned from N overrides" counter. Not a fitted model.
  - Demo seed: 3 synthetic teacher overrides on equivalent fractions
    (clearly tagged [SYNTHETIC DEMO DATA]) plus student stu_demo_02
    (Tamil medium, equivalent fractions) - the first question arrives at the
    refined estimate (0.36 vs the 0.20 default), so judges can see the
    override loop change the next child's path.
  - Teacher "why": every student in the attention panel now carries an
    evidence line (recent attempts + rule-based evidence band, with
    "hand-set rules, not a diagnosis").
  - Low-bandwidth proof: GET /api/demo/footprint reports the MEASURED byte
    size of the served app script, styles and question pack (shown in the
    footer as [MEASURED on this server build]); attempts made offline queue
    on the device and sync when the network returns (already built, now
    visible in the UI strings).
  - Cold start: the prerendered landing now opens with a "Loading Setu..."
    splash explaining that the free demo server sleeps when idle and the
    first visit can take up to about a minute (hosting, not the network).
  - Bug fix: SM-2 review interval is capped at 365 days (hand-set ceiling);
    uncapped, a long success streak overflowed Python's date range.

V3 FEATURES (this build)
  - Human-in-the-loop: a teacher override now adjusts that concept's starting
    mastery estimate (mark_cleared/close_gap -> at least 0.70; reinforce -> at
    most 0.30), labelled "teacher-adjusted, hand-set" everywhere it appears.
    It only sets the STARTING point; live evidence keeps updating it after.
  - Child-side loop: a wrong answer now returns a short "Why this answer is
    wrong" explainer keyed to the misconception tag (new module
    backend/app/misconception_explainers.py). English for all authored tags;
    Tamil for the demo spine tags marked DRAFT pending teacher review; tags
    without Tamil fall back to English with an honest is_fallback label.
  - Less teacher work: new GET /api/teacher/class/{id}/attention-summary +
    a "Who needs help now" panel on the dashboard: flagged, stuck (2+ in a
    row), bridge-recheck repeat failures and open suspected gaps in one list,
    urgent first, with the caveat "rule-based flags, not diagnoses".
  - Tamil/low-data robustness: engine language fallback (Tamil -> English with
    visible label) already covered by tests; the new explainers follow the
    same fallback contract. BKT needs no training data per child - it starts
    from the labelled hand-set prior and updates from the first attempt.

HONESTY (do not delete - judges can check every line)
  - BKT mastery is labelled "uncalibrated, hand-set" in the UI.
  - Diagnosis trail entries are rule-based hypotheses, never final diagnoses.
  - Tamil items are author-drafted, pending teacher review.
  - Benchmark numbers are US students (ASSISTments 2009), not Tamil Nadu.
