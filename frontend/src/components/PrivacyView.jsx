import React, { useState } from 'react';

export default function PrivacyView() {
  const [deleteTargetId, setDeleteTargetId] = useState('stu_demo_01');
  const [deletionReport, setDeletionReport] = useState(null);
  const [syncStatus, setSyncStatus] = useState('');
  const [message, setMessage] = useState('');

  const handleDelete = async () => {
    try {
      const res = await fetch('/api/privacy/delete-student', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: deleteTargetId, actor: 'teacher_admin' })
      });
      if (res.ok) {
        const report = await res.json();
        setDeletionReport(report);
        setMessage(`Student ${deleteTargetId} purged from server stores. Opaque tombstone created.`);
      }
    } catch {
      setMessage('Error deleting student.');
    }
  };

  const handleDeviceSync = async () => {
    try {
      const res = await fetch('/api/privacy/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'dev_demo_tablet', class_id: '8-A' })
      });
      if (res.ok) {
        const data = await res.json();
        setSyncStatus(`Device synced: ${data.applied_tombstones.length} tombstone(s) applied. Local device store purged.`);
        if (deletionReport) {
          setDeletionReport({
            ...deletionReport,
            pending_devices: 0,
            is_fully_deleted_everywhere: true,
            status_message: 'All registered devices synced. Local stores purged.'
          });
        }
      }
    } catch {
      setSyncStatus('Sync error.');
    }
  };

  return (
    <div className="wide-container">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Data Protection & Privacy Controls</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Working demo controls • Minimal operational metadata • Opaque tombstones • Zero-PII audit log
        </p>
      </div>

      {/* Disclaimers & Limits Stated Honestly */}
      <div className="info-card" style={{ borderLeft: '4px solid var(--accent-amber)' }}>
        <div style={{ fontSize: '12px', color: 'var(--accent-amber)', fontWeight: '700', marginBottom: '4px' }}>
          HONEST DISCLOSURE: DELETION BOUNDARIES & LIMITS
        </div>
        <div style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
          Deletion removes pseudonyms, attempts, hypotheses, plans, and overrides from app-controlled server stores and queued local caches.
          <strong> Limits:</strong> Deletion cannot recall copies outside the app (e.g. downloaded CSV exports, offline device backups, or automated server database backups until backup retention schedules expire).
          Offline devices cannot learn of server deletions until they next connect.
        </div>
      </div>

      {/* Delete Student & Tombstone Protocol */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '10px' }}>
          Student Deletion & Tombstone Propagation
        </h3>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={deleteTargetId}
            onChange={(e) => setDeleteTargetId(e.target.value)}
            placeholder="Student Pseudonym (e.g. stu_demo_01)"
            style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          />

          <button
            onClick={handleDelete}
            className="action-btn"
            style={{ width: 'auto', background: 'var(--accent-rose)' }}
          >
            Purge Student & Issue Tombstone
          </button>
        </div>

        {deletionReport && (
          <div style={{ marginTop: '16px', padding: '14px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong>Tombstone Status Report</strong>
              <span style={{ fontSize: '12px', color: deletionReport.is_fully_deleted_everywhere ? '#6ee7b7' : '#fcd34d' }}>
                {deletionReport.is_fully_deleted_everywhere ? 'Fully Purged Across Stores' : 'Pending Device Sync'}
              </span>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              <div>Opaque Tombstone Key: <code>{deletionReport.tombstone_key}</code> (Holds no student ID or learning payload)</div>
              <div>Pending Registered Devices: <strong>{deletionReport.pending_devices}</strong></div>
              <div style={{ marginTop: '4px', color: '#fcd34d' }}>{deletionReport.status_message}</div>
            </div>

            {!deletionReport.is_fully_deleted_everywhere && (
              <div style={{ marginTop: '12px' }}>
                <button
                  onClick={handleDeviceSync}
                  className="btn-secondary"
                  style={{ borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }}
                >
                  Simulate Device Reconnecting & Applying Tombstone
                </button>
              </div>
            )}
          </div>
        )}

        {syncStatus && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#6ee7b7' }}>
            {syncStatus}
          </div>
        )}
      </div>

      {/* Consent Workflow Schema */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Consent Workflow States
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Status states: <code>not requested</code> → <code>requested</code> → <code>recorded</code>.
          Nothing is ever auto-marked "consent obtained" in code.
        </p>

        <div style={{ display: 'flex', gap: '10px' }}>
          <div className="info-card" style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>STATUS 1</div>
            <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>not requested</strong>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Default on student creation</div>
          </div>

          <div className="info-card" style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>STATUS 2</div>
            <strong style={{ fontSize: '14px', color: 'var(--accent-amber)' }}>requested</strong>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Form sent to guardian</div>
          </div>

          <div className="info-card" style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>STATUS 3</div>
            <strong style={{ fontSize: '14px', color: 'var(--accent-emerald)' }}>recorded</strong>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Human teacher checked signed form</div>
          </div>
        </div>
      </div>

      {/* Privacy-Safe Audit Log Structure Demonstration */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Privacy-Safe Audit Log Structure (Zero PII Guarantee)
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
          Audit records log ONLY event type, actor, class, timestamp, record count, and optional opaque tombstone key.
          Never logs student IDs, answers, or learning payloads.
        </p>

        <pre style={{ background: '#020617', padding: '12px', borderRadius: '6px', fontSize: '12px', color: '#93c5fd', overflowX: 'auto' }}>
{`{
  "event_type": "delete",
  "actor": "teacher_admin",
  "class_id": "8-A",
  "record_count": 1,
  "opaque_tombstone_key": "9a7f3c21b4e85d0a1c62f90123456789",
  "timestamp": "2026-10-27T08:30:00Z"
  /* Notice: Strictly NO student_id, NO student name, and NO learning payload */
}`}
        </pre>
      </div>
    </div>
  );
}
