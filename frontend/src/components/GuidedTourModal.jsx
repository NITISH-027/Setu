import React, { useState, useEffect } from 'react';

export default function GuidedTourModal({ isOpen, onClose, onNavigateTab }) {
  const [step, setStep] = useState(1);
  const totalSteps = 5;
  const demoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL || '';

  // Reset to step 1 whenever opened
  useEffect(() => {
    if (isOpen) {
      setStep(1);
    }
  }, [isOpen]);

  // Keyboard navigation: Escape closes, Left/Right arrows navigate
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight' && step < totalSteps) {
        setStep((s) => s + 1);
      } else if (e.key === 'ArrowLeft' && step > 1) {
        setStep((s) => s - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, step, totalSteps, onClose]);

  if (!isOpen) return null;

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
              Step {step} of {totalSteps}
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
                      When probe evidence confirms a gap, the student receives a focused bridge lesson in their preferred language.
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
                <strong>Worksheet Notice:</strong> The worksheet printing feature is
                currently undergoing verification and sheets should be treated as
                reference templates.
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="tour-step-pane">
              <h2 id="tour-modal-title" className="tour-title">
                Explore the Live App
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                The guided tour is complete! You can explore the live prototype using
                the pre-seeded synthetic test accounts below:
              </p>

              <div className="tour-credentials-grid">
                <div className="cred-card">
                  <div className="cred-role">Student App</div>
                  <div className="cred-detail">
                    <div><strong>ID:</strong> <code>stu_demo_01</code></div>
                    <div><strong>PIN:</strong> <code>1234</code></div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Linear Equations practice & adaptive diagnostic probe
                    </div>
                  </div>
                  <button
                    type="button"
                    className="cred-action-btn"
                    onClick={() => onNavigateTab('student')}
                  >
                    Open Student App
                  </button>
                </div>

                <div className="cred-card">
                  <div className="cred-role">Teacher Dashboard</div>
                  <div className="cred-detail">
                    <div><strong>Username:</strong> <code>teacher_8a</code></div>
                    <div><strong>Password:</strong> <code>teacher123</code></div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Class 8-A dashboard, gap groups & pedagogical overrides
                    </div>
                  </div>
                  <button
                    type="button"
                    className="cred-action-btn"
                    onClick={() => onNavigateTab('teacher')}
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
        </div>

        {/* Footer Navigation */}
        <div className="tour-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            style={{ opacity: step === 1 ? 0.35 : 1 }}
          >
            ← Back
          </button>

          {/* Dots Indicator */}
          <div className="tour-dots">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <span
                key={i}
                className={`tour-dot ${step === i + 1 ? 'active' : ''}`}
                onClick={() => setStep(i + 1)}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>

          {step < totalSteps ? (
            <button
              type="button"
              className="action-btn"
              style={{ width: 'auto', minWidth: '100px', padding: '8px 18px' }}
              onClick={() => setStep((s) => Math.min(totalSteps, s + 1))}
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
