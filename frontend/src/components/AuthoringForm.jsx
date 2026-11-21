import React, { useState, useEffect } from 'react';

const EMPTY_OPTION = () => ({ text: '', is_correct: false, misconception_tag: '' });

/**
 * v5 teacher authoring: add or edit a question + its misconception tags from
 * the dashboard. Everything saved here is an UNREVIEWED DRAFT - the form says
 * so, the API says so, and the child's app labels it as draft.
 */
export default function AuthoringForm({ authToken, t }) {
  const [concepts, setConcepts] = useState([]);
  const [authored, setAuthored] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [concept, setConcept] = useState('');
  const [language, setLanguage] = useState('en');
  const [questionText, setQuestionText] = useState('');
  const [probeFor, setProbeFor] = useState('');
  const [options, setOptions] = useState([EMPTY_OPTION(), EMPTY_OPTION(), EMPTY_OPTION(), EMPTY_OPTION()]);
  const [issues, setIssues] = useState([]);
  const [status, setStatus] = useState('');

  const headers = { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    if (!authToken) return;
    fetch('/api/teacher/authoring/concepts', { headers })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setConcepts(d.concepts || []); })
      .catch(() => {});
    refreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken]);

  const refreshList = () => {
    fetch('/api/teacher/authoring/questions', { headers })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setAuthored(d.questions || []); })
      .catch(() => {});
  };

  const setOption = (i, patch) => {
    setOptions((opts) => opts.map((o, j) => (j === i ? { ...o, ...patch } : o)));
  };

  const resetForm = () => {
    setEditingId(null);
    setConcept('');
    setLanguage('en');
    setQuestionText('');
    setProbeFor('');
    setOptions([EMPTY_OPTION(), EMPTY_OPTION(), EMPTY_OPTION(), EMPTY_OPTION()]);
    setIssues([]);
  };

  const submit = async () => {
    setStatus('');
    setIssues([]);
    const payload = {
      concept,
      language,
      question_text: questionText,
      probe_for_misconception: probeFor || null,
      options: options
        .filter((o) => o.text.trim())
        .map((o) => ({
          text: o.text.trim(),
          is_correct: o.is_correct,
          misconception_tag: o.is_correct ? null : (o.misconception_tag.trim() || null),
        })),
    };
    const url = editingId ? `/api/teacher/authoring/questions/${editingId}` : '/api/teacher/authoring/questions';
    const method = editingId ? 'PUT' : 'POST';
    try {
      const res = await fetch(url, { method, headers, body: JSON.stringify(payload) });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setStatus(`Saved as UNREVIEWED DRAFT (${data.id})${data.version ? ' - version ' + data.version : ''}. A subject teacher must still review it.`);
        resetForm();
        refreshList();
      } else {
        setIssues((data.detail && data.detail.issues) || [{ severity: 'ERROR', code: 'REQUEST_FAILED', message: JSON.stringify(data.detail || data) }]);
      }
    } catch {
      setIssues([{ severity: 'ERROR', code: 'NETWORK', message: 'Network error - not saved.' }]);
    }
  };

  const startEdit = (item) => {
    // Refetch full payload is not available in the list; prefill what we have and let the teacher re-enter options.
    setEditingId(item.id);
    setConcept(item.concept);
    setLanguage(item.language);
    setQuestionText(item.question_text);
    setStatus(`Editing ${item.id} - re-enter the options, then save. Stays an unreviewed draft.`);
  };

  return <section className="teacher-card setu-authoring">
    <div className="teacher-card-heading"><div><p className="teacher-eyebrow">YOUR TEACHING TOOLKIT</p><h3>{t('teacher.authorTitle')}</h3></div><span className="teacher-evidence-pill">Unreviewed draft</span></div>
    <p className="teacher-muted">{t('teacher.authorNote')}</p>
    <div className="teacher-author-fields"><label>Concept<select aria-label="Concept" value={concept} onChange={e => setConcept(e.target.value)}><option value="">- choose -</option>{concepts.map(item => <option key={item.id} value={item.id}>{item.name} (Class {item.class_level})</option>)}</select></label><label>Language<select aria-label="Language" value={language} onChange={e => setLanguage(e.target.value)}><option value="en">English</option><option value="ta">தமிழ் (draft)</option><option value="hi">हिंदी (draft)</option><option value="te">తెలుగు (draft)</option></select></label></div>
    <label className="teacher-author-question">Question<textarea aria-label="Question" value={questionText} onChange={e => setQuestionText(e.target.value)} placeholder="Question text, e.g. Solve for x: x + 3 = 10" rows={3}/></label>
    <div className="teacher-author-options-heading"><strong>Answer options</strong><span>Select one correct answer. Add misconception tags to the others.</span></div>
    {options.map((option, index) => <div className="teacher-author-option" key={index}>
      <label className="teacher-author-radio"><input type="radio" name="author-correct" checked={option.is_correct} onChange={() => setOptions(opts => opts.map((item, i) => ({ ...item, is_correct: i === index })))} aria-label={`Mark option ${index + 1} as correct`} /><span>{String.fromCharCode(65 + index)}</span></label>
      <label className="teacher-option-text"><span>Option {index + 1}</span><input aria-label={`Option ${index + 1}`} value={option.text} onChange={e => setOption(index, { text: e.target.value })} placeholder={`Option ${index + 1}`}/></label>
      {!option.is_correct ? <label className="teacher-option-tag"><span>Misconception tag</span><input aria-label="Misconception tag" value={option.misconception_tag} onChange={e => setOption(index, { misconception_tag: e.target.value })} placeholder="tag_..."/></label> : <span className="teacher-evidence-pill">Correct answer</span>}
    </div>)}
    <label className="teacher-author-question teacher-probe">Diagnostic probe tag <small>Optional. Makes this a diagnostic probe.</small><input value={probeFor} onChange={e => setProbeFor(e.target.value)} placeholder="probe_for_misconception tag"/></label>
    {issues.length > 0 && <div className="teacher-notice is-error" role="alert">{issues.map((issue, index) => <p key={index}>{issue.severity}: {issue.message}</p>)}</div>}
    {status && <p className="teacher-notice is-success" role="status">{status}</p>}
    <div className="teacher-author-submit"><p>A subject teacher must check the maths and tags before this is used.</p><div><button className="btn-primary" onClick={submit} disabled={!concept || !questionText.trim()}>{editingId ? 'Save edit (stays draft)' : t('teacher.authorSubmit')}</button>{editingId && <button className="btn-secondary" onClick={resetForm}>Cancel edit</button>}</div></div>
    {authored.length > 0 && <div className="teacher-draft-list"><h4>Your drafted questions ({authored.length})</h4>{authored.slice(0, 10).map(item => <article key={item.id}><div><strong>{item.question_text.slice(0, 60)}</strong><small>{item.review_status} · v{item.version}</small></div><button className="btn-secondary" onClick={() => startEdit(item)}>Edit</button></article>)}</div>}
  </section>;
}
