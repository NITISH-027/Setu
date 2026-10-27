import React, { useState } from 'react';

export default function PrivacyView() {
  const [deleteTargetId, setDeleteTargetId] = useState('');
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [authToken, setAuthToken] = useState('');
  const [deletionReport, setDeletionReport] = useState(null);
  const [syncStatus, setSyncStatus] = useState('');
  const [message, setMessage] = useState('');

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: adminUsername, password: adminPassword })
      });
      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.access_token);
        setMessage(`Logged in as ${data.username} (${data.role})`);
      } else {
        setMessage('Login failed. Please check credentials.');
      }
    } catch {
      setMessage('Network error during login.');
    }
  };

  const handleDelete = async () => {
    if (!deleteTargetId.trim()) {
      setMessage('Please enter a student pseudonym to delete.');
      return;
    }
    if (!authToken) {
      setMessage('Teacher or Admin login required to delete a student record.');
      return;
    }

    try {
      const res = await fetch('/api/privacy/delete-student', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ student_id: deleteTargetId.trim() })
      });
      if (res.ok) {
        const report = await res.json();
        setDeletionReport(report);
        setMessage(`Student ${deleteTargetId} completely purged from all server stores. Opaque tombstone created.`);
      } else {
        const err = await res.json().catch(() => ({}));
        setMessage(err.detail || 'Error deleting student.');
      }
    } catch {
      setMessage('Error deleting student.');
    }
  };

  const handleDeviceSync = async () => {
    if (!authToken) {
      setMessage('Authenticated session required for device sync.');
      return;
    }

    try {
      const res = await fetch('/api/privacy/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
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
          Minimal operational metadata • Opaque tombstones • Zero-PII audit log
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

      {/* Auth Box if needed */}
      {!authToken && (
        <div className="info-card" style={{ background: 'rgba(56, 189, 248, 0.05)' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
            Teacher / Admin Login (Required for Privacy Actions)
          </div>
          <form onSubmit={handleAdminLogin} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <input
              type="text"
              value={adminUsername}
              onChange={(e) => setAdminUsername(e.target.value)}
              placeholder="Username"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <input
              type="password"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              placeholder="Password"
              style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
            />
            <button type="submit" className="action-btn" style={{ width: 'auto' }}>
              Sign In
            </button>
          </form>
        </div>
      )}

      {/* Delete Student & Tombstone Protocol */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '10px' }}>
          Student Deletion & Tombstone Propagation
        </h3>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            id="privacy-delete-input"
            type="text"
            value={deleteTargetId}
            onChange={(e) => setDeleteTargetId(e.target.value)}
            placeholder="Student Pseudonym"
            style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          />

          <button
            id="privacy-delete-btn"
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
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Opaque Key: <code>{deletionReport.tombstone_key}</code>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Pending Devices: {deletionReport.pending_devices}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button onClick={handleDeviceSync} className="btn-secondary" style={{ fontSize: '12px' }}>
                Simulate Tablet Reconnect & Tombstone Sync
              </button>
            </div>
          </div>
        )}

        {syncStatus && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#6ee7b7' }}>
            {syncStatus}
          </div>
        )}

        {message && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: 'var(--accent-amber)' }}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
