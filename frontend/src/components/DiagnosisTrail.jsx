import React from 'react';

// "Watch Setu think": the diagnosis loop, made visible.
// Every entry comes from a real engine decision (sequencer reason or an
// authoritative misconception tag). Nothing is staged or simulated.
// Honest framing: a hypothesis is a rule-based guess that gets TESTED -
// it is never shown as a final diagnosis.
const KIND_STYLE = {
  spot:    { icon: '?', cls: 'trail-spot' },
  check:   { icon: '🔍', cls: 'trail-check' },
  teach:   { icon: '📖', cls: 'trail-teach' },
  recheck: { icon: '↻', cls: 'trail-recheck' },
  win:     { icon: '✓', cls: 'trail-win' },
  flag:    { icon: '!', cls: 'trail-flag' },
  note:    { icon: '•', cls: 'trail-note' }
};

export default function DiagnosisTrail({ events = [] }) {
  if (!events || events.length === 0) return null;
  const shown = events.slice(-6);
  return (
    <div className="trail-wrap" data-testid="diagnosis-trail">
      <div className="trail-title">Watch Setu think</div>
      <div className="trail-list">
        {shown.map((ev, i) => {
          const st = KIND_STYLE[ev.kind] || KIND_STYLE.note;
          return (
            <div key={i} className={`trail-row ${st.cls}`}>
              <span className="trail-dot">{st.icon}</span>
              <span className="trail-text">{ev.text}</span>
            </div>
          );
        })}
      </div>
      <div className="trail-caption">
        A hypothesis is a rule-based guess Setu tests with a probe. It is never a final diagnosis.
      </div>
    </div>
  );
}
