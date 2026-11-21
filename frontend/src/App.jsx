import React, { useState, useEffect } from 'react';
import StudentView from './components/StudentView';
import TeacherView from './components/TeacherView';
import PrivacyView from './components/PrivacyView';
import ReviewView from './components/ReviewView';
import PaperModeView from './components/PaperModeView';
import GuidedTourModal from './components/GuidedTourModal';
import LearningHeader from './components/LearningHeader';

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
  const [studentSignedIn, setStudentSignedIn] = useState(false);
  const [teacherSignedIn, setTeacherSignedIn] = useState(false);
  const [isTestScreen, setIsTestScreen] = useState(false);
  const [isHomeScreen, setIsHomeScreen] = useState(false);
  const isTeacherDashboard = activeTab === 'teacher' && teacherSignedIn;
  const isLogin = (activeTab === 'student' && !studentSignedIn) || (activeTab === 'teacher' && !teacherSignedIn);
  const [devSimulateOffline, setDevSimulateOffline] = useState(false);
  const [isSystemOnline, setIsSystemOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [language, setLanguage] = useState('en');
  const [isTourOpen, setIsTourOpen] = useState(false);
  const loginNavigation = { onNavigate: setActiveTab, onTour: () => setIsTourOpen(true), onLanguageChange: setLanguage };

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
    <div className={isLogin ? "setu-app-login" : isTeacherDashboard ? "setu-app-teacher" : (isTestScreen || isHomeScreen) ? "setu-app-quiz" : "setu-app"}>
      {effectivelyOffline && (
        <div className="offline-banner" style={{ background: '#78350f', color: '#fef3c7', padding: '6px 12px', textAlign: 'center', fontSize: '12px', fontWeight: '600' }}>
          {!isSystemOnline
            ? 'DISCONNECTED MODE: Real network offline. Using local IndexedDB storage and local adaptive engine.'
            : 'DEV SIMULATION: Offline mode simulated. Using local IndexedDB storage.'}
        </div>
      )}

      {!isLogin && !isTestScreen && !isHomeScreen && !isTeacherDashboard && <LearningHeader activeTab={activeTab} onNavigate={setActiveTab} onTour={() => setIsTourOpen(true)} theme={theme} onThemeChange={setTheme} language={language} onLanguageChange={setLanguage} />}

      {/* Main View Area */}
      <main className="main-content">
        {activeTab === 'student' && (
          <StudentView
            loginNavigation={loginNavigation}
            onAuthChange={setStudentSignedIn}
            onTestScreenChange={setIsTestScreen}
            onHomeScreenChange={setIsHomeScreen}
            devSimulateOffline={devSimulateOffline}
            onToggleDevOffline={() => setDevSimulateOffline(!devSimulateOffline)}
            language={language}
            onLanguageChange={setLanguage}
          />
        )}
        {activeTab === 'teacher' && <TeacherView language={language} loginNavigation={loginNavigation} onAuthChange={setTeacherSignedIn} />}
        {activeTab === 'privacy' && <PrivacyView />}
        {activeTab === 'review' && <ReviewView />}
        {activeTab === 'paper' && <PaperModeView />}
      </main>

      {/* Honest Footer */}
      {!isLogin && !isTestScreen && !isHomeScreen && !isTeacherDashboard && <footer className="app-footer">
        <div>
          <strong>Setu:</strong> A wrong answer is a hypothesis, not a diagnosis. Inside an authored concept graph.
        </div>
        <div style={{ marginTop: '4px' }}>
          BKT estimates are <em>uncalibrated and hand-set</em>. Evidence scores are <em>rule-based heuristics</em>.
          Content is <em>author-drafted, unreviewed</em>. Demo controls only, not a legal or school compliance claim.
        </div>
        <FootprintNote />
      </footer>}

      {/* Guided Tour Modal for Judges */}
      <GuidedTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onNavigateTab={(tab) => {
          setActiveTab(tab);
          setIsTourOpen(false);
        }}
      />
    </div>
  );
}
