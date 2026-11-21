import React, { useEffect, useRef, useState } from 'react';
import { LoginIcon } from './LoginShell';
import './TestView.css';

/** The server still chooses and grades every adaptive item in order. */
export default function TestView({ studentId, token, onExit }) {
  const [phase, setPhase] = useState('loading');
  const [sessionState, setSessionState] = useState(null);
  const [selectedOptId, setSelectedOptId] = useState(null);
  const [reviewSequence, setReviewSequence] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const mounted = useRef(true);
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    (async () => {
      try {
        const response = await fetch(`/api/student/${studentId}/test/active`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal });
        if (!response.ok) throw new Error('Could not check for a saved test. Try again before starting.');
        const data = await response.json();
        if (!mounted.current) return;
        if (data.active) { setSessionState(data.active); setPhase('running'); }
        else setPhase('intro');
      } catch (e) {
        if (!mounted.current || e.name === 'AbortError') return;
        setError(e.message); setPhase('intro');
      }
    })();
    return () => { mounted.current = false; controller.abort(); };
  }, [studentId, token]);

  const startTest = async () => {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const response = await fetch(`/api/student/${studentId}/test/start`, { method: 'POST', headers, body: JSON.stringify({}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not start test.');
      if (!mounted.current) return;
      setSessionState(data); setSelectedOptId(null); setReviewSequence(null); setPhase('running');
    } catch (e) { if (mounted.current) setError(e.message); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  };

  const submitAnswer = async () => {
    if (pending.current || !selectedOptId || !sessionState?.current_item || reviewSequence !== null) return;
    const item = sessionState.current_item;
    const choice = selectedOptId;
    pending.current = true; setBusy(true); setError('');
    try {
      const response = await fetch(`/api/student/${studentId}/test/answer`, {
        method: 'POST', headers,
        body: JSON.stringify({ session_id: sessionState.session_id, question_id: item.question.id, selected_option_id: choice, attempt_id: `test-${sessionState.session_id}-${item.sequence}` })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Answer rejected. Your selection is still here; try again.');
      // Identical retries return the state itself; ordinary replies wrap it in session.
      const state = data.session || (data.session_id ? data : null);
      if (!state) throw new Error('The response was incomplete. Retry to recover the saved result.');
      if (!mounted.current) return;
      const recorded = state.answered_items?.find(answer => answer.sequence === item.sequence);
      const correct = recorded ? recorded.is_correct : data.server_graded_correct;
      setNotice(`Question ${item.sequence}: ${correct ? 'correct' : 'not quite'}. Answer recorded.`);
      setSessionState(state); setSelectedOptId(null); setReviewSequence(null);
      setPhase(state.status === 'completed' || data.completed ? 'summary' : 'running');
    } catch (e) { if (mounted.current) setError(e.message); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  };

  const history = sessionState?.answered_items || [];
  const summary = sessionState?.summary;
  const current = sessionState?.current_item;
  const reviewed = history.find(item => item.sequence === reviewSequence);
  const displayed = reviewed || current;
  const reviewing = Boolean(reviewed);
  const answered = sessionState?.answered_count || 0;
  const planned = sessionState?.planned_length || 0;
  const served = summary?.total_served ?? answered;
  const correct = summary?.total_correct ?? history.filter(item => item.is_correct).length;
  const percentage = served ? (correct / served * 100).toFixed(1).replace(/\.0$/, '') : null;
  const progress = phase === 'summary' ? 100 : planned ? Math.min(100, Math.round(answered / planned * 100)) : 0;
  const sequence = reviewed?.sequence || current?.sequence || 1;

  const review = (seq) => { if (busy) return; setReviewSequence(seq); setError(''); };
  const previous = () => {
    const previousItem = [...history].reverse().find(item => item.sequence < sequence);
    if (previousItem) review(previousItem.sequence);
  };
  const nextReviewed = () => {
    const nextItem = history.find(item => item.sequence > sequence);
    setReviewSequence(nextItem ? nextItem.sequence : null);
  };

  return <div className="setu-quiz-page">
    <header className="setu-quiz-header">
      <a className="setu-quiz-brand" href="#" onClick={e => { e.preventDefault(); if (!busy) onExit(); }} aria-label="Back to Setu practice"><LoginIcon /><span>Setu<span>Quiz</span></span></a>
      <nav aria-label="Quiz navigation"><button type="button" onClick={onExit} disabled={busy}>Practice</button><span className="setu-quiz-profile"><LoginIcon kind="user" /><span>{studentId}</span></span></nav>
    </header>
    <main className="setu-quiz-layout">
      <section className="setu-quiz-main" aria-labelledby="quiz-heading">
        <h1 id="quiz-heading">Class 8 Maths Quiz</h1>
        <div className="setu-quiz-progress-row"><div className="setu-quiz-track" role="progressbar" aria-label="Questions answered" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div>
        {phase === 'loading' && <p className="setu-quiz-intro" role="status">Checking your saved test...</p>}
        {phase === 'intro' && <div className="setu-quiz-intro"><h2>Your next step starts here.</h2><p>Questions adapt to your saved concept mastery and previous answers. This is an online test with no hints.</p><p>Next submits your answer and chooses the next question. Previous lets you review submitted answers, not change them. Future questions unlock as you go.</p><p className="setu-quiz-small">Mastery estimates remain uncalibrated and hand-set. Concepts with too few questions are listed in your report.</p><button id="start-test-btn" data-testid="start-test-btn" className="setu-quiz-primary" onClick={startTest} disabled={busy}>{busy ? 'Starting...' : 'Start Adaptive Test'}</button></div>}
        {notice && <p id="test-feedback" className="setu-quiz-notice" role="status">{notice}</p>}
        {displayed && phase !== 'intro' && <>
          <p className="setu-quiz-question"><strong>Question {displayed.sequence}/{planned}: </strong><span id="test-question-text">{displayed.question.question_text}</span></p>
          <p className="setu-quiz-topic">{displayed.concept_name}{displayed.is_fallback ? ' (English fallback: no item in your medium)' : ''}{reviewing ? ' · Submitted answer, read-only' : ''}</p>
          <div className="setu-quiz-options" role="group" aria-label="Answer choices">{displayed.question.options.map((option, i) => {
            const selected = (reviewing ? reviewed.selected_option_id : selectedOptId) === option.id;
            return <button type="button" key={option.id} data-testid={`test-option-${option.id}`} className={`setu-quiz-option${selected ? ' is-selected' : ''}${reviewing && selected ? reviewed.is_correct ? ' is-correct' : ' is-wrong' : ''}`} aria-pressed={selected} disabled={busy || reviewing} onClick={() => setSelectedOptId(option.id)}><span className="setu-quiz-option-letter" aria-hidden="true">{String.fromCharCode(65 + i)}</span><span>{option.text}</span>{selected && <span className="setu-quiz-check" aria-hidden="true">{reviewing ? reviewed.is_correct ? '✓' : '×' : '✓'}</span>}</button>;
          })}</div>
          {reviewing && <p className="setu-quiz-small">This answer was {reviewed.is_correct ? 'correct' : 'incorrect'}. Submitted answers stay locked so the adaptive sequence remains valid.</p>}
          <div className="setu-quiz-actions"><button type="button" className="setu-quiz-secondary" onClick={previous} disabled={busy || !history.some(item => item.sequence < sequence)}>Previous</button>{reviewing ? <button type="button" className="setu-quiz-primary" onClick={nextReviewed} disabled={busy}>{history.some(item => item.sequence > sequence) ? 'Next' : current ? 'Current question' : 'Back to report'}</button> : <button id="submit-test-answer" data-testid="submit-test-answer" type="button" className="setu-quiz-primary" disabled={!selectedOptId || busy} onClick={submitAnswer}>{busy ? 'Submitting...' : answered + 1 >= planned ? 'Finish test' : 'Next'}</button>}</div>
          {!reviewing && <p className="setu-quiz-submit-note">Next submits your selected answer. You cannot edit it afterward.</p>}
        </>}
        {phase === 'summary' && summary && !reviewing && <section className="setu-quiz-report" aria-label="Test report"><h2>Test Report</h2><p id="test-score" data-testid="test-score">{summary.total_correct} / {summary.total_served} correct</p><p className="setu-quiz-small">Mastery estimates: {summary.mastery_label}</p><div className="setu-quiz-concept-list">{summary.per_concept.map(concept => <div key={concept.concept_id}><strong>{concept.concept_id.replace(/c\d+_math_/, '').replace(/_/g, ' ')}</strong><span>{concept.correct}/{concept.served}</span><p>Estimate {(concept.mastery_before * 100).toFixed(0)}% → {(concept.mastery_after * 100).toFixed(0)}%{concept.misconception_tags.length ? ` · Observed: ${concept.misconception_tags.join(', ')}` : ''}</p></div>)}</div><p id="test-recommendation" data-testid="test-recommendation">{summary.recommendation}</p>{summary.excluded_concepts?.length > 0 && <p className="setu-quiz-small">Not assessed because of question-bank coverage: {summary.excluded_concepts.join(', ')}</p>}<button id="practice-weakest-btn" data-testid="practice-weakest-btn" className="setu-quiz-primary" onClick={onExit}>Practice {summary.weakest_concept_name || 'Recommended Concept'}</button></section>}
        {error && <p className="setu-quiz-error" role="alert">{error}</p>}
        {phase !== 'intro' && <button type="button" className="setu-quiz-back" onClick={onExit} disabled={busy}>{phase === 'summary' ? 'Back to practice' : 'Save and return to practice'}</button>}
      </section>
      <aside className="setu-quiz-sidebar" aria-label="Score and question status"><div className="setu-quiz-score"><strong>{percentage === null ? '—' : `${percentage}%`}</strong><p>{served ? `You got ${correct} out of ${served} answers correct` : 'Your score appears after your first answer'}</p></div>
        {planned > 0 && <><span id="test-progress" data-testid="test-progress" className="setu-sr-only">{current?.sequence || answered} / {planned}</span><nav className="setu-quiz-question-list" aria-label="Question status">{Array.from({ length: phase === 'summary' ? answered : planned }, (_, i) => {
          const seq = i + 1; const result = history.find(item => item.sequence === seq); const isCurrent = current?.sequence === seq; const active = reviewed ? seq === reviewSequence : isCurrent;
          return <button type="button" key={seq} data-testid={`quiz-status-${seq}`} className={active ? 'is-current' : ''} aria-current={active ? 'step' : undefined} aria-label={`Question ${seq}: ${result ? result.is_correct ? 'correct, review answer' : 'incorrect, review answer' : isCurrent ? 'current question' : 'not yet available'}`} disabled={busy || (!result && !isCurrent)} onClick={() => review(result ? seq : null)}><span className={`setu-quiz-dot ${result ? result.is_correct ? 'is-correct' : 'is-wrong' : ''}`} aria-hidden="true">{result ? result.is_correct ? '✓' : '×' : ''}</span>Question {seq}</button>;
        })}</nav><p className="setu-quiz-small">Review past answers. Future questions unlock one at a time.</p></>}
      </aside>
    </main>
  </div>;
}
