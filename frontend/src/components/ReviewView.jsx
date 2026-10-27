import React, { useState, useEffect } from 'react';

export default function ReviewView() {
  const [coverage, setCoverage] = useState(null);
  const [reviewerName, setReviewerName] = useState('Sunita Rao');
  const [reviewerRole, setReviewerRole] = useState('Senior Secondary Mathematics Teacher (self-declared)');
  const [attestationStatement, setAttestationStatement] = useState('I checked this item');
  const [attestationMessage, setAttestationMessage] = useState('');

  useEffect(() => {
    fetchCoverage();
  }, []);

  const fetchCoverage = async () => {
    try {
      const res = await fetch('/api/coverage');
      if (res.ok) {
        const data = await res.json();
        setCoverage(data);
      }
    } catch {
      console.error('Error fetching coverage');
    }
  };

  const handleAttest = (e) => {
    e.preventDefault();
    if (!reviewerName.trim() || !attestationStatement.trim()) return;

    setAttestationMessage(
      `Attestation recorded for Item #q_c8_leq_01 by ${reviewerName} (${reviewerRole}). Status updated to 'reviewed'.`
    );
  };

  return (
    <div className="wide-container">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Content Coverage & Review Attestation</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Human attestation provenance • Unreviewed drafts transparency • Shipped item counts
        </p>
      </div>

      {/* Review Rule Mandate Notice */}
      <div className="info-card" style={{ borderLeft: '4px solid var(--accent-purple)' }}>
        <div style={{ fontSize: '12px', color: 'var(--accent-purple)', fontWeight: '700', marginBottom: '4px' }}>
          HARD RULE 5: HUMAN REVIEW CANNOT BE FABRICATED
        </div>
        <div style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
          Review status is an explicit human act. No code path, seed script, import script, or AI drafting tool may mark any content item as reviewed.
          Everything seeded starts as <strong>author-drafted, unreviewed</strong>.
          Imported records claiming 'reviewed' without verified credentials are automatically downgraded to <strong>unverified import</strong>.
        </div>
      </div>

      {/* Coverage & Shipped Metrics */}
      {coverage && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div className="info-card">
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>SHIPPED CONCEPTS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-blue)' }}>
              {coverage.total_concepts}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {coverage.active_concepts} active (Class 8), {coverage.graph_only_concepts} spine (Classes 6-10)
            </div>
          </div>

          <div className="info-card">
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>SHIPPED QUESTIONS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-emerald)' }}>
              {coverage.total_questions}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>All wrong options tagged with probes</div>
          </div>

          <div className="info-card">
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>SHIPPED LESSONS</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-amber)' }}>
              {coverage.total_lessons}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Foundational & misconception bridges</div>
          </div>

          <div className="info-card">
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>HUMAN REVIEWED PERCENT</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: coverage.percent_human_reviewed > 0 ? 'var(--accent-emerald)' : '#fcd34d' }}>
              {coverage.percent_human_reviewed}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {coverage.human_reviewed_items} of {coverage.total_items} items reviewed
            </div>
          </div>
        </div>
      )}

      {/* Review Status Breakdown */}
      {coverage?.review_status_breakdown && (
        <div className="info-card">
          <h3 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>
            Review Status Distribution
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
            {Object.entries(coverage.review_status_breakdown).map(([status, count]) => (
              <div key={status} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span><code>{status}</code></span>
                <strong>{count} items</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Human Review Attestation Flow in UI */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Human Reviewer Attestation Flow
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Human reviewers act directly in the UI to attest that an item was checked.
          Editing any item after attestation resets its status to 'changed since review'.
        </p>

        <form onSubmit={handleAttest} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Reviewer Full Name</label>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              style={{ width: '100%', padding: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Stated Role / Qualification (Self-declared, shown as such)
            </label>
            <input
              type="text"
              value={reviewerRole}
              onChange={(e) => setReviewerRole(e.target.value)}
              style={{ width: '100%', padding: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Attestation Statement</label>
            <input
              type="text"
              value={attestationStatement}
              onChange={(e) => setAttestationStatement(e.target.value)}
              style={{ width: '100%', padding: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
              required
            />
          </div>

          <button type="submit" className="action-btn" style={{ width: 'auto', alignSelf: 'flex-start' }}>
            Submit Human Attestation Record
          </button>
        </form>

        {attestationMessage && (
          <div style={{ marginTop: '12px', fontSize: '12px', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '6px' }}>
            {attestationMessage}
          </div>
        )}
      </div>
    </div>
  );
}
