import React, { useState } from 'react';

export default function PaperModeView() {
  const [selectedConcept, setSelectedConcept] = useState('c8_math_linear_eq_one_var');
  const [teacherUsername, setTeacherUsername] = useState('');
  const [teacherPassword, setTeacherPassword] = useState('');
  const [teacherToken, setTeacherToken] = useState(null);
  const [authError, setAuthError] = useState('');

  const [bulkEntries, setBulkEntries] = useState([
    { student_id: 'stu_001', question_id: 'q_c8_leq_01', selected_option_id: 'opt_1' },
    { student_id: 'stu_002', question_id: 'q_c8_leq_01', selected_option_id: 'opt_2' }
  ]);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [submissionErrors, setSubmissionErrors] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePrintWorksheet = async () => {
    setAuthError('');
    let token = teacherToken;

    if (!token) {
      if (!teacherUsername.trim() || !teacherPassword.trim()) {
        setAuthError('Please enter teacher username and password to generate and print worksheets.');
        return;
      }
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: teacherUsername.trim(), password: teacherPassword.trim() })
        });
        if (res.ok) {
          const data = await res.json();
          token = data.access_token;
          setTeacherToken(token);
        } else {
          const err = await res.json().catch(() => ({}));
          setAuthError(err.detail || 'Authentication failed. Please verify teacher credentials.');
          return;
        }
      } catch {
        setAuthError('Network error authenticating teacher for printable sheet.');
        return;
      }
    }

    try {
      const res = await fetch(`/api/paper/sheet/${selectedConcept}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setAuthError(err.detail || `Failed to fetch printable sheet (${res.status}).`);
        return;
      }

      const htmlContent = await res.text();
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.open();
        printWindow.document.write(htmlContent);
        printWindow.document.close();
      } else {
        const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.target = '_blank';
        link.click();
        setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      }
    } catch {
      setAuthError('Network error fetching printable worksheet.');
    }
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

  return <div className="wide-container paper-mode-page">
    <header className="paper-heading"><p className="paper-eyebrow">FROM PAPER TO PRACTICE</p><h1>Teacher-Mediated Paper Mode</h1><p>Learning can start on a worksheet. Bring saved classroom answers back into the same adaptive engine.</p></header>
    <div className="paper-top-grid"><section className="paper-card paper-generator"><span className="paper-step">01 / PREPARE</span><h2>Generate Printable Question Worksheet</h2><p>Open a clean worksheet with question codes and option bubbles for offline classroom use.</p><label>Choose a concept<select aria-label="Worksheet concept" value={selectedConcept} onChange={e => setSelectedConcept(e.target.value)}><option value="c8_math_linear_eq_one_var">Linear Equations in One Variable (Class 8)</option><option value="c8_math_rational_ops">Operations on Rational Numbers (Class 8)</option><option value="c8_math_squares_square_roots">Squares and Square Roots (Class 8)</option></select></label><button className="action-btn" onClick={handlePrintWorksheet}>Open Printable Sheet in New Tab</button><small>Teacher sign-in is required. The worksheet opens separately.</small></section>
      <section className="paper-card paper-auth"><span className="paper-step">TEACHER ACCESS</span><h2>{teacherToken ? 'Your teacher session is ready.' : 'Sign in to keep records safe.'}</h2>{!teacherToken ? <><p>Your existing teacher account is used for worksheets and bulk entry.</p><label htmlFor="teacher-paper-username">Teacher username</label><input id="teacher-paper-username" type="text" autoComplete="username" value={teacherUsername} onChange={e => setTeacherUsername(e.target.value)} placeholder="Teacher username"/><label htmlFor="teacher-paper-password">Password</label><input id="teacher-paper-password" type="password" autoComplete="current-password" value={teacherPassword} onChange={e => setTeacherPassword(e.target.value)} placeholder="Password"/><button onClick={handleTeacherLogin} className="btn-secondary">Sign In</button></> : <><span className="paper-ready">✓ Signed in</span><p>The server checks access to each student's class before processing their answer.</p><small>Review student, question and option IDs before submitting. Results are saved to real learner records.</small></>}</section>
    </div>
    {authError && <p className="paper-notice is-error" role="alert">{authError}</p>}
    <section className="paper-card paper-entry"><div className="paper-entry-title"><div><p className="paper-eyebrow">02 / RECORD THE ANSWERS</p><h2>Bulk Response Entry (Teacher Form)</h2></div><button onClick={handleAddRow} className="btn-secondary">+ Add Student Row</button></div><p>Enter the chosen options from collected paper sheets. The server grades saved answers and updates mastery using the existing adaptive engine.</p><div className="paper-example-note">Example rows are prefilled. Replace them with the actual student, question and option IDs before submitting.</div>
    <div className="paper-entry-rows">{bulkEntries.map((row,index) => <article className="paper-entry-row" key={index}><span className="paper-row-number">{String(index + 1).padStart(2,'0')}</span><label htmlFor={`bulk-student-id-${index}`}>Student pseudonym<input id={`bulk-student-id-${index}`} data-testid={`bulk-student-id-${index}`} value={row.student_id} onChange={e => handleUpdateRow(index,'student_id',e.target.value)} placeholder="Student pseudonym"/></label><label htmlFor={`bulk-question-id-${index}`}>Question ID<input id={`bulk-question-id-${index}`} data-testid={`bulk-question-id-${index}`} value={row.question_id} onChange={e => handleUpdateRow(index,'question_id',e.target.value)} placeholder="Question ID"/></label><label htmlFor={`bulk-option-id-${index}`}>Chosen option ID<input id={`bulk-option-id-${index}`} data-testid={`bulk-option-id-${index}`} value={row.selected_option_id} onChange={e => handleUpdateRow(index,'selected_option_id',e.target.value)} placeholder="Option ID (opt_1, etc.)"/></label>{bulkEntries.length > 1 && <button className="paper-remove" aria-label={`Remove row ${index+1}`} onClick={() => handleRemoveRow(index)}>×</button>}</article>)}</div>
    <div className="paper-submit"><p>Submitting writes the answers to learner records. Check the IDs and choices first.</p><button id="process-bulk-paper-btn" data-testid="process-bulk-paper-btn" onClick={handleRealBulkSubmit} disabled={isSubmitting} className="action-btn">{isSubmitting ? 'Processing...' : 'Process Bulk Responses Through Engine'}</button></div>
        {/* Server Confirmed Results (Failure 8) */}
        {submissionResult && submissionResult.processed_count > 0 && (
          <div
            id="bulk-paper-success"
            data-testid="bulk-paper-success"
            style={{ marginTop: '12px', fontSize: '13px', color: 'var(--soft-green, #6ee7b7)', background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}
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
                      <td style={{ padding: '6px', color: res.is_correct ? 'var(--soft-green, #6ee7b7)' : 'var(--soft-red, #fca5a5)' }}>
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
            style={{ marginTop: '12px', fontSize: '13px', color: 'var(--soft-red, #fca5a5)', background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}
          >
            <strong>Bulk Submission Errors:</strong>
            <ul style={{ margin: '6px 0 0 16px', padding: 0 }}>
              {submissionErrors.map((err, i) => (
                <li key={i}>{err.student_id ? `[${err.student_id}] ` : ''}{err.error}</li>
              ))}
            </ul>
          </div>
        )}
    </section>
  </div>;
}
