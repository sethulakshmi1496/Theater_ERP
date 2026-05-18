import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { operationsAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
const TODAY = format(new Date(), 'yyyy-MM-dd');
export default function GeneratorPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ date: TODAY, hours_run: '', consumption: '', diesel_added: '', diesel_rate: '', notes: '' });
  const { data, isLoading } = useQuery({ queryKey: ['generator'], queryFn: () => operationsAPI.generator.list().then(r => r.data) });
  const mutation = useMutation({
    mutationFn: d => operationsAPI.generator.create(d),
    onSuccess: () => { qc.invalidateQueries(['generator']); toast.success('Generator log saved!'); setShowForm(false); setForm({ date: TODAY, hours_run: '', consumption: '', diesel_added: '', diesel_rate: '', notes: '' }); },
    onError: e => toast.error(e.response?.data?.detail || 'Failed'),
  });
  const records = data?.results || data || [];
  const dieselCostPreview = form.diesel_added && form.diesel_rate ? (parseFloat(form.diesel_added) * parseFloat(form.diesel_rate)).toFixed(2) : null;
  return (
    <div>
      <div className="page-header">
        <div><h1 className="page-title">🔋 Generator Log</h1><p className="page-subtitle">Matches GENERATOR READING.xlsx – tracks diesel consumption and costs.</p></div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Log</button>
      </div>
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🔋 New Generator Log</div>
            <form onSubmit={e => { e.preventDefault(); mutation.mutate(form); }}>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Date</label><input type="date" className="form-input" value={form.date} onChange={e => setForm(p => ({ ...p, date: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Hours Run</label><input type="number" step="0.01" className="form-input" placeholder="e.g. 1.50" value={form.hours_run} onChange={e => setForm(p => ({ ...p, hours_run: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Consumption (units)</label><input type="number" step="0.01" className="form-input" value={form.consumption} onChange={e => setForm(p => ({ ...p, consumption: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Diesel Added (Litres)</label><input type="number" step="0.01" className="form-input" placeholder="e.g. 140" value={form.diesel_added} onChange={e => setForm(p => ({ ...p, diesel_added: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Diesel Rate (₹/L)</label><input type="number" step="0.01" className="form-input" value={form.diesel_rate} onChange={e => setForm(p => ({ ...p, diesel_rate: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Diesel Cost (Auto)</label><input type="text" className="form-input" value={dieselCostPreview ? `₹${dieselCostPreview}` : ''} readOnly style={{ opacity: 0.6 }} /></div>
              </div>
              <div className="form-group"><label className="form-label">Notes</label><textarea className="form-textarea" rows="2" value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving...' : '🔋 Save Log'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead><tr><th>Date</th><th>Hours Run</th><th>Consumption</th><th>Diesel (L)</th><th>Rate (₹/L)</th><th>Diesel Cost</th></tr></thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="loading-cell">Loading...</td></tr>}
            {!isLoading && records.length === 0 && <tr><td colSpan={6} className="loading-cell">No generator logs yet.</td></tr>}
            {records.map(r => (
              <tr key={r.id}>
                <td><strong>{format(new Date(r.date), 'dd MMM yyyy')}</strong></td>
                <td>{r.hours_run}h</td>
                <td>{r.consumption}</td>
                <td>{r.diesel_added}L</td>
                <td>₹{r.diesel_rate}</td>
                <td><strong style={{ color: 'var(--warning)' }}>₹{parseFloat(r.diesel_cost).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
