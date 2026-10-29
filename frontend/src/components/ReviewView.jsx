import React, { useState, useEffect } from 'react';

export default function ReviewView() {
  const [coverage, setCoverage] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(null);
  const [reviewerName, setReviewerName] = useState('');
  const [reviewerRole, setReviewerRole] = useState('');
  const [attestationStatement, setAttestationStatement] = useState('I checked this item');
  const [attestationMessage, setAttestationMessage] = useState('');
  const [loginError, setLoginError] = useState('');

  // Content Editor State (Failure 10 & Acceptance Test L)
  const [editorPack, setEditorPack] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState('');
  const [editorItemJson, setEditorItemJson] = useState('');
  const [editorError, setEditorError] = useState('');
  const [editorSuccess, setEditorSuccess] = useState('');
  const [isSavingItem, setIsSavingItem] = useState(false);

  const handleReviewerLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setLoginError('Enter username and password');
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
        setToken(data.access_token);
        setReviewerName(data.username);
        setReviewerRole(data.role);
        setLoginError('');
        fetchCoverageWithToken(data.access_token);
        fetchEditorPack(data.access_token);
      } else {
        setLoginError('Login failed. Please check credentials.');
      }
    } catch {
      setLoginError('Network error during login.');
    }
  };

  const fetchCoverageWithToken = async (authToken) => {
    try {
      const res = await fetch('/api/coverage', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCoverage(data);
      }
    } catch {
      console.error('Error fetching coverage');
    }
  };

  const fetchEditorPack = async (authToken) => {
    try {
      const res = await fetch('/api/content/editor/pack', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEditorPack(data);
        if (data.questions && data.questions.length > 0 && !selectedItemId) {
          const firstQ = data.questions[0];
          setSelectedItemId(firstQ.id);
          setEditorItemJson(JSON.stringify(firstQ, null, 2));
        }
      }
    } catch {
      console.error('Error fetching editor pack');
    }
  };

  const handleSelectItem = (id) => {
    setSelectedItemId(id);
    setEditorError('');
    setEditorSuccess('');
    if (!editorPack) return;
    const foundQ = (editorPack.questions || []).find((q) => q.id === id);
    if (foundQ) {
      setEditorItemJson(JSON.stringify(foundQ, null, 2));
      return;
    }
    const foundL = (editorPack.lessons || []).find((l) => l.id === id);
    if (foundL) {
      setEditorItemJson(JSON.stringify(foundL, null, 2));
    }
  };

  const handleSaveEditorItem = async () => {
    setEditorError('');
    setEditorSuccess('');
    let parsed;
    try {
      parsed = JSON.parse(editorItemJson);
    } catch {
      setEditorError('Validator error: Invalid JSON syntax.');
      return;
    }

    if (!token) {
      setEditorError('Reviewer/Author token required to save content edits.');
      return;
    }

    setIsSavingItem(true);
    try {
      const res = await fetch('/api/content/editor/pack', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(parsed)
      });

      if (res.ok) {
        const data = await res.json();
        setEditorSuccess("Item successfully saved. Review status reset to 'author-drafted, unreviewed'.");
        fetchCoverageWithToken(token);
        fetchEditorPack(token);
      } else {
        const err = await res.json().catch(() => ({}));
        setEditorError(err.detail || `Validator error: HTTP ${res.status}`);
      }
    } catch {
      setEditorError('Network error saving item to pack.');
    } finally {
      setIsSavingItem(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCoverageWithToken(token);
      fetchEditorPack(token);
    }
  }, [token]);

  const handleAttest = async (e) => {
    e.preventDefault();
    if (!reviewerName.trim() || !attestationStatement.trim()) return;

    if (!token) {
      setAttestationMessage('Reviewer login required to record human attestation.');
      return;
    }

    try {
      const res = await fetch('/api/reviewer/attest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          item_id: 'q_c8_leq_01',
          status: 'reviewed, intended NCERT alignment verified',
          attestation_statement: attestationStatement
        })
      });

      if (res.ok) {
        setAttestationMessage(
          `Attestation recorded for Item #q_c8_leq_01 by ${reviewerName} (${reviewerRole}). Status updated to 'reviewed'.`
        );
        fetchCoverageWithToken(token);
      } else {
        const err = await res.json().catch(() => ({}));
        setAttestationMessage(err.detail || 'Attestation submission failed.');
      }
    } catch {
      setAttestationMessage('Network error submitting attestation.');
    }
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

      {/* Login if unauthenticated */}
      {!token && (
        <div className="info-card" style={{ background: 'rgba(56, 189, 248, 0.05)' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
            Reviewer Sign-In (Required to View Coverage & Attest Items)
          </div>
          <form onSubmit={handleReviewerLogin} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Reviewer Username"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <button type="submit" className="action-btn" style={{ width: 'auto' }}>
              Sign In
            </button>
          </form>
          {loginError && <div style={{ fontSize: '12px', color: '#fca5a5', marginTop: '6px' }}>{loginError}</div>}
        </div>
      )}

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

      {/* Attestation Form */}
      {token && (
        <div className="info-card">
          <h3 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '8px' }}>
            Review Attestation for Item #q_c8_leq_01
          </h3>
          <form onSubmit={handleAttest} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input
              type="text"
              value={attestationStatement}
              onChange={(e) => setAttestationStatement(e.target.value)}
              placeholder="Attestation statement..."
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <button type="submit" className="action-btn" style={{ width: 'auto' }}>
              Record Human Attestation
            </button>
          </form>
          {attestationMessage && (
            <div style={{ marginTop: '10px', fontSize: '12px', color: '#6ee7b7' }}>
              {attestationMessage}
            </div>
          )}
        </div>
      )}

      {/* Content Editor Section (Failure 10 & Acceptance Test L) */}
      {token && editorPack && (
        <div className="info-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700' }}>
              Pack Content Editor (Schema Validated)
            </h3>
            <span className="badge-heuristic">author-drafted, unreviewed</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Author or edit pack items. Every edit is strictly checked by the schema validator (requires valid options, exactly 1 correct option, misconception tags on wrong options).
            <strong> Review Reset Rule:</strong> Saving an edit automatically resets the item's review status to <em>'author-drafted, unreviewed'</em> and drops the human-reviewed percentage.
          </p>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '13px', fontWeight: '600' }}>Select Item to Edit:</label>
            <select
              id="editor-item-select"
              data-testid="editor-item-select"
              value={selectedItemId}
              onChange={(e) => handleSelectItem(e.target.value)}
              style={{ padding: '6px 10px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', fontSize: '12px' }}
            >
              <optgroup label="Questions">
                {(editorPack.questions || []).map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.id} - {q.question_text?.slice(0, 35)}...
                  </option>
                ))}
              </optgroup>
              <optgroup label="Lessons">
                {(editorPack.lessons || []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.id} - {l.concept} ({l.language})
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
              Item Definition (JSON payload):
            </label>
            <textarea
              id="editor-item-textarea"
              data-testid="editor-item-textarea"
              value={editorItemJson}
              onChange={(e) => setEditorItemJson(e.target.value)}
              rows={12}
              style={{
                width: '100%',
                padding: '10px',
                fontFamily: 'monospace',
                fontSize: '12px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#e2e8f0',
                borderRadius: '6px'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              id="save-editor-item-btn"
              data-testid="save-editor-item-btn"
              onClick={handleSaveEditorItem}
              disabled={isSavingItem}
              className="action-btn"
              style={{ width: 'auto' }}
            >
              {isSavingItem ? 'Validating & Saving...' : 'Save Item to Pack'}
            </button>
          </div>

          {editorSuccess && (
            <div
              id="editor-success-message"
              data-testid="editor-success-message"
              style={{ marginTop: '12px', fontSize: '13px', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}
            >
              ✓ {editorSuccess}
            </div>
          )}

          {editorError && (
            <div
              id="editor-error-message"
              data-testid="editor-error-message"
              style={{ marginTop: '12px', fontSize: '13px', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}
            >
              ⚠ {editorError}
            </div>
          )}

          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>
            <em>Note: Content authoring and review attestation tool only. Shipped materials are author-drafted and unreviewed. Not a compliance claim.</em>
          </div>
        </div>
      )}
    </div>
  );
}
