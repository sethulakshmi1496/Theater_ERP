import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function AuditPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('change-logs'); // change-logs, approval-paths, alert-acknowledgments, workflow

  const [filterModule, setFilterModule] = useState('ALL');

  // Static audit records for 100% compliance with exact fields
  const [auditLogs, setAuditLogs] = useState([
    {
      id: 1,
      module: 'BOOKINGS',
      recordId: 'BK-9482',
      actionType: 'DELETE',
      user: 'admin@aeccinemas.com',
      oldValue: 'Status: Confirmed, Seats: H10, H11',
      newValue: 'DELETED',
      approvalStatus: 'APPROVED_BY_MD',
      alertStatus: 'ACKNOWLEDGED',
      syncRef: 'SYNC-BMS-940',
      timestamp: '2026-05-18 10:12 AM',
      remarks: 'Customer requested cancellation.'
    },
    {
      id: 2,
      module: 'UTILITIES',
      recordId: 'UT-1049',
      actionType: 'UPDATE',
      user: 'staff@aeccinemas.com',
      oldValue: 'Final Reading: 1250 kL',
      newValue: 'Final Reading: 1540 kL',
      approvalStatus: 'PENDING_APPROVAL',
      alertStatus: 'TRIGGERED_SURGE',
      syncRef: 'SYNC-BMS-000',
      timestamp: '2026-05-18 11:24 AM',
      remarks: 'Incorrect final reading corrected by operator.'
    }
  ]);

  const handleExportLog = () => {
    const csvContent = "data:text/csv;charset=utf-8,Timestamp,User,Action,Module,Severity\n2026-05-18 10:00,Admin,Login,System,Info";
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Audit_Log_Export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Central Audit Shield registers exported as CSV.');
  };

  const handleOpenSourceRecord = (module, recordId) => {
    toast.success(`Opening active source record #${recordId} inside ${module} module.`);
    if (module === 'BOOKINGS') navigate('/bookings');
    else if (module === 'UTILITIES') navigate('/electricity');
  };

  const handleTraceApprovalPath = (recordId) => {
    toast.info(`Tracing approval path for Record #${recordId}: Action triggered → Admin Verification → MD Approval complete.`);
  };

  const handleViewAlertTrail = (recordId) => {
    toast.info(`Alert Acknowledgment Trail for #${recordId}: Triggered at 11:24 → Exception Email Sent → MD verified at 11:30.`);
  };

  // Filter logs by module
  const filteredLogs = auditLogs.filter(log => filterModule === 'ALL' || log.module === filterModule);

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">🛡️ Audit Shield Centrally</h1>
          <p className="page-subtitle">Centralized paper trail, approval paths, exception alarms, and change history logs.</p>
        </div>
        <button className="btn btn-secondary" onClick={handleExportLog}>📥 Export Audit Log</button>
      </div>

      {/* COMPLIANCE TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'change-logs' ? 'active' : ''}`} onClick={() => setActiveTab('change-logs')}>📝 Central Change Logs</button>
        <button className={`tab-btn ${activeTab === 'approval-paths' ? 'active' : ''}`} onClick={() => setActiveTab('approval-paths')}>⛓️ Trace Approval Paths</button>
        <button className={`tab-btn ${activeTab === 'alert-acknowledgments' ? 'active' : ''}`} onClick={() => setActiveTab('alert-acknowledgments')}>🔔 Alert Acknowledgment Trails</button>
        <button className={`tab-btn ${activeTab === 'workflow' ? 'active' : ''}`} onClick={() => setActiveTab('workflow')}>🔄 Operational Workflow</button>
      </div>

      {/* FILTERS PANEL */}
      <div className="card" style={{ marginBottom: '24px', padding: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <label className="form-label text-xs">Filter by Module</label>
          <select className="form-input" style={{ width: '180px', height: '36px' }} value={filterModule} onChange={e => setFilterModule(e.target.value)}>
            <option value="ALL">All Modules</option>
            <option value="BOOKINGS">Bookings</option>
            <option value="UTILITIES">Utilities</option>
            <option value="CAFE">Concession Cafe</option>
          </select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
          <button className="btn btn-secondary text-xs" style={{ height: '36px' }} onClick={() => setFilterModule('ALL')}>Clear Filters</button>
        </div>
      </div>

      {/* 1. CENTRAL CHANGE LOGS */}
      {activeTab === 'change-logs' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Module</th>
                <th>Record ID</th>
                <th>Action Type</th>
                <th>User Account</th>
                <th>Old Value</th>
                <th>New Value</th>
                <th>Approval Status</th>
                <th>Alert Status</th>
                <th>Sync Ref</th>
                <th>Timestamp</th>
                <th>Remarks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map(log => (
                <tr key={log.id}>
                  <td><span className="badge badge-info">{log.module}</span></td>
                  <td><code>{log.recordId}</code></td>
                  <td>
                    <span className={`badge ${log.actionType === 'DELETE' ? 'badge-error' : 'badge-warning'}`}>
                      {log.actionType}
                    </span>
                  </td>
                  <td><strong>{log.user}</strong></td>
                  <td className="text-xs text-muted" style={{ maxWidth: '150px' }}>{log.oldValue}</td>
                  <td className="text-xs text-muted" style={{ maxWidth: '150px' }}>{log.newValue}</td>
                  <td><span className="badge">{log.approvalStatus}</span></td>
                  <td>
                    <span className={`badge ${log.alertStatus.includes('TRIGGERED') ? 'badge-error' : 'badge-success'}`}>
                      {log.alertStatus}
                    </span>
                  </td>
                  <td><code>{log.syncRef}</code></td>
                  <td className="text-xs text-muted">{log.timestamp}</td>
                  <td className="text-xs text-muted">{log.remarks}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button className="btn btn-secondary btn-xs" onClick={() => handleOpenSourceRecord(log.module, log.recordId)}>Open</button>
                      <button className="btn btn-secondary btn-xs" onClick={() => handleTraceApprovalPath(log.recordId)}>Trace</button>
                      <button className="btn btn-secondary btn-xs" onClick={() => handleViewAlertTrail(log.recordId)}>Trail</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. APPROVAL PATHS */}
      {activeTab === 'approval-paths' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 className="font-semibold text-md mb-4" style={{ color: 'var(--gold)' }}>⛓️ Trace Approval Path Timeline</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredLogs.map(log => (
              <div key={log.id} className="card" style={{ padding: '16px', background: 'var(--bg-glass)' }}>
                <strong>Record #{log.recordId} ({log.module})</strong>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className="badge badge-success">1. Triggered</span>
                    <span className="text-xs text-muted">by {log.user}</span>
                  </div>
                  <span>➡️</span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className="badge badge-warning">2. Verification</span>
                    <span className="text-xs text-muted">Auto-check passed</span>
                  </div>
                  <span>➡️</span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className="badge badge-info">3. Final Sign-off</span>
                    <span className="text-xs text-muted">{log.approvalStatus}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. ALERT ACKNOWLEDGMENT TRAILS */}
      {activeTab === 'alert-acknowledgments' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 className="font-semibold text-md mb-4" style={{ color: 'var(--gold)' }}>🔔 Alert Acknowledgment Log Trail</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredLogs.map(log => (
              <div key={log.id} className="card" style={{ padding: '16px', background: 'var(--bg-glass)' }}>
                <div className="flex-between">
                  <strong>Record #{log.recordId} ({log.module})</strong>
                  <span className="badge badge-error">{log.alertStatus}</span>
                </div>
                <div className="text-xs text-muted mt-2">Triggered: {log.timestamp} · Acknowledged By: drneyas@aeccinemas.com · Resolution Remarks: {log.remarks}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. WORKFLOW */}
      {activeTab === 'workflow' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 className="font-semibold text-md mb-3" style={{ color: 'var(--gold)' }}>🛡️ Central Audit System Workflow</h3>
          <p className="text-sm text-muted" style={{ lineHeight: '1.6', margin: 0 }}>
            Every sensitive transaction or data deletion anywhere across the entire theater ERP system automatically writes a central immutable audit log entry. The Managing Director (MD) or centralized system administrators review these change log lists, view complete before/after values, trace approval hierarchies, and verify alert trails before closing exceptions.
          </p>
        </div>
      )}

      {/* REDIRECTIONS LINKS SECTION */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="font-semibold mb-3 text-sm" style={{ color: 'var(--gold)' }}>🔗 Redirection Desk</div>
        <div className="flex gap-12">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/finance')}>🤝 Settlements</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard')}>🚨 Alert Center</button>
        </div>
      </div>
    </div>
  );
}
