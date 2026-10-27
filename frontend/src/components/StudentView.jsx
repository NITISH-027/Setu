import React, { useState, useEffect } from 'react';
import { BKTEngine, RuleSequencer, HypothesisEngine, SpacedRepetitionScheduler } from '../engine/index.js';
import {
  saveOfflinePack,
  getOfflinePack,
  saveStudentProfile,
  getStudentProfile,
  saveLearningState,
  getLearningState,
  recordAttemptLocal,
  enqueueSyncAttempt,
  getSyncQueue,
  clearSyncQueue,
  wipeAllStudentData,
  derivePinVerifier,
  generateSaltHex,
  getAllLocalAttempts
} from '../storage/indexedDb.js';

export default function StudentView({ devSimulateOffline = false, onToggleDevOffline }) {
  const [studentId, setStudentId] = useState('');
  const [pin, setPin] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [classId, setClassId] = useState('8-A');
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [queuedCount, setQueuedCount] = useState(0);
  const [lastSyncTime, setLastSyncTime] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  // Learning state
  const [nextStepData, setNextStepData] = useState(null);
  const [selectedOptId, setSelectedOptId] = useState(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [currentMastery, setCurrentMastery] = useState(0.25);
  const [masteryLabel, setMasteryLabel] = useState('uncalibrated, hand-set');
  const [currentStage, setCurrentStage] = useState('solve');
  const [currentConcept, setCurrentConcept] = useState('c8_math_linear_eq_one_var');
  const [offlinePackData, setOfflinePackData] = useState(null);

  // Engines
  const [bktEngine] = useState(() => new BKTEngine());
  const [sequencer] = useState(() => new RuleSequencer());

  // Listen to real network connectivity
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      triggerSyncIfPossible();
    };
    const handleOffline = () => {
      setIsOnline(false);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Refresh queued count on mount
    refreshQueueCount();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const effectivelyOnline = isOnline && !devSimulateOffline;

  const refreshQueueCount = async () => {
    try {
      const q = await getSyncQueue();
      setQueuedCount(q.length);
    } catch {
      setQueuedCount(0);
    }
  };

  // Sign In Handler (Online or Offline with PBKDF2)
  const handleLogin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!studentId.trim() || !pin.trim()) {
      setStatusMessage('Please enter both student pseudonym and PIN.');
      return;
    }

    if (!effectivelyOnline) {
      // FIX 3c: Offline sign-in via stored PBKDF2 salted verifier
      try {
        const profile = await getStudentProfile(studentId.trim());
        if (!profile) {
          setStatusMessage('No offline profile found on this device. Please sign in online once first.');
          return;
        }

        if (profile.locked_until && Date.now() < profile.locked_until) {
          const rem = Math.ceil((profile.locked_until - Date.now()) / 1000);
          setStatusMessage(`Device locked. Please wait ${rem} seconds.`);
          return;
        }

        const computedHash = await derivePinVerifier(pin.trim(), profile.salt);
        if (computedHash !== profile.pin_verifier) {
          const fails = (profile.failed_attempts || 0) + 1;
          profile.failed_attempts = fails;
          if (fails >= 3) {
            profile.locked_until = Date.now() + 60000;
          }
          await saveStudentProfile(profile);
          setStatusMessage('Incorrect PIN.');
          return;
        }

        // Offline Login Succeeded!
        profile.failed_attempts = 0;
        profile.locked_until = null;
        await saveStudentProfile(profile);

        setAuthenticated(true);
        setClassId(profile.class_id || '8-A');
        setToken(profile.token || null);
        setStatusMessage('Signed in offline with cached device verifier.');

        // Load offline pack and local learning state
        const localPack = await getOfflinePack(profile.class_id || '8-A');
        setOfflinePackData(localPack);

        const localState = await getLearningState(studentId.trim());
        if (localState) {
          setCurrentMastery(localState.mastery || 0.25);
          setCurrentStage(localState.stage || 'solve');
          setCurrentConcept(localState.concept_id || 'c8_math_linear_eq_one_var');
        }

        await loadNextStepOffline(localPack, localState);
        await refreshQueueCount();
      } catch (err) {
        setStatusMessage(`Offline sign-in error: ${err.message}`);
      }
      return;
    }

    // Online Sign-In
    try {
      const res = await fetch('/api/auth/pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: 'dev_demo_tablet',
          student_id: studentId.trim(),
          pin: pin.trim()
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setStatusMessage(err.detail || 'Authentication failed');
        return;
      }

      const data = await res.json();
      setAuthenticated(true);
      setToken(data.access_token);
      const studentClass = data.class_id || '8-A';
      setClassId(studentClass);
      setStatusMessage('');

      // FIX 3c: Derive & store salted PBKDF2 verifier in IndexedDB for offline sign-in
      const salt = generateSaltHex();
      const verifier = await derivePinVerifier(pin.trim(), salt);
      await saveStudentProfile({
        student_id: studentId.trim(),
        class_id: studentClass,
        salt,
        pin_verifier: verifier,
        token: data.access_token,
        failed_attempts: 0,
        locked_until: null,
        cached_at: new Date().toISOString()
      });

      // FIX 2 & FIX 3a: Download full offline pack with answer keys and store in IndexedDB
      try {
        const packRes = await fetch(`/api/student/${studentId.trim()}/offline-pack`, {
          headers: { 'Authorization': `Bearer ${data.access_token}` }
        });
        if (packRes.ok) {
          const packData = await packRes.json();
          await saveOfflinePack(studentClass, packData);
          setOfflinePackData(packData);
        }
      } catch (err) {
        console.warn('Offline pack pre-caching error:', err);
      }

      // Load next step online
      await loadNextStepOnline(data.access_token, studentId.trim());
      await refreshQueueCount();
    } catch {
      setStatusMessage('Network error. Check connection or use offline mode.');
    }
  };

  // Load Next Step Online
  const loadNextStepOnline = async (sessionToken, sid) => {
    setSelectedOptId(null);
    setHintLevel(0);
    try {
      const res = await fetch(`/api/student/${sid}/next-step`, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNextStepData(data);
        if (data.step?.bkt_mastery !== undefined) {
          setCurrentMastery(data.step.bkt_mastery);
        }
        if (data.step?.stage) {
          setCurrentStage(data.step.stage);
        }
        if (data.item?.concept) {
          setCurrentConcept(data.item.concept);
        }

        // Cache state in IndexedDB
        await saveLearningState(sid, {
          stage: data.step?.stage || 'solve',
          concept_id: data.item?.concept || 'c8_math_linear_eq_one_var',
          mastery: data.step?.bkt_mastery || currentMastery
        });
      }
    } catch {
      // Network drop: fallback to offline next step
      const localPack = offlinePackData || await getOfflinePack(classId);
      const localState = await getLearningState(sid);
      await loadNextStepOffline(localPack, localState);
    }
  };

  // Load Next Step Offline (Using JS Engine & Local Pack)
  const loadNextStepOffline = async (packData, localState) => {
    setSelectedOptId(null);
    setHintLevel(0);
    const p = packData || offlinePackData;
    if (!p || !p.questions || p.questions.length === 0) {
      setStatusMessage('Offline pack not yet downloaded. Connect online to load content.');
      return;
    }

    const stage = localState?.stage || currentStage || 'solve';
    const concept = localState?.concept_id || currentConcept || 'c8_math_linear_eq_one_var';
    const mastery = localState?.mastery !== undefined ? localState.mastery : currentMastery;

    // Filter questions for this concept
    let candidates = p.questions.filter((q) => q.concept === concept);
    if (stage === 'probe') {
      const probes = candidates.filter((q) => q.is_probe);
      if (probes.length > 0) candidates = probes;
    }
    if (candidates.length === 0) {
      candidates = p.questions;
    }

    // Get previous attempts to avoid immediate repetition
    const pastAttempts = await getAllLocalAttempts();
    const answeredIds = new Set(pastAttempts.map((a) => a.question_id));
    let nextQ = candidates.find((q) => !answeredIds.has(q.id)) || candidates[0];

    // Build step & sanitized item
    const step = {
      action: 'PRESENT_ITEM',
      item_type: 'question',
      stage,
      concept_id: concept,
      bkt_mastery: mastery,
      mastery_label: 'uncalibrated, hand-set',
      reason: 'Adaptive offline practice step'
    };

    // Sanitize question for client view (no is_correct exposed in UI options)
    const sanitizedItem = {
      id: nextQ.id,
      concept: nextQ.concept,
      question_text: nextQ.question_text,
      options: nextQ.options.map((opt) => ({
        id: opt.id,
        text: opt.text,
        numeric_value: opt.numeric_value
      }))
    };

    // Hint ladder if present
    const ladder = p.hint_ladders?.find((l) => l.question_id === nextQ.id) || null;

    setNextStepData({
      step,
      item: sanitizedItem,
      hint_ladder: ladder
    });
  };

  // Submit Attempt (Unified Online/Offline flow)
  const handleSubmitAttempt = async () => {
    if (!selectedOptId || !nextStepData?.item) return;

    const item = nextStepData.item;
    const attemptId = `att_local_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    const qId = item.id;
    const cId = item.concept;

    if (effectivelyOnline && token) {
      // Online attempt submission
      try {
        const payload = {
          question_id: qId,
          concept_id: cId,
          selected_option_id: selectedOptId,
          attempt_id: attemptId,
          time_spent_seconds: 5
        };

        const res = await fetch(`/api/student/${studentId}/attempt`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const result = await res.json();
          setCurrentMastery(result.updated_mastery);
          setStatusMessage(`Server graded: ${result.server_graded_correct ? 'Correct' : 'Incorrect'}. Next step loaded.`);
          await loadNextStepOnline(token, studentId);
          await refreshQueueCount();
          return;
        }
      } catch {
        // Fallback to offline queueing below
      }
    }

    // FIX 3b: Offline Local Grading using JS Engine
    const pack = offlinePackData || await getOfflinePack(classId);
    if (!pack) {
      setStatusMessage('Error: No offline content pack available for grading.');
      return;
    }

    const fullQuestion = pack.questions.find((q) => q.id === qId);
    const matchedOpt = fullQuestion?.options.find((o) => o.id === selectedOptId);
    const localIsCorrect = matchedOpt?.is_correct || false;
    const localMiscTag = matchedOpt?.misconception_tag || null;

    // 1. Update BKT mastery locally
    const nextMastery = bktEngine.update(currentMastery, localIsCorrect);
    setCurrentMastery(nextMastery);

    // 2. Evaluate Sequencer locally
    let nextStage = currentStage;
    if (!localIsCorrect && currentStage === 'solve') {
      nextStage = 'probe';
    } else if (localIsCorrect && currentStage === 'probe') {
      nextStage = 'solve';
    }
    setCurrentStage(nextStage);

    // 3. Record in IndexedDB attempts & sync queue
    const attemptRecord = {
      attempt_id: attemptId,
      student_id: studentId,
      question_id: qId,
      concept_id: cId,
      selected_option_id: selectedOptId,
      is_correct: localIsCorrect,
      misconception_tag: localMiscTag,
      time_spent_seconds: 5,
      timestamp: new Date().toISOString()
    };

    await recordAttemptLocal(attemptRecord);
    await enqueueSyncAttempt(attemptRecord);

    // 4. Update local learning state in IndexedDB
    await saveLearningState(studentId, {
      stage: nextStage,
      concept_id: cId,
      mastery: nextMastery
    });

    await refreshQueueCount();

    setStatusMessage(
      `Offline graded locally: ${localIsCorrect ? 'Correct!' : 'Incorrect.'} Mastery updated to ${(nextMastery * 100).toFixed(0)}%. Queued for sync.`
    );

    // Load next question
    await loadNextStepOffline(pack, { stage: nextStage, concept_id: cId, mastery: nextMastery });
  };

  // Sync on Reconnect or Click (FIX 3f, FIX 4)
  const triggerSyncIfPossible = async () => {
    const queue = await getSyncQueue();
    if (queue.length === 0) return;
    if (!effectivelyOnline) return;

    try {
      const authHeader = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch('/api/privacy/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeader
        },
        body: JSON.stringify({
          device_id: 'dev_demo_tablet',
          class_id: classId || '8-A',
          queued_attempts: queue
        })
      });

      if (res.ok) {
        const syncData = await res.json();

        // FIX 4: If server indicates device is stale / unregistered, wipe local data
        if (syncData.is_stale_reset_required) {
          await wipeAllStudentData();
          setAuthenticated(false);
          setStatusMessage('Server policy: Device cache reset required. Please sign in online.');
          return;
        }

        // Clear local sync queue
        await clearSyncQueue();
        await refreshQueueCount();
        setLastSyncTime(new Date().toLocaleTimeString());

        // Update server authoritative mastery
        if (syncData.authoritative_mastery) {
          setCurrentMastery(syncData.authoritative_mastery.mastery_estimate);
          setMasteryLabel(syncData.authoritative_mastery.mastery_label || 'uncalibrated, hand-set');
        }

        setStatusMessage(`Synced ${syncData.synced_attempts_processed} offline attempts with server!`);
        if (token) {
          await loadNextStepOnline(token, studentId);
        }
      }
    } catch (err) {
      console.warn('Sync attempt failed:', err);
    }
  };

  // ----------------------------------------------------
  // Render Sign-In Form (Empty defaults, FIX 6)
  // ----------------------------------------------------
  if (!authenticated) {
    return (
      <div className="phone-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Student Sign-In</h2>
          <span
            id="connection-status-badge"
            className="badge-uncalibrated"
            style={{
              background: effectivelyOnline ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
              color: effectivelyOnline ? '#6ee7b7' : '#fca5a5'
            }}
          >
            {effectivelyOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Shared Device • Salted PIN Authentication • Offline Capable
        </p>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Student Pseudonym</label>
            <input
              id="student-id-input"
              data-testid="student-id-input"
              type="text"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="e.g. stu_demo_01"
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#fff',
                borderRadius: '6px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>4-Digit PIN</label>
            <input
              id="student-pin-input"
              data-testid="student-pin-input"
              type="password"
              maxLength="4"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="Enter PIN"
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#fff',
                borderRadius: '6px'
              }}
            />
          </div>

          <button
            id="student-signin-btn"
            data-testid="student-signin-btn"
            type="submit"
            className="action-btn"
          >
            {effectivelyOnline ? 'Sign In (Online)' : 'Sign In (Offline Profile)'}
          </button>
        </form>

        {statusMessage && (
          <div
            id="student-status-message"
            style={{
              marginTop: '12px',
              fontSize: '12px',
              color: statusMessage.includes('Correct') ? '#6ee7b7' : '#fca5a5',
              background: 'rgba(0,0,0,0.3)',
              padding: '8px',
              borderRadius: '4px'
            }}
          >
            {statusMessage}
          </div>
        )}

        {/* Developer simulation toggle aid */}
        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
          <button
            type="button"
            onClick={onToggleDevOffline}
            className="btn-secondary"
            style={{ fontSize: '11px', width: '100%' }}
          >
            {devSimulateOffline ? 'Disable Dev Offline Simulation' : 'Dev: Simulate Offline Mode'}
          </button>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------
  // Render Student Learning Screen
  // ----------------------------------------------------
  const step = nextStepData?.step;
  const item = nextStepData?.item;
  const hintLadder = nextStepData?.hint_ladder;

  return (
    <div className="phone-container">
      {/* Header with real state (FIX 3g) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Student: {studentId}</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>({classId})</span>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span
            id="connection-status-badge"
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '12px',
              background: effectivelyOnline ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
              color: effectivelyOnline ? '#6ee7b7' : '#fca5a5',
              fontWeight: '600'
            }}
          >
            {effectivelyOnline ? 'Online' : 'Offline'}
          </span>
          <button
            onClick={() => {
              setAuthenticated(false);
              setPin('');
            }}
            className="btn-secondary"
            style={{ fontSize: '10px', padding: '2px 6px' }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Honest Badges Row */}
      <div className="badge-row" style={{ marginBottom: '10px' }}>
        <span className="badge-stage">{currentStage}</span>
        <span id="mastery-estimate-badge" className="badge-uncalibrated">
          Mastery: {(currentMastery * 100).toFixed(0)}% (uncalibrated, hand-set)
        </span>
        <span id="queued-count-badge" className="badge-heuristic">
          Queued: {queuedCount}
        </span>
      </div>

      {lastSyncTime && (
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '8px' }}>
          Last sync: {lastSyncTime}
        </div>
      )}

      {/* Question Content */}
      {item && step?.item_type === 'question' && (
        <div className="info-card">
          <div className="q-text" style={{ fontSize: '15px', fontWeight: '600', marginBottom: '12px' }}>
            {item.question_text}
          </div>

          <div className="options-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {item.options.map((opt) => (
              <button
                key={opt.id}
                id={`opt-${opt.id}`}
                data-testid={`option-${opt.id}`}
                className={`option-btn ${selectedOptId === opt.id ? 'selected' : ''}`}
                onClick={() => setSelectedOptId(opt.id)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '10px',
                  borderRadius: '6px',
                  background: selectedOptId === opt.id ? 'rgba(56, 189, 248, 0.2)' : 'var(--bg-secondary)',
                  border: selectedOptId === opt.id ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  color: '#fff',
                  textAlign: 'left'
                }}
              >
                <span>{opt.text}</span>
                {selectedOptId === opt.id && <span style={{ color: 'var(--accent-blue)' }}>●</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action Submit */}
      {step?.item_type === 'question' && (
        <button
          id="submit-attempt-btn"
          data-testid="submit-attempt-btn"
          onClick={handleSubmitAttempt}
          disabled={!selectedOptId}
          className="action-btn"
          style={{ width: '100%', marginTop: '10px' }}
        >
          Submit Answer
        </button>
      )}

      {/* Hint Ladder */}
      {hintLadder && step?.item_type === 'question' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {hintLevel === 0 && (
            <button
              onClick={() => setHintLevel(1)}
              className="btn-secondary"
              style={{ fontSize: '11px' }}
            >
              Need a Hint? (Level 1)
            </button>
          )}
          {hintLevel >= 1 && (
            <div className="info-card" style={{ background: 'rgba(56, 189, 248, 0.08)', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: 'var(--accent-blue)', fontWeight: '700' }}>HINT LEVEL 1</div>
              <div style={{ fontSize: '13px' }}>{hintLadder.level_1_hint}</div>
              {hintLevel === 1 && (
                <button
                  onClick={() => setHintLevel(2)}
                  className="btn-secondary"
                  style={{ marginTop: '6px', fontSize: '10px' }}
                >
                  Show Partial Step
                </button>
              )}
            </div>
          )}
          {hintLevel >= 2 && (
            <div className="info-card" style={{ background: 'rgba(168, 85, 247, 0.08)', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: 'var(--accent-purple)', fontWeight: '700' }}>PARTIAL STEP (LEVEL 2)</div>
              <div style={{ fontSize: '13px' }}>{hintLadder.level_2_partial_step}</div>
            </div>
          )}
        </div>
      )}

      {/* Sync Control & Status */}
      <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          id="sync-now-btn"
          data-testid="sync-now-btn"
          onClick={triggerSyncIfPossible}
          disabled={!effectivelyOnline || queuedCount === 0}
          className="btn-secondary"
          style={{
            fontSize: '11px',
            borderColor: queuedCount > 0 && effectivelyOnline ? 'var(--accent-emerald)' : 'var(--border-color)',
            color: queuedCount > 0 && effectivelyOnline ? '#6ee7b7' : 'var(--text-muted)'
          }}
        >
          {queuedCount > 0 ? `Sync ${queuedCount} Queued Attempt(s)` : 'Queue Empty'}
        </button>

        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
          {effectivelyOnline ? 'Auto-sync active' : 'Offline: local IndexedDB'}
        </span>
      </div>

      {statusMessage && (
        <div
          id="student-status-message"
          style={{
            marginTop: '8px',
            fontSize: '11px',
            color: '#cbd5e1',
            background: 'rgba(0,0,0,0.3)',
            padding: '8px',
            borderRadius: '4px'
          }}
        >
          {statusMessage}
        </div>
      )}
    </div>
  );
}
