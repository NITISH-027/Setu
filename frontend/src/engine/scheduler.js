/**
 * SM-2 Spaced Repetition Scheduler JavaScript Port.
 * Matches Python implementation in backend/app/engine/scheduler.py.
 * Untuned and unvalidated against real classroom retention curves.
 */

export class SpacedRepetitionScheduler {
  constructor(defaultEaseFactor = 2.5) {
    this.defaultEase = defaultEaseFactor;
    this.disclaimer = "SM-2 intervals are untuned and unvalidated against classroom retention curves.";
  }

  scheduleNextReview(masteryState, quality, currentTime = null) {
    const now = currentTime ? new Date(currentTime) : new Date();
    const updated = { ...masteryState, last_seen: now.toISOString() };

    let intervalDays;
    if (quality >= 3) {
      if (updated.consecutive_successes === 0) {
        intervalDays = 1.0;
      } else if (updated.consecutive_successes === 1) {
        intervalDays = 3.0;
      } else {
        intervalDays = Math.round(updated.interval_days * updated.ease_factor * 10) / 10;
      }
      updated.consecutive_successes = (updated.consecutive_successes || 0) + 1;
    } else {
      updated.consecutive_successes = 0;
      intervalDays = 1.0;
    }

    const q = Math.max(0, Math.min(5, quality));
    const deltaEase = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02);
    const newEase = Math.max(1.3, Math.round((updated.ease_factor + deltaEase) * 100) / 100);

    updated.ease_factor = newEase;
    updated.interval_days = intervalDays;
    
    const nextDate = new Date(now.getTime() + intervalDays * 24 * 60 * 60 * 1000);
    updated.next_review = nextDate.toISOString();

    return updated;
  }
}
