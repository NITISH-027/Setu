import React, { useEffect, useState } from 'react';
import { LoginIcon } from './LoginShell';
import './StudentHome.css';

export default function StudentHome({ studentId, classId, token, online, queuedCount, currentConcept, currentStage, onContinue, onTest, onNavigate, onTour, onLogout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [section, setSection] = useState('dashboard');
  const [query, setQuery] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError('');
    if (!online) { setError('Offline: saved server totals are unavailable. Your cached practice is still available.'); return; }
    fetch(`/api/student/${studentId}/dashboard?timezone_offset_minutes=${-new Date().getTimezoneOffset()}`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error('Could not load saved activity. Continue practice and try again later.'); return response.json(); })
      .then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, [studentId, token, online]);
  const currentName = data?.concepts.find(c => c.concept_id === currentConcept)?.name || currentConcept.replace(/c\d+_math_/, '').replace(/_/g, ' ');
  const conceptList = (data?.concepts || []).filter(c => c.name.toLowerCase().includes(query.toLowerCase()));
  const concepts = section === 'chapters' ? conceptList : [...conceptList].sort((a, b) => b.attempts - a.attempts).slice(0, 5);
  const max = Math.max(1, ...(data?.activity || []).map(day => day.attempts));
  const accuracy = data?.total_attempts ? Math.round(data.total_correct / data.total_attempts * 100) : null;
  const go = (next) => { setSection(next); document.getElementById('home-content')?.scrollIntoView({ behavior: 'auto', block: 'start' }); };
  const number = value => value === undefined ? '—' : value;

  return <div className={`setu-home setu-section-${section}`}>
    <aside className="setu-home-sidebar">
      <a href="#" className="setu-home-brand" onClick={e => { e.preventDefault(); go('dashboard'); }}><LoginIcon /><span>Setu<span>Learn</span></span></a>
      <div className="setu-home-profile"><span className="setu-home-avatar"><LoginIcon kind="user" /></span><strong>{studentId}</strong><span>Class {classId} · Maths learner</span><div className="setu-home-streak"><span aria-hidden="true">✦</span> {data ? `${data.streak_days}-day streak` : 'Streak unavailable'}<small>Saved attempts, through today or yesterday</small></div></div>
      <p className="setu-home-menu-label">Your learning</p>
      <nav aria-label="Student navigation">
        <button type="button" className={section === 'dashboard' ? 'is-active' : ''} onClick={() => go('dashboard')}><span aria-hidden="true">◫</span>Dashboard</button>
        <button type="button" onClick={onContinue}><span aria-hidden="true">▷</span>Practice</button>
        <button type="button" className={section === 'chapters' ? 'is-active' : ''} onClick={() => go('chapters')}><span aria-hidden="true">▤</span>Chapters</button>
        <button type="button" className={section === 'progress' ? 'is-active' : ''} onClick={() => go('progress')}><span aria-hidden="true">▥</span>Progress</button>
      </nav>
      <div className="setu-home-current"><p className="setu-home-menu-label">Current learning path</p><strong>{currentName}</strong><p>Setu chooses your next step from your saved plan.</p><button type="button" onClick={onContinue}>Continue learning ↗</button></div>
      <div className="setu-home-tools"><button type="button" onClick={onLogout}>Log out</button><button type="button" onClick={onTour}>Guided tour</button><button id="tab-teacher" onClick={() => onNavigate('teacher')}>Teacher</button><button id="tab-privacy" onClick={() => onNavigate('privacy')}>Privacy</button><button id="tab-paper" onClick={() => onNavigate('paper')}>Paper mode</button><button id="tab-review" onClick={() => onNavigate('review')}>Content review</button></div>
    </aside>
    <main id="home-content" className="setu-home-content">
      <header className="setu-home-greeting"><p>{section === 'dashboard' ? `Welcome back, ${studentId}` : section === 'chapters' ? 'YOUR MATHS LIBRARY' : 'YOUR SAVED LEARNING'}</p><h1>{section === 'dashboard' ? <>Learn <span className="setu-home-spark" aria-hidden="true">✦</span> something new.</> : section === 'chapters' ? <>Little chapters. <span className="setu-home-spark" aria-hidden="true">▤</span> New possibilities.</> : <>Progress <span className="setu-home-spark" aria-hidden="true">✦</span> at your own pace.</>}</h1><span className="setu-home-connection">{online ? 'Online' : 'Offline'} · {queuedCount} queued on device</span></header>
      <div className="setu-home-search"><span aria-hidden="true">⌕</span><label className="setu-sr-only" htmlFor="chapter-search">Find a chapter</label><input id="chapter-search" placeholder="Find a chapter or maths concept" value={query} onChange={e => { setQuery(e.target.value); setSection('chapters'); }} /><span aria-hidden="true">↗</span></div>
      {error && <p className="setu-home-error" role="status">{error}</p>}
      {!data && !error && <p role="status" className="setu-home-loading">Loading your saved activity...</p>}
      <section className="setu-home-stats" aria-label="Learning statistics">
        <div><p>Concepts practised</p><strong>{number(data?.concepts_practised)}</strong><small>Across your saved attempts</small></div>
        <div><p>Questions answered</p><strong>{number(data?.total_attempts)}</strong><small>Practice + chapter tests</small></div>
        <div><p>Answer accuracy</p><strong>{accuracy === null ? '—' : `${accuracy}%`}</strong><small>{data?.total_attempts ? `${data.total_correct} of ${data.total_attempts} correct` : 'Appears after your first saved answer'}</small></div>
        <div><p>Active days</p><strong>{number(data?.active_days_last_7)}<span> / 7</span></strong><small>Days with saved attempts</small></div>
      </section>
      <div className="setu-home-grid">
        <section className="setu-home-panel setu-home-activity" aria-labelledby="activity-heading"><div className="setu-home-panel-title"><h2 id="activity-heading">Learning activity</h2><span>Last 7 days</span></div><p className="setu-home-subtitle">Saved answers, not time spent</p>
          {data ? <><div className="setu-home-chart" role="img" aria-label={data.activity.map(day => `${day.date}: ${day.attempts} attempts`).join('; ')}>{data.activity.map(day => <div className="setu-home-chart-col" key={day.date}><strong>{day.attempts}</strong><div className="setu-home-bar-space"><span style={{ height: `${day.attempts / max * 100}%` }} /></div><span>{new Date(`${day.date}T12:00:00`).toLocaleDateString('en', { weekday: 'short' })}</span></div>)}</div><p className="setu-home-subtitle">{data.total_attempts ? 'Synced server activity. Pending device answers are not included yet.' : 'No saved answers yet. Your first practice answer starts this chart.'}</p></> : <p className="setu-home-empty">Activity will appear when saved totals are available.</p>}
        </section>
        <section className="setu-home-panel setu-home-continue"><span className="setu-home-pill">Your next step</span><h2>Pick up where you left off.</h2><p>{currentName}</p><small>Current step: {currentStage.replace(/_/g, ' ')}</small><button id="continue-learning-btn" data-testid="continue-learning-btn" className="setu-home-primary" type="button" onClick={onContinue}>Continue learning <span aria-hidden="true">↗</span></button><hr /><p>{data?.active_test ? `Test in progress · ${data.active_test.answered}/${data.active_test.planned} answered` : 'Ready for a chapter check?'}</p><button id="home-test-btn" type="button" className="setu-home-secondary" disabled={!online} onClick={onTest}>{data?.active_test ? 'Continue your test' : 'Start a chapter test'}</button>{!online && <small>Chapter tests need an internet connection.</small>}</section>
        <section className="setu-home-panel setu-home-progress"><div className="setu-home-panel-title"><h2>{section === 'chapters' ? 'Maths chapters & concepts' : section === 'progress' ? 'Recent concept estimates' : 'Your concept progress'}</h2><button type="button" onClick={() => go(section === 'chapters' ? 'dashboard' : 'chapters')}>{section === 'chapters' ? 'Show recent' : 'View all'} ↗</button></div><p className="setu-home-subtitle">Mastery estimates are uncalibrated and hand-set, not course completion.</p>{section === 'chapters' ? <div className="setu-chapter-grid">{concepts.map((concept, index) => <article className="setu-chapter-card" key={concept.concept_id}><div className="setu-chapter-card-top"><span aria-hidden="true">▤</span><span>{concept.concept_id === currentConcept ? 'Current path' : concept.attempts ? 'Practised' : 'Not practised'}</span></div><h3>{concept.name}</h3><p>{concept.attempts} saved answers</p><div className="setu-chapter-estimate"><span>Mastery estimate</span><strong>{concept.mastery === null ? 'Not estimated' : `${Math.round(concept.mastery * 100)}%`}</strong></div>{concept.mastery !== null && <div className="setu-home-mastery-track"><span style={{ width: `${Math.round(concept.mastery * 100)}%` }} /></div>}</article>)}</div> : <><div className="setu-home-progress-head"><span>Concept</span><span>Attempts</span><span>Mastery estimate</span></div>{concepts.map(concept => <div className="setu-home-concept" key={concept.concept_id}><strong>{concept.name}</strong><span>{concept.attempts}</span><div>{concept.mastery === null ? <span className="setu-home-not-started">Not estimated</span> : <><div className="setu-home-mastery-track"><span style={{ width: `${Math.round(concept.mastery * 100)}%` }} /></div><span>{Math.round(concept.mastery * 100)}%</span></>}</div></div>)}</>}{data && !concepts.length && <p className="setu-home-empty">No concepts match your search.</p>}{section === 'progress' && <p className="setu-home-subtitle">Showing up to five concepts, ordered by saved answer count. View all opens the full chapter list.</p>}<p className="setu-home-subtitle">Continue follows your adaptive plan. Browsing this list does not change your assigned topic.</p></section>
      </div>
      <footer>Setu prototype · Author-drafted, unreviewed content · No real-student validation claimed.</footer>
    </main>
  </div>;
}
