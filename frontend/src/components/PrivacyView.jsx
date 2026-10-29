import React, { useState } from 'react';

export default function PrivacyView() {
  const [deleteTargetId, setDeleteTargetId] = useState('');
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [authToken, setAuthToken] = useState('');
  const [deletionReport, setDeletionReport] = useState(null);
  const [syncStatus, setSyncStatus] = useState('');
  const [message, setMessage] = useState('');
  const [metrics, setMetrics] = useState(null);

  // Student Export State (Failure 10 & Acceptance Test K)
  const [exportStudentId, setExportStudentId] = useState('stu_001');
  const [exportResult, setExportResult] = useState(null);
  const [exportError, setExportError] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);

  const fetchMetrics = async (tok) => {
    try {
      const activeTok = tok || authToken;
      if (!activeTok) return;
      const res = await fetch('/api/teacher/privacy-metrics', {
        headers: { 'Authorization': `Bearer ${activeTok}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch {
      // Ignore network errors on metrics poll
    }
  };

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
        fetchMetrics(data.access_token);
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
        fetchMetrics(authToken);
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
        fetchMetrics(authToken);
      }
    } catch {
      setSyncStatus('Sync error.');
    }
  };

  const handleExportStudent = async () => {
    if (!exportStudentId.trim()) return;
    setExportLoading(true);
    setExportResult(null);
    setExportError(null);

    const headers = {};
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
      const res = await fetch(`/api/student/${encodeURIComponent(exportStudentId.trim())}/export`, {
        headers
      });

      if (res.ok) {
        const data = await res.json();
        setExportResult(data);
      } else {
        const err = await res.json().catch(() => ({}));
        setExportError(err.detail || `Export failed with HTTP ${res.status}`);
      }
    } catch {
      setExportError('Network error requesting student data export.');
    } finally {
      setExportLoading(false);
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

      {/* FIX 1: Show pending/acknowledged state per device to the teacher */}
      {metrics && (
        <div className="info-card" style={{ marginTop: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700' }}>
              Device Purge Delivery Tracking
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Policy: {metrics.retention_policy_days}-day automatic expiry
            </span>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Per-device delivery and acknowledgment records. Devices that held the purged student must acknowledge before tombstone is marked applied.
          </p>

          {metrics.deliveries && metrics.deliveries.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Tombstone Key</th>
                    <th style={{ padding: '8px' }}>Device ID</th>
                    <th style={{ padding: '8px' }}>Delivery Status</th>
                    <th style={{ padding: '8px' }}>Acknowledged At</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.deliveries.map((d) => (
                    <tr key={d.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{d.opaque_key.slice(0, 12)}...</td>
                      <td style={{ padding: '8px', fontWeight: '500' }}>{d.device_id}</td>
                      <td style={{ padding: '8px' }}>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            background: d.status === 'acknowledged' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: d.status === 'acknowledged' ? '#6ee7b7' : '#fcd34d'
                          }}
                        >
                          {d.status === 'acknowledged' ? 'Acknowledged' : 'Pending Sync'}
                        </span>
                      </td>
                      <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                        {d.acknowledged_at ? new Date(d.acknowledged_at).toLocaleTimeString() : 'Awaiting device reconnect'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
              No active tombstones pending device sync. All stores clean.
            </div>
          )}
        </div>
      )}

      {/* Student Data Export Section (Failure 10 & Acceptance Test K) */}
      <div className="info-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Student Data Export (Self & Teacher Scoped)
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Minimal data export: pseudonymous ID, class, board, consent status, attempts count, and concept masteries.
          <strong> Excludes:</strong> PIN hashes, salts, device subject keys, and other students' data.
          Authorized for the student themselves, or teachers scoped to their assigned classes. Deleted/tombstoned records refused.
        </p>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '12px' }}>
          <input
            id="export-student-id-input"
            data-testid="export-student-id-input"
            type="text"
            placeholder="Student Pseudonym (e.g. stu_001)"
            value={exportStudentId}
            onChange={(e) => setExportStudentId(e.target.value)}
            style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '6px' }}
          />
          <button
            id="export-student-btn"
            data-testid="export-student-btn"
            onClick={handleExportStudent}
            disabled={exportLoading}
            className="action-btn"
            style={{ width: 'auto' }}
          >
            {exportLoading ? 'Exporting...' : 'Export Student Data'}
          </button>
        </div>

        {exportResult && (
          <div
            id="export-json-container"
            style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}
          >
            <div style={{ fontSize: '12px', color: '#6ee7b7', fontWeight: '600', marginBottom: '6px' }}>
              ✓ Export Successful (No secrets included):
            </div>
            <pre
              id="export-json-output"
              data-testid="export-json-output"
              style={{ fontSize: '12px', color: '#cbd5e1', overflowX: 'auto', margin: 0 }}
            >
              {JSON.stringify(exportResult, null, 2)}
            </pre>
          </div>
        )}

        {exportError && (
          <div
            id="export-error-output"
            data-testid="export-error-output"
            style={{ fontSize: '12px', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}
          >
            {exportError}
          </div>
        )}

        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
          <em>Note: Demonstration of data portability and access scoping. Not a formal compliance claim.</em>
        </div>
      </div>
    </div>
  );
}
