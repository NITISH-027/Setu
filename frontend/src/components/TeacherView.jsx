import React, { useState, useEffect } from 'react';

export default function TeacherView() {
  const [teacherId, setTeacherId] = useState('tea_01');
  const [selectedClass, setSelectedClass] = useState('8-A');
  const [dashboard, setDashboard] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [overrideModal, setOverrideModal] = useState(null); // { student_id, concept_id }
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideAction, setOverrideAction] = useState('assign_concept');
  const [actionSuccess, setActionSuccess] = useState('');

  useEffect(() => {
    fetchDashboard();
  }, [teacherId, selectedClass]);

  const fetchDashboard = async () => {
    setErrorMessage('');
    setActionSuccess('');
    try {
      const res = await fetch(`/api/teacher/class/${selectedClass}?teacher_id=${teacherId}`);
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
      } else {
        const err = await res.json();
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: teacherId,
          class_id: selectedClass,
          student_id: overrideModal.student_id,
          concept_id: overrideModal.concept_id || 'c8_math_rational_ops',
          action: overrideAction,
          reason: overrideReason
        })
      });

      if (res.ok) {
        setActionSuccess(`Override successfully applied for ${overrideModal.student_id}. Logged with reason.`);
        setOverrideModal(null);
        setOverrideReason('');
        fetchDashboard();
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || 'Failed to apply override');
      }
    } catch {
      setErrorMessage('Network error applying override.');
    }
  };

  return (
    <div className="wide-container">
      {/* Teacher Controls Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Teacher Control Dashboard</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Authenticated as: <strong>{teacherId}</strong> (Authorized for Class 8-A)
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Class View:</label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            style={{ padding: '6px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          >
            <option value="8-A">Class 8-A (Assigned)</option>
            <option value="8-B">Class 8-B (Restricted / Other Class)</option>
          </select>

          <button onClick={fetchDashboard} className="btn-secondary">Refresh</button>
        </div>
      </div>

      {/* Metrics Row */}
      {dashboard && (
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
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
              {Object.keys(dashboard.grouped_by_gap).length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Shared prerequisite gaps</div>
          </div>

          <div className="info-card" style={{ flex: '1 1 200px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>UNDECIDED STUDENTS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-amber)' }}>
              {dashboard.undecided_students.length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Thin/conflicting evidence ('not sure')</div>
          </div>
        </div>
      )}

      {/* Access Denied Alert for Negative Test Demonstration */}
      {errorMessage && (
        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '16px', borderRadius: '8px', color: '#fda4af' }}>
          <strong>Class Scoping Boundary:</strong> {errorMessage}
        </div>
      )}

      {actionSuccess && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', padding: '12px', borderRadius: '8px', color: '#6ee7b7' }}>
          {actionSuccess}
        </div>
      )}

      {/* Recommended 10-Minute Clinics */}
      {dashboard?.suggested_clinics?.length > 0 && (
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
            Recommended Small-Group Clinics (~10 Minutes)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {dashboard.suggested_clinics.map((clinic) => (
              <div key={clinic.clinic_id} className="clinic-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{clinic.concept_name}</strong>
                  <span style={{ fontSize: '11px', background: 'rgba(16, 185, 129, 0.3)', padding: '2px 6px', borderRadius: '4px' }}>
                    {clinic.recommended_duration_minutes} Mins
                  </span>
                </div>
                <div style={{ margin: '6px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {clinic.reason} (Students: {clinic.student_ids.join(', ')})
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grouped by Prerequisite Gap */}
      {dashboard && (
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
            Students Grouped by Supported Prerequisite Gap
          </h3>
          {Object.keys(dashboard.grouped_by_gap).length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No shared prerequisite gaps currently supported by probes.</p>
          ) : (
            <div className="dashboard-grid">
              {Object.entries(dashboard.grouped_by_gap).map(([gapId, students]) => (
                <div key={gapId} className="gap-group-card supported">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '14px', color: 'var(--accent-purple)' }}>{gapId}</strong>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{students.length} student(s)</span>
                  </div>

                  {students.map((st) => (
                    <div key={st.student_id} className="info-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>{st.student_id}</strong>
                        <span style={{ fontSize: '11px', color: 'var(--accent-amber)' }}>
                          BKT: {(st.bkt_mastery_estimate * 100).toFixed(0)}% (uncalibrated)
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Evidence Band: <strong>{st.evidence_band}</strong> (heuristic score: {st.evidence_score})
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Reason: {st.suggested_plan_reason}
                      </div>

                      <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                        <button
                          onClick={() => setOverrideModal({ student_id: st.student_id, concept_id: gapId })}
                          className="btn-secondary"
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                        >
                          Override Plan
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Undecided Students ("not sure" evidence) */}
      {dashboard?.undecided_students?.length > 0 && (
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px', color: '#fcd34d' }}>
            Undecided Students (Uncertainty Stated — Not Grouped into Gaps)
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Rule 3 Enforcement: Thin or conflicting probe evidence produces "not sure". Never a forced gap diagnosis.
          </p>

          <div className="dashboard-grid">
            {dashboard.undecided_students.map((st) => (
              <div key={st.student_id} className="gap-group-card undecided">
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>{st.student_id}</strong>
                  <span style={{ fontSize: '11px', color: 'var(--accent-amber)' }}>Status: Undecided</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Evidence Band: <strong>{st.evidence_band || 'None / Not Sure'}</strong>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  BKT Estimate: {(st.bkt_mastery_estimate * 100).toFixed(0)}% (uncalibrated, hand-set)
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Suggested Action: {st.suggested_plan_reason}
                </div>

                <button
                  onClick={() => setOverrideModal({ student_id: st.student_id, concept_id: st.current_concept_id })}
                  className="btn-secondary"
                  style={{ fontSize: '11px', padding: '4px 8px', marginTop: '6px' }}
                >
                  Teacher Intervention / Assign Concept
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="info-card" style={{ maxWidth: '440px', width: '90%', background: 'var(--bg-secondary)', border: '1px solid var(--accent-blue)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>
              Teacher Override: {overrideModal.student_id}
            </h3>

            <form onSubmit={handleApplyOverride} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Override Action</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
                >
                  <option value="assign_concept">Assign Different Concept</option>
                  <option value="close_gap">Mark Prerequisite Gap Closed</option>
                  <option value="skip_to_enrichment">Advance to Enrichment</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Mandatory Reason <span style={{ color: 'var(--accent-rose)' }}>*</span>
                </label>
                <textarea
                  rows="3"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="e.g. Student resolved integer sign error during small group clinic."
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
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
