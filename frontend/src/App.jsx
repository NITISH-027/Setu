import React, { useState, useEffect } from 'react';
import StudentView from './components/StudentView';
import { makeT } from './i18n/uiStrings.js';
import TeacherView from './components/TeacherView';
import PrivacyView from './components/PrivacyView';
import ReviewView from './components/ReviewView';
import PaperModeView from './components/PaperModeView';
import GuidedTourModal from './components/GuidedTourModal';

function FootprintNote() {
  const [fp, setFp] = useState(null);
  useEffect(() => {
    fetch('/api/demo/footprint').then((r) => (r.ok ? r.json() : null)).then(setFp).catch(() => {});
  }, []);
  if (!fp) return null;
  const kb = (b) => (b == null ? '?' : (b / 1024).toFixed(1));
  return (
    <div style={{ marginTop: '4px' }}>
      Built for low bandwidth: app script {kb(fp.js_bytes)} KB, styles {kb(fp.css_bytes)} KB, question pack {kb(fp.pack_bytes)} KB{' '}
      <em>{fp.label}</em>. Attempts made offline are queued on the device and sync when the network returns.
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('student');
  const [devSimulateOffline, setDevSimulateOffline] = useState(false);
  const [isSystemOnline, setIsSystemOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [language, setLanguage] = useState('en');
  const t = makeT(language);
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('setu_theme') || 'paathai';
    } catch {
      return 'paathai';
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('setu_theme', theme);
    } catch {}
  }, [theme]);

  useEffect(() => {
    const handleOnline = () => setIsSystemOnline(true);
    const handleOffline = () => setIsSystemOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const effectivelyOffline = !isSystemOnline || devSimulateOffline;

  return (
    <>
      {effectivelyOffline && (
        <div className="offline-banner" style={{ background: '#78350f', color: '#fef3c7', padding: '6px 12px', textAlign: 'center', fontSize: '12px', fontWeight: '600' }}>
          {!isSystemOnline
            ? 'DISCONNECTED MODE: Real network offline. Using local IndexedDB storage and local adaptive engine.'
            : 'DEV SIMULATION: Offline mode simulated. Using local IndexedDB storage.'}
        </div>
      )}

      {/* Main Header */}
      <header className="app-header">
        <div className="brand-section">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="logo-badge">SETU</div>
            <div className="brand-title">Adaptive Learning</div>
          </div>

          {/* Theme & Language Selectors & Guided Tour */}
          <div className="header-controls">
            <button
              id="guided-tour-btn"
              data-testid="guided-tour-btn"
              onClick={() => setIsTourOpen(true)}
              className="guided-tour-btn"
              title="Open 3-minute guided walkthrough for judges"
            >
              ✨ Guided Tour (3 min)
            </button>

            <select
              id="theme-select"
              data-testid="theme-select"
              aria-label="Color Theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="header-select theme-select"
            >
              <option value="paathai">⛰️ Paathai (Hill Path)</option>
              <option value="emerald">🌿 Emerald Jade</option>
              <option value="amethyst">✨ Velvet Amethyst</option>
              <option value="amber">🔥 Amber Sunset</option>
            </select>

            {/* Medium Language Switcher (Failure 5) */}
            <select
              id="language-select"
              data-testid="language-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="header-select language-select"
            >
              <option value="en">English (Supported)</option>
              <option value="hi">हिंदी (Unreviewed Draft)</option>
              <option value="ta">தமிழ் (Unreviewed Draft)</option>
              <option value="te">తెలుగు (Unreviewed Draft)</option>
            </select>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            id="tab-student"
            className={`nav-tab-btn ${activeTab === 'student' ? 'active' : ''}`}
            onClick={() => setActiveTab('student')}
          >
            {t('nav.student')}
          </button>
          <button
            id="tab-teacher"
            className={`nav-tab-btn ${activeTab === 'teacher' ? 'active' : ''}`}
            onClick={() => setActiveTab('teacher')}
          >
            {t('nav.teacher')}
          </button>
          <button
            id="tab-privacy"
            className={`nav-tab-btn ${activeTab === 'privacy' ? 'active' : ''}`}
            onClick={() => setActiveTab('privacy')}
          >
            {t('nav.privacy')}
          </button>
          <button
            id="tab-review"
            className={`nav-tab-btn ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => setActiveTab('review')}
          >
            {t('nav.review')}
          </button>
          <button
            id="tab-paper"
            className={`nav-tab-btn ${activeTab === 'paper' ? 'active' : ''}`}
            onClick={() => setActiveTab('paper')}
          >
            {t('nav.paper')}
          </button>
        </nav>
      </header>

      {/* Main View Area */}
      <main className="main-content">
        {activeTab === 'student' && (
          <StudentView
            devSimulateOffline={devSimulateOffline}
            onToggleDevOffline={() => setDevSimulateOffline(!devSimulateOffline)}
            language={language}
            onLanguageChange={setLanguage}
          />
        )}
        {activeTab === 'teacher' && <TeacherView language={language} />}
        {activeTab === 'privacy' && <PrivacyView />}
        {activeTab === 'review' && <ReviewView />}
        {activeTab === 'paper' && <PaperModeView />}
      </main>

      {/* Honest Footer */}
      <footer className="app-footer">
        <div>
          <strong>Setu:</strong> A wrong answer is a hypothesis, not a diagnosis. Inside an authored concept graph.
        </div>
        <div style={{ marginTop: '4px' }}>
          BKT estimates are <em>uncalibrated and hand-set</em>. Evidence scores are <em>rule-based heuristics</em>.
          Content is <em>author-drafted, unreviewed</em>. Demo controls only, not a legal or school compliance claim.
        </div>
        <FootprintNote />
      </footer>

      {/* Guided Tour Modal for Judges */}
      <GuidedTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onNavigateTab={(tab) => {
          setActiveTab(tab);
          setIsTourOpen(false);
        }}
      />
    </>
  );
}
