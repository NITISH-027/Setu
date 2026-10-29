import React, { useState, useEffect } from 'react';

export default function GuidedTourModal({ isOpen, onClose, onNavigateTab }) {
  const [step, setStep] = useState(1);
  const totalSteps = 5;
  const demoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL || '';

  // Interactive Prepared Previews state
  const [previewMode, setPreviewMode] = useState(null); // null | 'student' | 'teacher'

  // Student Preview States
  const [studentStage, setStudentStage] = useState(1); // 1: Practice, 2: Hypothesis, 3: Probe, 4: Lesson, 5: Bridge
  const [practiceChoice, setPracticeChoice] = useState(null); // '7' | '21'
  const [probeChoice, setProbeChoice] = useState(null); // '-4' | '4'
  const [bridgeChoice, setBridgeChoice] = useState(null); // '-7' | '7'

  // Teacher Preview States
  const [teacherOverrides, setTeacherOverrides] = useState({});
  const [activeOverrideTarget, setActiveOverrideTarget] = useState(null); // { studentId, conceptName }
  const [overrideReasonInput, setOverrideReasonInput] = useState('');
  const [overrideConfirmation, setOverrideConfirmation] = useState('');

  const resetStudentPreview = () => {
    setStudentStage(1);
    setPracticeChoice(null);
    setProbeChoice(null);
    setBridgeChoice(null);
  };

  const resetTeacherPreview = () => {
    setTeacherOverrides({});
    setActiveOverrideTarget(null);
    setOverrideReasonInput('');
    setOverrideConfirmation('');
  };

  // Reset to step 1 whenever opened
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setPreviewMode(null);
      resetStudentPreview();
      resetTeacherPreview();
    }
  }, [isOpen]);

  // Keyboard navigation: Escape closes, Left/Right arrows navigate (when not inside interactive preview)
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (activeOverrideTarget) {
          setActiveOverrideTarget(null);
        } else if (previewMode) {
          setPreviewMode(null);
        } else {
          onClose();
        }
      } else if (!previewMode) {
        if (e.key === 'ArrowRight' && step < totalSteps) {
          setStep((s) => s + 1);
        } else if (e.key === 'ArrowLeft' && step > 1) {
          setStep((s) => s - 1);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, step, totalSteps, previewMode, activeOverrideTarget, onClose]);

  if (!isOpen) return null;

  const handleOverrideSubmit = (e) => {
    e.preventDefault();
    if (!overrideReasonInput.trim() || !activeOverrideTarget) return;

    setTeacherOverrides((prev) => ({
      ...prev,
      [activeOverrideTarget.studentId]: overrideReasonInput.trim(),
    }));
    setOverrideConfirmation('Preview override recorded locally - no real student record changed');
    setActiveOverrideTarget(null);
    setOverrideReasonInput('');
  };

  return (
    <div
      className="tour-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-modal-title"
      onClick={onClose}
    >
      <div
        className="tour-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="tour-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="tour-badge">GUIDED TOUR</span>
            <span className="tour-step-counter">
              {previewMode
                ? previewMode === 'student'
                  ? 'Student Preview'
                  : 'Teacher Preview'
                : `Step ${step} of ${totalSteps}`}
            </span>
          </div>
          <button
            className="tour-close-btn"
            onClick={onClose}
            aria-label="Close Tour"
          >
            ✕
          </button>
        </div>

        {/* Step Progress Track */}
        <div className="tour-progress-bar">
          <div
            className="tour-progress-fill"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>

        {/* Step Content */}
        <div className="tour-body">
          {step === 1 && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                What Setu Solves
              </h2>
              <blockquote className="tour-quote">
                "A wrong answer is a starting point, not a diagnosis. Setu checks a
                possible prerequisite gap, offers a focused lesson when the
                evidence supports it, and guides the student back to practice.
                Teachers can review the evidence and intervene."
              </blockquote>
              <div className="tour-callout warning">
                <strong>Prototype Notice:</strong> This prototype uses an authored
                mathematics concept pack (CBSE Class 8 Linear Equations spine),
                not complete curriculum coverage or proven learning outcomes.
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                One Student Learning Journey
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Setu adapts the student's journey in 4 distinct beats:
              </p>

              <div className="tour-beats-list">
                <div className="tour-beat-item">
                  <span className="beat-number">1</span>
                  <div>
                    <strong>Wrong Answer on Practice</strong>
                    <div className="beat-desc">
                      Student makes an error on an original Class 8 question (e.g. sign transposition in linear equations).
                    </div>
                  </div>
                </div>

                <div className="tour-beat-item">
                  <span className="beat-number">2</span>
                  <div>
                    <strong>Prerequisite Diagnostic Probe</strong>
                    <div className="beat-desc">
                      Engine traverses the concept graph to probe foundational prerequisites (e.g. Class 6 integer operations) without penalizing stuck counters.
                    </div>
                  </div>
                </div>

                <div className="tour-beat-item">
                  <span className="beat-number">3</span>
                  <div>
                    <strong>Focused Micro-Lesson</strong>
                    <div className="beat-desc">
                      When probe evidence supports a gap, the student receives a focused bridge lesson in their preferred language.
                    </div>
                  </div>
                </div>

                <div className="tour-beat-item">
                  <span className="beat-number">4</span>
                  <div>
                    <strong>Bridge Re-Check & Return to Practice</strong>
                    <div className="beat-desc">
                      A focused check verifies understanding. Upon passing, the student returns directly to original topic practice. (Note: Review is a separate scheduled stage).
                    </div>
                  </div>
                </div>
              </div>

              {/* Prepared Example Label */}
              <div className="prepared-example-card">
                <div className="prepared-label">Prepared example: Stage Progression</div>
                <div className="stage-flow-chips">
                  <span className="flow-chip">1. solve</span>
                  <span className="flow-arrow">→</span>
                  <span className="flow-chip">2. probe</span>
                  <span className="flow-arrow">→</span>
                  <span className="flow-chip">3. learn</span>
                  <span className="flow-arrow">→</span>
                  <span className="flow-chip">4. bridge_recheck</span>
                  <span className="flow-arrow">→</span>
                  <span className="flow-chip">5. solve (resumed)</span>
                </div>
              </div>

              <div style={{ marginTop: '14px' }}>
                <button
                  type="button"
                  className="tour-inline-action-btn"
                  onClick={() => onNavigateTab('student')}
                >
                  ▶ Try this loop in the live app (Student App)
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                Teacher Intervention & Command
              </h2>
              <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                Teachers see likely prerequisite gaps and uncertain cases in real
                time on their dashboard, with students automatically grouped by
                shared gap for recommended 10-minute small-group clinics.
              </p>
              <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '8px' }}>
                Teachers can follow up in class with targeted practice, and retain
                strict pedagogical authority to override any algorithmic placement,
                mark gaps cleared, or request reinforcement with a mandatory logged reason.
              </p>

              {/* Prepared Example Label */}
              <div className="prepared-example-card">
                <div className="prepared-label">Prepared example: Grouped Gap Clinic</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                      Addition & Subtraction of Integers
                    </strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Students: stu_demo_01, stu_coll_A
                    </div>
                  </div>
                  <span className="badge-heuristic" style={{ fontSize: '10px' }}>
                    10-min clinic suggested
                  </span>
                </div>
              </div>

              <div style={{ marginTop: '14px' }}>
                <button
                  type="button"
                  className="tour-inline-action-btn"
                  onClick={() => onNavigateTab('teacher')}
                >
                  ▶ View Live Teacher Dashboard
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                Offline & Paper Support
              </h2>
              <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                Setu is purpose-built for low-connectivity classrooms: the PWA
                continues working directly on the student's mobile device or tablet
                using a service worker, local IndexedDB storage, and an on-device
                JavaScript adaptive engine.
              </p>
              <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '8px' }}>
                When connectivity is restored, queued attempts are uploaded for
                authoritative server-side grading and mastery updates. In classrooms
                with physical worksheets, teachers can enter student responses from
                paper practice via the Paper Mode entry tool.
              </p>

              <div className="tour-callout info">
                <strong>Simulation vs Reality:</strong> The in-app "Dev: Simulate
                Offline Mode" button exercises local client-side IndexedDB caching
                and grading logic; it is a developer demonstration separate from
                physical network disconnection.
              </div>

              <div className="tour-callout warning">
                <strong>Worksheet Notice:</strong> Worksheet printing is not available
                in this build; teachers can still enter answers from paper practice
                in the Paper Mode tab.
              </div>
            </div>
          )}

          {step === 5 && !previewMode && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                Explore Interactive Previews
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                Explore the student adaptive diagnostic loop and teacher command views
                directly through self-contained interactive previews without logging in:
              </p>

              <div className="tour-credentials-grid">
                <div className="cred-card">
                  <div>
                    <div className="cred-role">Student App Flow</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.45' }}>
                      Click-through CBSE Class 8 practice question, prerequisite gap detection, integer probe, focused micro-lesson, and bridge re-check.
                    </div>
                  </div>
                  <button
                    type="button"
                    className="cred-action-btn"
                    onClick={() => {
                      resetStudentPreview();
                      setPreviewMode('student');
                    }}
                  >
                    Open Student App
                  </button>
                </div>

                <div className="cred-card">
                  <div>
                    <div className="cred-role">Teacher Dashboard Flow</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.45' }}>
                      Explore synthetic Class 8-A gap clustering, 10-minute clinic suggestions, undecided cases, and interactive teacher overrides.
                    </div>
                  </div>
                  <button
                    type="button"
                    className="cred-action-btn"
                    onClick={() => {
                      resetTeacherPreview();
                      setPreviewMode('teacher');
                    }}
                  >
                    Open Teacher Dashboard
                  </button>
                </div>
              </div>

              {demoVideoUrl && (
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                  <a
                    href={demoVideoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="tour-video-btn"
                  >
                    ▶ Watch full demo video
                  </a>
                </div>
              )}
            </div>
          )}

          {/* STUDENT INTERACTIVE PREVIEW */}
          {step === 5 && previewMode === 'student' && (
            <div className="tour-step-pane">
              {/* Persistent Header Label (Required) */}
              <div className="preview-persistent-banner">
                <span>⚡</span>
                <span>
                  Prepared preview - illustrates the real student flow. Not connected to the live engine or real student data.
                </span>
              </div>

              {/* Navigation controls */}
              <div className="preview-top-nav">
                <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                  Screen {studentStage} of 5:{' '}
                  {studentStage === 1 && 'Practice Question'}
                  {studentStage === 2 && 'Diagnostic Gap Hypothesis'}
                  {studentStage === 3 && 'Prerequisite Probe'}
                  {studentStage === 4 && 'Focused Micro-Lesson'}
                  {studentStage === 5 && 'Bridge Re-Check & Resumption'}
                </span>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button
                    type="button"
                    className="preview-link-btn"
                    onClick={resetStudentPreview}
                  >
                    Restart preview
                  </button>
                  <button
                    type="button"
                    className="preview-link-btn"
                    onClick={() => setPreviewMode(null)}
                  >
                    ← Back to tour
                  </button>
                </div>
              </div>

              {/* STAGE 1: Real practice question */}
              {studentStage === 1 && (
                <div className="preview-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="flow-chip">Original Topic: CBSE Class 8 Math</span>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>Stage: solve</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--accent-secondary)', marginBottom: '8px' }}>
                    💡 <em>Judges: Select wrong answer (21) to see the prepared diagnostic path, or (7) to test correct feedback.</em>
                  </div>
                  <p style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', margin: '8px 0' }}>
                    Solve for x: x + 7 = 14
                  </p>
                  <div className="preview-options-stack">
                    <button
                      type="button"
                      className={`preview-opt-btn ${practiceChoice === '7' ? 'active' : ''}`}
                      onClick={() => setPracticeChoice('7')}
                    >
                      <span>A) 7</span>
                      {practiceChoice === '7' && <span>✓</span>}
                    </button>
                    <button
                      type="button"
                      className={`preview-opt-btn ${practiceChoice === '21' ? 'active-wrong' : ''}`}
                      onClick={() => setPracticeChoice('21')}
                    >
                      <span>B) 21</span>
                      {practiceChoice === '21' && <span>✗</span>}
                    </button>
                  </div>

                  {practiceChoice === '7' && (
                    <div className="preview-feedback-box correct">
                      <div><strong>✓ Correct!</strong> 7 + 7 = 14.</div>
                      <div style={{ marginTop: '4px', fontSize: '11.5px' }}>
                        In live practice, correct answers increment streak & mastery.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="action-btn"
                          style={{ width: 'auto', padding: '6px 14px', fontSize: '12px' }}
                          onClick={() => setStudentStage(2)}
                        >
                          Try prepared diagnostic path anyway →
                        </button>
                      </div>
                    </div>
                  )}

                  {practiceChoice === '21' && (
                    <div className="preview-feedback-box incorrect">
                      <div><strong>✗ Incorrect.</strong> Student added 7 to 14 instead of subtracting.</div>
                      <div style={{ marginTop: '4px', fontSize: '11.5px' }}>
                        Setu observes sign transposition confusion and activates prerequisite gap diagnosis.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="action-btn"
                          style={{ width: 'auto', padding: '6px 14px', fontSize: '12px' }}
                          onClick={() => setStudentStage(2)}
                        >
                          Continue to Diagnostic Gap Check →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STAGE 2: Hypothesis Card */}
              {studentStage === 2 && (
                <div className="preview-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="flow-chip">Adaptive Graph Traversal</span>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>Hypothesis Check</span>
                  </div>
                  <h3 style={{ fontSize: '15px', color: '#f59e0b', marginBottom: '8px' }}>
                    ⚠️ Possible prerequisite gap detected
                  </h3>
                  <p style={{ fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                    Setu's diagnostic engine noted an error consistent with sign inversion during equation transposition.
                  </p>
                  <p style={{ fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)', marginTop: '6px' }}>
                    Instead of repeatedly drilling the student on Class 8 equations, Setu steps back to check foundational Class 6 prerequisites without penalizing the student's mastery score.
                  </p>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', margin: '12px 0', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Target Prerequisite Concept</div>
                    <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Subtraction of Integers (Class 6: c6_int_sub)</strong>
                  </div>
                  <div className="preview-action-row">
                    <button
                      type="button"
                      className="action-btn"
                      style={{ width: 'auto', padding: '8px 16px', fontSize: '13px' }}
                      onClick={() => setStudentStage(3)}
                    >
                      Begin Prerequisite Probe →
                    </button>
                  </div>
                </div>
              )}

              {/* STAGE 3: Prerequisite Probe Question */}
              {studentStage === 3 && (
                <div className="preview-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="flow-chip">Prerequisite Probe (Class 6 Integers)</span>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>Stage: probe</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    <em>Prepared example: Prerequisite probes evaluate gap evidence without decrementing practice counters.</em>
                  </div>
                  <p style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', margin: '8px 0' }}>
                    What is 3 - 7?
                  </p>
                  <div className="preview-options-stack">
                    <button
                      type="button"
                      className={`preview-opt-btn ${probeChoice === '-4' ? 'active' : ''}`}
                      onClick={() => setProbeChoice('-4')}
                    >
                      <span>A) -4</span>
                      {probeChoice === '-4' && <span>✓</span>}
                    </button>
                    <button
                      type="button"
                      className={`preview-opt-btn ${probeChoice === '4' ? 'active-wrong' : ''}`}
                      onClick={() => setProbeChoice('4')}
                    >
                      <span>B) 4</span>
                      {probeChoice === '4' && <span>✗</span>}
                    </button>
                  </div>

                  {probeChoice === '4' && (
                    <div className="preview-feedback-box incorrect">
                      <div><strong>✗ Incorrect.</strong> 3 - 7 = -4 (evidence supports an integer subtraction gap).</div>
                      <div style={{ marginTop: '4px', fontSize: '11.5px' }}>
                        Setu provides a focused 2-minute micro-lesson to bridge this specific gap.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="action-btn"
                          style={{ width: 'auto', padding: '6px 14px', fontSize: '12px' }}
                          onClick={() => setStudentStage(4)}
                        >
                          Proceed to Focused Micro-Lesson (Prepared example) →
                        </button>
                      </div>
                    </div>
                  )}

                  {probeChoice === '-4' && (
                    <div className="preview-feedback-box correct">
                      <div><strong>✓ Correct:</strong> 3 - 7 = -4. Probe answered correctly.</div>
                      <div style={{ marginTop: '4px', fontSize: '11.5px' }}>
                        In the live engine, answers are scored individually and not every answer indicates a gap.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="action-btn"
                          style={{ width: 'auto', padding: '6px 14px', fontSize: '12px' }}
                          onClick={() => setStudentStage(4)}
                        >
                          Proceed to Micro-Lesson Example →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STAGE 4: Micro-lesson Card */}
              {studentStage === 4 && (
                <div className="preview-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="flow-chip">Focused Bridge Lesson</span>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>Stage: learn</span>
                  </div>
                  <h3 style={{ fontSize: '14px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                    📖 Concept Bridge: Subtraction of Integers
                  </h3>
                  <blockquote style={{ background: 'rgba(0,0,0,0.3)', borderLeft: '3px solid var(--accent-primary)', padding: '10px 14px', margin: '10px 0', fontSize: '13px', lineHeight: '1.5', color: '#e2e8f0', fontStyle: 'normal' }}>
                    "Prerequisite Bridge (Class 6 Integers): When subtracting a larger positive integer from a smaller one, the result is negative (e.g. 3 - 7 = -4). Move left on the number line."
                  </blockquote>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                    Focused on the exact misconception before returning the student to equations.
                  </p>
                  <div className="preview-action-row">
                    <button
                      type="button"
                      className="action-btn"
                      style={{ width: 'auto', padding: '8px 16px', fontSize: '13px' }}
                      onClick={() => setStudentStage(5)}
                    >
                      Take Bridge Re-Check →
                    </button>
                  </div>
                </div>
              )}

              {/* STAGE 5: Bridge re-check */}
              {studentStage === 5 && (
                <div className="preview-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="flow-chip">Bridge Re-Check</span>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>Stage: bridge_recheck</span>
                  </div>
                  <p style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', margin: '8px 0' }}>
                    What is 5 - 12?
                  </p>
                  <div className="preview-options-stack">
                    <button
                      type="button"
                      className={`preview-opt-btn ${bridgeChoice === '-7' ? 'active' : ''}`}
                      onClick={() => setBridgeChoice('-7')}
                    >
                      <span>A) -7</span>
                      {bridgeChoice === '-7' && <span>✓</span>}
                    </button>
                    <button
                      type="button"
                      className={`preview-opt-btn ${bridgeChoice === '7' ? 'active-wrong' : ''}`}
                      onClick={() => setBridgeChoice('7')}
                    >
                      <span>B) 7</span>
                      {bridgeChoice === '7' && <span>✗</span>}
                    </button>
                  </div>

                  {bridgeChoice === '-7' && (
                    <div className="preview-feedback-box correct">
                      <div><strong>✓ Correct!</strong> 5 - 12 = -7.</div>
                      <div style={{ marginTop: '6px', padding: '6px 8px', background: 'rgba(0,0,0,0.25)', borderRadius: '4px', fontSize: '12px' }}>
                        📈 <strong>Illustrative Mastery Increase:</strong> Integer Subtraction: 20% → 45% (illustrative only).
                      </div>
                      <div style={{ marginTop: '6px', fontSize: '12px' }}>
                        Bridge verified! Student returns directly to practice on original Class 8 Linear Equations.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={resetStudentPreview}
                        >
                          Restart preview
                        </button>
                        <button
                          type="button"
                          className="action-btn"
                          style={{ width: 'auto', padding: '6px 14px' }}
                          onClick={() => setPreviewMode(null)}
                        >
                          ← Back to tour
                        </button>
                      </div>
                    </div>
                  )}

                  {bridgeChoice === '7' && (
                    <div className="preview-feedback-box incorrect">
                      <div><strong>✗ Incorrect.</strong> 5 - 12 = -7.</div>
                      <div style={{ marginTop: '4px', fontSize: '12px' }}>
                        Prerequisite gap is not yet resolved. No mastery increase claimed.
                      </div>
                      <div className="preview-action-row">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => setBridgeChoice(null)}
                        >
                          Retry question
                        </button>
                        <button
                          type="button"
                          className="preview-link-btn"
                          onClick={() => setPreviewMode(null)}
                        >
                          Skip to finish preview
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div style={{ marginTop: '10px', textAlign: 'right' }}>
                <button
                  type="button"
                  className="preview-link-btn"
                  onClick={() => setPreviewMode(null)}
                >
                  ← Back to tour options
                </button>
              </div>
            </div>
          )}

          {/* TEACHER INTERACTIVE PREVIEW */}
          {step === 5 && previewMode === 'teacher' && (
            <div className="tour-step-pane">
              {/* Persistent Header Label (Required) */}
              <div className="preview-persistent-banner teacher">
                <span>⚡</span>
                <span>
                  Prepared preview - synthetic class data, not the live dashboard.
                </span>
              </div>

              {/* Navigation controls */}
              <div className="preview-top-nav">
                <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                  Teacher Dashboard Command View (Class 8-A)
                </span>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button
                    type="button"
                    className="preview-link-btn"
                    onClick={resetTeacherPreview}
                  >
                    Reset preview
                  </button>
                  <button
                    type="button"
                    className="preview-link-btn"
                    onClick={() => setPreviewMode(null)}
                  >
                    ← Back to tour
                  </button>
                </div>
              </div>

              {overrideConfirmation && (
                <div className="preview-feedback-box info" style={{ marginBottom: '12px' }}>
                  ✓ {overrideConfirmation}
                </div>
              )}

              {/* Gap Group Card */}
              <div className="preview-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span className="badge-heuristic" style={{ fontSize: '10px' }}>
                      10-min clinic suggested
                    </span>
                    <h3 style={{ fontSize: '14px', color: 'var(--text-primary)', marginTop: '4px' }}>
                      Addition & Subtraction of Integers
                    </h3>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    2 students
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Suggested intervention: 10-minute small-group number line workshop.
                </p>

                <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: '6px' }}>
                    <div>
                      <strong style={{ fontSize: '12.5px' }}>stu_demo_01</strong>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Stage: probe • Reason: Sign transposition on linear equations
                      </div>
                      {teacherOverrides['stu_demo_01'] && (
                        <div style={{ fontSize: '11px', color: '#a7f3d0', marginTop: '2px' }}>
                          ✓ Overridden: "{teacherOverrides['stu_demo_01']}"
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '11.5px', padding: '4px 10px' }}
                      onClick={() => {
                        setActiveOverrideTarget({ studentId: 'stu_demo_01', conceptName: 'Addition & Subtraction of Integers' });
                        setOverrideReasonInput(teacherOverrides['stu_demo_01'] || '');
                        setOverrideConfirmation('');
                      }}
                    >
                      Override
                    </button>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: '6px' }}>
                    <div>
                      <strong style={{ fontSize: '12.5px' }}>stu_coll_A</strong>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Stage: learn • Reason: Subtraction direction inverted
                      </div>
                      {teacherOverrides['stu_coll_A'] && (
                        <div style={{ fontSize: '11px', color: '#a7f3d0', marginTop: '2px' }}>
                          ✓ Overridden: "{teacherOverrides['stu_coll_A']}"
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '11.5px', padding: '4px 10px' }}
                      onClick={() => {
                        setActiveOverrideTarget({ studentId: 'stu_coll_A', conceptName: 'Addition & Subtraction of Integers' });
                        setOverrideReasonInput(teacherOverrides['stu_coll_A'] || '');
                        setOverrideConfirmation('');
                      }}
                    >
                      Override
                    </button>
                  </div>
                </div>
              </div>

              {/* Undecided Students Card */}
              <div className="preview-card">
                <h3 style={{ fontSize: '14px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Undecided Students (Thin / Conflicting Evidence)
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Algorithmic confidence threshold not met; requires human teacher evaluation or more practice items.
                </p>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div>
                    <strong style={{ fontSize: '12.5px' }}>stu_demo_02</strong>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Stage: solve • Reason: Inconsistent probe responses (evidence undecided)
                    </div>
                    {teacherOverrides['stu_demo_02'] && (
                      <div style={{ fontSize: '11px', color: '#a7f3d0', marginTop: '2px' }}>
                        ✓ Overridden: "{teacherOverrides['stu_demo_02']}"
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ fontSize: '11.5px', padding: '4px 10px' }}
                    onClick={() => {
                      setActiveOverrideTarget({ studentId: 'stu_demo_02', conceptName: 'Linear Equations in One Variable' });
                      setOverrideReasonInput(teacherOverrides['stu_demo_02'] || '');
                      setOverrideConfirmation('');
                    }}
                  >
                    Override
                  </button>
                </div>
              </div>

              {/* Interactive Override Dialog */}
              {activeOverrideTarget && (
                <div style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid var(--accent-primary)', borderRadius: '8px', padding: '12px', marginTop: '12px' }}>
                  <h4 style={{ fontSize: '13px', color: 'var(--text-primary)', marginBottom: '6px' }}>
                    Pedagogical Override for {activeOverrideTarget.studentId}
                  </h4>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    Concept: {activeOverrideTarget.conceptName}
                  </div>
                  <form onSubmit={handleOverrideSubmit}>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Reason for Override (Mandatory):
                    </label>
                    <textarea
                      rows={2}
                      value={overrideReasonInput}
                      onChange={(e) => setOverrideReasonInput(e.target.value)}
                      placeholder="e.g. Cleared gap during 1-on-1 whiteboard review..."
                      style={{ width: '100%', padding: '8px', fontSize: '12px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', marginBottom: '8px', resize: 'vertical' }}
                    />
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ fontSize: '12px' }}
                        onClick={() => setActiveOverrideTarget(null)}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="action-btn"
                        style={{ width: 'auto', fontSize: '12px', padding: '6px 14px' }}
                        disabled={!overrideReasonInput.trim()}
                      >
                        Submit Override
                      </button>
                    </div>
                  </form>
                </div>
              )}

              <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button
                  type="button"
                  className="preview-link-btn"
                  onClick={resetTeacherPreview}
                >
                  Reset preview data
                </button>
                <button
                  type="button"
                  className="preview-link-btn"
                  onClick={() => setPreviewMode(null)}
                >
                  ← Back to tour options
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="tour-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              if (previewMode) {
                setPreviewMode(null);
              } else {
                setStep((s) => Math.max(1, s - 1));
              }
            }}
            disabled={step === 1 && !previewMode}
            style={{ opacity: step === 1 && !previewMode ? 0.35 : 1 }}
          >
            ← Back
          </button>

          {/* Dots Indicator */}
          <div className="tour-dots">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <span
                key={i}
                className={`tour-dot ${step === i + 1 ? 'active' : ''}`}
                onClick={() => {
                  setPreviewMode(null);
                  setStep(i + 1);
                }}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>

          {step < totalSteps ? (
            <button
              type="button"
              className="action-btn"
              style={{ width: 'auto', minWidth: '100px', padding: '8px 18px' }}
              onClick={() => {
                setPreviewMode(null);
                setStep((s) => Math.min(totalSteps, s + 1));
              }}
            >
              Next →
            </button>
          ) : (
            <button
              type="button"
              className="action-btn"
              style={{ width: 'auto', minWidth: '100px', padding: '8px 18px' }}
              onClick={onClose}
            >
              Finish Tour ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
