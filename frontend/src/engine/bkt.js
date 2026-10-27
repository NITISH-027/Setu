/**
 * Bayesian Knowledge Tracing (BKT) JavaScript Port.
 * Matches Python Corbett & Anderson implementation in backend/app/engine/bkt.py.
 * Uncalibrated, hand-set parameters.
 */

export class BKTEngine {
  constructor(params = { prior: 0.2, learn: 0.15, guess: 0.2, slip: 0.1 }) {
    this.params = params;
    this.label = "uncalibrated, hand-set";
  }

  update(currentMastery, isCorrect, customParams = null) {
    const p = customParams || this.params;
    const priorMastery = Math.max(0.001, Math.min(0.999, currentMastery));

    let posterior;
    if (isCorrect) {
      // P(L | Correct) = P(L)*(1 - S) / [ P(L)*(1 - S) + (1 - P(L))*G ]
      const num = priorMastery * (1.0 - p.slip);
      const denom = num + (1.0 - priorMastery) * p.guess;
      posterior = denom > 0 ? num / denom : priorMastery;
    } else {
      // P(L | Incorrect) = P(L)*S / [ P(L)*S + (1 - P(L))*(1 - G) ]
      const num = priorMastery * p.slip;
      const denom = num + (1.0 - priorMastery) * (1.0 - p.guess);
      posterior = denom > 0 ? num / denom : priorMastery;
    }

    // Transition: P(L_next) = posterior + (1 - posterior) * P(T)
    const nextMastery = posterior + (1.0 - posterior) * p.learn;
    return Math.max(0.0, Math.min(1.0, Math.round(nextMastery * 10000) / 10000));
  }
}
