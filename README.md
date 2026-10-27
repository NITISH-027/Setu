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
| **Questions** | 32 | Structural checks passed; every wrong option tagged; probes provided |
| **Micro-Lessons** | 19 | English foundational & targeted bridges; draft unreviewed Hindi/Telugu |
| **Hint Ladders** | 32 | 3-tier ladder (level 1 hint, level 2 partial step, level 3 worked step) |
| **Total Items Tracked** | 83 | Questions, Lessons, Hint Ladders |
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
  When a student is deleted on the server, the app removes the pseudonym mapping, attempts, hypotheses, plans, overrides, and held exports from server databases and active stores.
- **Limits Outside the App**:  
  Deletion cannot recall data outside the app's boundary (e.g., offline backup files, previously downloaded CSV reports, or rotating server database backup snapshots until their stated retention expires).
- **Offline Devices & Tombstones**:  
  Offline mobile devices cannot receive instant deletion notifications while disconnected. The server records an opaque tombstone key (a random token holding **zero student IDs, zero names, and zero learning payloads**) and displays the pending state: `"Deletion pending, not yet applied on N devices"`.  
  The system **never claims 'all stores deleted' while any tombstone is pending**.  
  When an offline device reconnects, it applies the tombstone, purges local stores and queues, and blocks stale attempts from resurrecting the student. If an expired device connects after a tombstone has been purged, its local store is **reset rather than merged**.

---

## Design Assumptions (Users & Cadence)
These are engineering design assumptions, not empirical findings:
- **Students**: 10 to 15-minute bite-sized sessions on shared family mobile phones 3-4 times per week.
- **Teachers**: Open the weekly class dashboard once a week to review grouped shared gaps and run targeted 10-minute remedial clinics.
- **Remedial Records**: Gap-closed records generated on demand for parent communication and school planning.

---

## Quickstart & Verification

### 1. Run Automated Test Suite (Single Command)
```bash
python scripts/run_all_tests.py
```
Executes all 59 unit and integration tests across data models, validators, the adaptive engine, teacher controls, data protection, offline PWA flows, simulations, and hold-out tests.

### 2. Run Round 3 Hold-Out Test (Data-Only Adaptation)
```bash
python scripts/run_holdout_test.py
```
Validates that unseen questions and custom rules injected purely via data function immediately with zero code changes.

### 3. Run Backend Server
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```
Interactive API documentation available at `http://localhost:8000/docs`.

### 4. Run Frontend PWA
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` to access the interactive PWA interface.

---

## Architectural Decisions & Departures
Detailed architectural decisions, including our deliberate departure from Round 1 regarding collecting student first names or school names, are documented in [`DECISIONS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/DECISIONS.md).  
Every requirement status and its corresponding proving test are tracked in [`STATUS.md`](file:///d:/PROJECT_SOUCEFILE/Setu/STATUS.md).
