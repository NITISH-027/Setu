# Setu (सेतु)
### Teacher-Controlled Adaptive Learning for Classes 6 to 10
*Code Kernel '26 Hackathon Deliverable*

---

> **CRITICAL HONESTY NOTICE & SCOPE STATEMENT**  
> **Demo controls only, not a compliance claim.**  
> - **Core Claim**: Setu finds the likely prerequisite gap behind a wrong answer, with evidence and stated uncertainty, inside an authored concept graph. It adapts Learn, Solve and Test around that gap and keeps the teacher in control. **A wrong answer is a hypothesis, not a diagnosis.**  
> - **Two Distinct Numbers**:  
>   1. **BKT Mastery Estimate**: Per-concept probability with hand-set parameters (prior, learn, guess, slip). Displayed with label: `"uncalibrated, hand-set"`.  
>   2. **Hypothesis Evidence Score**: Rule-based heuristic (supporting probes minus contradicting probes, probe volume). Displayed as Low / Medium / High + raw evidence list, labelled `"heuristic evidence score"`. It is NOT a probability and is NOT derived from BKT.  
> - **Demo Data**: All demo profiles and test records represent **strictly synthetic students**. No real child data is collected, stored, or processed.

---

## Shipped Content Counts & Review Attestation
All shipped items are author-drafted and unreviewed by default in accordance with Hard Rule 5 (human attestation cannot be fabricated by scripts, seeds, or builders).

| Metric | Shipped Count | Status Label |
|---|---|---|
| **Total Concepts** | 20 | 7 Active (Class 8), 13 Spine (Classes 6, 7, 9, 10 labeled `graph-only`) |
| **Questions** | 101 | Active questions and probes across concepts; wrong options tagged |
| **Micro-Lessons** | 39 | Foundational & targeted bridges in English, Hindi drafts, Telugu drafts |
| **Hint Ladders** | 101 | 3-tier ladder (level 1 hint, level 2 partial step, level 3 worked step) per question |
| **Total Items Tracked** | 241 | Questions (101), Lessons (39), Hint Ladders (101) |
| **Human Reviewed Items** | 0 (0.0%) | `author-drafted, unreviewed` (No human review claims fabricated) |
| **Curriculum Alignment** | Intended NCERT | Labeled: *"intended NCERT alignment, unverified until references and content are checked"* |
| **Supported Languages** | 1 (`en`) | Hindi and Telugu drafts included as unreviewed drafts |

---

## Strict Authentication & Public Routes List
All API routes require a valid authenticated Bearer session token scoped by role and tenant, with all unauthenticated session fallbacks permanently removed.

**Exclusively Public Routes**:
1. `GET /health` — Service health probe.
2. `GET /api/pack` — Public concept spine and content pack metadata. **Strictly answer-free** (contains no `is_correct`, misconception tags, or worked solutions).
3. `POST /api/auth/login` — Teacher, Admin, and Reviewer credential sign-in.
4. `POST /api/auth/student-pin-login` — Student pseudonymous ID and salted PIN sign-in.

*All other routes require valid authenticated session tokens. Anonymous requests return HTTP 401; cross-class or wrong-role requests return HTTP 403; malformed bodies return HTTP 422.*

---

