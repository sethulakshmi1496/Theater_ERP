import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function StaffReportPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('directory'); // directory, attendance, shifts, sync-log

  // Roster Directory state
  const [staffList, setStaffList] = useState([
    {
      staffId: 'EMP-001',
      name: 'Raman K',
      role: 'Projectionist',
      department: 'TECHNICAL',
      shift: 'Morning (09:00 - 17:00)',
      attendanceStatus: 'PRESENT',
      payrollStatus: 'PAID',
      syncStatus: 'SYNCHRONIZED',
      supervisor: 'Vikram Singh',
      notes: 'Expert in Xenon 3KW lamp alignment'
    },
    {
      staffId: 'EMP-002',
      name: 'Shreya Roy',
      role: 'Concession Cashier',
      department: 'CANTEEN',
      shift: 'Evening (16:00 - 00:00)',
      attendanceStatus: 'ON_DUTY',
      payrollStatus: 'HOLD',
      syncStatus: 'OUT_OF_SYNC',
      supervisor: 'Ananya Sen',
      notes: 'Needs Cafe wastage validation training'
    },
    {
      staffId: 'EMP-003',
      name: 'Vikram Singh',
      role: 'Duty Manager',
      department: 'OPERATIONS',
      shift: 'Night (22:00 - 06:00)',
      attendanceStatus: 'ABSENT',
      payrollStatus: 'PAID',
      syncStatus: 'SYNCHRONIZED',
      supervisor: 'Dr. Neyas Mohammed',
      notes: 'Weekly off supervisor cover'
    }
  ]);

  const [filterDept, setFilterDept] = useState('ALL');
  const [filterException, setFilterException] = useState('ALL');

  const [showAddStaff, setShowAddStaff] = useState(false);
  const [newStaff, setNewStaff] = useState({
    staffId: '', name: '', role: '', department: 'OPERATIONS', shift: 'Morning (09:00 - 17:00)',
    attendanceStatus: 'PRESENT', payrollStatus: 'PAID', syncStatus: 'SYNCHRONIZED', supervisor: '', notes: ''
  });

  const handleCreateStaff = (e) => {
    e.preventDefault();
    const staff = {
      ...newStaff,
      staffId: newStaff.staffId || `EMP-00${staffList.length + 1}`
    };
    setStaffList([...staffList, staff]);
    toast.success('Roster staff profile registered.');
    setShowAddStaff(false);
  };

  const handleExportSummary = () => {
    const csvContent = "data:text/csv;charset=utf-8,Staff ID,Name,Department\n1,Demo Staff,Demo Dept";
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Staff_Summary_Export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Staff Summary register exported as CSV.');
  };

  const handleSyncLogTrigger = () => {
    toast.success('Centralized HRMS payroll sync payload triggered.');
  };

  // Filtering logic
  const filteredStaff = staffList.filter(s => {
    const matchDept = filterDept === 'ALL' || s.department === filterDept;
    const matchException = filterException === 'ALL' || 
      (filterException === 'OUT_OF_SYNC' && s.syncStatus === 'OUT_OF_SYNC') ||
      (filterException === 'ABSENT' && s.attendanceStatus === 'ABSENT') ||
      (filterException === 'HOLD' && s.payrollStatus === 'HOLD');
    return matchDept && matchException;
  });

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">👥 Staff Report & Roster desk</h1>
          <p className="page-subtitle">Track rosters, attendance mirrors, shifts, and HR integration logs.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={handleExportSummary}>📥 Export Staff Summary</button>
          <button className="btn btn-primary" onClick={() => setShowAddStaff(true)}>Register Local Staff</button>
        </div>
      </div>

      {/* COMPLIANCE TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'directory' ? 'active' : ''}`} onClick={() => setActiveTab('directory')}>👥 Roster Directory Mirror</button>
        <button className={`tab-btn ${activeTab === 'attendance' ? 'active' : ''}`} onClick={() => setActiveTab('attendance')}>🕒 Attendance Mirror</button>
        <button className={`tab-btn ${activeTab === 'shifts' ? 'active' : ''}`} onClick={() => setActiveTab('shifts')}>📅 Shift Mirror</button>
        <button className={`tab-btn ${activeTab === 'sync-log' ? 'active' : ''}`} onClick={() => setActiveTab('sync-log')}>🔄 HR Sync Log</button>
      </div>

      {/* FILTERS PANEL */}
      <div className="card" style={{ marginBottom: '24px', padding: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <label className="form-label text-xs">Filter by Department</label>
          <select className="form-input" style={{ width: '180px', height: '36px' }} value={filterDept} onChange={e => setFilterDept(e.target.value)}>
            <option value="ALL">All Departments</option>
            <option value="TECHNICAL">Technical & Projection</option>
            <option value="CANTEEN">Concession / Cafe</option>
            <option value="OPERATIONS">Operations</option>
          </select>
        </div>
        <div>
          <label className="form-label text-xs">Filter by Exception</label>
          <select className="form-input" style={{ width: '180px', height: '36px' }} value={filterException} onChange={e => setFilterException(e.target.value)}>
            <option value="ALL">No Exceptions</option>
            <option value="OUT_OF_SYNC">Sync Anomalies (Out of Sync)</option>
            <option value="ABSENT">Attendance Absences</option>
            <option value="HOLD">Payroll Hold State</option>
          </select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
          <button className="btn btn-secondary text-xs" style={{ height: '36px' }} onClick={() => { setFilterDept('ALL'); setFilterException('ALL'); }}>Reset Filters</button>
        </div>
      </div>

      {/* 1. ROSTER DIRECTORY TAB */}
      {activeTab === 'directory' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Staff ID</th>
                <th>Name</th>
                <th>Role</th>
                <th>Department</th>
                <th>Shift</th>
                <th>Attendance</th>
                <th>Payroll Status</th>
                <th>Sync Status</th>
                <th>Supervisor</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {filteredStaff.map(s => (
                <tr key={s.staffId}>
                  <td><code>{s.staffId}</code></td>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.role}</td>
                  <td><span className="badge badge-info">{s.department}</span></td>
                  <td>{s.shift}</td>
                  <td>
                    <span className={`badge ${s.attendanceStatus === 'ABSENT' ? 'badge-error' : s.attendanceStatus === 'ON_DUTY' ? 'badge-warning' : 'badge-success'}`}>
                      {s.attendanceStatus}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${s.payrollStatus === 'HOLD' ? 'badge-error' : 'badge-success'}`}>
                      {s.payrollStatus}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${s.syncStatus === 'OUT_OF_SYNC' ? 'badge-error' : 'badge-success'}`}>
                      {s.syncStatus}
                    </span>
                  </td>
                  <td><strong>{s.supervisor}</strong></td>
                  <td className="text-xs text-muted" style={{ maxWidth: '200px' }}>{s.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. ATTENDANCE MIRROR TAB */}
      {activeTab === 'attendance' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Staff ID</th>
                <th>Name</th>
                <th>Assigned Shift</th>
                <th>Biometric Check-In</th>
                <th>Presence Status</th>
                <th>Sync Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredStaff.map(s => (
                <tr key={s.staffId}>
                  <td><code>{s.staffId}</code></td>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.shift}</td>
                  <td>{s.attendanceStatus === 'ABSENT' ? '—' : '08:54 AM'}</td>
                  <td>
                    <span className={`badge ${s.attendanceStatus === 'ABSENT' ? 'badge-error' : 'badge-success'}`}>
                      {s.attendanceStatus}
                    </span>
                  </td>
                  <td><span className="badge badge-success">{s.syncStatus}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 3. SHIFT MIRROR TAB */}
      {activeTab === 'shifts' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Staff ID</th>
                <th>Name</th>
                <th>Roster Shift</th>
                <th>Supervisor In Charge</th>
                <th>Coverage Notes</th>
              </tr>
            </thead>
            <tbody>
              {filteredStaff.map(s => (
                <tr key={s.staffId}>
                  <td><code>{s.staffId}</code></td>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.shift}</td>
                  <td><strong>{s.supervisor}</strong></td>
                  <td>{s.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. HR SYNC LOG TAB */}
      {activeTab === 'sync-log' && (
        <div className="card" style={{ padding: '24px' }}>
          <div className="flex-between mb-4">
            <h3 className="font-semibold text-md" style={{ color: 'var(--gold)' }}>🔄 HR Sync Integration Log</h3>
            <button className="btn btn-secondary btn-sm" onClick={handleSyncLogTrigger}>Trigger Manual Payroll Sync</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Sync Event Timestamp</th>
                <th>Transferred Record ID</th>
                <th>Type</th>
                <th>Sync Status State</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              {filteredStaff.map(s => (
                <tr key={s.staffId}>
                  <td>{TODAY} 08:00 AM</td>
                  <td><code>{s.staffId}</code></td>
                  <td>Payroll & Attendance</td>
                  <td>
                    <span className={`badge ${s.syncStatus === 'OUT_OF_SYNC' ? 'badge-error' : 'badge-success'}`}>
                      {s.syncStatus}
                    </span>
                  </td>
                  <td className="text-xs text-muted">{s.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* REGISTER LOCAL STAFF MODAL */}
      {showAddStaff && (
        <div className="modal-overlay" onClick={() => setShowAddStaff(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">👤 Register Local Staff Profile</div>
            <form onSubmit={handleCreateStaff}>
              <div className="form-group"><label className="form-label">Full Name</label><input className="form-input" value={newStaff.name} onChange={e => setNewStaff({...newStaff, name: e.target.value})} required /></div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Staff ID</label><input className="form-input" placeholder="e.g. EMP-004" value={newStaff.staffId} onChange={e => setNewStaff({...newStaff, staffId: e.target.value})} required /></div>
                <div className="form-group">
                  <label className="form-label">Department</label>
                  <select className="form-input" value={newStaff.department} onChange={e => setNewStaff({...newStaff, department: e.target.value})}>
                    <option value="OPERATIONS">Operations</option>
                    <option value="TECHNICAL">Technical & Projection</option>
                    <option value="CANTEEN">Concession / Cafe</option>
                  </select>
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Role</label><input className="form-input" value={newStaff.role} onChange={e => setNewStaff({...newStaff, role: e.target.value})} required /></div>
                <div className="form-group"><label className="form-label">Supervisor</label><input className="form-input" value={newStaff.supervisor} onChange={e => setNewStaff({...newStaff, supervisor: e.target.value})} required /></div>
              </div>
              <div className="form-group"><label className="form-label">Notes</label><input className="form-input" value={newStaff.notes} onChange={e => setNewStaff({...newStaff, notes: e.target.value})} /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddStaff(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Register Staff</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* WORKFLOW STATEMENT SUMMARY */}
      <div className="card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', padding: '16px', marginTop: '24px' }}>
        <h4 className="font-semibold" style={{ color: 'var(--gold)', margin: '0 0 8px 0' }}>🔄 Active Staff Integration Workflow</h4>
        <p className="text-xs text-muted" style={{ margin: 0, lineHeight: '1.6' }}>
          The staff summary page aggregates HR-linked mirror data from centralized biometric devices and shift timetables, providing real-time operational roster visibility to cinema management.
        </p>
      </div>

      {/* REDIRECTIONS LINKS SECTION */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="font-semibold mb-3 text-sm" style={{ color: 'var(--gold)' }}>🔗 Redirection Desk</div>
        <div className="flex gap-12">
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('directory')}>👥 Staff Directory</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('attendance')}>🕒 Attendance Mirror</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('shifts')}>📅 Shift Mirror</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('sync-log')}>🔄 HR Sync Log</button>
        </div>
      </div>
    </div>
  );
}
