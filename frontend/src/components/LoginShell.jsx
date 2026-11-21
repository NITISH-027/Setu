import React, { useState } from 'react';
import './LoginShell.css';

export function LoginIcon({ kind = 'bridge' }) {
  const paths = {
    bridge: <><path d="M3 17h26M5 17c6-17 16-17 22 0M8 12v10M13 7v15M19 7v15M24 12v10" /></>,
    user: <><circle cx="16" cy="10" r="5"/><path d="M6 27v-3a10 10 0 0 1 20 0v3"/></>,
    lock: <><rect x="7" y="14" width="18" height="14" rx="4"/><path d="M11 14V9a5 5 0 0 1 10 0v5M16 20v3"/></>,
    eye: <><path d="M2 16s5-9 14-9 14 9 14 9-5 9-14 9S2 16 2 16Z"/><circle cx="16" cy="16" r="4"/></>
  };
  return <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind] || paths.bridge}</svg>;
}

export function LoginField({ label, secret = false, ...props }) {
  const [visible, setVisible] = useState(false);
  return <div className="setu-login-field">
    <label htmlFor={props.id}>{label}</label>
    <div className="setu-input-wrap">
      <span className="setu-input-icon"><LoginIcon kind={secret ? 'lock' : 'user'} /></span>
      <input {...props} type={secret ? (visible ? 'text' : 'password') : 'text'} />
      {secret && <button type="button" className="setu-eye" aria-label={visible ? `Hide ${label}` : `Show ${label}`} aria-pressed={visible} onClick={() => setVisible(!visible)}><LoginIcon kind="eye" /></button>}
    </div>
  </div>;
}

export default function LoginShell({ role, onNavigate, onTour, children, language, onLanguageChange }) {
  const student = role === 'student';
  return <div className="setu-login-page">
    <section className="setu-login-scene" aria-label="Setu sign in">
      <div className="setu-login-art" role="img" aria-label="Clay-style illustration of a student with a laptop, books and plants in a pastel learning room" />
      <div className="setu-login-story">
        <a className="setu-login-brand" href="#" onClick={(e) => { e.preventDefault(); onNavigate('student'); }} aria-label="Setu student sign in"><span><LoginIcon /></span><b className="brand-title">Setu</b></a>
        <div className="setu-login-welcome"><h1>Welcome back! <span aria-hidden="true">✦</span></h1><p>A little learning.<br />A new way forward.</p></div>
      </div>
      <div className="setu-login-card">
        <header><h2>Log in to your account</h2><p>{student ? 'Your next little breakthrough starts here.' : 'Help every learner find their next step.'} <span aria-hidden="true">♥</span></p></header>
        <div className="setu-role-tabs" aria-label="Sign-in role">
          <button id="tab-student" type="button" aria-pressed={student} onClick={() => onNavigate('student')}>Student</button>
          <button id="tab-teacher" type="button" aria-pressed={!student} onClick={() => onNavigate('teacher')}>Teacher</button>
        </div>
        <h3 className="setu-sr-only">{student ? 'Student Sign-In' : 'Teacher Sign-In'}</h3>
        {children}
        <p className="setu-login-help">{student ? 'Need a student ID or PIN? Ask your teacher.' : 'Need an account? Contact your Setu administrator.'}</p>
      </div>
    </section>
    <nav className="setu-login-utilities" aria-label="Setu tools">
      <button id="guided-tour-btn" data-testid="guided-tour-btn" onClick={onTour}>Guided Tour (3 min)</button>
      <span aria-hidden="true">·</span>
      <button id="tab-paper" onClick={() => onNavigate('paper')}>Paper mode</button>
      <button id="tab-review" onClick={() => onNavigate('review')}>Content review</button>
      <button id="tab-privacy" onClick={() => onNavigate('privacy')}>Privacy</button>
      <label className="setu-login-language"><span className="setu-sr-only">Language</span><select id="language-select" data-testid="language-select" value={language} onChange={(e) => onLanguageChange(e.target.value)}><option value="en">English</option><option value="hi">हिंदी (Draft)</option><option value="ta">தமிழ் (Draft)</option><option value="te">తెలుగు (Draft)</option></select></label>
    </nav>
  </div>;
}
