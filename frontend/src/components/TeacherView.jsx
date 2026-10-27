import React, { useState, useEffect } from 'react';

export default function TeacherView() {
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

  useEffect(() => {
    if (authToken) {
      fetchDashboard();
    }
  }, [authToken, selectedClass]);

  const fetchDashboard = async () => {
    if (!authToken) return;
    setErrorMessage('');
    setActionSuccess('');
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
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
    if (!overrideReason.trim()) {
      setErrorMessage('Override reason is mandatory and cannot be empty.');
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
          reason: overrideReason.trim()
        })
      });

      if (res.ok) {
        setActionSuccess(`Override successfully applied for ${overrideModal.student_id}. Logged with mandatory reason.`);
        setOverrideModal(null);
        setOverrideReason('');
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
              style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
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
              style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
          </div>

          <button id="teacher-signin-btn" type="submit" className="action-btn">
            Sign In
          </button>
        </form>

        {errorMessage && (
          <div style={{ marginTop: '12px', fontSize: '12px', color: '#fca5a5', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px' }}>
            {errorMessage}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="wide-container">
      {/* Teacher Controls Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Teacher Control Dashboard</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Authenticated as: <strong>{teacherName}</strong> (Assigned: {assignedClasses.join(', ') || 'None'})
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Class View:</label>
          <select
            id="class-selector"
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            style={{ padding: '6px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          >
            <option value="8-A">Class 8-A</option>
            <option value="8-B">Class 8-B</option>
          </select>

          <button onClick={fetchDashboard} className="btn-secondary">Refresh</button>
          <button onClick={() => { setAuthToken(null); setPassword(''); }} className="btn-secondary" style={{ fontSize: '11px' }}>
            Logout
          </button>
        </div>
      </div>

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

      {/* Access Denied Alert for Negative Test Demonstration */}
      {errorMessage && (
        <div style={{ marginTop: '16px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '16px', borderRadius: '8px', color: '#fda4af' }}>
          <strong>Class Scoping Boundary:</strong> {errorMessage}
        </div>
      )}

      {actionSuccess && (
        <div style={{ marginTop: '16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', padding: '12px', borderRadius: '8px', color: '#6ee7b7' }}>
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
                  Students: {clinic.students.join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '8px', maxWidth: '480px', width: '90%', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
              Teacher Pedagogical Override: {overrideModal.student_id}
            </h3>
            <form onSubmit={handleApplyOverride} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Action</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
                >
                  <option value="assign_concept">Assign Concept Directly</option>
                  <option value="mark_cleared">Mark Gap Cleared</option>
                  <option value="reinforce">Request Reinforcement</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Mandatory Pedagogical Reason</label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain why the algorithmic sequence is being overridden..."
                  rows={3}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={() => setOverrideModal(null)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="action-btn" style={{ width: 'auto' }}>
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
