# Setu - Pitch Outline (v5 refresh)

## The one-sentence concept
Setu helps teachers find which maths concepts students need support in, groups them, gives short targeted practice in Tamil, and checks if learning improved.

(A wrong answer is treated as a hypothesis about a prerequisite gap - never a diagnosis - and the teacher can override everything.)

## Slide flow (8 slides)
1. **Problem** - Tamil Nadu Class 8 maths: 38% at proficiency in SLAS (state's own assessment); ASER: only 37.8% of Std VIII can do division. Gaps compound silently.
2. **Why existing tools miss it** - fixed-order quizzes test what was taught, not the earlier-class gap behind the error; 88.3% of rural TN households have a smartphone but connectivity and shared devices rule out heavy always-online apps.
3. **The concept** (one-sentence line above) + the 4-beat journey: wrong answer -> hypothesis -> diagnostic probe -> micro-lesson -> bridge re-check -> back to practice.
4. **Live demo** (judge does it): one-tap student entry, answer wrong on purpose, watch the probe and lesson; teacher dashboard with "who needs help now", the why-line, and the override that the next child's starting estimate learns from.
5. **Teacher in charge** - override any placement (logged, reason required), the system learns starting estimates from overrides ("learned from N overrides" counter), and teachers author their own questions from a form - saved as unreviewed drafts that stay OUT of the assessment until a reviewer approves them (approve/reject with a recorded reason, attestation on approve).
6. **Built for the classroom that exists** - measured app weight: 279 KB script + 28 KB styles + 190 KB question pack [MEASURED on the demo server build]; works offline, attempts queue and sync; shared-device PIN profiles; Tamil UI (draft, teacher review pending).
7. **Evidence, honestly labelled** (below).
8. **Limits** (below) + ask: pilot with one school and a Tamil-maths teacher reviewer.

## Evidence slide - every number labelled
- **Gap discovery, simulated students**: with a planted Class 7 gap expressed in the student's errors, Setu identifies the correct gap in mean 4.3 questions (p90 = 5), 97.5% found within 12; a fixed-order quiz over the same pack needs mean 71 questions to reach the same gap. [SIMULATION - synthetic students, hand-set parameters, gap-discovery speed only, not real children]
- **Prerequisite chain probing**: when the expressed errors don't isolate a gap, Setu now walks the prerequisite chain probing one concept at a time instead of stopping at the first rejected hypothesis. In the planted Integer-gap scenario (errors point elsewhere) the miss dropped from 0% found to 55% found within 12 questions (mean 5.6); the fixed quiz needs mean 84. The main scenario above stayed the same or better (90.5% to 97.5%). [SIMULATION - same caveats; two-probe confirmation required before a gap is taught]
- **Override signal, synthetic logs**: a small logistic model fitted on simulated override logs predicts the teacher's action with 0.98 held-out accuracy (AUC 0.999, majority baseline 0.86), split by concept so no concept leaks between train and test. [SYNTHETIC OVERRIDES - the live engine uses hand-set shrinkage, not this model]
- **Mastery model fit, real public data**: BKT fitted by EM reaches AUC 0.73, a PFA-style logistic baseline 0.81. [MEASURED on my run, ASSISTments 2009-10, US students - says nothing about Setu's own content or Tamil Nadu]

## Limits slide - measured, not hedged
- **Content coverage**: an authored Class 6-8 CBSE spine (fractions and linear equations deepest), author-drafted and unreviewed. Tamil content is DRAFT pending teacher review; Hindi/Telugu are partial drafts; anything missing falls back to English with a visible label.
- **Estimates are uncalibrated**: BKT parameters are hand-set and labelled so in the UI. No accuracy number from any dataset is claimed for Setu's own questions.
- **Simulation honesty**: in the planted-Integer-gap scenario where the student's expressed errors point at a different concept, Setu finds the co-existing deeper gap in only 55% of simulated students within 12 questions (improved from 0% before prerequisite chain probing); the fixed quiz eventually catches it at mean 84 questions. Discovery follows the errors the child actually shows, and 45% of these miss cases remain a real limit.
- **No learning-gain claim**: nothing here measures children learning; the checked outcome is gap identification and bridge re-checks, not test-score improvement.
- **Synthetic override model**: the fitted override numbers come from a hand-set teacher policy; real teachers may override for reasons no feature captures.
- **Prototype ops**: free-tier hosting sleeps (first visit up to ~1 minute, splash explains); demo controls are not legal or school-compliance claims.

## If a judge asks "is this AI/ML?"
The live engine is Bayesian Knowledge Tracing with hand-set, honestly-labelled parameters plus rule-based hypothesis evidence. Fitted numbers exist (above) and are labelled by exactly whose data they come from. We would rather show a measured 0.15 than promise a borrowed 0.37.
