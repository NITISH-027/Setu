# 🌉 Setu (सेतु)

### Teacher-Controlled Adaptive Learning for Classes 6–8 Maths

[![Live Demo](https://img.shields.io/badge/demo-live_on_Render-brightgreen)](https://setu-demo-3ogx.onrender.com)
![Backend Tests](https://img.shields.io/badge/backend_tests-131-brightgreen)
![Engine Parity](https://img.shields.io/badge/JS--Python_engine_parity-42_assertions-brightgreen)
![Browser E2E](https://img.shields.io/badge/browser_E2E-14_journeys-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![React](https://img.shields.io/badge/react-18-61dafb)
![FastAPI](https://img.shields.io/badge/fastapi-0.141-009688)
![Offline First](https://img.shields.io/badge/PWA-offline--first-orange)
![External AI API](https://img.shields.io/badge/external_AI_API-none-lightgrey)

> 🏆 **Finalist — CodeQuest: National Tech Hackathon 2026** · Final Build & Innovation Showcase

---

## 🔗 Try It Right Now

| Link | Where |
|---|---|
| 🌐 **Live demo** | **https://setu-demo-3ogx.onrender.com** |
| 🎓 **Student app** | Open the demo → *Student App* → tap a student (no PIN needed in demo mode) |
| 👩‍🏫 **Teacher dashboard** | Open the demo → *Teacher Dashboard* → one-tap teacher entry |
| 🗺️ **Guided tour** | A 3-minute clickable judge tour is built into the landing page |

> ⏳ **Cold-start note:** the demo runs on a free server that sleeps when idle. The first visit can take up to about a minute to wake — that is hosting, not the app.

---

## 💡 What Is Setu?

In a government-school classroom of 40 students, one teacher cannot find out *why* each child is stuck. A wrong answer in Class 8 algebra is very often a Class 6 fraction gap in disguise.

**Setu (सेतु = bridge)** watches how a student answers, forms a *hypothesis* about the hidden prerequisite gap, proves or rejects it with diagnostic probes, teaches a short bridge lesson in the student's language, and only then returns to the original topic. The teacher stays in control the whole time.

---

## 🔁 The Adaptive Loop

```
❌ Wrong answer
   │
   ▼
🧠 Hypothesis — "maybe the gap is <prerequisite concept>" (never a diagnosis)
   │
   ▼
🧪 Diagnostic probes — prove or reject the hypothesis with evidence
   │
   ▼
📖 Bridge micro-lesson — short, in the student's language, with a 3-tier hint ladder
   │
   ▼
✏️ Practice + re-check
   │
   ▼
🔁 Transfer question — same idea, new format, so parroting does not count
   │
   ▼
🚀 Back to the original topic — fast learners move ahead at 85% mastery
```

Every step leaves a visible trail — the student can literally **"Watch Setu think"**, and the teacher sees the same evidence on their dashboard.

---

## ✨ Features

### 🎓 For the Student

- 🧭 **Adaptive Learn / Solve / Test flow** — every wrong answer routes to a diagnosed prerequisite gap, not just "try again"
- 🔗 **Prerequisite-chain probing** — if the first hypothesis is rejected but the student *passes* its probe, Setu probes the next prerequisite in the chain instead of giving up
- 💬 **"Why this answer is wrong"** — a misconception explainer keyed to the exact wrong option the student picked
- 🪜 **3-tier hint ladder on every question** — hint → partial step → worked step
- 🌐 **Language switching end-to-end** — English (full), Tamil / Hindi / Telugu (**unreviewed drafts**, visibly labelled, with labelled English fallback)
- 📴 **Offline-first PWA** — lessons and questions keep working with no network; answers queue on the device and sync later
- 🕒 **Spaced repetition (SM-2)** — review scheduling with a hand-set 365-day ceiling

### 👩‍🏫 For the Teacher

- 🚨 **"Who needs help now"** — one attention panel: flagged, stuck, repeat-failures and open suspected gaps, urgent first
- 👥 **Shared-gap clinics** — students with the same confirmed gap are grouped, with a suggested 10-minute clinic
- ✋ **One-tap quick check** — got-it / not-yet becomes one mastery observation per student
- 🛠️ **Overrides that teach the system** — teacher overrides adjust the *starting* estimate for the next student on that concept (hand-set rule, visibly labelled)
- ✍️ **Author questions without code** — dashboard form with structural validation (exactly one correct option, misconception tags required)
- ✅ **Reviewer approval workflow** — authored drafts never go live until a reviewer approves them; teachers get 403 on review endpoints
- 📝 **Paper-mode bulk entry** — marks from paper tests enter in bulk and update mastery

### 🛡️ Platform & Trust

- 🔐 **Strict authentication** — only 4 public routes (`/health`, `/api/pack`, teacher login, student PIN login); everything else returns 401/403/422 correctly
- 🗑️ **Real child-data deletion** — purges across 9 stores with opaque tombstones for offline devices; the app never claims "all deleted" while a tombstone is pending
- ⚖️ **Authoritative server re-grade** — offline answers are graded on-device, then unconditionally re-graded by the server on sync (the offline answer-key tradeoff is disclosed, not hidden)
- 📦 **Low-bandwidth by design** — `/api/demo/footprint` reports the *measured* byte size of the served app
- 🤖 **No external AI API** — the engine is Bayesian Knowledge Tracing + a misconception-tagged prerequisite graph + rule-based sequencing. Explainable, offline-capable, zero per-query cost.

---

## 📊 Content Pack (verified from [`packs/cbse_math_pack.json`](packs/cbse_math_pack.json))

| 📦 Item | Count | Detail |
|---|---|---|
| 🧩 Concepts | **21** | 8 active (7 × Class 8 + 1 × Class 7) · 13 graph-only spine (Classes 6–10) |
| ❓ Questions | **130** | 98 English · 11 Hindi · 11 Telugu · 10 Tamil (drafts) |
| 📚 Micro-lessons | **41** | 18 English · 11 Hindi · 11 Telugu · 1 Tamil (drafts) |
| 🪜 Hint ladders | **101** | 3 tiers per question |
| 🏷️ Wrong options tagged | **253 / 253** | every wrong option carries a misconception tag |
| 🔗 Prerequisite edges | **20** | the graph the engine reasons over |
| 👁️ Human-reviewed items | **0 (0%)** | everything ships as `author-drafted, unreviewed` — no review claim is fabricated |

---

## ⚖️ Honesty & Scope (read before judging)

| ✅ Setu **is** | ⛔ Setu is **not** |
|---|---|
| A working prototype that finds the *likely* prerequisite gap behind a wrong answer, with evidence and stated uncertainty | A diagnosis — a wrong answer is a **hypothesis**, never a final verdict |
| A BKT mastery estimate with **hand-set** parameters, labelled `uncalibrated, hand-set` everywhere it appears | A model fitted to real students |
| A rule-based **hypothesis evidence score** (Low / Medium / High + raw evidence) | A probability — it is not derived from BKT |
| Demo profiles of **strictly synthetic students** | Real child data — none is collected |
| Prototype content: Class 8 CBSE Maths active, Class 6–7 prerequisites in the graph, spine to Class 10 | Classroom-validated or school-ready content |
| English fully supported; Tamil / Hindi / Telugu as **unreviewed drafts** | A finished multilingual product |
| Benchmarked on **simulated students** and a public US dataset (ASSISTments 2009) | Tested on real Tamil Nadu classrooms — yet |

Every one of these lines is checkable in the code and in [`STATUS.md`](STATUS.md).

---

## 🧱 Tech Stack

| Layer | Choice | Why |
|---|---|---|
| 🖥️ Frontend | React 18 + Vite, installable PWA | offline-first, low-end Android friendly |
| ⚙️ Backend | Python 3.11+ · FastAPI · Uvicorn | typed, fast, easy to audit |
| 🧠 Engine | BKT + hypothesis engine + graph tracer + rule sequencer + SM-2 | explainable adaptation, no black box |
| 🪞 Engine parity | Same engine in JS (`frontend/src/engine`) with 42 parity assertions | offline grading matches the server |
| 🗄️ Database | SQLite (dev) → Postgres via `DATABASE_URL` (deploy) | zero-config locally, durable in production |
| 📴 Offline storage | IndexedDB + background sync queue | rural, low-connectivity classrooms |
| 🔑 Auth | Argon2 teacher passwords, salted student PINs, role + class scoping | shared-device classrooms |

## 🏗️ Architecture

```
┌────────────────────────────┐        HTTPS / JSON        ┌─────────────────────────────┐
│  📱 React PWA (Vite)       │ ◄────────────────────────► │  ⚙️ FastAPI backend          │
│  ├─ Student / Teacher /    │                            │  ├─ Adaptive engine           │
│  │  Reviewer views         │                            │  │  (BKT · hypotheses · graph) │
│  ├─ JS engine mirror       │                            │  ├─ Authoritative grading      │
│  └─ IndexedDB offline queue│                            │  └─ Deletion & tombstones      │
└────────────────────────────┘                            └──────────────┬──────────────┘
                                                                          │
                                                          🗄️ SQLite (dev) / Postgres (deploy)
```

---

## 🚀 Quickstart

**Prerequisites:** Python **3.11+**, Node.js **18+**

```bash
# 1️⃣ Clone and verify your environment end to end
git clone https://github.com/NITISH-027/Setu.git
cd Setu
python scripts/verify_fresh_install.py

# 2️⃣ Backend
cd backend
pip install -r requirements.txt

# 3️⃣ Seed demo data (first time only, prints demo credentials ONCE)
python ../scripts/seed_demo_data.py

# 4️⃣ Run with one-tap demo mode
#    Windows PowerShell:
$env:SETU_DEMO_MODE="true"; uvicorn app.main:app --port 8000
#    Linux / macOS:
SETU_DEMO_MODE=true uvicorn app.main:app --port 8000

# 5️⃣ Frontend (new terminal)
cd frontend
npm install
npm run build        # the backend serves frontend/dist automatically

# 6️⃣ Open http://localhost:8000
```

> 🎭 **Demo mode** (`SETU_DEMO_MODE=true`) gives one-tap student and teacher entry with synthetic profiles. It is **OFF by default**. Demo profiles reset to their seeded state on logout or session expiry (2-hour cap); real PIN accounts are never touched.

---

## ✅ Tests & Verification

| Suite | Command | Count |
|---|---|---|
| 🐍 Backend + integration | `python -m pytest tests/` | **131 tests** |
| 🪞 JS ↔ Python engine parity | `cd frontend && npm run test:parity` | **42 assertions** |
| 🌐 Real-browser journeys (Playwright) | `cd frontend && npx playwright test` | **14 journeys** — full learning loop, offline lifecycle, deletion propagation, 360px/390px layouts |
| 🕵️ Negative-control auth probes | `python scripts/negative_control_auth_probes.py` | **9 probes** — 401 / 403 / 422, zero answer leak |

📸 The [`screenshots/`](screenshots/) folder holds captured E2E evidence, including the full 12-step offline → sync → deletion flow.

---

## 📈 Benchmarks (all labelled, nothing cherry-picked)

Simulated classroom — 200 **synthetic** students, seed 42, [`scripts/setu_classroom_benchmark.py`](scripts/setu_classroom_benchmark.py):

| Scenario | Setu finds the gap | Fixed-order quiz |
|---|---|---|
| Class 7 gap **expressed** in the student's errors | ✅ **97.5%** within 12 questions (mean 4.3) | mean 71 questions |
| Integer gap **not expressed** in the first errors | ⚠️ **55%** within 12 questions (mean 5.6) | mean 84 questions |

The 45% miss in the second scenario is a **disclosed limit**: Setu follows expressed evidence, and a gap the student never shows cannot be detected.

Also included: [`scripts/setu_ml_benchmark.py`](scripts/setu_ml_benchmark.py) fits BKT on the public **ASSISTments 2009** dataset and prints a measured comparison (downloads ~83 MB of public data itself; quote only your own run, labelled `[MEASURED on my run]`).

---

## 📂 Repo Map

| Path | What lives there |
|---|---|
| [`backend/app/`](backend/app/) | FastAPI app + adaptive engine (`engine/`), authoring, teacher, privacy, i18n |
| [`frontend/src/`](frontend/src/) | React PWA views + JS engine mirror + IndexedDB storage |
| [`packs/`](packs/) | The authored content pack (concepts, questions, lessons, hints) |
| [`tests/`](tests/) | 131 backend / integration / simulation tests |
| [`scripts/`](scripts/) | Install verification, seeding, benchmarks, packaging |
| [`screenshots/`](screenshots/) | E2E visual evidence |

## 📚 Documentation

| File | Contents |
|---|---|
| 📋 [`STATUS.md`](STATUS.md) | Every requirement mapped to its proving test and evidence class |
| 🧪 [`TEST_RUN.md`](TEST_RUN.md) | Full output of a clean verification run |
| 🧭 [`DECISIONS.md`](DECISIONS.md) | Architectural decisions and deliberate tradeoffs |
| 🎬 [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | 3-minute demo script using synthetic students |
| 🗺️ [`PLAN.md`](PLAN.md) · [`PITCH_OUTLINE.md`](PITCH_OUTLINE.md) | Build plan and pitch outline |
| 🔥 [`KEEP_WARM.md`](KEEP_WARM.md) | 3-minute guide to keep the free Render demo awake |
| 📦 [`README_ROUND3.txt`](README_ROUND3.txt) | Round-by-round feature changelog (v3 → v6) |

---

## ⚠️ Known Limits

- 🧮 Mastery parameters are **hand-set**, not fitted to real students.
- 📚 Content is prototype-grade and **0% human-reviewed**; NCERT alignment is intended, not verified.
- 🌐 Tamil / Hindi / Telugu content and UI strings are **unreviewed drafts**.
- 🔓 Offline answer keys sit in IndexedDB — not secure against a determined student with devtools; the server's authoritative re-grade is the guard.
- 💤 Free-tier demo hosting sleeps when idle (first load up to ~1 minute).

## 🛣️ Future Scope

- 🧑‍🏫 Human teacher review of the full pack and the draft languages
- 🏫 A real classroom pilot to calibrate BKT parameters
- ➕ More subjects and Classes 6–8 breadth beyond the active Class 8 set
- 📊 Fitted models replacing hand-set rules once real (consented) data exists

---

## 👤 Author

Built by **Nitish Prabagaran** · 2nd-year CSE, Panimalar Engineering College, Chennai
💻 GitHub: [@NITISH-027](https://github.com/NITISH-027)
