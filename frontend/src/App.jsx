import React, { useState } from 'react';
import StudentView from './components/StudentView';
import TeacherView from './components/TeacherView';
import PrivacyView from './components/PrivacyView';
import ReviewView from './components/ReviewView';
import PaperModeView from './components/PaperModeView';

export default function App() {
  const [activeTab, setActiveTab] = useState('student');
  const [isOffline, setIsOffline] = useState(false);
  const [language, setLanguage] = useState('en');

  return (
    <>
      {isOffline && (
        <div className="offline-banner">
          DISCONNECTED MODE: Simulating offline PWA with local IndexedDB storage and sync queue.
        </div>
      )}

      {/* Main Header */}
      <header className="app-header">
        <div className="brand-section">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="logo-badge">SETU</div>
            <div className="brand-title">Adaptive Learning</div>
          </div>

          {/* Medium Language Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{ fontSize: '11px', padding: '4px 6px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px' }}
            >
              <option value="en">English (Supported)</option>
              <option value="hi">हिंदी (Unreviewed)</option>
              <option value="te">తెలుగు (Unreviewed)</option>
            </select>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeTab === 'student' ? 'active' : ''}`}
            onClick={() => setActiveTab('student')}
          >
            Student App (Phone)
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'teacher' ? 'active' : ''}`}
            onClick={() => setActiveTab('teacher')}
          >
            Teacher Dashboard
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'privacy' ? 'active' : ''}`}
            onClick={() => setActiveTab('privacy')}
          >
            Data & Privacy
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => setActiveTab('review')}
          >
            Coverage & Review
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'paper' ? 'active' : ''}`}
            onClick={() => setActiveTab('paper')}
          >
            Paper Mode
          </button>
        </nav>
      </header>

      {/* Main View Area */}
      <main className="main-content">
        {activeTab === 'student' && (
          <StudentView
            isOffline={isOffline}
            onToggleOffline={() => setIsOffline(!isOffline)}
          />
        )}
        {activeTab === 'teacher' && <TeacherView />}
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
          Demo controls only, not a legal or school compliance claim.
        </div>
      </footer>
    </>
  );
}
