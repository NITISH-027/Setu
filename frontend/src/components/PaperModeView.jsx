import React, { useState } from 'react';

export default function PaperModeView() {
  const [selectedConcept, setSelectedConcept] = useState('c8_math_linear_eq_one_var');
  const [teacherUsername, setTeacherUsername] = useState('teacher_ravi');
  const [teacherPassword, setTeacherPassword] = useState('teacher123');
  const [teacherToken, setTeacherToken] = useState(null);
  const [authError, setAuthError] = useState('');

  const [bulkEntries, setBulkEntries] = useState([
    { student_id: 'stu_001', question_id: 'q_c8_leq_01', selected_option_id: 'opt_1' },
    { student_id: 'stu_002', question_id: 'q_c8_leq_01', selected_option_id: 'opt_2' }
  ]);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [submissionErrors, setSubmissionErrors] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePrintWorksheet = () => {
    window.open(`/api/paper/sheet/${selectedConcept}`, '_blank');
  };

  const handleAddRow = () => {
    setBulkEntries([
      ...bulkEntries,
      { student_id: `stu_00${bulkEntries.length + 1}`, question_id: 'q_c8_leq_01', selected_option_id: 'opt_1' }
    ]);
  };

  const handleUpdateRow = (idx, field, value) => {
    const updated = [...bulkEntries];
    updated[idx][field] = value;
    setBulkEntries(updated);
  };

  const handleRemoveRow = (idx) => {
    setBulkEntries(bulkEntries.filter((_, i) => i !== idx));
  };

  const handleTeacherLogin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setAuthError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: teacherUsername.trim(), password: teacherPassword.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        setTeacherToken(data.access_token);
        setAuthError('');
      } else {
        const err = await res.json().catch(() => ({}));
        setAuthError(err.detail || 'Authentication failed');
      }
    } catch {
      setAuthError('Network error logging in as teacher.');
    }
  };

  const handleRealBulkSubmit = async () => {
    setIsSubmitting(true);
    setSubmissionResult(null);
    setSubmissionErrors([]);

    let activeToken = teacherToken;
    if (!activeToken) {
      // Auto-authenticate with entered credentials
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: teacherUsername.trim(), password: teacherPassword.trim() })
        });
        if (res.ok) {
          const data = await res.json();
          activeToken = data.access_token;
          setTeacherToken(activeToken);
        } else {
          setAuthError('Teacher authentication required to submit bulk paper responses.');
          setIsSubmitting(false);
          return;
        }
      } catch {
        setAuthError('Network error logging in as teacher.');
        setIsSubmitting(false);
        return;
      }
    }

    try {
      const res = await fetch('/api/teacher/bulk-paper-submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${activeToken}`
        },
        body: JSON.stringify({ responses: bulkEntries })
      });

      if (res.ok) {
        const data = await res.json();
        setSubmissionResult(data);
        if (data.errors && data.errors.length > 0) {
          setSubmissionErrors(data.errors);
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setSubmissionErrors([{ error: err.detail || 'Server error submitting paper responses.' }]);
      }
    } catch (err) {
      setSubmissionErrors([{ error: 'Network error calling bulk-paper-submit API.' }]);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="wide-container">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Teacher-Mediated Paper Mode</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          India Fit • No device at home • Printable question sets + bulk response entry
        </p>
      </div>

      {/* Generator Section */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Generate Printable Question Worksheet
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Outputs formatted clean printable HTML with question codes and option bubbles for offline classroom administration.
        </p>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            value={selectedConcept}
            onChange={(e) => setSelectedConcept(e.target.value)}
            style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          >
            <option value="c8_math_linear_eq_one_var">Linear Equations in One Variable (Class 8)</option>
            <option value="c8_math_rational_ops">Operations on Rational Numbers (Class 8)</option>
            <option value="c8_math_squares_square_roots">Squares and Square Roots (Class 8)</option>
          </select>

          <button onClick={handlePrintWorksheet} className="btn-secondary" style={{ borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }}>
            Open Printable Sheet in New Tab
          </button>
        </div>
      </div>

      {/* Teacher Authentication Card */}
      {!teacherToken && (
        <div className="info-card" style={{ background: 'rgba(56, 189, 248, 0.05)' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
            Teacher Credentials (Required for Bulk Paper Entry)
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              id="teacher-paper-username"
              type="text"
              value={teacherUsername}
              onChange={(e) => setTeacherUsername(e.target.value)}
              placeholder="Teacher Username"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <input
              id="teacher-paper-password"
              type="password"
              value={teacherPassword}
              onChange={(e) => setTeacherPassword(e.target.value)}
              placeholder="Password"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <button onClick={handleTeacherLogin} className="btn-secondary">
              Sign In
            </button>
          </div>
          {authError && <div style={{ fontSize: '12px', color: '#fca5a5', marginTop: '6px' }}>{authError}</div>}
        </div>
      )}

      {/* Bulk Entry Real Teacher Form (Failure 8) */}
      <div className="info-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700' }}>
            Bulk Response Entry (Teacher Form)
          </h3>
          <button onClick={handleAddRow} className="btn-secondary" style={{ fontSize: '12px', padding: '4px 8px' }}>
            + Add Student Row
          </button>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Teacher collects physical sheets and inputs chosen options in bulk.
          Submitted via real API endpoint (POST /api/teacher/bulk-paper-submit). Real AttemptDB and MasteryStateDB rows are updated.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
          {bulkEntries.map((row, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                id={`bulk-student-id-${idx}`}
                data-testid={`bulk-student-id-${idx}`}
                type="text"
                placeholder="Student Pseudonym"
                value={row.student_id}
                onChange={(e) => handleUpdateRow(idx, 'student_id', e.target.value)}
                style={{ width: '130px', padding: '6px 8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', fontSize: '12px' }}
              />
              <input
                id={`bulk-question-id-${idx}`}
                data-testid={`bulk-question-id-${idx}`}
                type="text"
                placeholder="Question ID"
                value={row.question_id}
                onChange={(e) => handleUpdateRow(idx, 'question_id', e.target.value)}
                style={{ width: '130px', padding: '6px 8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', fontSize: '12px' }}
              />
              <input
                id={`bulk-option-id-${idx}`}
                data-testid={`bulk-option-id-${idx}`}
                type="text"
                placeholder="Option ID (opt_1, etc.)"
                value={row.selected_option_id}
                onChange={(e) => handleUpdateRow(idx, 'selected_option_id', e.target.value)}
                style={{ width: '120px', padding: '6px 8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', fontSize: '12px' }}
              />
              {bulkEntries.length > 1 && (
                <button
                  onClick={() => handleRemoveRow(idx)}
                  className="btn-secondary"
                  style={{ fontSize: '10px', padding: '4px 6px', color: '#fca5a5', borderColor: '#fca5a5' }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>

        <button
          id="process-bulk-paper-btn"
          data-testid="process-bulk-paper-btn"
          onClick={handleRealBulkSubmit}
          disabled={isSubmitting}
          className="action-btn"
          style={{ width: 'auto' }}
        >
          {isSubmitting ? 'Processing...' : 'Process Bulk Responses Through Engine'}
        </button>

        {/* Server Confirmed Results (Failure 8) */}
        {submissionResult && submissionResult.processed_count > 0 && (
          <div
            id="bulk-paper-success"
            data-testid="bulk-paper-success"
            style={{ marginTop: '12px', fontSize: '13px', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}
          >
            <strong>Server Confirmed:</strong> Processed {submissionResult.processed_count} physical paper sheet responses through AdaptiveEngine.
            <div style={{ marginTop: '8px', overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '6px' }}>Student</th>
                    <th style={{ padding: '6px' }}>Correct?</th>
                    <th style={{ padding: '6px' }}>Next Stage</th>
                    <th style={{ padding: '6px' }}>Updated Mastery</th>
                  </tr>
                </thead>
                <tbody>
                  {submissionResult.results.map((res, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '6px', fontWeight: '600' }}>{res.student_id}</td>
                      <td style={{ padding: '6px', color: res.is_correct ? '#6ee7b7' : '#fca5a5' }}>
                        {res.is_correct ? 'Correct' : 'Incorrect'}
                      </td>
                      <td style={{ padding: '6px' }}>{res.next_step?.stage || 'solve'}</td>
                      <td style={{ padding: '6px' }}>{((res.updated_mastery || 0) * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Structured Errors (Failure 8 & Acceptance Test H) */}
        {submissionErrors.length > 0 && (
          <div
            id="bulk-paper-errors"
            data-testid="bulk-paper-errors"
            style={{ marginTop: '12px', fontSize: '13px', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}
          >
            <strong>Bulk Submission Errors:</strong>
            <ul style={{ margin: '6px 0 0 16px', padding: 0 }}>
              {submissionErrors.map((err, i) => (
                <li key={i}>{err.student_id ? `[${err.student_id}] ` : ''}{err.error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
