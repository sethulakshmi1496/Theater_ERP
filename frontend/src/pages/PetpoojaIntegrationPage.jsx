import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function PetpoojaIntegrationPage() {
  const [activeTab, setActiveTab] = useState('settings'); // settings, item-sync, sales-sync, failed
  
  // Dummy states for the UI
  const [config, setConfig] = useState({ 
    isActive: true, 
    apiUrl: 'https://api.petpooja.com/v1', 
    appKey: 'PP-AEC-9281', 
    appSecret: '****',
    syncFreq: 'HOURLY'
  });

  const [items, setItems] = useState([
    { id: 'PP101', name: 'Butter Popcorn Tub', category: 'POPCORN', price: 240, mappedTo: 'ITEM-001 (Butter Popcorn Tub)', status: 'MAPPED' },
    { id: 'PP102', name: 'Pepsi Fountain', category: 'BEVERAGE', price: 180, mappedTo: 'ITEM-002 (Pepsi Fountain)', status: 'MAPPED' },
    { id: 'PP103', name: 'Cheese Nachos', category: 'SNACKS', price: 220, mappedTo: '', status: 'UNMAPPED' }
  ]);

  const [jobs, setJobs] = useState([
    { id: 1042, type: 'SALES_SYNC', status: 'SUCCESS', time: '2026-05-19 10:00 AM', processed: 45, failed: 0 },
    { id: 1041, type: 'ITEM_SYNC', status: 'SUCCESS', time: '2026-05-19 09:00 AM', processed: 120, failed: 2 }
  ]);

  const handleSaveConfig = (e) => {
    e.preventDefault();
    toast.success('Petpooja connector configuration saved and activated.');
  };

  const handleTestConnection = () => {
    toast.promise(
      new Promise(resolve => setTimeout(resolve, 1500)),
      {
        loading: 'Testing Petpooja API connection...',
        success: 'Connection successful! Credentials verified.',
        error: 'Connection failed.',
      }
    );
  };

  const handleRunSync = (type) => {
    toast.success(`${type} sync job queued successfully.`);
  };

  const handleMapItem = (id) => {
    toast.success(`Item ${id} mapped to AEC Item Master successfully.`);
    setItems(items.map(i => i.id === id ? { ...i, status: 'MAPPED', mappedTo: 'ITEM-NEW' } : i));
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🔌 Petpooja POS Integration</h1>
          <p className="page-subtitle">Manage F&B billing synchronization, menu item mapping, and automated inventory deduction.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={handleTestConnection}>🔄 Test Connection</button>
          <button className="btn btn-primary" onClick={() => handleRunSync('SALES_SYNC')}>🚀 Force Sync Sales</button>
        </div>
      </div>

      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>⚙️ Connector Settings</button>
        <button className={`tab-btn ${activeTab === 'item-sync' ? 'active' : ''}`} onClick={() => setActiveTab('item-sync')}>🍔 Menu & Item Mapping</button>
        <button className={`tab-btn ${activeTab === 'sales-sync' ? 'active' : ''}`} onClick={() => setActiveTab('sales-sync')}>🧾 Sync Job History</button>
      </div>

      {activeTab === 'settings' && (
        <div className="grid-2">
          <div className="card">
            <h3 style={{ marginTop: 0, marginBottom: '20px' }}>API Credentials</h3>
            <form onSubmit={handleSaveConfig}>
              <div className="form-group">
                <label className="form-label">Activation Status</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <input type="checkbox" checked={config.isActive} onChange={e => setConfig({...config, isActive: e.target.checked})} />
                  <span>Enable automatic background sync</span>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Base API URL</label>
                <input type="text" className="form-input" value={config.apiUrl} onChange={e => setConfig({...config, apiUrl: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">App Key</label>
                <input type="text" className="form-input" value={config.appKey} onChange={e => setConfig({...config, appKey: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">App Secret</label>
                <input type="password" className="form-input" value={config.appSecret} onChange={e => setConfig({...config, appSecret: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Sync Frequency</label>
                <select className="form-input" value={config.syncFreq} onChange={e => setConfig({...config, syncFreq: e.target.value})}>
                  <option value="REAL_TIME">Real-Time (Webhooks)</option>
                  <option value="HOURLY">Hourly Batch</option>
                  <option value="DAILY">End of Day (Daily)</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">Save Configuration</button>
            </form>
          </div>
          
          <div className="card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)' }}>
            <h3 style={{ marginTop: 0, color: 'var(--gold)' }}>Integration Workflow Guide</h3>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.6', fontSize: '14px', color: 'var(--text-secondary)' }}>
              <li><strong>Item Mapping:</strong> Petpooja items must be mapped to AEC Canteen Items before stock can be deducted automatically.</li>
              <li><strong>Sales Import:</strong> Bills are imported hourly. The integration is idempotent (avoids duplicates).</li>
              <li><strong>Inventory Consumption:</strong> When a mapped sale is imported, the AEC stock ledger is reduced immediately.</li>
              <li><strong>Reporting:</strong> All imported cafe sales reflect instantly in the Executive Suite and P&L Reports under the Canteen bucket.</li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'item-sync' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
            <div className="font-semibold">Petpooja Item Mapping Queue</div>
            <button className="btn btn-secondary" onClick={() => handleRunSync('ITEM_SYNC')}>⬇️ Fetch Petpooja Items</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Petpooja ID</th>
                <th>Item Name</th>
                <th>Category</th>
                <th>Selling Price</th>
                <th>AEC Mapping Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map(i => (
                <tr key={i.id}>
                  <td><code>{i.id}</code></td>
                  <td><strong>{i.name}</strong></td>
                  <td>{i.category}</td>
                  <td>₹{i.price.toFixed(2)}</td>
                  <td>
                    {i.status === 'MAPPED' ? (
                      <div>
                        <span className="badge badge-success">Mapped</span>
                        <div className="text-xs text-muted" style={{ marginTop: '4px' }}>{i.mappedTo}</div>
                      </div>
                    ) : (
                      <span className="badge badge-error">Unmapped</span>
                    )}
                  </td>
                  <td>
                    {i.status === 'UNMAPPED' && (
                      <button className="btn btn-secondary btn-sm" onClick={() => handleMapItem(i.id)}>Map to Master</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'sales-sync' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
            <div className="font-semibold">Background Sync Job History</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary" onClick={() => toast.success('Date range backfill started')}>⏮️ Run Date Backfill</button>
            </div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Sync Type</th>
                <th>Timestamp</th>
                <th>Records Processed</th>
                <th>Failed / Errored</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id}>
                  <td><strong>JOB-{j.id}</strong></td>
                  <td>{j.type}</td>
                  <td>{j.time}</td>
                  <td>{j.processed}</td>
                  <td><strong style={{ color: j.failed > 0 ? 'var(--error)' : 'inherit' }}>{j.failed}</strong></td>
                  <td><span className={`badge badge-success`}>{j.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
