import React, { useState, useEffect } from 'react';

export default function StudentView({ isOffline, onToggleOffline }) {
  const [studentId, setStudentId] = useState('stu_demo_01');
  const [pin, setPin] = useState('1234');
  const [authenticated, setAuthenticated] = useState(false);
  const [nextStepData, setNextStepData] = useState(null);
  const [selectedOptId, setSelectedOptId] = useState(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [offlineQueue, setOfflineQueue] = useState([]);

  useEffect(() => {
    if (authenticated) {
      loadNextStep();
    }
  }, [authenticated, studentId]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (isOffline) {
      // Offline local authentication simulation
      if (pin === '1234') {
        setAuthenticated(true);
        setStatusMessage('Logged in (Offline Cached Profile)');
      } else {
        setStatusMessage('Incorrect PIN.');
      }
      return;
    }
    try {
      const res = await fetch('/api/auth/pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, pin })
      });
      if (res.ok) {
        setAuthenticated(true);
        setStatusMessage('');
      } else {
        const err = await res.json();
        setStatusMessage(err.detail || 'Authentication failed');
      }
    } catch {
      setStatusMessage('Network error. Switch to Offline Mode to practice disconnected.');
    }
  };

  const loadNextStep = async () => {
    setSelectedOptId(null);
    setHintLevel(0);
    try {
      const res = await fetch(`/api/student/${studentId}/next-step`);
      if (res.ok) {
        const data = await res.json();
        setNextStepData(data);
      }
    } catch {
      setStatusMessage('Error loading next step from server.');
    }
  };

  const handleSubmitAttempt = async () => {
    if (!selectedOptId || !nextStepData?.item) return;

    const item = nextStepData.item;
    const selectedOpt = item.options.find(o => o.id === selectedOptId);
    const isCorrect = selectedOpt?.is_correct || false;
    const misconceptionTag = selectedOpt?.misconception_tag || null;

    const payload = {
      question_id: item.id,
      concept_id: item.concept,
      selected_option_id: selectedOptId,
      is_correct: isCorrect,
      misconception_tag: misconceptionTag
    };

    if (isOffline) {
      // Queue offline
      setOfflineQueue(prev => [...prev, payload]);
      setStatusMessage('Offline: Attempt recorded locally in sync queue.');
      // Simulate local progression
      loadNextStep();
      return;
    }

    try {
      const res = await fetch(`/api/student/${studentId}/attempt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const result = await res.json();
        setStatusMessage(`Decision: ${result.decision.action} (${result.decision.reason})`);
        loadNextStep();
      }
    } catch {
      setStatusMessage('Submission error. Queueing locally.');
      setOfflineQueue(prev => [...prev, payload]);
    }
  };

  const handleSyncQueue = async () => {
    if (offlineQueue.length === 0) return;
    try {
      const res = await fetch('/api/privacy/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: 'dev_demo_tablet',
          class_id: '8-A',
          queued_attempts: offlineQueue
        })
      });
      if (res.ok) {
        setOfflineQueue([]);
        setStatusMessage('Sync complete! Queued attempts synchronized with server.');
        loadNextStep();
      }
    } catch {
      setStatusMessage('Sync failed. Check network connection.');
    }
  };

  if (!authenticated) {
    return (
      <div className="phone-container">
        <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Student Sign-In</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Shared Family Device • Sibling PIN Authentication
        </p>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Student Pseudonym</label>
            <select
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            >
              <option value="stu_demo_01">stu_demo_01 (Class 8-A)</option>
              <option value="stu_learner_B">stu_learner_B (Sibling - Class 8-A)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>4-Digit PIN</label>
            <input
              type="password"
              maxLength="4"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="1234"
              style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
          </div>

          <button type="submit" className="action-btn">Sign In</button>
        </form>

        {statusMessage && <div style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>{statusMessage}</div>}
      </div>
    );
  }

  const step = nextStepData?.step;
  const item = nextStepData?.item;
  const hintLadder = nextStepData?.hint_ladder;

  return (
    <div className="phone-container">
      {/* Sibling Switcher & Status Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Student: <strong>{studentId}</strong> (8-A)
        </span>
        <button
          onClick={() => setAuthenticated(false)}
          className="btn-secondary"
          style={{ fontSize: '11px', padding: '4px 8px' }}
        >
          Switch Profile
        </button>
      </div>

      {/* Honest Badges Row */}
      <div className="badge-row">
        {step && <span className="badge-stage">{step.stage}</span>}
        {step?.bkt_mastery !== undefined && (
          <span className="badge-uncalibrated">
            Mastery: {(step.bkt_mastery * 100).toFixed(0)}% (uncalibrated, hand-set)
          </span>
        )}
        {step?.evidence_band && (
          <span className="badge-heuristic">
            Evidence: {step.evidence_band} (heuristic evidence score)
          </span>
        )}
      </div>

      {/* Teacher Flag Alert if applicable */}
      {step?.teacher_flag && (
        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '12px', borderRadius: '8px', fontSize: '13px', color: '#fda4af' }}>
          <strong>Teacher Flag:</strong> {step.reason}
        </div>
      )}

      {/* Question or Micro-Lesson Content */}
      {item && step?.item_type === 'question' && (
        <div className="info-card">
          <div className="q-text">{item.question_text}</div>

          <div className="options-list">
            {item.options.map((opt) => (
              <button
                key={opt.id}
                className={`option-btn ${selectedOptId === opt.id ? 'selected' : ''}`}
                onClick={() => setSelectedOptId(opt.id)}
              >
                <span>{opt.text}</span>
                {selectedOptId === opt.id && <span>●</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {item && step?.item_type === 'lesson' && (
        <div className="info-card" style={{ borderLeft: '4px solid var(--accent-blue)' }}>
          <div style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: '700', marginBottom: '6px' }}>
            PREREQUISITE MICRO-LESSON BRIDGE
          </div>
          <div style={{ fontSize: '14px', lineHeight: '1.6' }}>{item.content}</div>
          <button
            onClick={() => loadNextStep()}
            className="action-btn"
            style={{ marginTop: '12px' }}
          >
            I Understand — Proceed to Bridge Re-Check
          </button>
        </div>
      )}

      {/* Action Submit */}
      {step?.item_type === 'question' && (
        <button
          onClick={handleSubmitAttempt}
          disabled={!selectedOptId}
          className="action-btn"
        >
          Submit Answer
        </button>
      )}

      {/* Hint Ladder */}
      {hintLadder && step?.item_type === 'question' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {hintLevel === 0 && (
            <button
              onClick={() => setHintLevel(1)}
              className="btn-secondary"
            >
              Need a Hint? (Step 1 of 3)
            </button>
          )}
          {hintLevel >= 1 && (
            <div className="info-card" style={{ background: 'rgba(56, 189, 248, 0.08)' }}>
              <div style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: '700' }}>HINT LEVEL 1</div>
              <div style={{ fontSize: '13px' }}>{hintLadder.level_1_hint}</div>
              {hintLevel === 1 && (
                <button
                  onClick={() => setHintLevel(2)}
                  className="btn-secondary"
                  style={{ marginTop: '8px', fontSize: '11px' }}
                >
                  Show Partial Step (Level 2)
                </button>
              )}
            </div>
          )}
          {hintLevel >= 2 && (
            <div className="info-card" style={{ background: 'rgba(168, 85, 247, 0.08)' }}>
              <div style={{ fontSize: '12px', color: 'var(--accent-purple)', fontWeight: '700' }}>PARTIAL STEP (LEVEL 2)</div>
              <div style={{ fontSize: '13px' }}>{hintLadder.level_2_partial_step}</div>
              {hintLevel === 2 && (
                <button
                  onClick={() => setHintLevel(3)}
                  className="btn-secondary"
                  style={{ marginTop: '8px', fontSize: '11px' }}
                >
                  Show Full Worked Step (Level 3)
                </button>
              )}
            </div>
          )}
          {hintLevel >= 3 && (
            <div className="info-card" style={{ background: 'rgba(245, 158, 11, 0.08)' }}>
              <div style={{ fontSize: '12px', color: 'var(--accent-amber)', fontWeight: '700' }}>FULL WORKED STEP (LEVEL 3)</div>
              <div style={{ fontSize: '13px' }}>{hintLadder.level_3_worked_step}</div>
            </div>
          )}
        </div>
      )}

      {/* Offline Status & Sync Control */}
      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={onToggleOffline}
          className="btn-secondary"
          style={{ fontSize: '11px', background: isOffline ? '#78350f' : 'rgba(255, 255, 255, 0.05)' }}
        >
          {isOffline ? 'Mode: Disconnected (Offline)' : 'Mode: Connected (Online)'}
        </button>

        {offlineQueue.length > 0 && !isOffline && (
          <button
            onClick={handleSyncQueue}
            className="btn-secondary"
            style={{ fontSize: '11px', borderColor: 'var(--accent-emerald)', color: '#6ee7b7' }}
          >
            Sync {offlineQueue.length} Queued
          </button>
        )}
      </div>

      {statusMessage && (
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px' }}>
          {statusMessage}
        </div>
      )}
    </div>
  );
}
