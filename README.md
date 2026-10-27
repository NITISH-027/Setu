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
| **Questions** | 39 | Direct probes for all 5 active Class 8 concepts; wrong options tagged |
| **Micro-Lessons** | 19 | English foundational & targeted bridges; draft unreviewed Hindi/Telugu |
| **Hint Ladders** | 39 | 3-tier ladder (level 1 hint, level 2 partial step, level 3 worked step) |
| **Total Items Tracked** | 97 | Questions, Lessons, Hint Ladders |
| **Human Reviewed Items** | 0 (0.0%) | `author-drafted, unreviewed` (No human review claims fabricated) |
| **Curriculum Alignment** | Intended NCERT | Labeled: *"intended NCERT alignment, unverified until references and content are checked"* |
| **Supported Languages** | 1 (`en`) | Hindi (`hi`) and Telugu (`te`) included as unreviewed drafts only |

---

## What Code Cannot Settle
The following critical dimensions cannot be proven or resolved through code, automated tests, or simulations alone. Each requires real-world empirical deployment, qualified educators, or human reviewers:

1. **Classroom Calibration of BKT and SM-2 Spaced Intervals**:  
   BKT parameters and repetition intervals are hand-set and untuned. Demonstrating that parameter recovery works on synthetic sequences does not substitute for empirical calibration against actual student retention and error curves across Indian classrooms.
2. **Learning-Gain Effectiveness**:  
   This codebase does not and cannot claim proven learning gains, accelerated mastery, or guaranteed grade improvements. Evaluating pedagogy requires controlled longitudinal classroom studies.
3. **Teacher Validation of Misconception Tags and Lessons**:  
   Automated validators verify structural integrity (DAG acyclicity, option tags, probe existence). They cannot judge pedagogical clarity, semantic ambiguity, age-appropriateness, or whether a misconception tag represents the genuine root of a child's mistake.
4. **School-Ready Consent and Retention Policies**:  
   The provided consent workflow (`not requested`, `requested`, `recorded`) and configurable retention schedules provide working demonstration controls only. They do not constitute an operational or institutional data agreement.
5. **Legal & Regulatory Compliance**:  
   No statute (such as DPDP Act, GDPR, or state school regulations) is claimed as satisfied. A real pilot involving children is blocked until:  
   *(a)* Applicable child-data privacy laws and individual school district requirements are formally evaluated;  
   *(b)* Guardian consent is recorded and verified under that process; and  
   *(c)* Qualified legal counsel conducts a comprehensive review.
6. **Hindi, Telugu, and Multi-Board Validity**:  
   Multilingual translations are drafts marked `"unreviewed"`. A language only counts as supported when verified by two human attestations (a fluent native speaker and a mathematics subject reviewer). Similarly, other boards (e.g., ICSE, State Boards) require official syllabus mappings and human subject review.

---

## Deletion Boundaries, Offline Devices & Tombstones
- **Scope of Deletion**:  
  When a student is deleted on the server, the app purges records across `StudentDB`, `PlanDB`, `MasteryStateDB`, `HypothesisDB`, `AttemptDB`, `DecisionDB`, and `PinProfileDB`. Any lingering teacher override logs are sanitized to `[PURGED]`.
- **Limits Outside the App**:  
  Deletion cannot recall data outside the app's boundary (e.g., offline backup files, previously downloaded CSV reports, or rotating server database backup snapshots until their stated retention expires).
- **Offline Devices & Tombstones**:  
  Offline mobile devices cannot receive instant deletion notifications while disconnected. The server records an opaque tombstone key (a random token holding **zero student IDs, zero names, and zero learning payloads**) and displays the pending state: `"Deletion pending, not yet applied on N devices"`.  
  The system **never claims 'all stores deleted' while any tombstone is pending**.  
  When an offline device reconnects, it applies the tombstone, purges local stores and queues, and blocks stale attempts from resurrecting the student. If an expired device connects after a tombstone has been purged (or after 30 days of inactivity), its local store is **reset rather than merged**.

---

## Quickstart & Complete Test Verification

### 1. Fresh Install Verification
```bash
python scripts/verify_fresh_install.py
```
Verifies python virtualenv dependencies and system prerequisites.

### 2. Backend & Integration Tests (65 passed)
```bash
python -m pytest tests/ -v
```
Executes all 65 automated tests covering SQLAlchemy persistence across restarts, Argon2 password verification, role/class scoping, server-side grading spoof rejection, zero-trace tombstone deletion, BKT update equations, and declarative sequencer rules.

### 3. JavaScript Engine Parity Tests (40 passed)
```bash
cd frontend && npm run test:parity
```
Verifies exact numerical and logical equivalence between Python and client-side JavaScript BKT, SM-2, Hypothesis, and Sequencer engines using `packs/golden_test_vectors.json`.

### 4. Real Browser E2E Phone Layout Tests (Playwright Chromium)
```bash
cd frontend && npm run test:e2e
```
Launches real headless Chromium to verify unclipped layouts and zero horizontal overflow at 360px and 390px (iPhone) viewports, generating authentic visual proofs in `screenshots/`:
- `screenshots/mobile_360px.png`
- `screenshots/mobile_390px.png`
- `screenshots/student_solve_flow.png`
- `screenshots/teacher_dashboard.png`

---

## Key Documentation Files
- [`STATUS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/STATUS.md): Every requirement mapped to proving test and **Evidence Class** (`browser-e2e`, `api-integration`, `unit`, `simulation-only`, `manual-unverified`).
- [`TEST_RUN.md`](file:///d:/PROJECT_SOUCEFILE/Setu/TEST_RUN.md): Full terminal output from the latest clean test run.
- [`DECISIONS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DECISIONS.md): Architectural decisions, including minimal student metadata.
- [`DEMO_SCRIPT.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DEMO_SCRIPT.md): 3-minute presentation script using strictly synthetic demo students.

