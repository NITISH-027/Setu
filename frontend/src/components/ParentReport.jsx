import React, { useEffect, useState } from 'react';

export default function ParentReport({ token, classId, onClose }) {
  const [students, setStudents] = useState([]);
  const [studentId, setStudentId] = useState('');
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null); setStudentId(''); setStudents([]); setError(''); setBusy(true);
    fetch(`/api/teacher/class/${encodeURIComponent(classId)}/report-students`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal
    }).then(async res => {
      if (!res.ok) throw new Error('Could not load students. Check your session and class access.');
      const data = await res.json();
      setStudents(data.students); setStudentId(data.students[0] || '');
    }).catch(e => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [token, classId]);
  useEffect(() => {
    if (!studentId) return;
    const controller = new AbortController();
    setReport(null); setError(''); setStatus(''); setBusy(true);
    fetch(`/api/teacher/student/${encodeURIComponent(studentId)}/parent-report`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: 'no-store'
    }).then(async res => {
      if (!res.ok) throw new Error('Could not load this report. Check your connection and access.');
      setReport(await res.json());
    }).catch(e => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [token, studentId]);

  async function copyReport() {
    try {
      await navigator.clipboard.writeText(report.share_text);
      setStatus('Copied. Open the correct parent chat in WhatsApp, paste, check, then send.');
    } catch {
      setStatus('Copy is unavailable here. Select the preview text below and copy it manually.');
    }
  }
  async function shareReport() {
    try {
      await navigator.share({ title: 'Setu home practice note', text: report.share_text });
      setStatus('Share sheet closed. Setu cannot confirm whether a message was sent.');
    } catch (e) {
      if (e.name !== 'AbortError') setStatus('Sharing is unavailable. Use Copy for WhatsApp instead.');
    }
  }
  return <section className="parent-report" aria-label="Parent report">
    <div className="report-toolbar">
      <div><p className="report-eyebrow">SCHOOL TO HOME</p><h2>Five minutes, together.</h2></div>
      <button className="btn-secondary" onClick={onClose}>Back to teacher screen</button>
    </div>
    <p>A small home-practice note, based on saved answers. English only for now.</p>
    <label htmlFor="report-student">Choose student in {classId}</label>
    <select id="report-student" value={studentId} onChange={e => { if (e.target.value !== studentId) { setReport(null); setStatus(''); setBusy(true); setStudentId(e.target.value); } }} disabled={!students.length}>
      {students.map(id => <option key={id} value={id}>{id}</option>)}
    </select>
    {!busy && !students.length && !error && <p>No students in this class yet.</p>}
    {busy && <p role="status">Preparing note...</p>}
    {error && <p role="alert">{error}</p>}
    {report && !busy && <>
      <div className="report-safety"><strong>Check the parent before sharing.</strong> The copied note leaves out the student ID and class. Only share with the child's authorised parent or guardian. Nothing is sent automatically.</div>
      <div className="report-paper">
        <p className="report-eyebrow">SETU / HOME PRACTICE</p>
        <h3>A next step, not a label.</h3>
        <p className="report-date">Prepared {report.generated_at}</p>
        <p className="report-summary">{report.summary}</p>
        {report.focus.map((item, i) => <article className="report-activity" key={item.concept_id}>
          <p className="report-eyebrow">PRACTICE {i + 1}</p>
          <h4>{item.topic}</h4>
          <p>{item.missed} of {item.attempted} recent answers in this topic need another look.</p>
          <p><strong>Try at home</strong><br />{item.activity}</p>
        </article>)}
        {!!report.attempts_used && <p>Spend 5 minutes together. Let your child explain; do not rush to give the answer. If they are still stuck, ask their teacher.</p>}
        <p className="report-disclaimer">{report.note}</p>
      </div>
      <details className="report-preview"><summary>Preview exactly what will be copied or shared</summary><pre>{report.share_text}</pre></details>
      <div className="report-actions">
        <button className="action-btn" onClick={copyReport}>Copy for WhatsApp</button>
        {typeof navigator.share === 'function' && <button className="btn-secondary" onClick={shareReport}>Share...</button>}
      </div>
      {status && <p role="status">{status}</p>}
    </>}
  </section>;
}
