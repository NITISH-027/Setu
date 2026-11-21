import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

import { makeT } from '../i18n/uiStrings.js';
import AuthoringForm from './AuthoringForm';
import LoginShell, { LoginField } from './LoginShell';
import ParentReport from './ParentReport';
import TeacherDashboard from './TeacherDashboard';
import TeacherLearnerRows from './TeacherLearnerRows';

export default function TeacherView({ language = 'en', loginNavigation, onAuthChange }) {
  const t = makeT(language);
  const [showParentReport, setShowParentReport] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authToken, setAuthToken] = useState(null);
  useEffect(() => {
    onAuthChange?.(Boolean(authToken));
    return () => onAuthChange?.(false);
  }, [authToken, onAuthChange]);
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
  const [testsLoaded, setTestsLoaded] = useState(false);
  const currentScope = useRef('');
  currentScope.current = `${authToken}:${selectedClass}`;


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
      setDashboard(null); setAttention(null); setTestSessions([]); setTestsLoaded(false);
      setOverrideModal(null); setOverrideReason(''); setActionSuccess('');
      fetchDashboard();
      fetchAttention();
    }
  }, [authToken, selectedClass]);

  const [attention, setAttention] = useState(null);

  const fetchAttention = async (tok) => {
    const scope = currentScope.current;
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}/attention-summary`, {
        headers: { 'Authorization': `Bearer ${tok || authToken}` }
      });
      const data = res.ok ? await res.json() : null;
      if (scope === currentScope.current) setAttention(data);
    } catch { /* panel is advisory; dashboard still works */ }
  };

  const fetchDashboard = async () => {
    if (!authToken) return;
    const scope = currentScope.current;
    setErrorMessage('');
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (scope !== currentScope.current) return;
        setDashboard(data);
        try {
          const tRes = await fetch(`/api/teacher/class/${selectedClass}/tests`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          });
          if (tRes.ok) {
            const tData = await tRes.json();
            if (scope === currentScope.current) { setTestSessions(tData.test_sessions || []); setTestsLoaded(true); }
          }
        } catch { /* test results are additive; dashboard still stands */ }
      } else {
        const err = await res.json().catch(() => ({}));
        if (scope !== currentScope.current) return;
        setDashboard(null);
        setAttention(null); setTestSessions([]);
        setErrorMessage(err.detail || 'Access Denied: Teacher cannot view this class.');
      }
    } catch {
      if (scope === currentScope.current) { setDashboard(null); setAttention(null); setTestSessions([]); setTestsLoaded(false); setErrorMessage('Network error fetching dashboard.'); }
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
        fetchDashboard(); fetchAttention();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || 'Failed to apply override');
      }
    } catch {
      setErrorMessage('Network error applying override.');
    }
  };

  const handleLogout = () => {
    if (authToken) fetch('/api/auth/logout', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } }).catch(() => {});
    localStorage.removeItem('setu_demo_teacher');
    setAuthToken(null); setPassword(''); setDashboard(null); setAttention(null); setTestSessions([]); setTestsLoaded(false);
  };

  if (!authToken) {
    return (
      <LoginShell role="teacher" {...loginNavigation} language={language}>
        <form onSubmit={handleLogin} className="setu-login-form">
          <LoginField label="Username" id="teacher-username-input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" autoComplete="username" autoCapitalize="none" spellCheck={false} required />
          <LoginField label="Password" secret id="teacher-password-input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" required />
          <button id="teacher-signin-btn" type="submit" className="setu-login-submit">Log in</button>
        </form>
        {errorMessage && <div className="setu-login-status" role="alert">{errorMessage}</div>}
        <div className="setu-login-divider">or explore a demo</div>
        <button id="teacher-demo-btn" data-testid="teacher-demo-btn" type="button" onClick={handleDemoLogin} className="setu-login-secondary">Try the teacher demo</button>
        <p className="setu-login-demo-hint">No password needed when demo mode is enabled.</p>
      </LoginShell>
    );
  }

  if (showParentReport) return <div className="setu-teacher-report"><ParentReport token={authToken} classId={selectedClass} onClose={() => setShowParentReport(false)} /></div>;

  return (
    <TeacherDashboard teacherName={teacherName} assignedClasses={assignedClasses} selectedClass={selectedClass} dashboard={dashboard} attention={attention} testSessions={testsLoaded ? testSessions : null} onLogout={handleLogout} onParentReport={() => setShowParentReport(true)}>
    <div className="teacher-workspace-content">
      <header className="teacher-workspace-toolbar">
        <div><p className="teacher-eyebrow">CLASSROOM WORKSPACE</p><h2>Small steps, thoughtful support.</h2><p>Signed in as <strong>{teacherName}</strong> · Assigned: {assignedClasses.join(', ') || 'None'}</p></div>
        <div className="teacher-workspace-actions"><label htmlFor="class-selector">{t('teacher.classView')}<select id="class-selector" value={selectedClass} onChange={e => setSelectedClass(e.target.value)}><option value="8-A">Class 8-A</option><option value="8-B">Class 8-B</option></select></label><button onClick={() => { fetchDashboard(); fetchAttention(); }} className="btn-secondary">{t('teacher.refresh')}</button></div>
      </header>
      {errorMessage && !overrideModal && <div className="teacher-notice is-error" role="alert"><strong>Error:</strong> {errorMessage}</div>}
      {actionSuccess && <div className="teacher-notice is-success" role="status">{actionSuccess}</div>}
      <div className="teacher-workspace-top">
        <section id="attention-summary-panel" className="teacher-card">
          <div className="teacher-card-heading"><div><p className="teacher-eyebrow">A CLOSER LOOK</p><h3>{t('teacher.attentionTitle')}</h3></div><span className="teacher-count">{attention?.count ?? '—'}</span></div>
          {!attention && <p className="teacher-muted">Attention summary is loading or unavailable.</p>}
          {attention?.count === 0 && <div className="teacher-empty"><span aria-hidden="true">✦</span><p>{t('teacher.attentionEmpty')}</p></div>}
          {attention?.students_needing_attention.slice(0, 8).map(student => <article className="teacher-attention-row" key={student.student_id}><strong>{student.student_id}{student.urgency >= 3 ? ' - ' + t('teacher.urgent') : ''}</strong>{student.reasons.map((reason, index) => <p key={index}>{reason}</p>)}{student.evidence_line && <small>{t('teacher.why')}: {student.evidence_line}</small>}</article>)}
          {attention?.override_learning?.total_overrides > 0 && <p className="teacher-muted">{t('teacher.learnedFrom').replace('{n}', attention.override_learning.total_overrides)} {attention.override_learning.label}</p>}
          {attention?.count > 8 && <p className="teacher-muted">+ {attention.count - 8} more. {attention.note}</p>}
          {attention?.count > 0 && attention.count <= 8 && <p className="teacher-muted">{attention.note}</p>}
        </section>
        <section className="teacher-card teacher-parent-card"><span className="teacher-evidence-pill">SCHOOL TO HOME</span><h3>Bring the next step home.</h3><p>A short parent note with one or two practice ideas. Preview it before sharing.</p><button className="action-btn" onClick={() => setShowParentReport(true)}>Parent report</button><small>Nothing is shared automatically.</small></section>
      </div>
      {authToken && <AuthoringForm authToken={authToken} t={t} />}
      {dashboard && <>
        <section className="teacher-card">
          <div className="teacher-card-heading"><div><p className="teacher-eyebrow">SHARED PREREQUISITES</p><h3>Students grouped by supported gap</h3></div><span className="teacher-count">{Object.keys(dashboard.grouped_by_gap || {}).length} groups</span></div>
          <p className="teacher-muted">Evidence is rule-based, not a diagnosis. Review the details before overriding.</p>
          {Object.keys(dashboard.grouped_by_gap || {}).length === 0 ? <div className="teacher-empty"><span aria-hidden="true">◎</span><p>No supported gap groups currently.</p></div> : Object.entries(dashboard.grouped_by_gap).map(([gapId, students]) => <section className="teacher-gap-group" key={gapId}><h4>{gapId}<span>{students.length} learners</span></h4><TeacherLearnerRows students={students} onOverride={setOverrideModal} supported /></section>)}
        </section>
        <section className="teacher-card">
          <div className="teacher-card-heading"><div><p className="teacher-eyebrow">KEEP OBSERVING</p><h3>Undecided learners</h3></div><span className="teacher-count">{dashboard.undecided_students?.length || 0}</span></div><p className="teacher-muted">Thin or conflicting evidence, or practice still in progress. Mastery estimates are uncalibrated and hand-set.</p>
          {dashboard.undecided_students?.length ? <TeacherLearnerRows students={dashboard.undecided_students} onOverride={setOverrideModal} /> : <div className="teacher-empty"><p>No undecided students.</p></div>}
        </section>
        <section className="teacher-card teacher-quality"><div><p className="teacher-eyebrow">QUALITY SIGNAL</p><h3>Teacher judgment, recorded.</h3><p>{dashboard.total_overrides} overrides / {dashboard.total_decisions} saved decisions. Every override keeps its pedagogical reason.</p></div><strong>{(dashboard.override_rate * 100).toFixed(1)}%<small>override rate</small></strong></section>
      </>}
      <section className="teacher-card"><div className="teacher-card-heading"><div><p className="teacher-eyebrow">SAVED CHAPTER TESTS</p><h3>Learning, one answer at a time.</h3></div><span className="teacher-count">{testsLoaded ? testSessions.length : '—'}</span></div>
        {!testSessions.length && <div className="teacher-empty"><p>{testsLoaded ? 'No saved chapter-test sessions in this class yet.' : 'Chapter-test sessions are loading or unavailable.'}</p></div>}
        {testSessions.map(session => <article className="teacher-session" key={session.session_id} data-testid={`test-session-${session.student_id}`}><div><strong>{session.student_id}</strong><span className="teacher-evidence-pill">{session.status === 'completed' ? `${session.correct_count}/${session.answered_count} correct` : `in progress ${session.answered_count}/${session.planned_length}`}</span></div><p>{session.started_at ? new Date(session.started_at).toLocaleString() : ''}{session.summary?.weakest_concept_name ? ` · Weakest: ${session.summary.weakest_concept_name}` : ''}</p>{session.summary?.misconception_tags?.length > 0 && <small>Misconceptions seen: {session.summary.misconception_tags.join(', ')}</small>}{session.summary && <small>Estimates: {session.summary.mastery_label}</small>}</article>)}
      </section>
      {dashboard?.suggested_clinics?.length > 0 && <section className="teacher-card"><div className="teacher-card-heading"><div><p className="teacher-eyebrow">ABOUT TEN MINUTES</p><h3>Suggested small-group clinics</h3></div></div>{dashboard.suggested_clinics.map(clinic => <article className="teacher-session" key={clinic.clinic_id}><strong>{clinic.concept_name}</strong><p>Students: {(clinic.students || clinic.student_ids || []).join(', ')}</p><span className="teacher-evidence-pill">Suggested intervention</span></article>)}</section>}
      {/* Override Modal */}
      {overrideModal && createPortal(
        <div className="setu-teacher-modal" role="dialog" aria-modal="true" aria-label="Teacher pedagogical override" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
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
      , document.body)}
    </div>
    </TeacherDashboard>
  );
}
