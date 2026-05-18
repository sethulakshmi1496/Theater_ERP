import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { screensAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

const TODAY = format(new Date(), 'yyyy-MM-dd');

export default function LampsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('inventory'); // inventory, logs, trend, workflow

  const [showLogForm, setShowLogForm] = useState(false);
  const [showInventoryForm, setShowInventoryForm] = useState(false);
  const [showScheduleForm, setShowScheduleForm] = useState(false);

  // Lamp records list
  const [lamps, setLamps] = useState([
    {
      id: 'LMP-001',
      screen: 'Screen 1',
      lampId: 'LMP-001',
      lampType: 'Xenon 3KW',
      installDate: '2025-12-10',
      openingHours: 1200,
      closingHours: 1208,
      workingHours: 8,
      balanceLife: 1792,
      threshold: 100,
      vendor: 'Barco Services Asia',
      replacementDate: '2026-08-15',
      status: 'ACTIVE',
      archived: false,
    },
    {
      id: 'LMP-002',
      screen: 'Screen 2',
      lampId: 'LMP-002',
      lampType: 'Xenon 2KW',
      installDate: '2026-01-15',
      openingHours: 2920,
      closingHours: 2928,
      workingHours: 8,
      balanceLife: 72, // low
      threshold: 100,
      vendor: 'Christie Support',
      replacementDate: '2026-05-22',
      status: 'CRITICAL_ALERT',
      archived: false,
    }
  ]);

  const [form, setForm] = useState({ screen: 'Screen 1', openingHours: '', closingHours: '' });
  const [invForm, setInvForm] = useState({ screen: 'Screen 1', lampId: '', lampType: 'Xenon 3KW', installDate: TODAY, openingHours: '', threshold: '100', vendor: '', status: 'ACTIVE' });
  const [schedForm, setSchedForm] = useState({ lampId: 'LMP-001', replacementDate: TODAY, remarks: '' });

  const handleRegisterLamp = (e) => {
    e.preventDefault();
    const newL = {
      id: invForm.lampId || `LMP-00${lamps.length + 1}`,
      screen: invForm.screen,
      lampId: invForm.lampId || `LMP-00${lamps.length + 1}`,
      lampType: invForm.lampType,
      installDate: invForm.installDate,
      openingHours: parseFloat(invForm.openingHours || 0),
      closingHours: parseFloat(invForm.openingHours || 0),
      workingHours: 0,
      balanceLife: 3000 - parseFloat(invForm.openingHours || 0),
      threshold: parseFloat(invForm.threshold),
      vendor: invForm.vendor,
      replacementDate: '',
      status: invForm.status,
      archived: false,
    };
    setLamps([...lamps, newL]);
    toast.success('Projection Lamp registered successfully.');
    setShowInventoryForm(false);
  };

  const handleUpdateHours = (e) => {
    e.preventDefault();
    const open = parseFloat(form.openingHours);
    const close = parseFloat(form.closingHours);
    const diff = close - open;
    if (diff < 0) {
      toast.error('Closing hours must be greater than or equal to opening hours.');
      return;
    }
    setLamps(lamps.map(l => l.screen === form.screen ? {
      ...l,
      openingHours: open,
      closingHours: close,
      workingHours: diff,
      balanceLife: l.balanceLife - diff,
      status: (l.balanceLife - diff) < l.threshold ? 'CRITICAL_ALERT' : l.status
    } : l));
    toast.success('Lamp hours updated successfully.');
    setShowLogForm(false);
  };

  const handleScheduleReplacement = (e) => {
    e.preventDefault();
    setLamps(lamps.map(l => l.lampId === schedForm.lampId ? {
      ...l,
      replacementDate: schedForm.replacementDate,
      status: 'REPLACEMENT_SCHEDULED'
    } : l));
    toast.success(`Replacement scheduled successfully for ${schedForm.replacementDate}.`);
    setShowScheduleForm(false);
  };

  const handleTriggerAlert = (lampId) => {
    toast.error(`⚠️ Threshold Alert Triggered: Lamp ${lampId} balance life is below threshold limit.`);
  };

  const handleArchiveLamp = (lampId) => {
    setLamps(lamps.map(l => l.lampId === lampId ? { ...l, archived: true, status: 'ARCHIVED' } : l));
    toast.success(`Lamp ${lampId} archived successfully.`);
  };

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">💡 Projection Lamps Tracker</h1>
          <p className="page-subtitle">Track lamp lifecycle hours, calculate balance life, and schedule critical replacements.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setShowInventoryForm(true)}>Register Lamp</button>
          <button className="btn btn-primary" onClick={() => setShowLogForm(true)}>Update Hours</button>
        </div>
      </div>

      {/* COMPLIANCE TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'inventory' ? 'active' : ''}`} onClick={() => setActiveTab('inventory')}>📋 Lamp Registry Master</button>
        <button className={`tab-btn ${activeTab === 'trend' ? 'active' : ''}`} onClick={() => setActiveTab('trend')}>📈 Balance Life Trend</button>
        <button className={`tab-btn ${activeTab === 'workflow' ? 'active' : ''}`} onClick={() => setActiveTab('workflow')}>🔄 Lifecycle Workflow</button>
      </div>

      {/* 1. REGISTRY MASTER TAB */}
      {activeTab === 'inventory' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Screen</th>
                <th>Lamp ID</th>
                <th>Lamp Type</th>
                <th>Install Date</th>
                <th>Opening Hours</th>
                <th>Closing Hours</th>
                <th>Working Hours</th>
                <th>Balance Life</th>
                <th>Threshold</th>
                <th>Vendor</th>
                <th>Replacement Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {lamps.filter(l => !l.archived).map(l => (
                <tr key={l.id}>
                  <td><strong>{l.screen}</strong></td>
                  <td><code>{l.lampId}</code></td>
                  <td><span className="badge badge-neutral">{l.lampType}</span></td>
                  <td>{l.installDate}</td>
                  <td>{l.openingHours}h</td>
                  <td>{l.closingHours}h</td>
                  <td><strong>{l.workingHours}h</strong></td>
                  <td>
                    <strong style={{ color: l.balanceLife < l.threshold ? 'var(--error)' : 'var(--success)' }}>
                      {l.balanceLife}h
                    </strong>
                  </td>
                  <td>{l.threshold}h</td>
                  <td>{l.vendor}</td>
                  <td>{l.replacementDate || '—'}</td>
                  <td>
                    <span className={`badge ${l.status === 'CRITICAL_ALERT' ? 'badge-error' : l.status === 'REPLACEMENT_SCHEDULED' ? 'badge-warning' : 'badge-success'}`}>
                      {l.status}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {l.balanceLife < l.threshold && l.status !== 'REPLACEMENT_SCHEDULED' && (
                        <button className="btn btn-secondary btn-xs" onClick={() => setShowScheduleForm(true)}>Schedule</button>
                      )}
                      <button className="btn btn-secondary btn-xs" style={{ background: 'var(--error)', border: 'none' }} onClick={() => handleArchiveLamp(l.lampId)}>Archive</button>
                      {l.balanceLife < l.threshold && (
                        <button className="btn btn-secondary btn-xs" onClick={() => handleTriggerAlert(l.lampId)}>⚠️ Alert</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. BALANCE TREND TAB */}
      {activeTab === 'trend' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 className="font-semibold text-md mb-4" style={{ color: 'var(--gold)' }}>📈 Projected Depreciation Trends</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {lamps.map(l => {
              const pct = (l.balanceLife / 3000) * 100;
              return (
                <div key={l.id} className="card" style={{ padding: '16px', background: 'var(--bg-glass)' }}>
                  <div className="flex-between mb-2">
                    <strong>{l.screen} ({l.lampType})</strong>
                    <strong style={{ color: l.balanceLife < l.threshold ? 'var(--error)' : 'var(--success)' }}>{l.balanceLife} hrs left ({pct.toFixed(0)}%)</strong>
                  </div>
                  <div className="lamp-bar-track">
                    <div className={`lamp-bar-fill ${l.balanceLife < l.threshold ? 'critical' : ''}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="text-xs text-muted mt-2">Recommended replacement planned date: {l.replacementDate || 'Not scheduled yet'}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. LIFECYCLE WORKFLOW TAB */}
      {activeTab === 'workflow' && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 className="font-semibold text-md mb-4" style={{ color: 'var(--gold)' }}>🔄 Interactive Lamp Lifecycle Stepper</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '24px 0', position: 'relative' }}>
            <div style={{ position: 'absolute', left: 0, right: 0, height: '2px', background: 'var(--border)', zIndex: 1 }} />
            {['Lamp Registered', 'Usage Updated Periodically', 'Balance Tracked', 'Threshold Crossed', 'Replacement Planned & Recorded'].map((step, idx) => (
              <div key={idx} style={{ position: 'relative', zIndex: 2, background: '#1e1e2e', padding: '8px 16px', borderRadius: '20px', border: '1px solid var(--primary)', textAlign: 'center' }}>
                <div className="text-xs text-muted">Step {idx + 1}</div>
                <strong style={{ fontSize: '12px' }}>{step}</strong>
              </div>
            ))}
          </div>
          <div className="text-sm text-muted mt-6" style={{ lineHeight: '1.6' }}>
            <strong>Operational Procedure:</strong> Newly purchased projection lamps must be entered into the Master Register with default vendor terms. Operators record daily opening/closing hours. When remaining balance hours fall below the preconfigured safety threshold limit, standard exception alerts are pushed automatically to the Executive Suite, requiring managers to schedule physical replacements.
          </div>
        </div>
      )}

      {/* MODALS */}

      {/* REGISTER NEW LAMP */}
      {showInventoryForm && (
        <div className="modal-overlay" onClick={() => setShowInventoryForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">💡 Register New Projector Lamp</div>
            <form onSubmit={handleRegisterLamp}>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Screen Link</label>
                  <select className="form-input" value={invForm.screen} onChange={e => setInvForm({...invForm, screen: e.target.value})}>
                    <option value="Screen 1">Screen 1</option>
                    <option value="Screen 2">Screen 2</option>
                  </select>
                </div>
                <div className="form-group"><label className="form-label">Lamp ID</label><input className="form-input" value={invForm.lampId} onChange={e => setInvForm({...invForm, lampId: e.target.value})} placeholder="e.g. LMP-003" required /></div>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Lamp Type</label><input className="form-input" value={invForm.lampType} onChange={e => setInvForm({...invForm, lampType: e.target.value})} required /></div>
                <div className="form-group"><label className="form-label">Install Date</label><input type="date" className="form-input" value={invForm.installDate} onChange={e => setInvForm({...invForm, installDate: e.target.value})} required /></div>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Opening Hours</label><input type="number" className="form-input" value={invForm.openingHours} onChange={e => setInvForm({...invForm, openingHours: e.target.value})} required /></div>
                <div className="form-group"><label className="form-label">Alert Threshold Limit (hrs)</label><input type="number" className="form-input" value={invForm.threshold} onChange={e => setInvForm({...invForm, threshold: e.target.value})} required /></div>
              </div>
              <div className="form-group"><label className="form-label">Vendor Master Link</label><input className="form-input" value={invForm.vendor} onChange={e => setInvForm({...invForm, vendor: e.target.value})} placeholder="e.g. Christie Support" required /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowInventoryForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Save Lamp</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* UPDATE HOURS */}
      {showLogForm && (
        <div className="modal-overlay" onClick={() => setShowLogForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🕒 Update Lamp Hours</div>
            <form onSubmit={handleUpdateHours}>
              <div className="form-group">
                <label className="form-label">Screen Link</label>
                <select className="form-input" value={form.screen} onChange={e => setForm({...form, screen: e.target.value})}>
                  {lamps.map(l => <option key={l.id} value={l.screen}>{l.screen}</option>)}
                </select>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Opening Hours</label><input type="number" className="form-input" value={form.openingHours} onChange={e => setForm({...form, openingHours: e.target.value})} required /></div>
                <div className="form-group"><label className="form-label">Closing Hours</label><input type="number" className="form-input" value={form.closingHours} onChange={e => setForm({...form, closingHours: e.target.value})} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowLogForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Save Log</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SCHEDULE REPLACEMENT */}
      {showScheduleForm && (
        <div className="modal-overlay" onClick={() => setShowScheduleForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">📅 Plan & Schedule Lamp Replacement</div>
            <form onSubmit={handleScheduleReplacement}>
              <div className="form-group">
                <label className="form-label">Select Lamp</label>
                <select className="form-input" value={schedForm.lampId} onChange={e => setSchedForm({...schedForm, lampId: e.target.value})}>
                  {lamps.map(l => <option key={l.id} value={l.lampId}>{l.screen} - {l.lampId}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Proposed Replacement Date</label><input type="date" className="form-input" value={schedForm.replacementDate} onChange={e => setSchedForm({...schedForm, replacementDate: e.target.value})} required /></div>
              <div className="form-group"><label className="form-label">Remarks / Work Order Notes</label><input type="text" className="form-input" value={schedForm.remarks} onChange={e => setSchedForm({...schedForm, remarks: e.target.value})} /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowScheduleForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Confirm Schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REDIRECTIONS LINKS SECTION */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="font-semibold mb-3 text-sm" style={{ color: 'var(--gold)' }}>🔗 Redirection Desk</div>
        <div className="flex gap-12">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/assets')}>⚙️ Asset Registry</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/assets')}>🛠️ Maintenance Desk</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard')}>🚨 Alert Center</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard')}>👑 Executive Suite</button>
        </div>
      </div>
    </div>
  );
}
