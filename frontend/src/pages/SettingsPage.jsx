import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsAPI, authAPI } from '../api';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  
  const tabs = [
    { id: 'profile', label: '👤 Tenant Profile' },
    { id: 'modules', label: '🧩 Modules & Features' },
    { id: 'alert-rules', label: '🚨 Alert Rules' },
    { id: 'vendors', label: '💼 Vendor Master' },
    { id: 'parking', label: '🚗 Parking Configuration' },
    { id: 'integrations', label: '📡 Integration Hub' }
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">⚙️ System Governance Settings</h1>
          <p className="page-subtitle">Configure self-serve parameters, active modules, alert thresholds, vendor details, and parking rates.</p>
        </div>
      </div>

      <div className="tabs" style={{ display: 'flex', gap: '12px', marginBottom: '24px', borderBottom: '1px solid var(--border)', overflowX: 'auto', paddingBottom: '4px' }}>
        {tabs.map(t => (
          <div 
            key={t.id} 
            onClick={() => setActiveTab(t.id)}
            style={{ 
              padding: '12px 20px', cursor: 'pointer', whiteSpace: 'nowrap',
              borderBottom: activeTab === t.id ? '2px solid var(--primary)' : '2px solid transparent',
              color: activeTab === t.id ? 'var(--primary)' : 'var(--text-muted)',
              fontWeight: activeTab === t.id ? '600' : '400'
            }}
          >
            {t.label}
          </div>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'profile' && <ProfileSettings />}
        {activeTab === 'modules' && <ModuleSettings />}
        {activeTab === 'alert-rules' && <AlertRulesSettings />}
        {activeTab === 'vendors' && <VendorMasterSettings />}
        {activeTab === 'parking' && <ParkingSettings />}
        {activeTab === 'integrations' && <IntegrationHubSettings />}
      </div>
    </div>
  );
}

// 1. TENANT PROFILE
function ProfileSettings() {
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('');
  const [timezone, setTimezone] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['tenant-profile'],
    queryFn: () => settingsAPI.profile().then(r => r.data),
  });

  const mutation = useMutation({
    mutationFn: (payload) => settingsAPI.updateProfile(data.id, payload),
    onSuccess: () => { qc.invalidateQueries(['tenant-profile']); toast.success('Profile updated successfully!'); }
  });

  if (isLoading) return <div className="loading-cell">Loading profile...</div>;

  return (
    <div className="card" style={{ maxWidth: '600px' }}>
      <h3 className="font-semibold mb-4 text-lg">Tenant Profile</h3>
      <div className="form-group">
        <label className="form-label">Business Theater Name</label>
        <div className="flex gap-12">
          <input className="form-input" defaultValue={data?.name} onChange={e => setName(e.target.value)} />
          <button className="btn btn-secondary" onClick={() => mutation.mutate({name: name || data.name})}>Update</button>
        </div>
      </div>
      <div className="form-group mt-4">
        <label className="form-label">System Currency Code</label>
        <div className="flex gap-12">
          <input className="form-input" defaultValue={data?.currency} onChange={e => setCurrency(e.target.value)} />
          <button className="btn btn-secondary" onClick={() => mutation.mutate({currency: currency || data.currency})}>Update</button>
        </div>
      </div>
      <div className="form-group mt-4">
        <label className="form-label">Operating Timezone</label>
        <div className="flex gap-12">
          <input className="form-input" defaultValue={data?.timezone} onChange={e => setTimezone(e.target.value)} />
          <button className="btn btn-secondary" onClick={() => mutation.mutate({timezone: timezone || data.timezone})}>Update</button>
        </div>
      </div>
      <div className="mt-6 p-4 rounded bg-dark" style={{ border: '1px solid var(--border)', background: 'var(--bg-glass)' }}>
        <div className="text-sm text-muted">AEC Tenant Slug: <span className="font-mono" style={{ color: 'var(--gold)' }}>{data?.slug}</span></div>
        <div className="text-sm text-muted mt-3">SaaS Subscription Status: <span className="badge badge-warning">{data?.plan?.toUpperCase()} Plan</span></div>
      </div>
    </div>
  );
}

