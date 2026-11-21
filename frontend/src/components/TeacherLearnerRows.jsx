import React from 'react';

export default function TeacherLearnerRows({ students, onOverride, supported = false }) {
  return <div className="teacher-learner-list">{students.map(student => <article className="teacher-learner-row" key={student.student_id}>
    <div className="teacher-learner-identity"><span aria-hidden="true">{student.student_id.slice(-2).toUpperCase()}</span><div><strong>{student.student_id}</strong><small>{student.current_concept_id || 'Concept not assigned'}</small></div></div>
    <div className="teacher-learner-evidence"><span className="teacher-evidence-pill">{student.evidence_band || 'Evidence pending'}</span><p>{student.suggested_plan_reason || 'No saved plan reason.'}</p>{(student.evidence_details || []).slice(0, 3).map((detail, index) => <small key={index}>{typeof detail === 'string' ? detail : JSON.stringify(detail)}</small>)}</div>
    <div className="teacher-learner-mastery"><strong>{student.bkt_mastery_estimate == null ? '—' : `${Math.round(student.bkt_mastery_estimate * 100)}%`}</strong><small>{student.bkt_label || 'Not estimated'}</small></div>
    <button id={`override-btn-${student.student_id}`} data-testid={`override-btn-${student.student_id}`} className="btn-secondary" onClick={() => onOverride({ student_id: student.student_id, concept_id: (supported && student.gap_concept_id) || student.current_concept_id })}>Override</button>
  </article>)}</div>;
}
