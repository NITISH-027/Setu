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
  Tests:     python -m pytest tests   (expect 115 passed)

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