## Offline Engine & Answer Keys Tradeoff
Setu provides an offline-first architecture for rural and low-connectivity schools:
1. **Separation of Surfaces**:
   - Online learning endpoints (`GET /api/student/{id}/next-step`) never return answers or misconception tags. Correctness is provided only after grading.
   - Offline learning downloads a dedicated, authenticated pack via `GET /api/student/{id}/offline-pack` (restricted to the authenticated student's assigned class).
2. **Deliberate Tradeoff & Honest Threat Model**:
   - Because offline grading occurs entirely on-device via the client-side JavaScript engine (`frontend/src/engine`), the offline pack stored in IndexedDB contains answer keys.
   - These keys are stored in IndexedDB and never rendered into the DOM.
   - **We state plainly that this is NOT secure against a student**: a determined student with physical access and browser devtools can inspect IndexedDB and view answer keys.
   - **Authoritative Server Guard**: Upon reconnection and sync, the server unconditionally re-grades every queued attempt against the authoritative server database. The server's calculated mastery replaces the local estimate.

---

## Deletion Boundaries, Offline Devices & Tombstones
- **Scope of Deletion**:  
  When a student is deleted on the server, the app purges records across `StudentDB`, `PlanDB`, `MasteryStateDB`, `HypothesisDB`, `AttemptDB`, `DecisionDB`, `PinProfileDB`, `SessionDB`, and `DeviceDB`. Any lingering teacher override logs are sanitized to `[PURGED]`.
- **Limits Outside the App**:  
  Deletion cannot recall data outside the app's boundary (e.g., offline backup files, previously downloaded CSV reports, or rotating server database backup snapshots until their stated retention expires).
- **Offline Devices & Tombstones**:  
  Offline mobile devices cannot receive instant deletion notifications while disconnected. The server records an opaque tombstone key (a random token holding **zero student IDs, zero names, and zero learning payloads**) and displays the pending state: `"Deletion pending, not yet applied on N devices"`.  
  The system **never claims 'all stores deleted' while any tombstone is pending**.  
  When an offline device reconnects, it applies the tombstone, purges local stores and queues, and blocks stale attempts from resurrecting the student. If an expired device connects after a tombstone has been purged (or after 30 days of inactivity), its local store is **reset rather than merged**.

---

## Prerequisites & System Requirements
- **Python**: **Python 3.11 or newer** is strictly required (`numpy 2.4.6` and `scipy 1.17.1` wheel metadata declares `Requires-Python >= 3.11`). The script `scripts/verify_fresh_install.py` checks the interpreter version before running.
- **Node.js**: Node.js 18.0 or newer.
- **Browser**: Google Chrome / Chromium for Playwright browser-level E2E tests.

---

## Quickstart & Complete Test Verification

### 1. Fresh Installation & Environment Verification
```bash
python scripts/verify_fresh_install.py
```
Checks Python interpreter (>= 3.11), verifies dependencies, executes backend tests, builds the frontend bundle, and runs JS/Python engine parity.

### 2. Run Complete Backend & Integration Tests
```bash
python -m pytest tests/ -v
```

### 3. Run Negative-Control Auth Probes
```bash
python scripts/negative_control_auth_probes.py
```

### 4. Run JavaScript Engine Parity Tests (42 Primitive Parity Assertions)
Verifies mathematical and algorithmic logic parity for engine primitives (BKT, SM-2, sequencer, hypothesis) between Python and JavaScript engines; does not claim complete UI parity:
```bash
cd frontend && npm run test:parity
```

### 5. Run Real Browser E2E & Offline Playwright Suite (14 Shipped Browser Tests)
```bash
cd frontend && npx playwright test
```
Executes the shipped browser test suite (14 browser tests across acceptance journeys, mobile viewports, and offline flows) against the real FastAPI backend and Vite preview server on fresh SQLite test database:
- `acceptance_journeys.spec.js`: Tests A through L covering the full learning journey, stuck override, fast learner, teacher bulk entry, student data export, and content editor schema validator.
- `layout_and_tabs.spec.js`: Rendered layout and 0 horizontal overflow across all 5 tabs at 360px and 390px.
- `e2e.spec.js`: Mobile navigation and viewports at 360px and 390px.
- `offline_deletion_device.spec.js`: Real browser student deletion flow — student A signs in online on Device 1, caches data, goes offline, deleted via real teacher route, reconnects with purge-only token, IndexedDB wiped, offline sign-in fails, acknowledged on server, and second device unaffected.
- `offline_flow.spec.js`: Comprehensive 10-step offline lifecycle (online login -> offline disconnect -> reload -> offline login -> 3 questions answered & graded locally via JS engine -> IndexedDB reload persistence -> reconnect & authoritative server sync).
- `reset_wipe.spec.js`: Stale/unregistered device RESET response causing complete client IndexedDB wipe.

### 6. Generate Clean Submission ZIP (Verified, Excluded Paths Checked)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/package.ps1
```
Or with Python:
```bash
python scripts/build_submission_zip.py
```
Or on Linux:
```bash
bash scripts/package.sh
```

---

## Key Documentation Files
- [`STATUS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/STATUS.md): Every requirement mapped to proving test and **Evidence Class** (`browser-e2e`, `api-integration`, `unit`, `simulation-only`, `manual-unverified`).
- [`TEST_RUN.md`](file:///d:/PROJECT_SOUCEFILE/Setu/TEST_RUN.md): Full terminal output from the latest clean test run.
- [`DECISIONS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DECISIONS.md): Architectural decisions and deliberate tradeoffs.

- [`DECISIONS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DECISIONS.md): Architectural decisions, including minimal student metadata.
- [`DEMO_SCRIPT.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DEMO_SCRIPT.md): 3-minute presentation script using strictly synthetic demo students.

