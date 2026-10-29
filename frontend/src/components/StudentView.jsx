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
  getAllLocalAttempts,
  deleteStudentBySubjectKey,
  getOrCreateDeviceId,
  setMeta,
  getMeta
} from '../storage/indexedDb.js';

export default function StudentView({ devSimulateOffline = false, onToggleDevOffline, language = 'en', onLanguageChange }) {
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
  const [prevStage, setPrevStage] = useState(null);
  const [currentConcept, setCurrentConcept] = useState('c8_math_linear_eq_one_var');
  const [conceptMasteries, setConceptMasteries] = useState({});
  const [offlinePackData, setOfflinePackData] = useState(null);

  // Engines
  const [bktEngine] = useState(() => new BKTEngine());
  const [sequencer] = useState(() => new RuleSequencer());

  // Listen to real network connectivity
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      triggerSyncIfPossible(true);
    };
    const handleOffline = () => {
      setIsOnline(false);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Refresh queued count on mount and check pending purges
    refreshQueueCount();
    checkAndApplyDevicePurges();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const effectivelyOnline = isOnline && !devSimulateOffline;

  // Automatically trigger sync when connectivity transitions to online
  useEffect(() => {
    if (effectivelyOnline) {
      triggerSyncIfPossible(true);
    }
  }, [effectivelyOnline]);

  // Failure 5: When medium language changes, reload next step in selected medium
  useEffect(() => {
    if (authenticated) {
      if (effectivelyOnline && token) {
        loadNextStepOnline(token, studentId);
      } else {
        (async () => {
          const pack = offlinePackData || (await getOfflinePack(classId));
          const localState = await getLearningState(studentId);
          await loadNextStepOffline(pack, localState);
        })();
      }
    }
  }, [language]);

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
      const devId = await getOrCreateDeviceId();
      const res = await fetch('/api/auth/pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: devId,
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

      // FIX 1: Store per-device purge credential in IndexedDB metadata
      if (data.device_purge_token) {
        await setMeta('device_purge_token', data.device_purge_token);
      }

      // FIX 1 & FIX 3c: Derive & store salted PBKDF2 verifier and subject_key in IndexedDB
      const salt = generateSaltHex();
      const verifier = await derivePinVerifier(pin.trim(), salt);
      await saveStudentProfile({
        student_id: studentId.trim(),
        subject_key: data.subject_key || null,
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
      const langParam = language ? `?language=${encodeURIComponent(language)}` : '';
      const res = await fetch(`/api/student/${sid}/next-step${langParam}`, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNextStepData(data);
        if (data.step?.bkt_mastery !== undefined) {
          setCurrentMastery(data.step.bkt_mastery);
        }
        if (data.step?.stage) {
          setPrevStage(currentStage);
          setCurrentStage(data.step.stage);
        }

        // FIX 1: Keep target topic separate from displayed item concept.
        // data.item.concept is the question's concept (which may be a diagnostic probe from another grade).
        // target_concept_id is the student's plan target concept.
        const targetConcept = data.step?.target_concept_id || currentConcept || 'c8_math_linear_eq_one_var';
        setCurrentConcept(targetConcept);

        // Cache state in IndexedDB carrying target, hypothesis, evidence counters and per-concept mastery
        const existingLocal = (await getLearningState(sid)) || {};
        await saveLearningState(sid, {
          ...existingLocal,
          stage: data.step?.stage || 'solve',
          concept_id: targetConcept,
          displayed_concept_id: data.item?.concept || targetConcept,
          gap_concept_id: data.step?.gap_concept_id !== undefined ? data.step.gap_concept_id : existingLocal.gap_concept_id,
          misconception_tag: data.step?.misconception_tag !== undefined ? data.step.misconception_tag : existingLocal.misconception_tag,
          stuck_attempts: data.step?.stuck_attempts !== undefined ? data.step.stuck_attempts : (existingLocal.stuck_attempts || 0),
          bridge_recheck_fails: data.step?.bridge_recheck_fails !== undefined ? data.step.bridge_recheck_fails : (existingLocal.bridge_recheck_fails || 0),
          consecutive_successes: data.step?.consecutive_successes !== undefined ? data.step.consecutive_successes : (existingLocal.consecutive_successes || 0),
          mastery: data.step?.bkt_mastery !== undefined ? data.step.bkt_mastery : currentMastery,
          concept_masteries: {
            ...(existingLocal.concept_masteries || {}),
            ...(data.item?.concept && data.step?.bkt_mastery !== undefined ? { [data.item.concept]: data.step.bkt_mastery } : {})
          }
        });
      }
    } catch {
      // Network drop: fallback to offline next step
      const localPack = offlinePackData || (await getOfflinePack(classId));
      const localState = await getLearningState(sid);
      await loadNextStepOffline(localPack, localState);
    }
  };

  // Handle explicit Continue from Micro-Lesson
  const handleContinueLesson = async () => {
    if (effectivelyOnline && token) {
      try {
        const res = await fetch(`/api/student/${studentId}/continue-lesson`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          setPrevStage(currentStage);
          setCurrentStage('bridge_recheck');
          await loadNextStepOnline(token, studentId);
          return;
        }
      } catch (err) {
        console.warn('Online continue-lesson failed, falling back to local storage', err);
      }
    }

    // Offline explicit transition
    const localState = (await getLearningState(studentId)) || {};
    localState.stage = 'bridge_recheck';
    await saveLearningState(studentId, localState);
    setPrevStage(currentStage);
    setCurrentStage('bridge_recheck');
    const pack = offlinePackData || (await getOfflinePack(classId));
    await loadNextStepOffline(pack, localState);
  };

  // Load Next Step Offline (Using JS Engine & Local Pack)
  const loadNextStepOffline = async (packData, localState) => {
    setSelectedOptId(null);
    setHintLevel(0);
    const p = packData || offlinePackData;
    if (!p) {
      setStatusMessage('Offline pack not yet downloaded. Connect online to load content.');
      return;
    }

    const stage = localState?.stage || currentStage || 'solve';
    const concept = localState?.concept_id || currentConcept || 'c8_math_linear_eq_one_var';
    let gapConcept = localState?.gap_concept_id || null;
    const mastery = localState?.mastery !== undefined ? localState.mastery : currentMastery;
    const stuckAttempts = localState?.stuck_attempts || 0;
    const bridgeFails = localState?.bridge_recheck_fails || 0;

    // Check teacher flags offline
    if (bridgeFails >= 2) {
      setNextStepData({
        step: {
          item_type: 'flag',
          stage,
          reason: 'Student failed the bridge check repeatedly. Teacher flagged for small-group clinic intervention.',
          teacher_flag: 'REPEATED_BRIDGE_FAIL',
          bkt_mastery: mastery
        },
        item: null
      });
      return;
    }

    if (stuckAttempts >= 2) {
      setNextStepData({
        step: {
          item_type: 'flag',
          stage,
          reason: 'Student is stuck after multiple failed attempts. Teacher assistance flagged.',
          teacher_flag: 'STUCK_STUDENT',
          bkt_mastery: mastery
        },
        item: null
      });
      return;
    }

    // 1. Move ahead stage
    if (stage === 'move_ahead') {
      setNextStepData({
        step: {
          item_type: 'enrichment',
          stage: 'move_ahead',
          reason: 'High mastery verified with consistent evidence. Advancing ahead to next concept or enrichment.',
          bkt_mastery: mastery
        },
        item: null
      });
      return;
    }

    // 2. Learn stage (Micro-lesson)
    if (stage === 'learn') {
      const lessons = p.lessons || [];
      const miscTag = localState?.misconception_tag || null;
      let matchedLesson = null;
      let isFallback = false;

      // FIX 1: Match lesson to the actual misconception and language, not first lesson matching gap OR original topic
      if (miscTag) {
        matchedLesson = lessons.find(l => (l.misconception === miscTag || l.addresses_misconception === miscTag) && l.language === language);
        if (!matchedLesson && language !== 'en') {
          matchedLesson = lessons.find(l => (l.misconception === miscTag || l.addresses_misconception === miscTag) && l.language === 'en');
          if (matchedLesson) isFallback = true;
        }
      }

      // If no misconception-matched lesson, fallback to gap concept lesson
      if (!matchedLesson && gapConcept) {
        matchedLesson = lessons.find(l => l.concept === gapConcept && l.language === language);
        if (!matchedLesson && language !== 'en') {
          matchedLesson = lessons.find(l => l.concept === gapConcept && l.language === 'en');
          if (matchedLesson) isFallback = true;
        }
      }

      // If still not matched, fallback to target concept lesson
      if (!matchedLesson) {
        matchedLesson = lessons.find(l => l.concept === concept && l.language === language);
        if (!matchedLesson && language !== 'en') {
          matchedLesson = lessons.find(l => l.concept === concept && l.language === 'en');
          if (matchedLesson) isFallback = true;
        }
      }

      if (!matchedLesson && lessons.length > 0) {
        matchedLesson = lessons[0];
      }

      setNextStepData({
        step: {
          item_type: 'lesson',
          stage: 'learn',
          concept_id: gapConcept || concept,
          bkt_mastery: mastery,
          is_fallback: isFallback,
          fallback_label: isFallback ? 'English fallback (No lesson in your medium)' : null,
          reason: `Delivering targeted micro-lesson bridge for '${miscTag || gapConcept || concept}'.`
        },
        item: matchedLesson ? {
          id: matchedLesson.id,
          concept: matchedLesson.concept,
          content: matchedLesson.content,
          language: matchedLesson.language,
          is_fallback: isFallback
        } : null
      });
      return;
    }

    // 3. Bridge Re-Check stage
    if (stage === 'bridge_recheck') {
      const targetRecheckConcept = gapConcept || concept;
      const qs = p.questions || [];
      let candidates = qs.filter(q => q.concept === targetRecheckConcept && q.language === language);
      let isFallback = false;
      if (candidates.length === 0 && language !== 'en') {
        candidates = qs.filter(q => q.concept === targetRecheckConcept && q.language === 'en');
        isFallback = true;
      }
      if (candidates.length === 0) {
        candidates = qs.filter(q => q.concept === targetRecheckConcept);
      }
      if (candidates.length === 0) candidates = qs;

      const pastAttempts = await getAllLocalAttempts();
      const answeredIds = new Set(pastAttempts.map(a => a.question_id));
      const nextQ = candidates.find(q => !answeredIds.has(q.id)) || candidates[0];
      const ladder = (p.hints || p.hint_ladders)?.find(l => l.question_id === nextQ.id) || null;

      setNextStepData({
        step: {
          item_type: 'question',
          stage: 'bridge_recheck',
          concept_id: targetRecheckConcept,
          bkt_mastery: mastery,
          is_fallback: isFallback,
          reason: `Bridge re-check: verifying understanding of foundational prerequisite '${targetRecheckConcept}'.`
        },
        item: {
          id: nextQ.id,
          concept: nextQ.concept,
          question_text: nextQ.question_text,
          language: nextQ.language,
          is_fallback: isFallback,
          options: nextQ.options.map(opt => ({
            id: opt.id,
            text: opt.text,
            numeric_value: opt.numeric_value
          }))
        },
        hint_ladder: ladder
      });
      return;
    }

    // 4. Probe stage
    if (stage === 'probe') {
      const qs = p.questions || [];
      const miscTag = localState?.misconception_tag || null;

      if (!miscTag) {
        // Honest recovery message: no active misconception diagnosed, resume practice on target topic
        setCurrentStage('solve');
        await loadNextStepOffline(p, { ...localState, stage: 'solve' });
        return;
      }

      // FIX 1: Match probes strictly using the pack's probe_for_misconception field
      let probes = qs.filter(q => q.probe_for_misconception === miscTag && q.language === language);
      let isFallback = false;
      if (probes.length === 0 && language !== 'en') {
        probes = qs.filter(q => q.probe_for_misconception === miscTag && q.language === 'en');
        if (probes.length > 0) isFallback = true;
      }
      if (probes.length === 0) {
        probes = qs.filter(q => q.probe_for_misconception === miscTag);
      }

      if (probes.length === 0) {
        // No probe found for this misconception in pack: honest recovery to target topic
        setCurrentStage('solve');
        await loadNextStepOffline(p, { ...localState, stage: 'solve' });
        return;
      }

      const pastAttempts = await getAllLocalAttempts();
      const answeredIds = new Set(pastAttempts.map(a => a.question_id));
      const probeQ = probes.find(pr => !answeredIds.has(pr.id)) || probes[0];
      const ladder = (p.hints || p.hint_ladders)?.find(l => l.question_id === probeQ.id) || null;

      setNextStepData({
        step: {
          item_type: 'question',
          stage: 'probe',
          concept_id: probeQ.concept,
          bkt_mastery: mastery,
          is_fallback: isFallback,
          reason: `Administering diagnostic probe to test suspected misconception '${miscTag}'.`
        },
        item: {
          id: probeQ.id,
          concept: probeQ.concept,
          question_text: probeQ.question_text,
          language: probeQ.language,
          is_fallback: isFallback,
          options: probeQ.options.map(opt => ({
            id: opt.id,
            text: opt.text,
            numeric_value: opt.numeric_value
          }))
        },
        hint_ladder: ladder
      });
      return;
    }

    // 5. Default Solve stage
    const qs = p.questions || [];
    let candidates = qs.filter(q => q.concept === concept && q.language === language);
    let isFallback = false;
    if (candidates.length === 0 && language !== 'en') {
      candidates = qs.filter(q => q.concept === concept && q.language === 'en');
      isFallback = true;
    }
    if (candidates.length === 0 && language === 'en') {
      candidates = qs.filter(q => q.concept === concept && (q.language === 'en' || !q.language));
    }

    const pastAttempts = await getAllLocalAttempts();
    const answeredIds = new Set(pastAttempts.map(a => a.question_id));
    const unseen = candidates.filter(q => !answeredIds.has(q.id));

    if (unseen.length === 0 && candidates.length > 0 && mastery >= 0.85 && (localState?.consecutive_successes || 0) >= 3) {
      // Pool exhausted with verified high mastery: advance!
      setNextStepData({
        step: {
          item_type: 'enrichment',
          stage: 'move_ahead',
          reason: 'All practice questions completed with verified high mastery. Advancing ahead to enrichment.',
          bkt_mastery: mastery
        },
        item: null
      });
      return;
    }

    const nextQ = unseen.length > 0 ? unseen[0] : candidates[0];
    const ladder = (p.hints || p.hint_ladders)?.find(l => l.question_id === nextQ.id) || null;

    setNextStepData({
      step: {
        item_type: 'question',
        stage: 'solve',
        concept_id: concept,
        bkt_mastery: mastery,
        mastery_label: 'uncalibrated, hand-set',
        is_fallback: isFallback,
        reason: 'Adaptive practice question selected to calibrate to current mastery estimate.'
      },
      item: {
        id: nextQ.id,
        concept: nextQ.concept,
        question_text: nextQ.question_text,
        language: nextQ.language,
        is_fallback: isFallback,
        options: nextQ.options.map(opt => ({
          id: opt.id,
          text: opt.text,
          numeric_value: opt.numeric_value
        }))
      },
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
          const targetConcept = result.concept_id || cId;
          setConceptMasteries((prev) => ({ ...prev, [targetConcept]: result.updated_mastery }));
          if (targetConcept === currentConcept) {
            setCurrentMastery(result.updated_mastery);
          }
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
    const pack = offlinePackData || (await getOfflinePack(classId));
    if (!pack) {
      setStatusMessage('Error: No offline content pack available for grading.');
      return;
    }

    const fullQuestion = pack.questions.find((q) => q.id === qId);
    const matchedOpt = fullQuestion?.options.find((o) => o.id === selectedOptId);
    const localIsCorrect = matchedOpt?.is_correct || false;
    const localMiscTag = matchedOpt?.misconception_tag || null;
    const targetConcept = fullQuestion?.concept || cId;

    // FIX 3: Update BKT mastery for the question's OWN concept
    const currentTargetMastery = conceptMasteries[targetConcept] !== undefined
      ? conceptMasteries[targetConcept]
      : (targetConcept === currentConcept ? currentMastery : 0.2);
    const nextMastery = bktEngine.update(currentTargetMastery, localIsCorrect);

    const updatedConceptMasteries = {
      ...conceptMasteries,
      [targetConcept]: nextMastery
    };
    setConceptMasteries(updatedConceptMasteries);
    if (targetConcept === currentConcept) {
      setCurrentMastery(nextMastery);
    }

    // 2. Evaluate Sequencer state locally
    const localState = (await getLearningState(studentId)) || {};
    let nextStage = currentStage;
    let nextStuckAttempts = localState?.stuck_attempts || 0;
    let nextBridgeFails = localState?.bridge_recheck_fails || 0;
    let nextConsecutiveSuccesses = localState?.consecutive_successes || 0;
    let gapConcept = localState?.gap_concept_id || null;
    let activeMiscTag = localState?.misconception_tag || null;

    if (localIsCorrect) {
      if (targetConcept === currentConcept) {
        nextConsecutiveSuccesses += 1;
      }
      if (currentStage === 'solve' || currentStage === 'bridge_recheck') {
        nextStuckAttempts = 0;
      }
    } else {
      if (targetConcept === currentConcept) {
        nextConsecutiveSuccesses = 0;
      }
      if (currentStage === 'solve' || currentStage === 'bridge_recheck') {
        nextStuckAttempts += 1;
      }
    }

    if (currentStage === 'probe') {
      if (!localIsCorrect) {
        // Probe wrong confirms gap -> move to micro-lesson
        nextStage = 'learn';
        nextStuckAttempts = 0; // resets upon entering lesson
        gapConcept = targetConcept || localState?.gap_concept_id || null;
      } else {
        // Probe correct contradicts gap -> return to practice
        nextStage = 'solve';
        gapConcept = null;
        activeMiscTag = null;
      }
    } else if (currentStage === 'solve') {
      if (!localIsCorrect) {
        if (localMiscTag) {
          nextStage = 'probe';
          activeMiscTag = localMiscTag;
        } else if (nextStuckAttempts >= 2) {
          nextStage = 'flag';
        }
      } else {
        const origMastery = updatedConceptMasteries[currentConcept] !== undefined ? updatedConceptMasteries[currentConcept] : currentMastery;
        if (targetConcept === currentConcept && origMastery >= 0.85 && nextConsecutiveSuccesses >= 3) {
          nextStage = 'move_ahead';
        }
      }
    } else if (currentStage === 'bridge_recheck') {
      if (localIsCorrect) {
        // Bridge recheck passed: return to saved original target topic
        nextStage = 'solve';
        nextBridgeFails = 0;
        nextStuckAttempts = 0;
        gapConcept = null;
        activeMiscTag = null;
      } else {
        nextBridgeFails += 1;
        if (nextBridgeFails >= 2) {
          nextStage = 'flag';
        }
      }
    }

    setPrevStage(currentStage);
    setCurrentStage(nextStage);

    // 3. Record in IndexedDB attempts & sync queue
    const attemptRecord = {
      attempt_id: attemptId,
      student_id: studentId,
      question_id: qId,
      concept_id: targetConcept,
      selected_option_id: selectedOptId,
      is_correct: localIsCorrect,
      misconception_tag: localMiscTag,
      time_spent_seconds: 5,
      timestamp: new Date().toISOString()
    };

    await recordAttemptLocal(attemptRecord);
    await enqueueSyncAttempt(attemptRecord);

    // 4. Update local learning state in IndexedDB (keeping student state isolated)
    const updatedLocalState = {
      stage: nextStage,
      concept_id: currentConcept,
      gap_concept_id: gapConcept,
      misconception_tag: activeMiscTag,
      stuck_attempts: nextStuckAttempts,
      bridge_recheck_fails: nextBridgeFails,
      consecutive_successes: nextConsecutiveSuccesses,
      mastery: updatedConceptMasteries[currentConcept] !== undefined ? updatedConceptMasteries[currentConcept] : currentMastery,
      concept_masteries: updatedConceptMasteries
    };
    await saveLearningState(studentId, updatedLocalState);
    await refreshQueueCount();

    setStatusMessage(
      `Offline graded locally: ${localIsCorrect ? 'Correct!' : 'Incorrect.'} Mastery for ${targetConcept} updated to ${(nextMastery * 100).toFixed(0)}%. Queued for sync.`
    );

    // Load next step offline
    await loadNextStepOffline(pack, updatedLocalState);
  };

  // FIX 1: Check and apply per-device purge instructions using device_purge_token
  const checkAndApplyDevicePurges = async () => {
    try {
      const purgeToken = await getMeta('device_purge_token');
      if (!purgeToken) return;

      const res = await fetch('/api/device/purge-instructions', {
        headers: { 'X-Device-Purge-Token': purgeToken }
      });

      if (res.ok) {
        const data = await res.json();
        const instructions = data.purge_instructions || [];
        if (instructions.length === 0) return;

        const ackedIds = [];
        for (const inst of instructions) {
          const resDel = await deleteStudentBySubjectKey(inst.subject_key);
          ackedIds.push(inst.delivery_id);
          if (resDel.deleted) {
            setAuthenticated(false);
            setToken(null);
            setStatusMessage('Student profile purged by teacher policy.');
          }
        }

        if (ackedIds.length > 0) {
          await fetch('/api/device/purge-ack', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Device-Purge-Token': purgeToken
            },
            body: JSON.stringify({ delivery_ids: ackedIds })
          });
        }
      }
    } catch (err) {
      console.warn('Purge check error:', err);
    }
  };

  // Sync on Reconnect or Click (FIX 1, FIX 3f, FIX 4)
  const triggerSyncIfPossible = async (forceOnline = false) => {
    const isConnOnline = forceOnline || effectivelyOnline || (navigator.onLine && !devSimulateOffline);
    if (!isConnOnline) return;

    // Always check for pending device purges when online (FIX 1)
    await checkAndApplyDevicePurges();

    const queue = await getSyncQueue();
    if (queue.length === 0) return;

    try {
      const devId = await getOrCreateDeviceId();
      const purgeToken = await getMeta('device_purge_token');
      const authHeader = token ? { 'Authorization': `Bearer ${token}` } : {};
      const purgeHeader = purgeToken ? { 'X-Device-Purge-Token': purgeToken } : {};

      const res = await fetch('/api/privacy/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeader,
          ...purgeHeader
        },
        body: JSON.stringify({
          device_id: devId,
          class_id: classId || '8-A',
          queued_attempts: queue
        })
      });

      if (res.status === 401) {
        // Session token invalidated after deletion; purge check
        await checkAndApplyDevicePurges();
        return;
      }

      if (res.ok) {
        const syncData = await res.json();

        // FIX 4: If server indicates device is stale / unregistered, wipe local data
        if (syncData.is_stale_reset_required) {
          await wipeAllStudentData();
          setAuthenticated(false);
          setStatusMessage('Server policy: Device cache reset required. Please sign in online.');
          return;
        }

        // FIX 1: Apply any purge instructions returned on sync
        if (syncData.purge_instructions && syncData.purge_instructions.length > 0) {
          const ackedIds = [];
          for (const inst of syncData.purge_instructions) {
            const resDel = await deleteStudentBySubjectKey(inst.subject_key);
            ackedIds.push(inst.delivery_id);
            if (resDel.deleted) {
              setAuthenticated(false);
              setToken(null);
              setStatusMessage('Student profile purged by teacher policy.');
            }
          }
          if (ackedIds.length > 0 && purgeToken) {
            await fetch('/api/device/purge-ack', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-Device-Purge-Token': purgeToken
              },
              body: JSON.stringify({ delivery_ids: ackedIds })
            });
          }
        }

        // Do not clear sync queue if in purge-only mode
        if (syncData.purge_mode) {
          return;
        }

        // Clear local sync queue ONLY for attempts saved by server
        if (syncData.synced_attempt_ids && syncData.synced_attempt_ids.length > 0) {
          await clearSyncQueue(syncData.synced_attempt_ids);
        } else if (syncData.synced_attempts_processed > 0) {
          await clearSyncQueue();
        }
        await refreshQueueCount();
        setLastSyncTime(new Date().toLocaleTimeString());

        // Update server authoritative mastery
        if (syncData.authoritative_mastery) {
          setCurrentMastery(syncData.authoritative_mastery.mastery_estimate);
          setMasteryLabel(syncData.authoritative_mastery.mastery_label || 'uncalibrated, hand-set');
        }

        // Reconcile server authoritative plan and stage with local state
        if (syncData.authoritative_state) {
          const authState = syncData.authoritative_state;
          if (authState.current_stage) {
            setPrevStage(currentStage);
            setCurrentStage(authState.current_stage);
          }
          if (authState.current_concept_id) {
            setCurrentConcept(authState.current_concept_id);
          }
          const currentLocal = (await getLearningState(studentId)) || {};
          const mergedState = {
            ...currentLocal,
            stage: authState.current_stage || currentLocal.stage,
            concept_id: authState.current_concept_id || currentLocal.concept_id,
            gap_concept_id: authState.gap_concept_id !== undefined ? authState.gap_concept_id : currentLocal.gap_concept_id,
            stuck_attempts: authState.stuck_attempts_count !== undefined ? authState.stuck_attempts_count : currentLocal.stuck_attempts,
            bridge_recheck_fails: authState.bridge_recheck_fails !== undefined ? authState.bridge_recheck_fails : currentLocal.bridge_recheck_fails,
            consecutive_successes: authState.consecutive_successes !== undefined ? authState.consecutive_successes : currentLocal.consecutive_successes,
            mastery: authState.mastery_estimate !== undefined ? authState.mastery_estimate : currentLocal.mastery
          };
          await saveLearningState(studentId, mergedState);
        }

        if (syncData.synced_attempts_processed > 0) {
          setStatusMessage(`Synced ${syncData.synced_attempts_processed} offline attempts with server!`);
        }
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
              setToken(null);
              setStudentId('');
              setNextStepData(null);
              setSelectedOptId(null);
              setHintLevel(0);
              setCurrentMastery(0.2);
              setCurrentConcept('c8_math_linear_eq_one_var');
              setCurrentStage('solve');
              setPrevStage(null);
              setConceptMasteries({});
              setStatusMessage('');
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

      {/* Visible message for every stage change (Acceptance Test A & Failure 2) */}
      <div
        id="stage-change-message"
        data-testid="stage-change-message"
        style={{
          margin: '10px 0',
          padding: '10px 14px',
          borderRadius: '8px',
          fontSize: '13px',
          fontWeight: '500',
          background: currentStage === 'probe'
            ? 'rgba(234, 179, 8, 0.15)'
            : currentStage === 'learn'
            ? 'rgba(56, 189, 248, 0.15)'
            : currentStage === 'bridge_recheck'
            ? 'rgba(168, 85, 247, 0.15)'
            : currentStage === 'move_ahead'
            ? 'rgba(16, 185, 129, 0.15)'
            : currentStage === 'flag'
            ? 'rgba(239, 68, 68, 0.15)'
            : (prevStage && prevStage !== 'solve')
            ? 'rgba(34, 197, 94, 0.15)'
            : 'rgba(255, 255, 255, 0.05)',
          border: '1px solid ' + (
            currentStage === 'probe' ? 'rgba(234, 179, 8, 0.4)'
            : currentStage === 'learn' ? 'rgba(56, 189, 248, 0.4)'
            : currentStage === 'bridge_recheck' ? 'rgba(168, 85, 247, 0.4)'
            : currentStage === 'move_ahead' ? 'rgba(16, 185, 129, 0.4)'
            : currentStage === 'flag' ? 'rgba(239, 68, 68, 0.4)'
            : (prevStage && prevStage !== 'solve') ? 'rgba(34, 197, 94, 0.4)'
            : 'var(--border-color)'
          ),
          color: currentStage === 'probe'
            ? '#fde047'
            : currentStage === 'learn'
            ? '#7dd3fc'
            : currentStage === 'bridge_recheck'
            ? '#d8b4fe'
            : currentStage === 'move_ahead'
            ? '#6ee7b7'
            : currentStage === 'flag'
            ? '#fca5a5'
            : '#e2e8f0'
        }}
      >
        {currentStage === 'probe' && 'Diagnostic Probe: Checking foundational prerequisite...'}
        {currentStage === 'learn' && 'Micro-Lesson: Reviewing prerequisite concept bridge.'}
        {currentStage === 'bridge_recheck' && 'Bridge Re-check: Verifying prerequisite mastery before continuing.'}
        {currentStage === 'solve' && (prevStage === 'bridge_recheck' || prevStage === 'learn' || prevStage === 'probe') && 'Returned to original topic: Solved the prerequisite gap! Back to standard practice.'}
        {currentStage === 'solve' && (!prevStage || prevStage === 'solve') && 'Standard Practice: Solve the problem below.'}
        {currentStage === 'move_ahead' && 'Fast Track: Mastery achieved! Advancing ahead.'}
        {currentStage === 'flag' && 'Intervention: Teacher notified for 1-on-1 clinic support.'}
      </div>

      {/* Lesson Screen (Failure 2) */}
      {step?.item_type === 'lesson' && (
        <div id="lesson-screen" data-testid="lesson-screen" className="info-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="badge-heuristic">author-drafted, unreviewed</span>
            <span id="lesson-language-badge" className="badge-uncalibrated">
              Medium: {item?.language ? item.language.toUpperCase() : language.toUpperCase()}
              {item?.is_fallback ? ' (English fallback)' : ''}
            </span>
          </div>
          <h3 id="lesson-title" style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px', color: '#fff' }}>
            {item?.title || 'Micro-Lesson Bridge'}
          </h3>
          <div
            id="lesson-content"
            data-testid="lesson-content"
            style={{
              fontSize: '14px',
              lineHeight: '1.6',
              color: '#e2e8f0',
              marginBottom: '16px',
              whiteSpace: 'pre-wrap'
            }}
          >
            {item?.content || 'Review the prerequisite material carefully before attempting the re-check.'}
          </div>
          <button
            id="continue-lesson-btn"
            data-testid="continue-lesson-btn"
            onClick={handleContinueLesson}
            className="action-btn"
            style={{ width: '100%' }}
          >
            Continue
          </button>
        </div>
      )}

      {/* Teacher Flag Screen (Failure 2) */}
      {step?.item_type === 'flag' && (
        <div id="teacher-flag-screen" data-testid="teacher-flag-screen" className="info-card" style={{ borderLeft: '4px solid #f43f5e' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#fca5a5', marginBottom: '8px' }}>
            Teacher Assistance Flagged
          </h3>
          <p id="teacher-flag-message" style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.5' }}>
            Your teacher has been notified. Please wait or ask your teacher.
          </p>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Reason: {step?.reason || 'Concept practice paused for small group clinic.'}
          </div>
        </div>
      )}

      {/* Move-Ahead / Enrichment Screen (Failure 2) */}
      {step?.item_type === 'enrichment' && (
        <div id="enrichment-screen" data-testid="enrichment-screen" className="info-card" style={{ borderLeft: '4px solid #10b981' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#6ee7b7', marginBottom: '8px' }}>
            High Mastery Verified!
          </h3>
          <p id="move-ahead-message" style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.5' }}>
            {step?.reason || 'Congratulations! You demonstrated strong mastery. Advancing ahead to next concept!'}
          </p>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Next concept / enrichment unlocked: {currentConcept}
          </div>
        </div>
      )}

      {/* Question Content */}
      {item && step?.item_type === 'question' && (
        <div id="question-card" data-testid="question-card" data-concept={item.concept} className="info-card">
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
              id="request-hint-btn"
              data-testid="request-hint-btn"
              onClick={() => setHintLevel(1)}
              className="btn-secondary"
              style={{ fontSize: '11px' }}
            >
              Need a Hint? (Level 1)
            </button>
          )}
          {hintLevel >= 1 && (
            <div id="hint-display-card" className="info-card" style={{ background: 'rgba(56, 189, 248, 0.08)', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: 'var(--accent-blue)', fontWeight: '700' }}>HINT LEVEL 1</div>
              <div id="hint-level-1-text" style={{ fontSize: '13px' }}>{hintLadder.level_1_hint}</div>
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
          id="student-footer-status-message"
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
