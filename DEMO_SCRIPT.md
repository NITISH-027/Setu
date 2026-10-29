# Setu 3-Minute Demo Video Script
**Setting**: Screen recording with voiceover (No real children; strictly synthetic demo profiles).  
**Target Time**: 2 minutes 50 seconds.  
**Honesty Disclaimers**: All content is author-drafted and unreviewed (0.0% reviewed). Mastery estimates are hand-set and uncalibrated. No compliance claims are made.

---

### [0:00 - 0:25] Opening: Context & Honest Claims
- **Visual**: Setu UI loaded on screen (`http://localhost:5173`). Showing the Student App in mobile view (390px) with clearly visible honest badges: *Stage: Solve*, *Mastery: uncalibrated, hand-set*, and footer disclaimer: *"A wrong answer is a hypothesis, not a diagnosis. Inside an authored concept graph."*
- **Voiceover**:  
  *"This is Setu, an adaptive learning system built for Classes 6 to 10 that keeps the teacher firmly in command.  
  Our core claim: Setu identifies the likely prerequisite gap behind a student's mistake, with evidence and stated uncertainty, inside an authored concept graph.  
  We make no inflated claims: mastery estimates are clearly labeled 'uncalibrated, hand-set', evidence is a 'rule-based heuristic', and our CBSE Class 8 content is author-drafted and unreviewed. Today's demonstration uses strictly synthetic student profiles."*

---

### [0:25 - 1:15] Student Screen: Wrong Answer → Hypothesis → Probes → Micro-Lesson
- **Visual**: Student attempts Class 8 Linear Equations question: `Solve for x: x + 7 = 14`. Selects wrong option with transposition misconception.
- **Voiceover**:  
  *"The student makes an initial mistake on standard practice. Rather than assuming a diagnosis, Setu opens a working hypothesis with score band 'Low' and transitions to a diagnostic probe.  
  The stage badge changes to 'probe' with an explicit banner: 'Diagnostic Probe: Checking foundational prerequisite understanding'.  
  Notice our crucial engine design: diagnostic probes do NOT penalize the student on the stuck counter.  
  The student attempts the diagnostic probe. Because probe evidence confirms the struggle with integer operations, Setu traverses the prerequisite graph back to Class 6 addition and subtraction of integers.  
  Next, the student is served a dedicated micro-lesson screen in their selected language. The screen provides clear instruction, a language status badge, and an explicit 'Continue' button."*

---

### [1:15 - 1:50] Bridge Re-Check & Return to Original Topic
- **Visual**: Student clicks 'Continue' on the lesson screen. The stage badge transitions to 'bridge_recheck'. Student answers correctly. The screen returns to 'solve' stage with the message 'Returned to original topic: Practice resumed'.
- **Voiceover**:  
  *"Clicking Continue explicitly advances the learning plan to Bridge Re-check. Here, the student answers a focused prerequisite verification question.  
  Upon answering correctly, Setu closes the bridge and returns the student directly to their original Class 8 topic with an updated mastery estimate.  
  Had the student struggled repeatedly on the bridge or consecutive solve attempts, the system would immediately transition to a Teacher Flag screen rather than trapping the student in an endless loop."*

---

### [1:50 - 2:25] Teacher Control Dashboard: Shared Gaps, Clinics & Overrides
- **Visual**: Teacher signs in with teacher credentials for Class 8-A. The dashboard displays Override Rate, Supported Gap Groups, and Recommended 10-Minute Small-Group Clinics.
- **Voiceover**:  
  *"Switching to the Teacher Dashboard. A teacher sees only their assigned class—cross-class access strictly returns HTTP 403.  
  Students who share a confirmed foundational gap are grouped together, and Setu recommends a targeted 10-minute remedial clinic.  
  Students with conflicting or thin probe evidence are kept separate under 'Undecided' labeled 'not sure'—preventing algorithmic over-diagnosis.  
  Teachers can override any plan with one click: assigning a concept, marking a gap cleared, or requesting reinforcement. Every override requires a mandatory logged reason, updating the teacher override rate in real time as our primary quality metric."*

---

### [2:25 - 2:50] Paper Mode Bulk Entry & Offline-First Resiliency
- **Visual**: Switch to 'Paper Mode' tab. Teacher enters student responses from paper sheets. Real server processing confirms graded count and student state updates. Switch to 'Data & Privacy' tab to show student data export with zero secret leakage.
- **Voiceover**:  
  *"For low-resource classrooms, Paper Mode allows teachers to bulk-enter physical test responses directly through the grading engine.  
  On shared family phones, Setu operates completely offline as a PWA using local IndexedDB storage, synchronizing securely when connectivity returns.  
  Students and teachers can export their learning logs at any time with complete data isolation and zero secret leakage.  
  Setu keeps adaptive learning transparent, honest, and under teacher command. Thank you."*
