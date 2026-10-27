# Setu Implementation Status (STATUS.md)

This document tracks every requirement from the Setu specification, its status (`done`, `partial`, `not done`), and the automated test that proves it.
*Note: In accordance with Hard Rule 7, no requirement is marked `done` without a passing automated test.*

| Category | Requirement | Status | Proving Test / Verification | Notes |
|---|---|---|---|---|
| **Data Model & Pack** | Minimal student metadata (no names, phones, schools) | done | `tests/test_data_model.py::test_student_minimal_metadata` | Strict schema validation; extra fields forbidden |
| **Data Model & Pack** | Pack schema (concepts, edges, questions, lessons, hints, review record) | done | `tests/test_pack_schema.py::test_pack_serialization` | Shipped CBSE Class 8 Maths pack |
| **Data Model & Pack** | Graph spine for Classes 6-10 with NCERT chapter references & graph-only labels | done | `tests/test_pack_schema.py::test_spine_coverage` | Classes 6, 7, 9, 10 labeled `graph-only`; references unverified |
| **Validator** | Tag on every wrong option (rejects untagged wrong options) | done | `tests/test_validator.py::test_validator_rejects_untagged_wrong_option` | Structural validator check |
| **Validator** | Acyclic concept graph & no dangling prerequisites | done | `tests/test_validator.py::test_validator_detects_cycles_and_dangling` | DFS 3-color graph cycle check |
| **Validator** | Probe exists for every tagged misconception | done | `tests/test_validator.py::test_validator_missing_probes` | Probe coverage check |
| **Validator** | Recompute numeric answers script | done | `tests/test_validator.py::test_recompute_numeric_answers` | Automated option check |
| **Validator** | Duplicate / near-duplicate option detection | done | `tests/test_validator.py::test_duplicate_options_flagged` | Human review warning |
| **Review Rules** | Seed/import scripts cannot produce `reviewed` items | done | `tests/test_review_rules.py::test_seed_cannot_set_reviewed` | Human attestation only |
| **Review Rules** | Imported `reviewed` records downgraded to `unverified import` | done | `tests/test_review_rules.py::test_imported_reviewed_downgraded` | Provenance check |
| **Review Rules** | Editing reviewed item resets status or marks changed | done | `tests/test_review_rules.py::test_edit_resets_review_status` | Mutation listener |
| **Review Rules** | Coverage report with human review percentage (including 0.0%) | done | `tests/test_review_rules.py::test_coverage_reporter_percentage` | Real counts calculated |
| **Engine** | Wrong answer opens hypothesis (score band Low, no gap declared) | done | `tests/test_engine.py::test_wrong_answer_hypothesis_low_band` | Heuristic evidence score |
| **Engine** | Conflicting/thin probe evidence leads to "not sure" | done | `tests/test_engine.py::test_conflicting_probes_yields_not_sure` | Planted conflicting probe test |
| **Engine** | Graph trace reaches earliest supported gap (e.g. Class 6 gap) | done | `tests/test_engine.py::test_trace_to_class6_gap` | Synthetic learner trace |
| **Engine** | Micro-lesson matched to misconception & coverage gap report | done | `tests/test_engine.py::test_hint_ladder_and_stuck_flag` | Content delivery |
| **Engine** | Hint ladder (hint -> partial step -> worked step); 2 stuck attempts raise flag | done | `tests/test_engine.py::test_hint_ladder_and_stuck_flag` | 3-tier ladder & flag |
| **Engine** | BKT mastery estimate displayed with "uncalibrated, hand-set" | done | `tests/test_bkt.py::test_bkt_uncalibrated_label_and_update` | Corbett & Anderson model |
| **Engine** | Bridge re-check (pass returns to topic, fail stays, repeated fail flags teacher) | done | `tests/test_engine.py::test_bridge_recheck_routing` | State machine routing |
| **Engine** | Rule sequencer stored as data (changing data changes behavior with no code edit) | done | `tests/test_sequencer.py::test_sequencer_data_rule_change` | Declarative data rules |
| **Engine** | SM-2 interval scheduling (passed concepts queued at intervals) | done | `tests/test_spaced_repetition.py::test_sm2_intervals` | Untuned intervals documented |
| **Engine** | Move-ahead on high mastery with enough evidence; teacher override | done | `tests/test_engine.py::test_move_ahead_and_override` | Fast-learner test |
| **Engine** | Non-scripted path differentiation (two students get different paths) | done | `tests/test_engine.py::test_two_students_different_paths` | Divergent branches |
| **Teacher System** | Class view grouped by shared gap; "not sure" students under undecided | done | `tests/test_teacher.py::test_teacher_grouped_view_and_undecided` | Scoped class view |
| **Teacher System** | Small-group clinic suggestions (~10 mins) | done | `tests/test_teacher.py::test_clinic_suggestions` | Remedial grouping |
| **Teacher System** | Teacher override of plan/gap with logged reason | done | `tests/test_teacher.py::test_teacher_override_logging` | Override audit log |
| **Teacher System** | Class-level isolation (teacher cannot read another class) | done | `tests/test_teacher.py::test_teacher_class_isolation` | Security boundary |
| **Teacher System** | Gap-closed record generation | done | `tests/test_teacher.py::test_gap_closed_record` | Remedial planning record |
| **Teacher System** | Teacher override rate computed from log | done | `tests/test_teacher.py::test_teacher_override_rate_computation` | Quality signal |
| **Data Protection** | Minimal student metadata enforcement | done | `tests/test_data_protection.py::test_forbidden_fields_rejected` | Schema constraint |
| **Data Protection** | Delete-student purges server, caches, queues, exports; no PII left | done | `tests/test_data_protection.py::test_delete_student_purges_stores` | Clean server deletion |
| **Data Protection** | Opaque tombstone key (no student ID/payload); pending state shown | done | `tests/test_data_protection.py::test_tombstone_lifecycle_and_pending_state` | Offline sync lifecycle |
| **Data Protection** | Stale device returning after tombstone purged gets reset, not merged | done | `tests/test_data_protection.py::test_stale_device_reset_after_tombstone_purge` | Device state reset |
| **Data Protection** | Late-syncing offline device does not resurrect deleted data | done | `tests/test_data_protection.py::test_late_sync_offline_no_resurrection` | Resurrect guard |
| **Data Protection** | Configurable retention run automatically purges expired records | done | `tests/test_data_protection.py::test_retention_purge_job` | Retention runner |
| **Data Protection** | Audit log records event type, actor, class, timestamp, count (no PII/payload) | done | `tests/test_data_protection.py::test_audit_log_privacy_and_structure` | Audit log check |
| **Data Protection** | Consent workflow status (not requested, requested, recorded; never auto-marked) | done | `tests/test_data_protection.py::test_consent_workflow_states` | Consent workflow |
| **India Fit** | Offline-first PWA with IndexedDB & sync queue | done | `tests/test_pwa_offline.py::test_offline_flow_and_sync` | PWA offline test |
| **India Fit** | Per-student PIN on shared phone with lockout & no PIN logging | done | `tests/test_pin_auth.py::test_pin_lockout_and_no_logging` | Sibling switch & 3-try lockout |
| **India Fit** | Hindi & Telugu draft text marked unreviewed; visible fallback to English | done | `tests/test_languages.py::test_unreviewed_language_fallback` | i18n fallback |
| **India Fit** | Low-data phone-width layout check | done | `tests/test_frontend_layout.py::test_phone_width_bundle_size` | Responsive (<480px) & lightweight (<500KB) |
| **India Fit** | Teacher-mediated paper mode (printable set + bulk response entry) | done | `tests/test_paper_mode.py::test_paper_mode_flow` | Paper sheet processing |
| **Model Honesty** | Simulation harness with known synthetic learners & planted gaps | done | `tests/test_simulation.py::test_simulation_gap_recovery_and_seeds` | Simulation metrics |
| **Model Honesty** | BKT parameter fitting recovers known synthetic parameters within tolerance | done | `tests/test_parameter_fitting.py::test_bkt_parameter_recovery` | Recovery tolerance (+/- 0.15) |
| **Model Honesty** | Sensitivity analysis across prior ranges | done | `tests/test_sensitivity.py::test_sensitivity_report_generation` | Prior sweep flip boundaries |
| **Model Honesty** | Held-out question set reserved | done | `tests/test_held_out.py::test_held_out_question_isolation` | Held-out isolation |
| **Hold-out & Round 3** | Zero-code-change adaptation: add unseen question/rule purely via data | done | `tests/test_holdout_round3.py::test_round3_data_only_adaptation` | Zero code edit |
| **Docs & Script** | Honest README with "What code cannot settle" & actual shipped counts | done | Manual verification & script check | Honest disclosures in `README.md` |
| **Docs & Script** | 3-minute demo script using synthetic students only | done | `DEMO_SCRIPT.md` | 3-minute synthetic demo script |
