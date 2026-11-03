import React, { useState, useEffect } from 'react';

/**
 * Adaptive Chapter Test (Learn - Solve - TEST leg).
 * Online-only: every item is selected on the server against the student's
 * current per-concept mastery estimate. No hints during a test - a test
 * measures; practice teaches.
 */
export default function TestView({ studentId, token, onExit }) {
  const [phase, setPhase] = useState('intro'); // intro | running | summary
  const [sessionState, setSessionState] = useState(null);
  const [selectedOptId, setSelectedOptId] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Resume an in-progress session if one exists
    (async () => {
      try {
        const res = await fetch(`/api/student/${studentId}/test/active`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.active) {
            setSessionState(data.active);
            setPhase('running');
          }
        }
      } catch { /* start fresh */ }
    })();
  }, []);

  const startTest = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`/api/student/${studentId}/test/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not start test');
      setSessionState(data);
      setPhase('running');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const submitAnswer = async () => {
    if (!selectedOptId || !sessionState?.current_item) return;
    setBusy(true);
    setError('');
    const item = sessionState.current_item;
    try {
      const res = await fetch(`/api/student/${studentId}/test/answer`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionState.session_id,
          question_id: item.question.id,
          selected_option_id: selectedOptId,
          attempt_id: `test-${sessionState.session_id}-${item.sequence}`
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Answer rejected');
      setFeedback(data.server_graded_correct ? 'correct' : 'wrong');
      setTimeout(() => {
        setFeedback(null);
        setSelectedOptId(null);
        if (data.completed) {
          setSummary(data.summary);
          setPhase('summary');
        } else {
          setSessionState(data.session);
        }
      }, 900);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const cardStyle = {
    background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
    borderRadius: '10px', padding: '16px', marginTop: '10px'
  };

  if (phase === 'intro') {
    return (
      <div className="phone-container">
        <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Chapter Test - Class 8 Maths</h2>
        <div style={cardStyle}>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Questions are chosen using your current concept mastery and coverage, and your
            answers update mastery for later selections. Difficulty changes are limited by the
            available question bank. No hints during a test - it measures where you stand.
          </p>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Estimates remain <em>uncalibrated, hand-set</em>. Concepts with too few questions are
            reported at the end, not hidden.
          </p>
        </div>
        {error && <p style={{ color: '#fca5a5', fontSize: '12px' }}>{error}</p>}
        <button id="start-test-btn" data-testid="start-test-btn" onClick={startTest} disabled={busy}
          className="action-btn" style={{ marginTop: '12px', width: '100%', padding: '12px' }}>
          {busy ? 'Starting...' : 'Start Adaptive Test'}
        </button>
        <button onClick={onExit} className="btn-secondary" style={{ marginTop: '8px', width: '100%' }}>
          Back to Practice
        </button>
      </div>
    );
  }

  if (phase === 'running' && sessionState?.current_item) {
    const item = sessionState.current_item;
    return (
      <div className="phone-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Chapter Test</span>
          <span id="test-progress" data-testid="test-progress" className="badge-heuristic">
            {sessionState.answered_count + 1} / {sessionState.planned_length}
          </span>
        </div>
        <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
          {item.concept_name} {item.is_fallback ? '(English fallback - no item in your medium)' : ''}
        </p>
        <div style={cardStyle}>
          <p id="test-question-text" style={{ fontSize: '15px', fontWeight: '500', marginBottom: '12px' }}>
            {item.question.question_text}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {item.question.options.map((opt) => (
              <button
                key={opt.id}
                data-testid={`test-option-${opt.id}`}
                onClick={() => setSelectedOptId(opt.id)}
                disabled={busy || feedback !== null}
                style={{
                  textAlign: 'left', padding: '10px 12px', borderRadius: '8px', fontSize: '14px',
                  border: selectedOptId === opt.id ? '2px solid #34d399' : '1px solid var(--border-color)',
                  background: selectedOptId === opt.id ? 'rgba(52, 211, 153, 0.12)' : 'var(--bg-primary)',
                  color: '#fff', cursor: 'pointer'
                }}
              >
                {opt.text}
              </button>
            ))}
          </div>
        </div>
        {feedback && (
          <p id="test-feedback" style={{
            marginTop: '10px', fontSize: '14px', fontWeight: '600',
            color: feedback === 'correct' ? '#6ee7b7' : '#fca5a5'
          }}>
            {feedback === 'correct' ? 'Correct - the next question adapts upward.' : 'Not quite - recorded for your report.'}
          </p>
        )}
        {error && <p style={{ color: '#fca5a5', fontSize: '12px' }}>{error}</p>}
        <button id="submit-test-answer" data-testid="submit-test-answer" onClick={submitAnswer}
          disabled={!selectedOptId || busy || feedback !== null}
          className="action-btn" style={{ marginTop: '12px', width: '100%', padding: '12px' }}>
          Submit Answer
        </button>
      </div>
    );
  }

  if (phase === 'summary' && summary) {
    return (
      <div className="phone-container">
        <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Test Report</h2>
        <div style={cardStyle}>
          <p id="test-score" data-testid="test-score" style={{ fontSize: '20px', fontWeight: '700' }}>
            {summary.total_correct} / {summary.total_served} correct
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Mastery estimates: {summary.mastery_label}
          </p>
        </div>
        {summary.per_concept.map((c) => (
          <div key={c.concept_id} style={{ ...cardStyle, padding: '10px 14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span>{c.concept_id.replace(/c\d+_math_/, '').replace(/_/g, ' ')}</span>
              <span>{c.correct}/{c.served}</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              estimate {(c.mastery_before * 100).toFixed(0)}% → {(c.mastery_after * 100).toFixed(0)}%
              {c.misconception_tags.length > 0 ? ` • saw: ${c.misconception_tags.join(', ')}` : ''}
            </div>
          </div>
        ))}
        <div style={{ ...cardStyle, border: '1px solid rgba(56, 189, 248, 0.4)' }}>
          <p id="test-recommendation" data-testid="test-recommendation" style={{ fontSize: '13px' }}>
            {summary.recommendation}
          </p>
        </div>
        <button id="practice-weakest-btn" data-testid="practice-weakest-btn" onClick={onExit}
          className="action-btn" style={{ marginTop: '12px', width: '100%', padding: '12px' }}>
          Practice {summary.weakest_concept_name || 'Recommended Concept'}
        </button>
      </div>
    );
  }

  return <div className="phone-container"><p style={{ color: 'var(--text-muted)' }}>Loading test...</p></div>;
}
