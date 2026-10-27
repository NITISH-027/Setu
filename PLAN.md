# Setu Implementation Plan

## Architecture & Principles
- **Core Claim**: Setu finds the likely prerequisite gap behind a wrong answer, with evidence and stated uncertainty, inside an authored concept graph. A wrong answer is a hypothesis, not a diagnosis.
- **Rule Enforcement**:
  - No claims of proven diagnosis, calibrated accuracy, compliance, or learning gains.
  - Clear separation between (1) hand-set BKT mastery estimate and (2) heuristic evidence score (Low/Medium/High + raw evidence).
  - Human-only review attestation for content (author-drafted, flagged, reviewed).
  - Demo data uses strictly synthetic students. Minimal metadata: pseudonymous_id, class_id, board, medium_language, pin_hash, created_at, consent_status.
  - Rigorous data controls: tombstone lifecycle, audit log (counts/actions only, zero PII/payload), clean deletion.

---

## Build Order

### Phase 1: Data Model and Pack Schema
- Schemas for Concepts, PrerequisiteEdges, Questions, Options with misconception tags, Lessons, Hints, ReviewRecords.
- Schemas for Student (pseudonymous, minimal fields), Attempt, Hypothesis, MasteryState, TeacherOverride, Plan, Tombstone, AuditEvent.
- Pack format definition (JSON/YAML) with versioning, board, class, subject, language, and review records.
- Initial pack data: CBSE Class 8 Maths with spine reaching Class 6-7 prerequisites ("intended NCERT alignment, unverified until references and content are checked"). Graph-only nodes for Classes 6, 7, 9, 10.
- Draft Hindi and Telugu translations marked "unreviewed".
- Unit tests for models and serialization.

### Phase 2: Validator and Coverage Report
- Structural integrity checks:
  - Every wrong option has a valid misconception tag.
  - No dangling prerequisites; acyclic graph verification.
  - Every tagged misconception has at least one probe.
  - Recomputation verification for numeric options/answers.
  - Duplicate / near-duplicate option detection.
- Human review rule enforcement:
  - Scripts/imports cannot set review status to `reviewed`.
  - Imported records claiming `reviewed` without verified provenance downgraded to `unverified import`.
  - Modifying an item resets review status or flags as `changed since review`.
- Coverage reporter (uncovered concepts, missing probes/lessons, unused tags, unreviewed counts).
- Web editor/API for content authoring & reviewer attestation flow.

### Phase 3: Engine
- **Diagnose**: Wrong answer initiates a Hypothesis with heuristic evidence score (Low, no immediate gap declared).
- **Probe**: Prerequisite probe selection; conflicting or thin evidence produces "not sure" and requests more probes.
- **Trace**: Graph traversal to earliest supported gap; reaches lower classes when supported.
- **BKT Engine**: Pure-Python Bayesian Knowledge Tracing with hand-set, uncalibrated parameters (prior, learn, guess, slip).
- **Learn & Solve**: Micro-lesson selection, hint ladder (hint -> partial step -> full worked step), difficulty adjustment, 2 stuck attempts raise teacher flag.
- **Test & Bridge Re-check**: Adaptive post-bridge check; pass returns to original topic, fail stays on gap, repeated fails flag teacher.
- **Sequencer**: Data-driven declarative rule engine (JSON/YAML rules, plain-language "why this question" explanation). Changing rule data changes behavior without code edits.
- **SM-2 Spacing**: Spacing intervals (documented as untuned/unvalidated).

### Phase 4: Teacher System
- Grouped class view by shared gap with explicit uncertainty ("not sure" students grouped separately under undecided).
- Suggested ~10-minute clinic groups.
- Override capability for any decision/plan/gap status with mandatory logged reason.
- Gap-closed record generation for remedial planning.
- Class-scoping isolation (negative tests: teacher cannot read other classes).
- Teacher override rate metrics computation.

### Phase 5: Data Protection & Consent
- Minimal student metadata schema enforcement.
- Delete-student endpoint: server store purge, tombstone generation with opaque key (no PII, no learning payload).
- Offline device tombstone propagation: pending status visible, local cache purge on sync, stale device reset if tombstone expired.
- Configurable retention job with audit trail.
- Privacy-safe audit log: event type, teacher/system actor, class, timestamp, record count (no answers, no payload, no student IDs).
- Consent workflow schema with states: `not requested`, `requested`, `recorded` (never auto-marked).

### Phase 6: PWA, Offline, PIN, Languages, Paper Mode
- FastAPI backend serving API and pack distribution.
- React (Vite) PWA frontend:
  - IndexedDB offline storage for student attempts and sync queue.
  - PIN authentication with hashing, sibling switching on shared devices, lockout after failed attempts, no PIN logging.
  - Phone-width responsive UI with low bundle footprint.
  - Externalized i18n with visible fallback to English when translations are missing.
  - Paper mode: printable question set generation from pack and bulk teacher response entry.

### Phase 7: Simulation, Parameter Fitting, Sensitivity
- Synthetic student learner harness with known parameter profiles and planted misconceptions.
- Simulation reports: gap identification rate, failure cases with deterministic seeds.
- Pure-Python BKT parameter fitting module from synthetic logs with recovery error tests.
- Sensitivity analysis module across prior ranges.
- Held-out question set reserved for future evaluation.

### Phase 8: Acceptance Tests & Hold-Out Test
- Single command test runner (`python scripts/run_all_tests.py` & `pytest`).
- Automated tests verifying every requirement from Parts 1-4.
- Hold-out test: adding unseen question/rule purely via data to verify zero-code-change adaptation.

### Phase 9: Documentation & Deliverables
- `README.md` with honest labels, "What code cannot settle", shipped counts, demo controls note.
- `STATUS.md` with every requirement mapped to passing tests.
- `DECISIONS.md` documenting architecture choices and departures (such as minimal student metadata).
- 3-minute demo script using synthetic students only.