// 2. MODULES & FEATURES
function ModuleSettings() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['tenant-modules'], queryFn: () => settingsAPI.modules().then(r => r.data) });
  
  const mutation = useMutation({
    mutationFn: ({id, is_enabled}) => settingsAPI.updateModule(id, { is_enabled }),
    onSuccess: () => { qc.invalidateQueries(['tenant-modules']); toast.success('Module settings modified!'); }
  });

  const records = data?.results || data || [];

  return (
    <div className="card">
      <h3 className="font-semibold mb-4 text-lg">Active Operational Modules</h3>
      <table className="data-table">
        <thead><tr><th>Module Key Identifier</th><th>Operational Scope</th><th>Status</th><th>Toggle state</th></tr></thead>
        <tbody>
          {isLoading && <tr><td colSpan={4} className="loading-cell">Loading...</td></tr>}
          {records.map(r => (
            <tr key={r.id}>
              <td className="font-mono"><strong>{r.module_key}</strong></td>
              <td className="text-muted text-xs">Governs access rules, page routes, and background sync engines.</td>
              <td>
                <span className={`badge ${r.is_enabled ? 'badge-success' : 'badge-neutral'}`}>
                  {r.is_enabled ? 'Active Enabled' : 'Disabled'}
                </span>
              </td>
              <td>
                <button className="btn btn-secondary btn-sm" onClick={() => mutation.mutate({ id: r.id, is_enabled: !r.is_enabled })}>
                  {r.is_enabled ? 'Disable' : 'Enable'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 3. ALERT RULES
function AlertRulesSettings() {
  const [rules, setRules] = useState([
    { id: 1, name: 'Diesel Overburn Threshold', module: 'GENERATOR', limit: '3.5 Liters/hour', state: 'ENABLED' },
    { id: 2, name: 'Projection Lamp Safety life', module: 'LAMPS', limit: '200 Hours remaining', state: 'ENABLED' },
    { id: 3, name: 'Utility readings standard deviation', module: 'UTILITIES', limit: '20% drift deviation', state: 'ENABLED' }
  ]);

  const toggleRule = (id) => {
    setRules(rules.map(r => r.id === id ? { ...r, state: r.state === 'ENABLED' ? 'DISABLED' : 'ENABLED' } : r));
    toast.success('Warning rule status modified successfully.');
  };

  return (
    <div className="card">
      <h3 className="font-semibold mb-4 text-lg">⚠️ Auto-Alert Rule Triggers</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Rule ID</th>
            <th>Rule Description</th>
            <th>Target Module</th>
            <th>Safety Limit Value</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rules.map(r => (
            <tr key={r.id}>
              <td><strong>RULE-00{r.id}</strong></td>
              <td><strong>{r.name}</strong></td>
              <td><span className="badge badge-info">{r.module}</span></td>
              <td><code>{r.limit}</code></td>
              <td>
                <span className={`badge ${r.state === 'ENABLED' ? 'badge-success' : 'badge-neutral'}`}>
                  {r.state}
                </span>
              </td>
              <td>
                <button className="btn btn-secondary btn-sm" onClick={() => toggleRule(r.id)}>
                  {r.state === 'ENABLED' ? 'Disable' : 'Enable'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 4. VENDOR MASTER
function VendorMasterSettings() {
  const [vendors, setVendors] = useState([
    { id: 1, name: 'Barco Services Asia', category: 'SPARES_TECHNICAL', phone: '+91 22 4930 1000', email: 'spares@barco.com', terms: 'Net 30' },
    { id: 2, name: 'PepsiCo Beverages India', category: 'CAFE_INVENTORY', phone: '+91 12 4470 2000', email: 'canteen@pepsico.com', terms: 'Net 15' }
  ]);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', category: 'CAFE_INVENTORY', phone: '', email: '', terms: 'Net 15' });

  const handleSubmit = (e) => {
    e.preventDefault();
    const newVen = {
      id: vendors.length + 1,
      name: form.name,
      category: form.category,
      phone: form.phone,
      email: form.email,
      terms: form.terms
    };
    setVendors([...vendors, newVen]);
    toast.success('Vendor profile registered inside Master Master data.');
    setShowForm(false);
    setForm({ name: '', category: 'CAFE_INVENTORY', phone: '', email: '', terms: 'Net 15' });
  };

  return (
    <div className="card">
      <div className="flex-between mb-4">
        <h3 className="font-semibold text-lg" style={{ margin: 0 }}>💼 Registered Suppliers & Service Providers</h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>+ Register Vendor</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Vendor Name</th>
            <th>Service Category</th>
            <th>Phone / Email</th>
            <th>Default Terms</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {vendors.map(v => (
            <tr key={v.id}>
              <td><strong>{v.name}</strong></td>
              <td><span className="badge badge-info">{v.category}</span></td>
              <td>
                <div>📞 {v.phone}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>✉️ {v.email}</div>
              </td>
              <td>{v.terms}</td>
              <td><span className="badge badge-success">Active</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">💼 Register Service Vendor</div>
            <form onSubmit={handleSubmit}>
              <div className="form-group"><label className="form-label">Company Name</label><input className="form-input" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required /></div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select className="form-input" value={form.category} onChange={e => setForm({...form, category: e.target.value})}>
                    <option value="CAFE_INVENTORY">Cafe Supplies</option>
                    <option value="SPARES_TECHNICAL">Technical & Projection Spares</option>
                    <option value="UTILITY_AGENCY">Utility Readings/Meters Agency</option>
                  </select>
                </div>
                <div className="form-group"><label className="form-label">Payment Terms</label><input className="form-input" placeholder="e.g. Net 30" value={form.terms} onChange={e => setForm({...form, terms: e.target.value})} required /></div>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Phone</label><input className="form-input" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} required /></div>
                <div className="form-group"><label className="form-label">Email</label><input type="email" className="form-input" value={form.email} onChange={e => setForm({...form, email: e.target.value})} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Save Vendor</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// 5. PARKING CONFIGURATION
function ParkingSettings() {
  const [pricing, setPricing] = useState([
    { id: 1, vehicleType: '2 Wheeler (Bike)', baseRate: 30.00, hourlyIncrement: 10.00, capacityLimit: 150 },
    { id: 2, vehicleType: '4 Wheeler (Car)', baseRate: 60.00, hourlyIncrement: 20.00, capacityLimit: 80 }
  ]);

  const [editingId, setEditingId] = useState(null);
  const [editRate, setEditRate] = useState('');

  const handleSaveRate = (id) => {
    setPricing(pricing.map(p => p.id === id ? { ...p, baseRate: parseFloat(editRate) } : p));
    toast.success('Parking tariff rate card updated successfully.');
    setEditingId(null);
  };

  return (
    <div className="card">
      <h3 className="font-semibold mb-4 text-lg">🚗 Vehicle Parking Tariffs & Capacities</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Vehicle Category</th>
            <th>Base Rate (First 3 Hrs)</th>
            <th>Hourly Increment</th>
            <th>Total Slot Capacity Limit</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {pricing.map(p => (
            <tr key={p.id}>
              <td><strong>{p.vehicleType}</strong></td>
              <td>
                {editingId === p.id ? (
                  <input type="number" className="form-input" style={{ width: '100px' }} value={editRate} onChange={e => setEditRate(e.target.value)} />
                ) : (
                  <strong>₹{p.baseRate.toFixed(2)}</strong>
                )}
              </td>
              <td>₹{p.hourlyIncrement.toFixed(2)}/hour</td>
              <td>{p.capacityLimit} bays</td>
              <td>
                {editingId === p.id ? (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn-success btn-xs" onClick={() => handleSaveRate(p.id)}>Save</button>
                    <button className="btn btn-secondary btn-xs" onClick={() => setEditingId(null)}>Cancel</button>
                  </div>
                ) : (
                  <button className="btn btn-secondary btn-xs" onClick={() => { setEditingId(p.id); setEditRate(p.baseRate.toString()); }}>Edit rate</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 6. INTEGRATION HUB
function IntegrationHubSettings() {
  const [syncState, setSyncState] = useState([
    { id: 1, source: 'BookMyShow Ticketing Api', status: 'ACTIVE', lastSync: '2026-05-18 14:45', count: 145 },
    { id: 2, source: 'District GBO Box Office Parser', status: 'ACTIVE', lastSync: '2026-05-18 09:12', count: 1 }
  ]);

  return (
    <div className="card">
      <h3 className="font-semibold mb-4 text-lg">📡 Connected Integration Connectors</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {syncState.map(sync => (
          <div key={sync.id} className="card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px' }}>
            <div>
              <strong style={{ fontSize: '16px' }}>{sync.source}</strong>
              <div className="text-xs text-muted" style={{ marginTop: '4px' }}>Last Successful handshake: {sync.lastSync} · Transferred: {sync.count} entries</div>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span className="badge badge-success">{sync.status}</span>
              <button className="btn btn-secondary text-xs" style={{ padding: '4px 8px' }} onClick={() => { toast.success(`Manual sync handshake triggered for ${sync.source}`); }}>Force Sync</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
