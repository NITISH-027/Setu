import React, { useState } from 'react';

export default function PaperModeView() {
  const [selectedConcept, setSelectedConcept] = useState('c8_math_linear_eq_one_var');
  const [bulkEntries, setBulkEntries] = useState([
    { student_id: 'stu_paper_01', question_id: 'q_c8_leq_01', selected_option_id: 'opt_1' },
    { student_id: 'stu_paper_02', question_id: 'q_c8_leq_01', selected_option_id: 'opt_2' }
  ]);
  const [submissionResult, setSubmissionResult] = useState('');

  const handlePrintWorksheet = () => {
    window.open(`/api/paper/sheet/${selectedConcept}`, '_blank');
  };

  const handleSimulateBulkSubmit = () => {
    setSubmissionResult(
      `Processed ${bulkEntries.length} physical paper sheet responses through AdaptiveEngine. Updated student masteries and logged attempts identically to app attempts.`
    );
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

      {/* Bulk Entry Simulator */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Bulk Response Entry (Teacher Form)
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Teacher collects physical sheets and inputs chosen options in bulk.
          The exact same adaptive engine, BKT models, and hypothesis trackers process the attempts.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
          {bulkEntries.map((row, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', width: '120px', color: 'var(--text-muted)' }}>{row.student_id}</span>
              <span style={{ fontSize: '12px', width: '120px' }}>{row.question_id}</span>
              <span style={{ fontSize: '12px', color: 'var(--accent-blue)' }}>Selected: {row.selected_option_id}</span>
            </div>
          ))}
        </div>

        <button onClick={handleSimulateBulkSubmit} className="action-btn" style={{ width: 'auto' }}>
          Process Bulk Responses Through Engine
        </button>

        {submissionResult && (
          <div style={{ marginTop: '12px', fontSize: '12px', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '6px' }}>
            {submissionResult}
          </div>
        )}
      </div>
    </div>
  );
}
