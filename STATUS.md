# Setu Implementation Status (STATUS.md)

This document tracks every requirement from the Setu specification, its status (`done`, `partial`, `not done`), the automated test that proves it, and its **Evidence Class**:
- `browser-e2e`: Real headless browser automation (Playwright driving Chromium)
- `api-integration`: Live API client tests against FastAPI routes and SQLite database
- `unit`: Pure in-memory unit tests
- `simulation-only`: Algorithmic synthetic learner evaluations
- `manual-unverified`: Explicit human disclosures / documentation

---

| Category | Requirement | Status | Proving Test / Verification | Evidence Class | Notes |
|---|---|---|---|---|---|
| **Data Model & Pack** | Minimal student metadata (no names, phones, schools) | done | `tests/test_data_model.py::test_student_minimal_metadata` | `unit` | Strict schema validation; extra fields forbidden |
| **Data Model & Pack** | Pack schema (concepts, edges, questions, lessons, hints, review record) | done | `tests/test_pack_schema.py::test_pack_serialization` | `unit` | Shipped CBSE Class 8 Maths pack (89 Qs, 27 Lessons) |
| **Data Model & Pack** | Graph spine for Classes 6-10 with NCERT chapter references & graph-only labels | done | `tests/test_pack_schema.py::test_spine_coverage` | `unit` | Classes 6, 7, 9, 10 labeled `graph-only`; references unverified |
| **Validator** | Tag on every wrong option (rejects untagged wrong options) | done | `tests/test_validator.py::test_validator_rejects_untagged_wrong_option` | `unit` | Structural validator check |
| **Validator** | Acyclic concept graph & no dangling prerequisites | done | `tests/test_validator.py::test_validator_detects_cycles_and_dangling` | `unit` | DFS 3-color graph cycle check |
| **Validator** | Direct probes exist for all active Class 8 concepts (>=2 probes/concept) | done | `tests/test_validator.py::test_validator_missing_probes` | `unit` | Direct probe coverage for all 7 active Class 8 concepts |
| **Validator** | Recompute numeric answers script | done | `tests/test_validator.py::test_recompute_numeric_answers` | `unit` | Automated arithmetic option check |
| **Validator** | Duplicate / near-duplicate option detection | done | `tests/test_validator.py::test_duplicate_options_flagged` | `unit` | Human review warning |
| **Review Rules** | Seed/import scripts cannot produce `reviewed` items | done | `tests/test_review_rules.py::test_seed_cannot_set_reviewed` | `unit` | Human attestation only |
| **Review Rules** | Imported `reviewed` records downgraded to `unverified import` | done | `tests/test_review_rules.py::test_imported_reviewed_downgraded` | `unit` | Provenance check |
| **Review Rules** | Editing reviewed item resets status to `author-drafted, unreviewed` | done | `tests/test_review_rules.py::test_edit_resets_review_status` | `unit` | Mutation listener & editor reset |
| **Review Rules** | Coverage report with human review percentage (starts at 0.0%) | done | `tests/test_review_rules.py::test_coverage_reporter_percentage` | `unit` | Real counts calculated (0/205 items, 0.0%) |
| **Engine** | Wrong answer opens hypothesis (score band Low, no gap declared) | done | `tests/test_engine.py::test_wrong_answer_hypothesis_low_band` | `unit` | Heuristic evidence score |
| **Engine** | Conflicting/thin probe evidence leads to "not sure" | done | `tests/test_engine.py::test_conflicting_probes_yields_not_sure` | `unit` | Planted conflicting probe test |
| **Engine** | Graph trace reaches earliest supported gap (e.g. Class 6 gap) | done | `tests/test_engine.py::test_trace_to_class6_gap` | `unit` | Synthetic learner trace |
| **Engine** | Micro-lesson matched to misconception & coverage gap report | done | `tests/test_engine.py::test_hint_ladder_and_stuck_flag` | `unit` | Content delivery |
| **Engine** | Hint ladder (hint -> partial step -> worked step); 2 stuck attempts raise flag | done | `tests/test_engine.py::test_hint_ladder_and_stuck_flag` | `unit` | 3-tier ladder & flag |
| **Engine** | BKT mastery estimate displayed with "uncalibrated, hand-set" | done | `tests/test_bkt.py::test_bkt_uncalibrated_label_and_update` | `unit` | Corbett & Anderson model |
| **Engine** | Bridge re-check (pass returns to topic, fail stays, repeated fail flags teacher) | done | `tests/test_engine.py::test_bridge_recheck_routing` | `unit` | State machine routing |
| **Engine** | Rule sequencer stored as data (changing data changes behavior with no code edit) | done | `tests/test_sequencer.py::test_sequencer_data_rule_change` | `unit` | Declarative data rules |
| **Engine** | SM-2 interval scheduling (passed concepts queued at intervals) | done | `tests/test_spaced_repetition.py::test_sm2_intervals` | `unit` | Untuned intervals documented |
| **Engine** | Move-ahead on high mastery with enough evidence; teacher override | done | `tests/test_engine.py::test_move_ahead_and_override` | `unit` | Fast-learner test |
| **Engine** | Non-scripted path differentiation (two students get different paths) | done | `tests/test_engine.py::test_two_students_different_paths` | `unit` | Divergent branches |
| **Parity** | Pure-JS Engine Port with 100% Golden Test Vector Parity | done | `frontend/test_parity.js` (`npm run test:parity`) | `unit` | 40/40 assertions: BKT, SM-2, Hypothesis, Sequencer |
| **Server Persistence** | SQLAlchemy SQLite persistence across restarts (no in-memory stores) | done | `tests/test_api_security_persistence.py::test_server_side_grading_spoof_override` | `api-integration` | Attempts, states, and overrides stored in DB |
| **Auth & Security** | Strict Auth Enforcement: all no-session fallbacks removed; 401 on missing token | done | `tests/test_api_security_persistence.py::test_auth_enforcement_negative_controls` & `scripts/negative_control_auth_probes.py` | `api-integration` | 401 across all 8 sensitive routes; no tea_01 or query fallbacks |
| **Auth & Security** | Strict Role & Class Scoping: students restricted to self; teachers to class | done | `tests/test_api_security_persistence.py::test_teacher_class_scoping_negative_control` | `api-integration` | 403 on cross-student or cross-class access |
| **Auth & Security** | Malformed payloads return 422, never 500 | done | `tests/test_api_security_persistence.py::test_malformed_attempt_payload_returns_422` | `api-integration` | Input validation prevents 500s |
| **Auth & Security** | CORS restricted to explicit allowlist from environment variable (no wildcard) | done | `tests/test_api_security_persistence.py::test_cors_allowlist_restriction` | `api-integration` | No wildcard with credentials |
| **Residual Answer Leak** | Zero answer leak online; authenticated offline pack for offline grading | done | `tests/test_api_security_persistence.py::test_zero_answer_leak_online_and_authenticated_offline_pack` | `api-integration` | Next-step & public pack contain no is_correct; offline pack scoped to class |
| **Data Protection** | Minimal student metadata enforcement | done | `tests/test_data_protection.py::test_forbidden_fields_rejected` | `unit` | Schema constraint |
| **Data Protection** | Clean student deletion purges all tables, sessions, overrides & PIN profiles | done | `tests/test_api_security_persistence.py::test_zero_pii_deletion_and_tombstone_lifecycle` | `api-integration` | Full DB scan asserts zero residue of student ID and override text |
| **Data Protection** | Restricted revocation device purge token & tombstone lifecycle | done | `tests/test_api_security_persistence.py::test_zero_pii_deletion_and_tombstone_lifecycle` | `api-integration` | Offline device fetches tombstone, purges, and gains no learning access |
| **Data Protection** | Stale device returning after 30 days flagged for reset, not merged | done | `tests/test_api_security_persistence.py::test_stale_device_detection_on_sync` | `api-integration` | Server returns is_stale_reset_required |
| **Data Protection** | Browser RESET wipe: client IndexedDB completely wiped on RESET response | done | `frontend/tests/reset_wipe.spec.js` | `browser-e2e` | Browser verifies 0 attempts, 0 queue, 0 profiles in IndexedDB |
| **Data Protection** | Audit log records event type, actor, class, timestamp, count (zero PII) | done | `tests/test_api_security_persistence.py::test_zero_pii_deletion_and_tombstone_lifecycle` | `api-integration` | No answers, no payload, no student IDs |
| **Data Protection** | Configurable retention run automatically purges expired records | done | `tests/test_data_protection.py::test_retention_purge_job` | `unit` | Retention runner |
| **Teacher System** | Class view grouped by shared gap; "not sure" students under undecided | done | `tests/test_teacher.py::test_teacher_grouped_view_and_undecided` | `unit` | Scoped class view |
| **Teacher System** | Small-group clinic suggestions (~10 mins) | done | `tests/test_teacher.py::test_clinic_suggestions` | `unit` | Remedial grouping |
| **Teacher System** | Teacher override of plan/gap with mandatory logged reason | done | `tests/test_teacher.py::test_teacher_override_logging` | `unit` | Override audit log |
| **Teacher System** | Gap-closed record generation | done | `tests/test_teacher.py::test_gap_closed_record` | `unit` | Remedial planning record |
| **Teacher System** | Teacher override rate computed from log | done | `tests/test_teacher.py::test_teacher_override_rate_computation` | `unit` | Quality signal |
| **PWA & Offline** | Full Real Browser Offline PWA Lifecycle (10 steps) | done | `frontend/tests/offline_flow.spec.js` | `browser-e2e` | Real network disconnect, page reload, PBKDF2 offline auth, local JS engine grading, IndexedDB attempt/queue reload persistence, reconnect authoritative sync |
| **PWA & Offline** | System fonts only (no external Google Fonts CDN at runtime) | done | `frontend/index.html`, `frontend/src/index.css` | `browser-e2e` | Offline compliant; no third-party CDN |
| **UI & Layout** | Real rendered layout & no horizontal overflow across all 5 tabs at 360px & 390px | done | `frontend/tests/layout_and_tabs.spec.js` | `browser-e2e` | Screenshots: `screenshots/layout_360px_*.png`, `screenshots/layout_390px_*.png` |
| **India Fit** | Hindi & Telugu draft text (5 Qs + 5 lessons per lang); visible English fallback | done | `tests/test_languages.py::test_unreviewed_language_fallback` | `unit` | Real draft translations; 0.0% reviewed |
| **India Fit** | Teacher-mediated paper mode (printable set + bulk response entry) | done | `tests/test_paper_mode.py::test_paper_mode_flow` | `unit` | Paper sheet processing |
| **Demo Safeguards** | Seed script generates random credentials and refuses in production; zero default inputs | done | `tests/test_api_security_persistence.py::test_seed_script_and_production_startup_refusal` | `api-integration` | Random PIN/password, is_seeded check, empty login fields |
| **Model Honesty** | Simulation harness with known synthetic learners & planted gaps | done | `tests/test_simulation.py::test_simulation_gap_recovery_and_seeds` | `simulation-only` | Simulation metrics |
| **Model Honesty** | BKT parameter fitting recovers known synthetic parameters within tolerance | done | `tests/test_parameter_fitting.py::test_bkt_parameter_recovery` | `simulation-only` | Recovery tolerance (+/- 0.15) |
| **Model Honesty** | Sensitivity analysis across prior ranges | done | `tests/test_sensitivity.py::test_sensitivity_report_generation` | `simulation-only` | Prior sweep flip boundaries |
| **Model Honesty** | Held-out question set reserved | done | `tests/test_held_out.py::test_held_out_question_isolation` | `unit` | Held-out isolation |
| **Hold-out & Round 3** | Zero-code-change adaptation: add unseen question/rule purely via data | done | `tests/test_holdout_round3.py::test_round3_data_only_adaptation` | `unit` | Zero code edit |
| **Docs & Script** | Honest README with "What code cannot settle" & actual shipped counts | done | Manual verification & script check | `manual-unverified` | Honest disclosures in `README.md` |
| **Docs & Script** | 3-minute demo script using synthetic students only | done | `DEMO_SCRIPT.md` | `manual-unverified` | 3-minute synthetic demo script |

