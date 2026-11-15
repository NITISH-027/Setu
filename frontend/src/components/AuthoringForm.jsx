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

  return (
    <div className="info-card" style={{ marginBottom: '14px', borderLeft: '4px solid var(--accent-secondary, #f59e0b)' }}>
      <h3 style={{ fontSize: '15px', marginBottom: '6px' }}>{t('teacher.authorTitle')}</h3>
      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '8px' }}>
        {t('teacher.authorNote')}
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
        <label style={{ fontSize: '12px' }}>
          Concept:
          <select value={concept} onChange={(e) => setConcept(e.target.value)} style={{ marginLeft: '4px' }}>
            <option value="">- choose -</option>
            {concepts.map((c) => (
              <option key={c.id} value={c.id}>{c.name} (Class {c.class_level})</option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: '12px' }}>
          Language:
          <select value={language} onChange={(e) => setLanguage(e.target.value)} style={{ marginLeft: '4px' }}>
            <option value="en">English</option>
            <option value="ta">தமிழ் (draft)</option>
            <option value="hi">हिंदी (draft)</option>
            <option value="te">తెలుగు (draft)</option>
          </select>
        </label>
      </div>

      <textarea
        value={questionText}
        onChange={(e) => setQuestionText(e.target.value)}
        placeholder="Question text, e.g. Solve for x: x + 3 = 10"
        style={{ width: '100%', minHeight: '44px', marginBottom: '8px', fontSize: '13px' }}
      />

      {options.map((o, i) => (
        <div key={i} style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px', fontSize: '12px' }}>
          <input
            type="radio"
            name="author-correct"
            checked={o.is_correct}
            onChange={() => setOptions((opts) => opts.map((x, j) => ({ ...x, is_correct: j === i })))}
            title="Mark as the correct option"
          />
          <input
            value={o.text}
            onChange={(e) => setOption(i, { text: e.target.value })}
            placeholder={`Option ${i + 1}`}
            style={{ width: '110px' }}
          />
          {!o.is_correct && (
            <input
              value={o.misconception_tag}
              onChange={(e) => setOption(i, { misconception_tag: e.target.value })}
              placeholder="misconception tag (tag_...)"
              style={{ flex: 1 }}
            />
          )}
          {o.is_correct && <span style={{ color: 'var(--text-muted)' }}>correct answer</span>}
        </div>
      ))}

      <div style={{ marginTop: '6px', fontSize: '12px' }}>
        <input
          value={probeFor}
          onChange={(e) => setProbeFor(e.target.value)}
          placeholder="Optional: probe_for_misconception tag (makes this a diagnostic probe)"
          style={{ width: '70%' }}
        />
      </div>

      {issues.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          {issues.map((i, k) => (
            <div key={k} style={{ fontSize: '12px', color: i.severity === 'ERROR' ? '#b91c1c' : '#b45309' }}>
              {i.severity}: {i.message}
            </div>
          ))}
        </div>
      )}
      {status && <div style={{ fontSize: '12px', color: 'var(--accent-primary)', marginTop: '8px' }}>{status}</div>}

      <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
        <button className="btn-primary" onClick={submit} disabled={!concept || !questionText.trim()}>
          {editingId ? 'Save edit (stays draft)' : t('teacher.authorSubmit')}
        </button>
        {editingId && <button onClick={resetForm}>Cancel edit</button>}
      </div>

      {authored.length > 0 && (
        <div style={{ marginTop: '10px', fontSize: '12px' }}>
          <strong>Your drafted questions ({authored.length}):</strong>
          {authored.slice(0, 10).map((item) => (
            <div key={item.id} style={{ display: 'flex', gap: '8px', alignItems: 'center', borderTop: '1px solid var(--border-color)', padding: '4px 0' }}>
              <span style={{ flex: 1 }}>{item.question_text.slice(0, 60)} <em style={{ color: 'var(--text-muted)' }}>[{item.review_status}, v{item.version}]</em></span>
              <button style={{ fontSize: '11px' }} onClick={() => startEdit(item)}>Edit</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
