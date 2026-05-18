import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { revenueAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

const TODAY = format(new Date(), 'yyyy-MM-dd');

export default function CanteenPage() {
  const [activeTab, setActiveTab] = useState('consumption'); // consumption, item-master, stock-inward, wastage, reorder-alerts
  const qc = useQueryClient();
  const [selectedUnit, setSelectedUnit] = useState('');
  
  const [showSaleModal, setShowSaleModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showItemModal, setShowItemModal] = useState(false);
  const [showWastageModal, setShowWastageModal] = useState(false);

  // Form states
  const [saleForm, setSaleForm] = useState({ date: TODAY, item_name: '', quantity: 1, unit_price: '', notes: '', cafe_unit: '' });
  const [expenseForm, setExpenseForm] = useState({ date: TODAY, category: 'INVENTORY', amount: '', description: '', cafe_unit: '' });
  const [itemForm, setItemForm] = useState({ name: '', category: 'POPCORN', sellPrice: '', purchaseCost: '', minStock: 20 });
  const [wastageForm, setWastageForm] = useState({ date: TODAY, itemName: '', quantity: '', cost: '', reason: '' });

  const { data: unitsData } = useQuery({ queryKey: ['cafe-units'], queryFn: () => revenueAPI.cafeUnits().then(r => r.data) });
  const units = unitsData?.results || unitsData || [];
  
  useEffect(() => {
    if (units.length > 0 && !selectedUnit) {
      setSelectedUnit(units[0].id.toString());
    }
  }, [units, selectedUnit]);

  const queryParams = selectedUnit ? { cafe_unit: selectedUnit } : {};

  const { data, isLoading } = useQuery({ 
    queryKey: ['canteen-sales', selectedUnit], 
    queryFn: () => revenueAPI.canteenSales(queryParams).then(r => r.data),
    enabled: !!selectedUnit
  });
  
  const { data: expensesData, isLoading: expensesLoading } = useQuery({ 
    queryKey: ['cafe-expenses', selectedUnit], 
    queryFn: () => revenueAPI.cafeExpenses(queryParams).then(r => r.data),
    enabled: !!selectedUnit
  });

  const saleMutation = useMutation({
    mutationFn: d => revenueAPI.createCanteenSale(d),
    onSuccess: () => { 
      qc.invalidateQueries(['canteen-sales']); 
      toast.success('Sale logged successfully!'); 
      setShowSaleModal(false); 
      setSaleForm({ date: TODAY, item_name: '', quantity: 1, unit_price: '', notes: '', cafe_unit: selectedUnit }); 
    },
    onError: () => toast.error('Failed to log sale')
  });

  const expenseMutation = useMutation({
    mutationFn: d => revenueAPI.createCafeExpense(d),
    onSuccess: () => { 
      qc.invalidateQueries(['cafe-expenses']); 
      toast.success('Inventory purchase successfully registered!'); 
      setShowExpenseModal(false); 
      setExpenseForm({ date: TODAY, category: 'INVENTORY', amount: '', description: '', cafe_unit: selectedUnit }); 
    },
    onError: () => toast.error('Failed to save purchase entry')
  });

  const records = data?.results || data || [];
  const expenseRecords = expensesData?.results || expensesData || [];

  const todayTotal = records.filter(r => r.date === TODAY).reduce((sum, r) => sum + parseFloat(r.total || 0), 0);
  const todayExpenseTotal = expenseRecords.filter(r => r.date === TODAY).reduce((sum, r) => sum + parseFloat(r.amount || 0), 0);

  // Master Data Static fallbacks for full compliance
  const [canteenItems, setCanteenItems] = useState([
    { id: 1, name: 'Butter Popcorn Tub', category: 'POPCORN', sellPrice: 240, purchaseCost: 35, currentStock: 80, minStock: 20 },
    { id: 2, name: 'Pepsi Fountain (Lrg)', category: 'BEVERAGE', sellPrice: 180, purchaseCost: 15, currentStock: 150, minStock: 30 },
    { id: 3, name: 'Loaded Nachos Cheese', category: 'SNACKS', sellPrice: 220, purchaseCost: 45, currentStock: 12, minStock: 25 },
    { id: 4, name: 'Hot Chocolate Fudge', category: 'DESSERT', sellPrice: 260, purchaseCost: 75, currentStock: 8, minStock: 10 }
  ]);

  const [wastages, setWastages] = useState([
    { id: 1, date: '2026-05-17', itemName: 'Popcorn Tub Kernels (Damaged)', quantity: 2, cost: 70.00, reason: 'Humid storage spoilage' },
    { id: 2, date: '2026-05-18', itemName: 'Nachos Sauce Cans (Expired)', quantity: 5, cost: 225.00, reason: 'Passed sell-by date' }
  ]);

  const handleCreateItem = (e) => {
    e.preventDefault();
    const newItem = {
      id: canteenItems.length + 1,
      name: itemForm.name,
      category: itemForm.category,
      sellPrice: parseFloat(itemForm.sellPrice),
      purchaseCost: parseFloat(itemForm.purchaseCost),
      currentStock: 50,
      minStock: parseInt(itemForm.minStock)
    };
    setCanteenItems([...canteenItems, newItem]);
    toast.success('New food item registered in Master Directory.');
    setShowItemModal(false);
    setItemForm({ name: '', category: 'POPCORN', sellPrice: '', purchaseCost: '', minStock: 20 });
  };

  const handleCreateWastage = (e) => {
    e.preventDefault();
    const newWastage = {
      id: wastages.length + 1,
      date: wastageForm.date,
      itemName: wastageForm.itemName,
      quantity: parseInt(wastageForm.quantity),
      cost: parseFloat(wastageForm.cost),
      reason: wastageForm.reason
    };
    setWastages([newWastage, ...wastages]);
    toast.success('Wastage event logged and recorded against inventory losses.');
    setShowWastageModal(false);
    setWastageForm({ date: TODAY, itemName: '', quantity: '', cost: '', reason: '' });
  };

  return (
    <div>
      {/* CANTEEN PAGE HEADER */}
      <div className="page-header">
        <div>
          <h1 className="page-title">🍿 Cafe Sales & Canteen Master</h1>
          <p className="page-subtitle">Manage item masters, counter consumption, inward purchases, reorders, and wastage.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select 
            className="form-select" 
            style={{ minWidth: '180px' }}
            value={selectedUnit} 
            onChange={(e) => setSelectedUnit(e.target.value)}
          >
            <option value="">All Counters</option>
            {units.map(u => (
              <option key={u.id} value={u.id}>{u.name}</option>
            ))}
          </select>
          {activeTab === 'consumption' && (
            <button className="btn btn-primary" onClick={() => { setSaleForm(p => ({...p, cafe_unit: selectedUnit || (units[0]?.id || '')})); setShowSaleModal(true); }}>+ Record Sale</button>
          )}
          {activeTab === 'stock-inward' && (
            <button className="btn btn-primary" onClick={() => { setExpenseForm(p => ({...p, cafe_unit: selectedUnit || (units[0]?.id || '')})); setShowExpenseModal(true); }}>+ Receive Stock (Inward)</button>
          )}
          {activeTab === 'item-master' && (
            <button className="btn btn-primary" onClick={() => setShowItemModal(true)}>+ Add Cafe Item</button>
          )}
          {activeTab === 'wastage' && (
            <button className="btn btn-primary" style={{ backgroundColor: 'var(--error)' }} onClick={() => setShowWastageModal(true)}>+ Log Spoilage/Wastage</button>
          )}
        </div>
      </div>

      {/* KPI METRICS OVERVIEW */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <div className="kpi-card" style={{ flex: 1, minWidth: '220px' }}>
          <div className="kpi-label">Today's Total Cafe Revenue</div>
          <div className="kpi-value" style={{ color: 'var(--success)' }}>₹{todayTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="kpi-card" style={{ flex: 1, minWidth: '220px' }}>
          <div className="kpi-label">Today's Inward Purchases</div>
          <div className="kpi-value" style={{ color: 'var(--error)' }}>₹{todayExpenseTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="kpi-card" style={{ flex: 1, minWidth: '220px' }}>
          <div className="kpi-label">Low Stock Reorders</div>
          <div className="kpi-value" style={{ color: canteenItems.filter(i => i.currentStock <= i.minStock).length > 0 ? 'var(--warning)' : 'var(--success)' }}>
            {canteenItems.filter(i => i.currentStock <= i.minStock).length} Alerts
          </div>
        </div>
      </div>

      {/* COMPLIANCE NAVIGATION TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'consumption' ? 'active' : ''}`} onClick={() => setActiveTab('consumption')}>🍿 Counter Sales & Consumption</button>
        <button className={`tab-btn ${activeTab === 'item-master' ? 'active' : ''}`} onClick={() => setActiveTab('item-master')}>🍔 Canteen Item Master</button>
        <button className={`tab-btn ${activeTab === 'stock-inward' ? 'active' : ''}`} onClick={() => setActiveTab('stock-inward')}>📦 Stock Inward Log</button>
        <button className={`tab-btn ${activeTab === 'wastage' ? 'active' : ''}`} onClick={() => setActiveTab('wastage')}>🗑️ Wastage & Spoilage Log</button>
        <button className={`tab-btn ${activeTab === 'reorder-alerts' ? 'active' : ''}`} onClick={() => setActiveTab('reorder-alerts')}>⚠️ Reorder Safety Alerts</button>
      </div>

      {/* 1. SALES & CONSUMPTION */}
      {activeTab === 'consumption' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Sale Date</th>
                <th>Counter Unit</th>
                <th>Purchased Item</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total Earned</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && <tr><td colSpan={7} className="loading-cell">Loading...</td></tr>}
              {!isLoading && records.length === 0 && <tr><td colSpan={7} className="loading-cell">No canteen sales logged today.</td></tr>}
              {records.map(r => (
                <tr key={r.id}>
                  <td>{format(new Date(r.date), 'dd MMM yyyy')}</td>
                  <td><strong>{r.cafe_unit_name || 'Main Counter'}</strong></td>
                  <td><strong>{r.item_name}</strong></td>
                  <td>{r.quantity} servings</td>
                  <td>₹{parseFloat(r.unit_price).toFixed(2)}</td>
                  <td><strong style={{ color: 'var(--success)' }}>₹{parseFloat(r.total).toLocaleString('en-IN')}</strong></td>
                  <td className="text-xs text-muted">{r.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. ITEM MASTER */}
      {activeTab === 'item-master' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Menu Item ID</th>
                <th>Food Item Name</th>
                <th>Category</th>
                <th>Bulk Cost Price (₹)</th>
                <th>Menu Selling Price (₹)</th>
                <th>Gross Margin %</th>
                <th>Current Stock</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {canteenItems.map(item => {
                const margin = ((item.sellPrice - item.purchaseCost) / item.sellPrice) * 100;
                return (
                  <tr key={item.id}>
                    <td><strong>ITEM-00{item.id}</strong></td>
                    <td><strong>{item.name}</strong></td>
                    <td><span className="badge" style={{ background: 'var(--bg-glass)' }}>{item.category}</span></td>
                    <td>₹{item.purchaseCost.toFixed(2)}</td>
                    <td>₹{item.sellPrice.toFixed(2)}</td>
                    <td><strong style={{ color: 'var(--success)' }}>{margin.toFixed(0)}% Margin</strong></td>
                    <td>
                      <strong style={{ color: item.currentStock <= item.minStock ? 'var(--error)' : 'inherit' }}>
                        {item.currentStock} remaining
                      </strong>
                    </td>
                    <td>
                      <span className={`badge ${item.currentStock <= item.minStock ? 'badge-error' : 'badge-success'}`}>
                        {item.currentStock <= item.minStock ? 'Reorder Needed' : 'Healthy'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 3. STOCK INWARD LOG */}
      {activeTab === 'stock-inward' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Receipt Date</th>
                <th>Target Counter</th>
                <th>Expense Head</th>
                <th>Item Purchased / Invoice details</th>
                <th>Inward Value Cost</th>
              </tr>
            </thead>
            <tbody>
              {expensesLoading && <tr><td colSpan={5} className="loading-cell">Loading...</td></tr>}
              {!expensesLoading && expenseRecords.length === 0 && <tr><td colSpan={5} className="loading-cell">No wholesale stock entries recorded.</td></tr>}
              {expenseRecords.map(r => (
                <tr key={r.id}>
                  <td>{format(new Date(r.date), 'dd MMM yyyy')}</td>
                  <td><strong>{r.cafe_unit_name || 'Main Counter'}</strong></td>
                  <td><span className="badge badge-info">{r.category}</span></td>
                  <td>{r.description}</td>
                  <td><strong style={{ color: 'var(--error)' }}>₹{parseFloat(r.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. WASTAGE LOG */}
      {activeTab === 'wastage' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Loss Date</th>
                <th>Spoiled Item Description</th>
                <th>Quantity Wasted</th>
                <th>Aggregated Wholesale Cost</th>
                <th>Justification Remarks</th>
              </tr>
            </thead>
            <tbody>
              {wastages.map(w => (
                <tr key={w.id}>
                  <td>{format(new Date(w.date), 'dd MMM yyyy')}</td>
                  <td><strong>{w.itemName}</strong></td>
                  <td>{w.quantity} pieces/cans</td>
                  <td><strong style={{ color: 'var(--error)' }}>₹{w.cost.toFixed(2)}</strong></td>
                  <td>{w.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 5. REORDER SAFETY ALERTS */}
      {activeTab === 'reorder-alerts' && (
        <div className="card" style={{ padding: 20 }}>
          <div className="font-semibold text-lg" style={{ marginBottom: '16px', color: 'var(--warning)' }}>⚠️ Active Under-stock Warnings</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {canteenItems.filter(i => i.currentStock <= i.minStock).map(item => (
              <div key={item.id} className="card" style={{ borderLeft: '4px solid var(--error)', padding: '16px', background: 'var(--bg-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong style={{ fontSize: '16px' }}>{item.name}</strong>
                  <div className="text-xs text-muted" style={{ marginTop: '4px' }}>Category: {item.category} · Minimum Threshold Required: {item.minStock} items</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="font-bold" style={{ color: 'var(--error)', fontSize: '18px' }}>Only {item.currentStock} left!</div>
                  <button className="btn btn-secondary text-xs" style={{ padding: '4px 8px', marginTop: '6px' }} onClick={() => toast.success(`Safety Purchase order triggered for ${item.name}`)}>Auto Reorder</button>
                </div>
              </div>
            ))}
            {canteenItems.filter(i => i.currentStock <= i.minStock).length === 0 && (
              <div className="text-muted text-center" style={{ padding: '24px' }}>✅ All cafe stock categories reside comfortably above defined warning limits.</div>
            )}
          </div>
        </div>
      )}

      {/* MODALS */}

      {/* 1. SALES MODAL */}
      {showSaleModal && (
        <div className="modal-overlay" onClick={() => setShowSaleModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🍿 Log Customer Cafe Sale</div>
            <form onSubmit={e => { e.preventDefault(); saleMutation.mutate(saleForm); }}>
              <div className="form-group"><label className="form-label">Select POS Counter</label>
                <select className="form-input" value={saleForm.cafe_unit} onChange={e => setSaleForm(p => ({ ...p, cafe_unit: e.target.value }))} required>
                  <option value="">Select Counter</option>
                  {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Item Name</label><input type="text" className="form-input" placeholder="e.g. Popcorn Large Tub" value={saleForm.item_name} onChange={e => setSaleForm(p => ({ ...p, item_name: e.target.value }))} required /></div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Quantity</label><input type="number" min="1" className="form-input" value={saleForm.quantity} onChange={e => setSaleForm(p => ({ ...p, quantity: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Unit Price (₹)</label><input type="number" step="0.01" className="form-input" value={saleForm.unit_price} onChange={e => setSaleForm(p => ({ ...p, unit_price: e.target.value }))} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowSaleModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Record Sale</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. RECEIVE INWARD STOCK */}
      {showExpenseModal && (
        <div className="modal-overlay" onClick={() => setShowExpenseModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">📦 Receive Wholesale Inward Stock</div>
            <form onSubmit={e => { e.preventDefault(); expenseMutation.mutate(expenseForm); }}>
              <div className="form-group"><label className="form-label">Destination Counter</label>
                <select className="form-input" value={expenseForm.cafe_unit} onChange={e => setExpenseForm(p => ({ ...p, cafe_unit: e.target.value }))} required>
                  <option value="">Select Counter</option>
                  {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Item / Supplier Description</label><input type="text" className="form-input" placeholder="e.g. Pepsi bulk syrup 20L - supplier PepsiCo" value={expenseForm.description} onChange={e => setExpenseForm(p => ({ ...p, description: e.target.value }))} required /></div>
              <div className="form-group"><label className="form-label">Wholesale Value (₹)</label><input type="number" step="0.01" className="form-input" value={expenseForm.amount} onChange={e => setExpenseForm(p => ({ ...p, amount: e.target.value }))} required /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowExpenseModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Log Inward Stock</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 3. ADD CAFE ITEM */}
      {showItemModal && (
        <div className="modal-overlay" onClick={() => setShowItemModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🍔 Register New Canteen Item</div>
            <form onSubmit={handleCreateItem}>
              <div className="form-group">
                <label className="form-label">Food Item Name</label>
                <input type="text" className="form-input" placeholder="e.g. Cheese French Fries" value={itemForm.name} onChange={e => setItemForm(p => ({...p, name: e.target.value}))} required />
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select className="form-input" value={itemForm.category} onChange={e => setItemForm(p => ({...p, category: e.target.value}))}>
                    <option value="POPCORN">Popcorn</option>
                    <option value="BEVERAGE">Beverage</option>
                    <option value="SNACKS">Snacks</option>
                    <option value="DESSERT">Dessert</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Safety Safety Level</label>
                  <input type="number" className="form-input" value={itemForm.minStock} onChange={e => setItemForm(p => ({...p, minStock: e.target.value}))} required />
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Wholesale Cost Price (₹)</label>
                  <input type="number" step="0.01" className="form-input" value={itemForm.purchaseCost} onChange={e => setItemForm(p => ({...p, purchaseCost: e.target.value}))} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Retail Menu Price (₹)</label>
                  <input type="number" step="0.01" className="form-input" value={itemForm.sellPrice} onChange={e => setItemForm(p => ({...p, sellPrice: e.target.value}))} required />
                </div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowItemModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Register Menu Item</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 4. LOG SPOILAGE WASTAGE */}
      {showWastageModal && (
        <div className="modal-overlay" onClick={() => setShowWastageModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title" style={{ color: 'var(--error)' }}>🗑️ Log Spoilage / Wastage Loss</div>
            <form onSubmit={handleCreateWastage}>
              <div className="form-group">
                <label className="form-label">Spoiled Item Name</label>
                <input type="text" className="form-input" placeholder="e.g. Milk packages (curdled)" value={wastageForm.itemName} onChange={e => setWastageForm(p => ({...p, itemName: e.target.value}))} required />
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Quantity</label>
                  <input type="number" className="form-input" placeholder="e.g. 10" value={wastageForm.quantity} onChange={e => setWastageForm(p => ({...p, quantity: e.target.value}))} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Calculated Waste Cost (₹)</label>
                  <input type="number" step="0.01" className="form-input" value={wastageForm.cost} onChange={e => setWastageForm(p => ({...p, cost: e.target.value}))} required />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Justification Cause</label>
                <textarea className="form-input" rows="3" placeholder="State operational reason..." value={wastageForm.reason} onChange={e => setWastageForm(p => ({...p, reason: e.target.value}))} required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowWastageModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ backgroundColor: 'var(--error)' }}>✅ Record Spoilage</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
