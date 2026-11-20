import React, { useState, useEffect } from 'react';

import { makeT } from '../i18n/uiStrings.js';
import AuthoringForm from './AuthoringForm';
import ParentReport from './ParentReport';

export default function TeacherView({ language = 'en' }) {
  const t = makeT(language);
  const [showParentReport, setShowParentReport] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authToken, setAuthToken] = useState(null);
  const [teacherName, setTeacherName] = useState('');
  const [assignedClasses, setAssignedClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('8-A');
  const [dashboard, setDashboard] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [overrideModal, setOverrideModal] = useState(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideAction, setOverrideAction] = useState('assign_concept');
  const [actionSuccess, setActionSuccess] = useState('');
  const [testSessions, setTestSessions] = useState([]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both username and password.');
      return;
    }

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.demo) {
          localStorage.setItem('setu_demo_teacher', '1');
        }
        setAuthToken(data.access_token);
        setTeacherName(data.username);
        setAssignedClasses(data.assigned_classes || []);
        if (data.assigned_classes && data.assigned_classes.length > 0) {
          setSelectedClass(data.assigned_classes[0]);
        }
        setErrorMessage('');
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || 'Authentication failed');
      }
    } catch {
      setErrorMessage('Network error during login.');
    }
  };

  // Demo mode (SETU_DEMO_MODE=true on backend): one-tap teacher entry, no password.
  const handleDemoLogin = async () => {
    setErrorMessage('');
    try {
      const res = await fetch('/api/auth/demo-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: 'teacher' })
      });
      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.access_token);
        setTeacherName(data.username);
        setAssignedClasses(data.assigned_classes || []);
        if (data.assigned_classes && data.assigned_classes.length > 0) {
          setSelectedClass(data.assigned_classes[0]);
        }
      } else if (res.status === 403) {
        setErrorMessage('Demo mode is off on the backend. Start it with SETU_DEMO_MODE=true to use one-tap entry.');
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || 'Demo login failed.');
      }
    } catch {
      setErrorMessage('Network error during demo login.');
    }
  };

  useEffect(() => {
    if (authToken) {
      fetchDashboard();
      fetchAttention();
    }
  }, [authToken, selectedClass]);

  const [attention, setAttention] = useState(null);

  const fetchAttention = async (tok) => {
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}/attention-summary`, {
        headers: { 'Authorization': `Bearer ${tok || authToken}` }
      });
      if (res.ok) setAttention(await res.json());
    } catch { /* panel is advisory; dashboard still works */ }
  };

  const fetchDashboard = async () => {
    if (!authToken) return;
    setErrorMessage('');
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
        try {
          const tRes = await fetch(`/api/teacher/class/${selectedClass}/tests`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          });
          if (tRes.ok) {
            const tData = await tRes.json();
            setTestSessions(tData.test_sessions || []);
          }
        } catch { /* test results are additive; dashboard still stands */ }
      } else {
        const err = await res.json().catch(() => ({}));
        setDashboard(null);
        setErrorMessage(err.detail || 'Access Denied: Teacher cannot view this class.');
      }
    } catch {
      setErrorMessage('Network error fetching dashboard.');
    }
  };

  const handleApplyOverride = async (e) => {
    e.preventDefault();
    const trimmed = overrideReason.trim();
    if (!trimmed) {
      setErrorMessage('Override reason is mandatory and cannot be empty.');
      return;
    }
    if (trimmed.length < 3) {
      setErrorMessage('Teacher override reason must be at least 3 characters.');
      return;
    }

    try {
      const res = await fetch('/api/teacher/override', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          class_id: selectedClass,
          student_id: overrideModal.student_id,
          concept_id: overrideModal.concept_id || 'c8_math_rational_ops',
          action: overrideAction,
          reason: trimmed
        })
      });

      if (res.ok) {
        setActionSuccess(`Override successfully applied for ${overrideModal.student_id}. Logged with mandatory reason.`);
        setOverrideModal(null);
        setOverrideReason('');
        setErrorMessage('');
        fetchDashboard();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || 'Failed to apply override');
      }
    } catch {
      setErrorMessage('Network error applying override.');
    }
  };

  if (!authToken) {
    return (
      <div className="wide-container" style={{ maxWidth: '420px', margin: '40px auto' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Teacher Sign-In</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Class-scoped authentication • Argon2 verification
        </p>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Username</label>
            <input
              id="teacher-username-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              style={{ width: '100%', padding: '10px', background: 'var(--input-bg, var(--bg-secondary))', border: '1px solid var(--border-color)', color: 'var(--input-text, #fff)', borderRadius: '6px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Password</label>
            <input
              id="teacher-password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              style={{ width: '100%', padding: '10px', background: 'var(--input-bg, var(--bg-secondary))', border: '1px solid var(--border-color)', color: 'var(--input-text, #fff)', borderRadius: '6px' }}
            />
          </div>

          <button id="teacher-signin-btn" type="submit" className="action-btn">
            Sign In
          </button>

          <button
            id="teacher-demo-btn"
            data-testid="teacher-demo-btn"
            type="button"
            onClick={handleDemoLogin}
            className="btn-secondary"
            style={{ width: '100%', borderStyle: 'dashed' }}
          >
            ⛰️ Judge demo: one-tap teacher entry (no password)
          </button>
        </form>

        {errorMessage && (
          <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--soft-red, #fca5a5)', background: 'var(--inset-bg, rgba(0,0,0,0.3))', padding: '8px', borderRadius: '4px' }}>
            {errorMessage}
          </div>
        )}
      </div>
    );
  }

  if (showParentReport) return <ParentReport token={authToken} classId={selectedClass} onClose={() => setShowParentReport(false)} />;

  return (
    <div className="wide-container">
      {/* Teacher Controls Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>{t('teacher.title')}</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Authenticated as: <strong>{teacherName}</strong> (Assigned: {assignedClasses.join(', ') || 'None'})
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{t('teacher.classView')}</label>
          <select
            id="class-selector"
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            style={{ padding: '6px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--input-text, #fff)', borderRadius: '6px' }}
          >
            <option value="8-A">Class 8-A</option>
            <option value="8-B">Class 8-B</option>
          </select>

          <button onClick={fetchDashboard} className="btn-secondary">{t('teacher.refresh')}</button>
          <button onClick={() => {
            // Tell the server the session ended (triggers demo reset sweep for demo entries).
            if (authToken) {
              fetch('/api/auth/logout', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } }).catch(() => {});
            }
            localStorage.removeItem('setu_demo_teacher');
            setAuthToken(null); setPassword('');
          }} className="btn-secondary" style={{ fontSize: '11px' }}>
            Logout
          </button>
        </div>
      </div>

      <div className="info-card" style={{ margin: '16px 0' }}>
        <h3>Bring the next step home</h3>
        <p style={{ margin: '8px 0' }}>A short parent note with one or two practice ideas. Preview it before sharing.</p>
        <button className="action-btn" onClick={() => setShowParentReport(true)}>Parent report</button>
      </div>

      {/* v3: Who needs help now - one-screen attention summary */}
      {attention && (
        <div id="attention-summary-panel" className="info-card" style={{ marginBottom: '14px', borderLeft: '4px solid var(--accent-primary)' }}>
          <h3 style={{ fontSize: '15px', marginBottom: '6px' }}>{t('teacher.attentionTitle')} ({attention.count})</h3>
          {attention.count === 0 && (
            <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>{t('teacher.attentionEmpty')}</div>
          )}
          {attention.students_needing_attention.slice(0, 8).map((s) => (
            <div key={s.student_id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-color)', fontSize: '12.5px' }}>
              <div style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                {s.student_id}{s.urgency >= 3 ? ' - ' + t('teacher.urgent') : ''}
              </div>
              {s.reasons.map((r, i) => (
                <div key={i} style={{ color: 'var(--text-secondary)' }}>- {r}</div>
              ))}
              {s.evidence_line && (
                <div style={{ color: 'var(--text-muted)', fontSize: '11.5px', marginTop: '2px' }}>
                  {t('teacher.why')}: {s.evidence_line}
                </div>
              )}
            </div>
          ))}
          {attention.override_learning && attention.override_learning.total_overrides > 0 && (
            <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '8px', background: 'var(--bg-subtle)', padding: '6px 8px', borderRadius: '6px' }}>
              {t('teacher.learnedFrom').replace('{n}', attention.override_learning.total_overrides)}
              {' '}{attention.override_learning.label}
            </div>
          )}
          {attention.count > 8 && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
              + {attention.count - 8} more. {attention.note}
            </div>
          )}
          {attention.count > 0 && attention.count <= 8 && (
            <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '6px' }}>{attention.note}</div>
          )}
        </div>
      )}

      {/* v5: teacher authoring - add/edit questions as unreviewed drafts */}
      {authToken && <AuthoringForm authToken={authToken} t={t} />}

      {/* Metrics Row */}
      {dashboard && (
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '16px' }}>
          <div className="info-card" style={{ flex: '1 1 200px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>OVERRIDE RATE (QUALITY SIGNAL)</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-blue)' }}>
              {(dashboard.override_rate * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {dashboard.total_overrides} overrides / {dashboard.total_decisions} decisions
            </div>
          </div>

          <div className="info-card" style={{ flex: '1 1 200px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>SUPPORTED GAP GROUPS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-purple)' }}>
              {Object.keys(dashboard.grouped_by_gap || {}).length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Shared prerequisite gaps</div>
          </div>

          <div className="info-card" style={{ flex: '1 1 200px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>UNDECIDED STUDENTS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-amber)' }}>
              {dashboard.undecided_students?.length || 0}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Thin/conflicting evidence ('not sure')</div>
          </div>
        </div>
      )}

      {/* Adaptive Chapter Test Results (persisted sessions) */}
      {testSessions.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
            Chapter Test Results (Adaptive)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {testSessions.map((s) => (
              <div key={s.session_id} className="clinic-box" data-testid={`test-session-${s.student_id}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{s.student_id}</strong>
                  <span className="badge-heuristic">
                    {s.status === 'completed' ? `${s.correct_count}/${s.answered_count} correct` : `in progress ${s.answered_count}/${s.planned_length}`}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {s.started_at ? new Date(s.started_at).toLocaleString() : ''}
                  {s.summary?.weakest_concept_name ? ` • Weakest: ${s.summary.weakest_concept_name}` : ''}
                </div>
                {s.summary?.misconception_tags?.length > 0 && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Misconceptions seen: {s.summary.misconception_tags.join(', ')}
                  </div>
                )}
                {s.summary && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Estimates: {s.summary.mastery_label}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Access Denied / Error Alert */}
      {errorMessage && !overrideModal && (
        <div style={{ marginTop: '16px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '16px', borderRadius: '8px', color: 'var(--soft-rose, #fda4af)' }}>
          <strong>Error:</strong> {errorMessage}
        </div>
      )}

      {actionSuccess && (
        <div style={{ marginTop: '16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', padding: '12px', borderRadius: '8px', color: 'var(--soft-green, #6ee7b7)' }}>
          {actionSuccess}
        </div>
      )}

      {/* Recommended Small-Group Clinics */}
      {dashboard?.suggested_clinics?.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
            Recommended Small-Group Clinics (~10 Minutes)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {dashboard.suggested_clinics.map((clinic) => (
              <div key={clinic.clinic_id} className="clinic-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{clinic.concept_name}</strong>
                  <span className="badge-heuristic">Suggested intervention</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Students: {(clinic.students || clinic.student_ids || []).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grouped by Supported Gap */}
      {dashboard && (
        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
            Students Grouped by Supported Gap
          </h3>
          {Object.keys(dashboard.grouped_by_gap || {}).length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No supported gap groups currently.</p>
          ) : (
            Object.entries(dashboard.grouped_by_gap).map(([gapId, students]) => (
              <div key={gapId} style={{ marginBottom: '16px', padding: '16px', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <h4 style={{ fontSize: '14px', color: 'var(--accent-purple)', marginBottom: '8px' }}>
                  Gap: {gapId} ({students.length} students)
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {students.map((st) => (
                    <div key={st.student_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-primary)', padding: '10px', borderRadius: '6px' }}>
                      <div>
                        <strong>{st.student_id}</strong> • Mastery: {((st.bkt_mastery_estimate || 0) * 100).toFixed(0)}% ({st.bkt_label}) • Concept: {st.current_concept_id}
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{st.suggested_plan_reason}</div>
                        {st.evidence_band && (
                          <div style={{ fontSize: '11px', marginTop: '3px' }}>
                            <span className="badge-uncalibrated" style={{ fontSize: '10px' }}>
                              evidence: {st.evidence_band} (rule-based, not a diagnosis)
                            </span>
                          </div>
                        )}
                        {(st.evidence_details || []).slice(0, 3).map((d, i) => (
                          <div key={i} style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            • {typeof d === 'string' ? d : JSON.stringify(d)}
                          </div>
                        ))}
                      </div>
                      <button
                        id={`override-btn-${st.student_id}`}
                        data-testid={`override-btn-${st.student_id}`}
                        onClick={() => setOverrideModal({ student_id: st.student_id, concept_id: st.gap_concept_id || st.current_concept_id })}
                        className="btn-secondary"
                        style={{ fontSize: '12px' }}
                      >
                        Override
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}

          {/* Undecided Students */}
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginTop: '24px', marginBottom: '12px' }}>
            Undecided Students (Thin / Conflicting Evidence or In-Progress)
          </h3>
          {(!dashboard.undecided_students || dashboard.undecided_students.length === 0) ? (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No undecided students.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {dashboard.undecided_students.map((st) => (
                <div key={st.student_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-secondary)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                  <div>
                    <strong>{st.student_id}</strong> • Mastery: {((st.bkt_mastery_estimate || 0) * 100).toFixed(0)}% ({st.bkt_label}) • Reason: {st.suggested_plan_reason}
                    {st.evidence_band && (
                      <div style={{ fontSize: '11px', marginTop: '3px' }}>
                        <span className="badge-uncalibrated" style={{ fontSize: '10px' }}>
                          evidence: {st.evidence_band} (rule-based, not a diagnosis)
                        </span>
                      </div>
                    )}
                    {(st.evidence_details || []).slice(0, 3).map((d, i) => (
                      <div key={i} style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        • {typeof d === 'string' ? d : JSON.stringify(d)}
                      </div>
                    ))}
                  </div>
                  <button
                    id={`override-btn-${st.student_id}`}
                    data-testid={`override-btn-${st.student_id}`}
                    onClick={() => setOverrideModal({ student_id: st.student_id, concept_id: st.current_concept_id })}
                    className="btn-secondary"
                    style={{ fontSize: '12px' }}
                  >
                    Override
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '8px', maxWidth: '480px', width: '90%', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
              Teacher Pedagogical Override: {overrideModal.student_id}
            </h3>
            {errorMessage && (
              <div id="override-error-msg" style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '10px 12px', borderRadius: '6px', color: 'var(--soft-rose, #fda4af)', fontSize: '13px', marginBottom: '12px' }}>
                {errorMessage}
              </div>
            )}
            <form onSubmit={handleApplyOverride} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Action</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'var(--input-text, #fff)', borderRadius: '6px' }}
                >
                  <option value="assign_concept">Assign Concept Directly</option>
                  <option value="mark_cleared">Mark Gap Cleared</option>
                  <option value="reinforce">Request Reinforcement</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Mandatory Pedagogical Reason</label>
                <textarea
                  id="override-reason-input"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain why the algorithmic sequence is being overridden..."
                  rows={3}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'var(--input-text, #fff)', borderRadius: '6px' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={() => { setOverrideModal(null); setErrorMessage(''); }} className="btn-secondary">
                  Cancel
                </button>
                <button id="apply-override-btn" type="submit" className="action-btn" style={{ width: 'auto' }}>
                  Log & Apply Override
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
