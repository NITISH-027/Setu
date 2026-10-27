# Architectural & Design Decisions (DECISIONS.md)

This log records architectural decisions, departures from earlier drafts, and constraints for the Setu project.

---

### DEC-001: Minimal Student Metadata & Departure from Round 1
- **Context**: Round 1 documentation mentioned collecting first name, class, and school.
- **Decision**: The demo intentionally departs from collecting first names or school names. Allowed student fields are strictly limited to:
  `pseudonymous_id`, `class_id` (class and section), `board`, `medium_language`, `pin_hash`, `created_at`, `consent_status`.
- **Rationale**: Minimal operational metadata is sufficient to demonstrate adaptive learning, diagnostic tracing, and teacher controls without creating privacy risks. In a real deployment, a teacher-held pseudonym/alias map would be kept by the school offline if needed.
- **Reference**: Prompt Part 3 ("Data Protection").

---

### DEC-002: Core Stack Selection
- **Frontend**: React (Vite) Single Page Application / Progressive Web App (PWA) with Vanilla CSS (no Tailwind, per user preferences and clean bundle footprint), Native/IDB IndexedDB storage for offline persistence.
- **Backend**: Python 3.11 + FastAPI with Uvicorn.
- **Database**: SQLite for local development and test suite execution; PostgreSQL schema compatibility supported via SQLAlchemy/SQLModel abstractions.
- **Models**: Pure Python implementations of concept graph traversal, Bayesian Knowledge Tracing (BKT), rule sequencer, and SM-2 spaced repetition scheduler. No GPU dependencies. No runtime external AI API calls required.
- **Rationale**: Meets low-resource requirements, rapid testability, fully reproducible offline execution, and deployment flexibility for Indian school contexts.

---

### DEC-003: Two Distinct Numbers Principle
- **Decision**: BKT mastery estimate and Hypothesis Evidence Score must never be confused or conflated.
  1. **BKT Mastery Estimate**: Per-concept probability modeled with hand-set parameters (prior, learn, guess, slip). Displayed with label: `"uncalibrated, hand-set"`.
  2. **Hypothesis Evidence Score**: Rule-based heuristic score based on probe evidence (supporting probes minus contradicting probes, probe volume). Displayed as `Low`, `Medium`, or `High` plus raw evidence list, labelled `"heuristic evidence score"`. It is NOT a probability and is not derived from BKT.
- **Rationale**: Prevents false appearance of mathematical precision; forces transparency when evidence is thin or conflicting.

---

### DEC-004: Content Review Provenance & Attestation
- **Decision**: No script, seed tool, import process, AI drafting tool, or automated builder process may set an item's review status to `reviewed`.
- **Rule**:
  - Review status defaults to `author-drafted, unreviewed`.
  - Marking `reviewed` requires an explicit human attestation record (reviewer name, role/qualification, timestamp, item version, and statement).
  - Editing an item after review immediately resets status to `unreviewed` or flags it as `changed since review`.
  - Imported records claiming `reviewed` are automatically downgraded to `unverified import` unless cryptographic or verified provenance against registered reviewer accounts exists.

---

### DEC-005: Privacy-Preserving Deletion & Tombstone Protocol
- **Decision**: Deletion removes student learning records from server database and queues a tombstone.
- **Tombstone Key**: An opaque one-way key (hash or random token) with timestamp and status. Contains no PII, no student ID, and no learning payloads.
- **Offline Sync**: Offline devices apply the tombstone during sync, purge local records and queued writes, and are blocked from re-uploading stale records. If a tombstone has expired and been purged from the server, any late-connecting device has its local class store reset rather than merged.
- **Audit Log**: Audit logs only log action type, acting user/system, class, timestamp, and record count. No student IDs, answers, or learning payloads are ever logged.

---

### DEC-006: Intended NCERT Alignment & Syllabus Honesty
- **Decision**: Class 8 CBSE Mathematics pack is authored with intended NCERT alignment. It is explicitly labelled: `"intended NCERT alignment, unverified until references and content are checked"`. Nodes in Classes 6, 7, 9, 10 without questions are clearly labelled `"graph-only"`.
