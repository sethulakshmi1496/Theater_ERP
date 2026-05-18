import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { operationsAPI, screensAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

const TODAY = format(new Date(), 'yyyy-MM-dd');

const CATEGORY_ICONS = {
  LAMP: '💡',
  PROJECTOR: '📽️',
  SOUND: '🔊',
  DG_SET: '⚡',
  METER: '📟',
  GLASSES: '🕶️',
  HVAC: '❄️',
  UPS: '🔋',
};

function LifeBar({ pct, alert }) {
  const color = pct === null ? '#888' : pct < 10 ? '#ef4444' : pct < 30 ? '#f59e0b' : '#22c55e';
  return (
    <div style={{ background: 'rgba(255,255,255,0.07)', borderRadius: 99, height: 8, overflow: 'hidden', marginTop: 6 }}>
      <div style={{ width: `${Math.max(pct ?? 0, 0.5)}%`, background: color, height: '100%', borderRadius: 99, transition: 'width 0.4s' }} />
    </div>
  );
}

export default function AssetRegistryPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('registry'); // registry, glasses, tickets, preventive, orders, amc
  const [categoryFilter, setCategoryFilter] = useState('LAMP');
  const [screenFilter, setScreenFilter] = useState('');
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [showLogModal, setShowLogModal] = useState(null);
  const [showHistory, setShowHistory] = useState(null);

  // Forms state
  const [assetForm, setAssetForm] = useState({ template: '', screen: '', serial_number: '', installed_date: TODAY, alert_threshold_hours: 100, is_active: true });
  const [logForm, setLogForm] = useState({ opening_value: '', closing_value: '', cost: '', notes: '', log_date: TODAY });
  const [ticketForm, setTicketForm] = useState({ assetId: '', category: 'HARDWARE', priority: 'HIGH', description: '', reportedBy: 'Manager' });
  const [pmForm, setPmForm] = useState({ assetId: '', serviceType: 'ROUTINE', nextDueDate: TODAY, vendor: '', remarks: '' });
  const [orderForm, setOrderForm] = useState({ ticketId: '', engineerName: '', partsUsed: '', partsCost: '', status: 'IN_PROGRESS' });
  const [amcForm, setAmcForm] = useState({ name: '', vendor: '', startDate: TODAY, endDate: TODAY, cost: '', coverageType: 'COMPREHENSIVE' });

  // Data fetching
  const { data: categories } = useQuery({ queryKey: ['asset-categories'], queryFn: () => operationsAPI.assetCategories.list().then(r => r.data?.results ?? r.data) });
  const { data: templates } = useQuery({ queryKey: ['asset-templates', categoryFilter], queryFn: () => operationsAPI.assetTemplates.list({ category__key: categoryFilter }).then(r => r.data?.results ?? r.data), enabled: !!categoryFilter });
  const { data: assets, isLoading } = useQuery({ queryKey: ['tenant-assets', categoryFilter, screenFilter], queryFn: () => operationsAPI.tenantAssets.list({ template__category__key: categoryFilter || undefined, screen: screenFilter || undefined }).then(r => r.data?.results ?? r.data) });
  const { data: assetLogs } = useQuery({ queryKey: ['asset-logs', showHistory?.id], queryFn: () => operationsAPI.assetLogs.list({ asset: showHistory.id }).then(r => r.data?.results ?? r.data), enabled: !!showHistory });
  const { data: screens } = useQuery({ queryKey: ['screens'], queryFn: () => screensAPI.list().then(r => r.data?.results ?? r.data) });

  const addAssetMutation = useMutation({
    mutationFn: (d) => operationsAPI.tenantAssets.create(d),
    onSuccess: () => {
      qc.invalidateQueries(['tenant-assets']);
      toast.success('Asset successfully registered inside Canonical Master Registry!');
      setShowAddAsset(false);
      setAssetForm({ template: '', screen: '', serial_number: '', installed_date: TODAY, alert_threshold_hours: 100, is_active: true });
    },
    onError: (e) => toast.error('Failed to register asset.')
  });

  const logMutation = useMutation({
    mutationFn: (d) => operationsAPI.assetLogs.create(d),
    onSuccess: () => {
      qc.invalidateQueries(['tenant-assets']);
      qc.invalidateQueries(['asset-logs', showLogModal?.id]);
      toast.success('Hours registered and logged to service log.');
      setShowLogModal(null);
      setLogForm({ opening_value: '', closing_value: '', cost: '', notes: '', log_date: TODAY });
    },
    onError: (e) => toast.error('Failed to log hours.')
  });

  const assetList = Array.isArray(assets) ? assets : [];
  const screenList = Array.isArray(screens) ? screens : [];
  const templateList = Array.isArray(templates) ? templates : [];
  const categoryList = Array.isArray(categories) ? categories : [];

  // Static Compliance Sub-page registers
  const [glasses, setGlasses] = useState([
    { id: 1, batchNo: 'BATCH-2026-A', totalQty: 500, currentIssued: 142, damagedQty: 18, location: 'Counter 1' },
    { id: 2, batchNo: 'BATCH-2026-B', totalQty: 400, currentIssued: 85, damagedQty: 5, location: 'Counter 2' }
  ]);

  const [tickets, setTickets] = useState([
    { id: 1, assetName: 'Projection Bulb Barco A1', category: 'HARDWARE', priority: 'HIGH', status: 'OPEN', description: 'Screen 1 projector bulb flicker', reportedBy: 'Staff', date: '2026-05-18' },
    { id: 2, assetName: 'Yamaha Sound Processor X3', category: 'AUDIO', priority: 'MEDIUM', status: 'IN_PROGRESS', description: 'Surround sound left channel hum', reportedBy: 'Manager', date: '2026-05-17' }
  ]);

  const [preventive, setPreventive] = useState([
    { id: 1, assetName: '125 KVA DG Generator', serviceType: 'OIL_CHANGE', nextDueDate: '2026-06-05', vendor: 'Cummins Ltd', remarks: 'Replaced air filters last run.' },
    { id: 2, assetName: 'Screen 2 Xenon Lamp', serviceType: 'CALIBRATION', nextDueDate: '2026-05-28', vendor: 'Barco Services', remarks: 'Maintain color balance' }
  ]);

  const [workOrders, setWorkOrders] = useState([
    { id: 1, ticketId: 'TCK-002', engineerName: 'Aman Sharma', partsUsed: 'Surround speaker connector pin', partsCost: 850.00, status: 'RESOLVED', timestamp: '2026-05-18T10:30:00' },
    { id: 2, ticketId: 'TCK-001', engineerName: 'John Cummins', partsUsed: 'Pending inspection', partsCost: 0, status: 'IN_PROGRESS', timestamp: '2026-05-18T14:10:00' }
  ]);

  const [amcs, setAmcs] = useState([
    { id: 1, name: 'DG Set Comprehensive Contract', vendor: 'Cummins India', startDate: '2026-01-01', endDate: '2026-12-31', cost: 45000.00, coverageType: 'COMPREHENSIVE' },
    { id: 2, name: 'Projector Xenon Spares Contract', vendor: 'Barco Services Asia', startDate: '2026-04-01', endDate: '2027-03-31', cost: 120000.00, coverageType: 'PARTS_ONLY' }
  ]);

  const handleCreateTicket = (e) => {
    e.preventDefault();
    const newTck = {
      id: tickets.length + 1,
      assetName: ticketForm.assetId || 'Universal Asset',
      category: ticketForm.category,
      priority: ticketForm.priority,
      status: 'OPEN',
      description: ticketForm.description,
      reportedBy: ticketForm.reportedBy,
      date: TODAY
    };
    setTickets([newTck, ...tickets]);
    toast.success('Fault ticket raised successfully inside Maintenance Desk.');
    setTicketForm({ assetId: '', category: 'HARDWARE', priority: 'HIGH', description: '', reportedBy: 'Manager' });
  };

  const handleCreatePM = (e) => {
    e.preventDefault();
    const newPm = {
      id: preventive.length + 1,
      assetName: pmForm.assetId || 'Universal Asset',
      serviceType: pmForm.serviceType,
      nextDueDate: pmForm.nextDueDate,
      vendor: pmForm.vendor,
      remarks: pmForm.remarks
    };
    setPreventive([newPm, ...preventive]);
    toast.success('Periodic maintenance schedule locked.');
    setPmForm({ assetId: '', serviceType: 'ROUTINE', nextDueDate: TODAY, vendor: '', remarks: '' });
  };

  const handleCreateWorkOrder = (e) => {
    e.preventDefault();
    const newOrder = {
      id: workOrders.length + 1,
      ticketId: orderForm.ticketId,
      engineerName: orderForm.engineerName,
      partsUsed: orderForm.partsUsed || 'No parts used',
      partsCost: parseFloat(orderForm.partsCost || 0),
      status: orderForm.status,
      timestamp: new Date().toISOString()
    };
    setWorkOrders([newOrder, ...workOrders]);
    toast.success('Work order created and assigned.');
    setOrderForm({ ticketId: '', engineerName: '', partsUsed: '', partsCost: '', status: 'IN_PROGRESS' });
  };

  const handleCreateAMC = (e) => {
    e.preventDefault();
    const newAmc = {
      id: amcs.length + 1,
      name: amcForm.name,
      vendor: amcForm.vendor,
      startDate: amcForm.startDate,
      endDate: amcForm.endDate,
      cost: parseFloat(amcForm.cost),
      coverageType: amcForm.coverageType
    };
    setAmcs([newAmc, ...amcs]);
    toast.success('AMC & Warranty service contract registered.');
    setAmcForm({ name: '', vendor: '', startDate: TODAY, endDate: TODAY, cost: '', coverageType: 'COMPREHENSIVE' });
  };

  const byScreen = {};
  assetList.forEach(a => {
    const key = a.screen ? (a.screen_name || `Screen ${a.screen}`) : 'Unassigned';
    if (!byScreen[key]) byScreen[key] = [];
    byScreen[key].push(a);
  });

  const openLogModal = (asset) => {
    setShowLogModal(asset);
    setLogForm(p => ({ ...p, opening_value: String(asset.current_hours || '0'), log_date: TODAY }));
  };

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <h1 className="page-title">🏗️ Asset Registry & Maintenance Desk</h1>
          <p className="page-subtitle">Canonical asset directory, 3D glasses inventory, PM logs, and AMC registries.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {activeTab === 'registry' && (
            <button className="btn btn-primary" onClick={() => setShowAddAsset(true)}>+ Register Asset</button>
          )}
          {activeTab === 'tickets' && (
            <button className="btn btn-primary" style={{ backgroundColor: 'var(--error)' }} onClick={() => toast.success('Form overlay triggered')}>+ File Fault Ticket</button>
          )}
          {activeTab === 'preventive' && (
            <button className="btn btn-primary" onClick={() => toast.success('Form overlay triggered')}>+ Schedule PM</button>
          )}
          {activeTab === 'orders' && (
            <button className="btn btn-primary" onClick={() => toast.success('Form overlay triggered')}>+ Dispatch Work Order</button>
          )}
          {activeTab === 'amc' && (
            <button className="btn btn-primary" onClick={() => toast.success('Form overlay triggered')}>+ Register AMC Contract</button>
          )}
        </div>
      </div>

      {/* COMPLIANCE TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`} onClick={() => setActiveTab('registry')}>🖥️ Asset registry</button>
        <button className={`tab-btn ${activeTab === 'glasses' ? 'active' : ''}`} onClick={() => setActiveTab('glasses')}>🕶️ 3D Glasses Tracker</button>
        <button className={`tab-btn ${activeTab === 'tickets' ? 'active' : ''}`} onClick={() => setActiveTab('tickets')}>🎫 Fault Tickets</button>
        <button className={`tab-btn ${activeTab === 'preventive' ? 'active' : ''}`} onClick={() => setActiveTab('preventive')}>📅 Preventive Maintenance</button>
        <button className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`} onClick={() => setActiveTab('orders')}>🛠️ Work Orders</button>
        <button className={`tab-btn ${activeTab === 'amc' ? 'active' : ''}`} onClick={() => setActiveTab('amc')}>⏳ AMC & Warranty</button>
      </div>

      {/* 1. CANONICAL ASSET REGISTRY */}
      {activeTab === 'registry' && (
        <div>
          {/* Category Filter Pills */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
            <button onClick={() => setCategoryFilter('')} style={{ padding: '6px 16px', borderRadius: 99, border: '1px solid var(--border)', background: !categoryFilter ? 'var(--primary)' : 'transparent', color: !categoryFilter ? '#fff' : 'var(--text-muted)', cursor: 'pointer', fontSize: 13 }}>All</button>
            {categoryList.map(cat => (
              <button key={cat.key} onClick={() => setCategoryFilter(cat.key)} style={{ padding: '6px 16px', borderRadius: 99, border: '1px solid var(--border)', background: categoryFilter === cat.key ? 'var(--primary)' : 'transparent', color: categoryFilter === cat.key ? '#fff' : 'var(--text-muted)', cursor: 'pointer', fontSize: 13 }}>
                {CATEGORY_ICONS[cat.key] ?? '📦'} {cat.label}
              </button>
            ))}
          </div>

          {isLoading ? <div className="loading-cell">Loading assets...</div> :
          assetList.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>No assets registered inside this category.</div>
          ) : (
            Object.entries(byScreen).map(([screenName, screenAssets]) => (
              <div key={screenName} style={{ marginBottom: 32 }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-secondary)', marginBottom: 12, borderLeft: '3px solid var(--primary)', paddingLeft: 10 }}>📍 {screenName}</div>
                <div className="grid-2" style={{ gap: 16 }}>
                  {screenAssets.map(asset => {
                    const pct = asset.life_percentage !== null ? parseFloat(asset.life_percentage) : null;
                    const isAlert = pct !== null && pct < 15;
                    const catIcon = CATEGORY_ICONS[asset.category_key] ?? '📦';
                    return (
                      <div key={asset.id} className="card" style={{ borderColor: isAlert ? 'rgba(239,68,68,0.5)' : undefined, position: 'relative' }}>
                        {isAlert && <span className="badge badge-error" style={{ position: 'absolute', top: 12, right: 12 }}>🚨 LIFE WARNING</span>}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                          <span style={{ fontSize: 28 }}>{catIcon}</span>
                          <div>
                            <div style={{ fontWeight: 700 }}>{asset.template_name}</div>
                            <code style={{ fontSize: 11, color: 'var(--text-muted)' }}>S/N: {asset.serial_number}</code>
                          </div>
                        </div>
                        <div className="grid-2" style={{ gap: 10, marginBottom: 12 }}>
                          <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: 10 }}>
                            <div className="text-xs text-muted">Current Hours</div>
                            <strong>{parseFloat(asset.current_hours).toFixed(1)}h</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: 10 }}>
                            <div className="text-xs text-muted">Remaining</div>
                            <strong style={{ color: isAlert ? 'var(--error)' : 'var(--success)' }}>{asset.remaining_hours !== null ? `${parseFloat(asset.remaining_hours).toFixed(1)}h` : '—'}</strong>
                          </div>
                        </div>
                        {pct !== null && (
                          <>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-xs text-muted">Life Consumed</span><span className="text-xs">{(100 - pct).toFixed(1)}%</span></div>
                            <LifeBar pct={pct} alert={isAlert} />
                          </>
                        )}
                        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                          <button className="btn btn-primary" style={{ flex: 1, padding: '6px 0', fontSize: 13 }} onClick={() => openLogModal(asset)}>+ Log Hours</button>
                          <button className="btn btn-secondary" style={{ flex: 1, padding: '6px 0', fontSize: 13 }} onClick={() => setShowHistory(asset)}>🕒 Service History</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 2. 3D GLASSES TRACKER */}
      {activeTab === 'glasses' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch Number</th>
                <th>Total Stock</th>
                <th>Currently Issued</th>
                <th>Damaged / Lost</th>
                <th>Location / Counter</th>
                <th>Available Balance</th>
              </tr>
            </thead>
            <tbody>
              {glasses.map(g => (
                <tr key={g.id}>
                  <td><strong>{g.batchNo}</strong></td>
                  <td>{g.totalQty} units</td>
                  <td>{g.currentIssued} in-use</td>
                  <td><strong style={{ color: 'var(--error)' }}>{g.damagedQty} damaged</strong></td>
                  <td>{g.location}</td>
                  <td><strong style={{ color: 'var(--success)' }}>{g.totalQty - g.currentIssued - g.damagedQty} units</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 3. FAULT TICKETS */}
      {activeTab === 'tickets' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticket ID</th>
                <th>Affected Asset</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Issue Description</th>
                <th>Reported By</th>
                <th>Raiser Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map(t => (
                <tr key={t.id}>
                  <td><strong>TCK-00{t.id}</strong></td>
                  <td><strong>{t.assetName}</strong></td>
                  <td><span className="badge" style={{ background: 'var(--bg-glass)' }}>{t.category}</span></td>
                  <td><span className={`badge ${t.priority === 'HIGH' ? 'badge-error' : 'badge-warning'}`}>{t.priority}</span></td>
                  <td>{t.description}</td>
                  <td>{t.reportedBy}</td>
                  <td>{t.date}</td>
                  <td><span className={`badge ${t.status === 'OPEN' ? 'badge-warning' : 'badge-info'}`}>{t.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. PREVENTIVE MAINTENANCE */}
      {activeTab === 'preventive' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>PM Plan ID</th>
                <th>Rostered Equipment</th>
                <th>Service Plan Category</th>
                <th>Target Next Due Date</th>
                <th>Service Agency / Vendor</th>
                <th>Remarks / Spares required</th>
              </tr>
            </thead>
            <tbody>
              {preventive.map(pm => (
                <tr key={pm.id}>
                  <td><strong>PM-00{pm.id}</strong></td>
                  <td><strong>{pm.assetName}</strong></td>
                  <td><span className="badge badge-info">{pm.serviceType}</span></td>
                  <td><strong style={{ color: 'var(--warning)' }}>{pm.nextDueDate}</strong></td>
                  <td>{pm.vendor}</td>
                  <td className="text-xs text-muted">{pm.remarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 5. WORK ORDERS */}
      {activeTab === 'orders' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>WO Ref ID</th>
                <th>Linked Ticket</th>
                <th>Field Engineer</th>
                <th>Parts Replaced / Used</th>
                <th>Material Cost</th>
                <th>Authorized State</th>
              </tr>
            </thead>
            <tbody>
              {workOrders.map(o => (
                <tr key={o.id}>
                  <td><strong>WO-2026-{o.id}</strong></td>
                  <td>{o.ticketId}</td>
                  <td><strong>{o.engineerName}</strong></td>
                  <td>{o.partsUsed}</td>
                  <td><strong style={{ color: 'var(--error)' }}>₹{o.partsCost.toFixed(2)}</strong></td>
                  <td><span className={`badge ${o.status === 'RESOLVED' ? 'badge-success' : 'badge-warning'}`}>{o.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 6. AMC & WARRANTY */}
      {activeTab === 'amc' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Contract ID</th>
                <th>Contract Description</th>
                <th>Authorized Vendor</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Premium Cost</th>
                <th>Coverage Type</th>
              </tr>
            </thead>
            <tbody>
              {amcs.map(a => (
                <tr key={a.id}>
                  <td><strong>AMC-00{a.id}</strong></td>
                  <td><strong>{a.name}</strong></td>
                  <td>{a.vendor}</td>
                  <td>{a.startDate}</td>
                  <td>{a.endDate}</td>
                  <td><strong>₹{a.cost.toLocaleString('en-IN')}</strong></td>
                  <td><span className="badge badge-success">{a.coverageType}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* MODALS */}

      {/* ADD ASSET MODAL */}
      {showAddAsset && (
        <div className="modal-overlay" onClick={() => setShowAddAsset(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🏗️ Register Canonical Asset</div>
            <form onSubmit={e => { e.preventDefault(); addAssetMutation.mutate(assetForm); }}>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select className="form-select" value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                    {categoryList.map(c => <option key={c.key} value={c.key}>{CATEGORY_ICONS[c.key]} {c.label}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Template (Model)</label>
                  <select className="form-select" value={assetForm.template} onChange={e => setAssetForm(p => ({ ...p, template: e.target.value }))} required>
                    <option value="">Select template…</option>
                    {templateList.map(t => <option key={t.id} value={t.id}>{t.manufacturer} {t.model_number}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Serial Number</label>
                  <input className="form-input" placeholder="e.g. SN-BAR-9841" value={assetForm.serial_number} onChange={e => setAssetForm(p => ({ ...p, serial_number: e.target.value }))} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Linked Screen</label>
                  <select className="form-select" value={assetForm.screen} onChange={e => setAssetForm(p => ({ ...p, screen: e.target.value }))}>
                    <option value="">Unassigned</option>
                    {screenList.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ textAlign: 'right', marginTop: 16, display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddAsset(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Register Asset</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LOG HOURS MODAL */}
      {showLogModal && (
        <div className="modal-overlay" onClick={() => setShowLogModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">
              {CATEGORY_ICONS[showLogModal.category_key] ?? '📦'} Log Hours — {showLogModal.serial_number}
            </div>
            <form onSubmit={e => { e.preventDefault(); logMutation.mutate({ asset: showLogModal.id, ...logForm }); }}>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Date</label><input type="date" className="form-input" value={logForm.log_date} onChange={e => setLogForm(p => ({ ...p, log_date: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Opening Value</label><input type="number" className="form-input" value={logForm.opening_value} onChange={e => setLogForm(p => ({ ...p, opening_value: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Closing Value</label><input type="number" className="form-input" value={logForm.closing_value} onChange={e => setLogForm(p => ({ ...p, closing_value: e.target.value }))} required /></div>
              </div>
              <div className="form-group"><label className="form-label">Notes</label><textarea className="form-textarea" rows="2" value={logForm.notes} onChange={e => setLogForm(p => ({ ...p, notes: e.target.value }))} /></div>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowLogModal(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary">💾 Save Log</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* HISTORY TIMELINE MODAL */}
      {showHistory && (
        <div className="modal-overlay" onClick={() => setShowHistory(null)}>
          <div className="modal" style={{ maxWidth: 700 }} onClick={e => e.stopPropagation()}>
            <div className="modal-title">🕒 Asset Service History — {showHistory.serial_number}</div>
            <div className="text-xs text-muted" style={{ marginBottom: 20 }}>{showHistory.template_name}</div>
            {!assetLogs && <div className="loading-cell">Loading…</div>}
            {assetLogs && assetLogs.length === 0 && <div className="loading-cell">No logs registered yet.</div>}
            {assetLogs && assetLogs.length > 0 && (
              <div style={{ position: 'relative', paddingLeft: 28 }}>
                <div style={{ position: 'absolute', left: 10, top: 0, bottom: 0, width: 2, background: 'var(--border)' }} />
                {assetLogs.map((log, i) => (
                  <div key={log.id} style={{ position: 'relative', marginBottom: 20 }}>
                    <div style={{ position: 'absolute', left: -22, top: 4, width: 12, height: 12, borderRadius: '50%', background: i === 0 ? 'var(--primary)' : 'var(--border)', border: '2px solid var(--bg-card)' }} />
                    <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 10, padding: '12px 16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <strong style={{ fontSize: 13 }}>{format(new Date(log.log_date), 'dd MMM yyyy')}</strong>
                        <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 700 }}>+{parseFloat(log.delta).toFixed(2)}h</span>
                      </div>
                      <div style={{ display: 'flex', gap: 20, fontSize: 12, color: 'var(--text-muted)' }}>
                        <span>Open: {log.opening_value}h</span><span>→</span><span>Close: {log.closing_value}h</span>
                      </div>
                      {log.notes && <div style={{ fontSize: 12, marginTop: 6, color: 'var(--text-muted)' }}>📝 {log.notes}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setShowHistory(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
