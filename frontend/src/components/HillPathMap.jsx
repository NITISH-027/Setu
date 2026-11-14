import React from 'react';

// Paathai (hill path) level map: concepts visited this session become
// milestone stones on a winding climb. Honest by construction - only
// concepts the student has actually touched appear; nothing is promised.
const MASTERY_DONE_THRESHOLD = 0.85;

function prettyConcept(conceptId) {
  if (!conceptId) return '';
  const parts = conceptId.split('_');
  // ids look like c7_math_equivalent_fractions -> Equivalent Fractions
  const words = parts.slice(2).join(' ');
  return words.replace(/\b\w/g, (c) => c.toUpperCase()) || conceptId;
}

export default function HillPathMap({ masteries = {}, currentConcept }) {
  const seen = Object.keys(masteries);
  const concepts = currentConcept && !seen.includes(currentConcept)
    ? [...seen, currentConcept]
    : seen;

  if (concepts.length === 0) {
    return (
      <div className="hillmap-wrap" data-testid="hillpath-map">
        <svg viewBox="0 0 320 64" className="hillmap-svg" aria-label="Learning path: not started yet">
          <path d="M12 50 C 90 50, 110 18, 170 18 S 250 50, 308 26" className="hillmap-path" fill="none" />
          <circle cx="12" cy="50" r="9" className="hillmap-stone hillmap-current" />
          <text x="12" y="54" textAnchor="middle" className="hillmap-mark">&#9733;</text>
        </svg>
        <div className="hillmap-caption">Your climb starts here. Every stone is a concept you visit.</div>
      </div>
    );
  }

  const n = concepts.length;
  const doneCount = concepts.filter((c) => (masteries[c] || 0) >= MASTERY_DONE_THRESHOLD).length;

  // Winding S-curve points, left to right
  const points = concepts.map((c, i) => {
    const x = n === 1 ? 160 : 22 + (i * 276) / (n - 1);
    const y = 40 - 18 * Math.sin(i * 1.15);
    return { c, x, y };
  });
  const pathD = points
    .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
    .join(' ');

  return (
    <div className="hillmap-wrap" data-testid="hillpath-map">
      <svg viewBox="0 0 320 78" className="hillmap-svg" aria-label="Learning path map">
        <path d={pathD} className="hillmap-path" fill="none" />
        {points.map((p) => {
          const mastery = masteries[p.c] || 0;
          const isCurrent = p.c === currentConcept;
          const isDone = mastery >= MASTERY_DONE_THRESHOLD;
          const cls = isCurrent ? 'hillmap-current' : isDone ? 'hillmap-done' : 'hillmap-visited';
          const mark = isCurrent ? '\u2605' : isDone ? '\u2713' : '';
          return (
            <g key={p.c}>
              <circle cx={p.x} cy={p.y} r="9" className={`hillmap-stone ${cls}`} />
              {mark && (
                <text x={p.x} y={p.y + 4} textAnchor="middle" className="hillmap-mark">
                  {mark}
                </text>
              )}
              <text x={Math.max(34, Math.min(286, p.x))} y={p.y + 22} textAnchor="middle" className="hillmap-label">
                {prettyConcept(p.c).slice(0, 12)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="hillmap-caption">
        {doneCount} milestone{doneCount === 1 ? '' : 's'} crossed. Orange stone = where you are now.
      </div>
    </div>
  );
}
