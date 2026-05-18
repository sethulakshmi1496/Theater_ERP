import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { screensAPI } from '../api';
import toast from 'react-hot-toast';
import api from '../api/client';

export default function ScreenBuilderPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: screens, isLoading } = useQuery({ queryKey: ['screens'], queryFn: () => screensAPI.list().then(r => r.data) });
  
  const [editingPrice, setEditingPrice] = useState({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [newScreenName, setNewScreenName] = useState('');
  const [newScreenType, setNewScreenType] = useState('2D');
  
  const [selectedConfigScreen, setSelectedConfigScreen] = useState(null);
  const [configCategories, setConfigCategories] = useState([]);

  const deleteScreenMutation = useMutation({
    mutationFn: (id) => screensAPI.delete(id),
    onSuccess: () => {
      qc.invalidateQueries(['screens']);
      toast.success('Screen deleted successfully');
    },
    onError: (e) => toast.error('Cannot delete screen, existing data might depend on it.')
  });

  const createScreenMutation = useMutation({
    mutationFn: (data) => screensAPI.create(data),
    onSuccess: () => {
      qc.invalidateQueries(['screens']);
      toast.success('New screen created!');
      setShowAddModal(false);
      setNewScreenName('');
    },
    onError: () => toast.error('Failed to create screen')
  });

  const updatePriceMutation = useMutation({
    mutationFn: ({ id, price }) => api.patch(`/screens/categories/${id}/`, { price }),
    onSuccess: () => {
      qc.invalidateQueries(['screens']);
      toast.success('Price version updated successfully! Old bookings remain untouched.');
    },
    onError: (e) => toast.error('Failed to update price')
  });

  const configureSeatsMutation = useMutation({
    mutationFn: ({ id, categories }) => screensAPI.configureSeats(id, { categories }),
    onSuccess: (res) => {
      qc.invalidateQueries(['screens']);
      toast.success(`Layout configured! Total capacity set to ${res.data.total_seats}`);
      setSelectedConfigScreen(null);
    },
    onError: (e) => toast.error(e.response?.data?.error || 'Failed to configure seats')
  });

  if (isLoading) return <div>Loading Builder...</div>;

  const screenList = Array.isArray(screens) ? screens : (screens?.results || []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🏗️ Screen Builder & Dynamic Pricing</h1>
          <p className="page-subtitle">Add screens, configure capacity, and manage dynamic price versioning.</p>
        </div>
      </div>

      <div className="grid-2">
        {screenList.map(screen => (
          <div key={screen.id} className="card" style={{ position: 'relative', cursor: 'pointer', transition: 'transform 0.2s', ':hover': { transform: 'translateY(-2px)' } }} onClick={() => navigate(`/builder/screen/${screen.id}`)}>
            <div className="flex-between" style={{ marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
              <div className="flex gap-8" style={{ alignItems: 'center' }}>
                <h2 className="font-semibold" style={{ fontSize: '18px' }}>{screen.name}</h2>
                <div className="badge badge-info">{screen.total_seats} Seats</div>
                <div className="badge badge-neutral" style={{ fontSize: '11px' }}>{screen.screen_type || '2D'}</div>
              </div>
              <button 
                className="btn btn-secondary btn-sm" 
                style={{ color: 'var(--error)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(`Are you sure you want to delete ${screen.name}?`)) {
                    deleteScreenMutation.mutate(screen.id);
                  }
                }}
              >
                🗑️ Delete Screen
              </button>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <h3 className="font-medium text-sm text-muted" style={{ marginBottom: '8px' }}>Active Seat Classes & Pricing</h3>
              <table className="data-table" style={{ fontSize: '14px' }}>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Color</th>
                    <th>Current Rate</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {screen.categories?.map(cat => (
                    <tr key={cat.id} onClick={(e) => e.stopPropagation()}>
                      <td><strong>{cat.name}</strong></td>
                      <td>
                        <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: cat.color_code }} />
                      </td>
                      <td>
                        {editingPrice[cat.id] !== undefined ? (
                          <input 
                            type="number" 
                            className="form-input" 
                            style={{ width: '80px', padding: '4px' }} 
                            value={editingPrice[cat.id]} 
                            onChange={e => setEditingPrice(p => ({ ...p, [cat.id]: e.target.value }))} 
                            onClick={e => e.stopPropagation()}
                          />
                        ) : (
                          <span style={{ color: 'var(--success)', fontWeight: 600 }}>₹{cat.price}</span>
                        )}
                      </td>
                      <td>
                        {editingPrice[cat.id] !== undefined ? (
                          <div className="flex gap-4">
                            <button className="btn btn-success btn-sm" onClick={(e) => {
                              e.stopPropagation();
                              updatePriceMutation.mutate({ id: cat.id, price: editingPrice[cat.id] });
                              setEditingPrice(p => { const n = {...p}; delete n[cat.id]; return n; });
                            }}>Save</button>
                            <button className="btn btn-secondary btn-sm" onClick={(e) => {
                              e.stopPropagation();
                              setEditingPrice(p => { const n = {...p}; delete n[cat.id]; return n; });
                            }}>X</button>
                          </div>
                        ) : (
                          <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); setEditingPrice(p => ({ ...p, [cat.id]: cat.price })); }}>
                            Update Price
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {(!screen.categories || screen.categories.length === 0) && (
                    <tr><td colSpan={4} className="text-center text-muted">No classes configured</td></tr>
                  )}
                </tbody>
              </table>
              <div className="text-xs text-muted" style={{ marginTop: '8px', fontStyle: 'italic' }}>
                * Updating a price creates a new Price Version. P&L reports for past dates will use the historical rates.
              </div>
            </div>

            <div className="flex gap-8" style={{ marginTop: '24px' }}>
              <button 
                className="btn btn-primary" 
                style={{ flex: 1 }} 
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedConfigScreen(screen);
                  setConfigCategories(
                    screen.categories && screen.categories.length > 0 
                      ? screen.categories.map(c => ({ name: c.name, price: c.price, color: c.color_code, seat_count: 50 }))
                      : [
                          { name: 'Platinum', price: 250, color: '#E5E4E2', seat_count: 100 },
                          { name: 'Gold', price: 180, color: '#FFD700', seat_count: 100 },
                          { name: 'Silver', price: 150, color: '#C0C0C0', seat_count: 100 }
                        ]
                  );
                }}
              >
                Configure Seat Layout
              </button>
            </div>
          </div>
        ))}
        
        <div className="card flex-center" style={{ borderStyle: 'dashed', cursor: 'pointer', background: 'transparent' }} onClick={() => setShowAddModal(true)}>
          <div className="text-center text-muted">
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>+</div>
            <div className="font-semibold">Add New Screen</div>
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h2>Add New Screen</h2>
              <button className="btn-close" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label className="form-label">Screen Name (e.g. Screen 3)</label>
              <input
                type="text"
                className="form-input"
                value={newScreenName}
                onChange={(e) => setNewScreenName(e.target.value)}
                placeholder="Screen Name"
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label className="form-label">Screen Type</label>
              <select className="form-select" value={newScreenType} onChange={e => setNewScreenType(e.target.value)}>
                {['2D', '3D', 'IMAX', '4DX', 'OTHER'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
              <button 
                className="btn btn-primary" 
                disabled={!newScreenName.trim() || createScreenMutation.isPending}
                onClick={() => createScreenMutation.mutate({ name: newScreenName, screen_type: newScreenType, total_seats: 0 })}
              >
                {createScreenMutation.isPending ? 'Creating...' : 'Create Screen'}
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedConfigScreen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2>Configure Layout: {selectedConfigScreen.name}</h2>
              <button className="btn-close" onClick={() => setSelectedConfigScreen(null)}>×</button>
            </div>
            <p className="text-sm text-muted" style={{ marginBottom: '16px' }}>
              Define the seating capacity for each class. This will re-generate the entire seating map for this screen.
              <br/><strong className="text-warning">Warning:</strong> If there are existing bookings for future shows on this screen, re-configuring may fail to protect data integrity.
            </p>
            
            <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '16px' }}>
              {configCategories.map((cat, idx) => (
                <div key={idx} className="flex gap-8" style={{ marginBottom: '12px', alignItems: 'center' }}>
                  <input type="text" className="form-input" placeholder="Class (e.g. Platinum)" value={cat.name} onChange={e => {
                    const newCats = [...configCategories]; newCats[idx].name = e.target.value; setConfigCategories(newCats);
                  }} style={{ flex: 2 }} />
                  
                  <input type="number" className="form-input" placeholder="₹ Price" value={cat.price} onChange={e => {
                    const newCats = [...configCategories]; newCats[idx].price = e.target.value; setConfigCategories(newCats);
                  }} style={{ flex: 1 }} />
                  
                  <input type="number" className="form-input" placeholder="Total Seats" value={cat.seat_count} onChange={e => {
                    const newCats = [...configCategories]; newCats[idx].seat_count = e.target.value; setConfigCategories(newCats);
                  }} style={{ flex: 1 }} />

                  <input type="color" value={cat.color} onChange={e => {
                    const newCats = [...configCategories]; newCats[idx].color = e.target.value; setConfigCategories(newCats);
                  }} style={{ width: '40px', height: '40px', padding: '0', border: 'none', background: 'transparent', cursor: 'pointer' }} />
                  
                  <button className="btn btn-secondary btn-sm" onClick={() => {
                    const newCats = [...configCategories]; newCats.splice(idx, 1); setConfigCategories(newCats);
                  }}>🗑️</button>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" onClick={() => setConfigCategories([...configCategories, { name: '', price: 100, color: '#FFFFFF', seat_count: 50 }])}>
                + Add Seat Class
              </button>
            </div>

            <div className="flex gap-12" style={{ justifyContent: 'flex-end', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
                <strong className="text-info">New Capacity: {configCategories.reduce((sum, c) => sum + (parseInt(c.seat_count) || 0), 0)}</strong>
              </div>
              <button className="btn btn-secondary" onClick={() => setSelectedConfigScreen(null)}>Cancel</button>
              <button 
                className="btn btn-primary" 
                disabled={configureSeatsMutation.isPending || configCategories.length === 0}
                onClick={() => configureSeatsMutation.mutate({ id: selectedConfigScreen.id, categories: configCategories })}
              >
                {configureSeatsMutation.isPending ? 'Generating...' : 'Generate Layout'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
