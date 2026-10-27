# Setu 3-Minute Demo Video Script
**Setting**: Screen recording with voiceover (No real children, strictly synthetic demo students).  
**Total Target Time**: 2 minutes 50 seconds.

---

### [0:00 - 0:25] Opening: Context & Core Claim
- **Visual**: Setu UI loaded on screen (`http://localhost:5173`). Showing the Student App in phone-width container (460px) and honest badge labels.
- **Voiceover**:  
  *"This is Setu, a teacher-controlled adaptive learning system built for Classes 6 to 10 for the Code Kernel '26 hackathon.  
  Our core claim: Setu finds the likely prerequisite gap behind a wrong answer, with evidence and stated uncertainty, inside an authored concept graph.  
  Notice our rule of honesty right away: a wrong answer is a working hypothesis, not a diagnosis. Two numbers are never conflated: BKT mastery estimate is clearly labeled 'uncalibrated, hand-set', while evidence score is a rule-based heuristic labeled 'heuristic evidence score'. All profiles shown today are synthetic."*

---

### [0:25 - 1:05] Student Flow: Wrong Answer → Hypothesis → Probes → Trace
- **Visual**: Student `stu_demo_01` attempts equation: `x + 7 = 3`. Clicks option `x = 4` (integer subtraction misconception).
- **Voiceover**:  
  *"Our synthetic student answers `x = 4`. Notice what happens: the system does NOT jump to a conclusion. It opens a hypothesis with score band 'Low' and initiates a focused prerequisite probe.  
  Next question: the probe checks Class 6 integers: 'What is 3 - 7?'. The student chooses `4`.  
  Now that probe evidence supports the gap, Setu traverses the prerequisite graph backwards. It traces the struggle from Class 8 Linear Equations back to the Class 6 foundational concept: 'Addition and Subtraction of Integers'. This is an evidence-backed trace within our authored graph, not an unverified claim of causation."*

---

### [1:05 - 1:40] Bridge Micro-Lesson → Re-Check Routing
- **Visual**: PWA displays the micro-lesson bridge explaining negative integer subtraction on a number line, then moves to Bridge Re-Check.
- **Voiceover**:  
  *"Setu delivers a short, simple micro-lesson bridge. Once reviewed, it administers a short adaptive re-check.  
  On passing the re-check, the student returns to their original topic. If they struggle repeatedly, the rule sequencer flags the teacher for small-group intervention."*

---

### [1:40 - 2:15] Teacher Dashboard: Grouped Gaps, Uncertainty & Override
- **Visual**: Switch to 'Teacher Dashboard' tab. Select Class 8-A.
- **Voiceover**:  
  *"Switching to the Teacher Dashboard. A teacher sees only their assigned class. Notice the grouping: students who share the supported Class 6 integer gap are grouped together, and Setu recommends a 10-minute targeted clinic.  
  Crucially, look at the Undecided section: students with thin or conflicting probe evidence are labeled 'not sure' and kept separate—never forced into a false diagnosis.  
  The teacher stays in full command. With one click, the teacher can override any plan, assign a new topic, or mark a gap closed, with a mandatory reason logged for parent remedial reports. Notice our override rate metric updating in real time as our primary quality signal."*

---

### [2:15 - 2:35] India Fit: Offline PWA & Sibling PIN
- **Visual**: Click 'Mode: Disconnected (Offline)'. Submit an answer. Show attempt stored in local sync queue. Reconnect and click 'Sync'.
- **Voiceover**:  
  *"Setu is engineered for Indian contexts. It functions as an offline-first PWA with local IndexedDB storage. Students on low-data connections can complete an entire week's practice completely offline. When network returns, queued writes synchronize smoothly. Shared family phones are protected with sibling PIN profiles and lockout protection."*

---

### [2:35 - 2:50] Privacy & Data Controls: Deletion & Opaque Tombstones
- **Visual**: Switch to 'Data & Privacy' tab. Click 'Purge Student'. Show opaque tombstone generated and pending device sync status.
- **Voiceover**:  
  *"Finally, our data protection controls. Deleting a student removes their learning payload across server databases and caches. Offline devices are managed via opaque tombstones holding zero student identifiers. Notice that the server visibly states 'Deletion pending on 1 device' until the device syncs and purges its local cache. No false claims of full deletion are ever made while a tombstone is pending.  
  Setu keeps technology honest, transparent, and under the teacher's control. Thank you."*
