import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { revenueAPI, screensAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
const TODAY = format(new Date(), 'yyyy-MM-dd');
export default function AdvertisingPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ show: '', slot_type: 'PRE_SHOW', advertiser_name: '', duration_seconds: 30, amount: '', invoice_number: '' });
  const { data, isLoading } = useQuery({ queryKey: ['ad-slots'], queryFn: () => revenueAPI.adSlots().then(r => r.data) });
  const { data: shows } = useQuery({ queryKey: ['shows'], queryFn: () => screensAPI.shows().then(r => r.data) });
  const mutation = useMutation({
    mutationFn: d => revenueAPI.createAdSlot(d),
    onSuccess: () => { qc.invalidateQueries(['ad-slots']); toast.success('Ad slot recorded!'); setShowForm(false); },
    onError: () => toast.error('Failed'),
  });
  const records = data?.results || data || [];
  const showList = shows?.results || shows || [];
  return (
    <div>
      <div className="page-header">
        <div><h1 className="page-title">📺 On-Screen Advertising</h1><p className="page-subtitle">Pre-show and Interval ad slot revenue tracking</p></div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Ad Slot</button>
      </div>
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">📺 Record Ad Slot</div>
            <form onSubmit={e => { e.preventDefault(); mutation.mutate(form); }}>
              <div className="form-group"><label className="form-label">Show</label>
                <select className="form-select" value={form.show} onChange={e => setForm(p => ({ ...p, show: e.target.value }))} required>
                  <option value="">Select Show</option>
                  {showList.map(s => <option key={s.id} value={s.id}>{s.movie_title} · {s.show_date} · {s.screen_name}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Slot Type</label>
                <select className="form-select" value={form.slot_type} onChange={e => setForm(p => ({ ...p, slot_type: e.target.value }))}>
                  <option value="PRE_SHOW">Pre-Show</option>
                  <option value="INTERVAL">Interval</option>
                </select>
              </div>
              <div className="form-group"><label className="form-label">Advertiser Name</label><input className="form-input" value={form.advertiser_name} onChange={e => setForm(p => ({ ...p, advertiser_name: e.target.value }))} required /></div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Duration (sec)</label><input type="number" className="form-input" value={form.duration_seconds} onChange={e => setForm(p => ({ ...p, duration_seconds: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Amount (₹)</label><input type="number" step="0.01" className="form-input" value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Invoice #</label><input className="form-input" value={form.invoice_number} onChange={e => setForm(p => ({ ...p, invoice_number: e.target.value }))} /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead><tr><th>Show</th><th>Slot</th><th>Advertiser</th><th>Duration</th><th>Amount</th><th>Invoice</th></tr></thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="loading-cell">Loading...</td></tr>}
            {!isLoading && records.length === 0 && <tr><td colSpan={6} className="loading-cell">No ad slots recorded.</td></tr>}
            {records.map(r => (
              <tr key={r.id}>
                <td className="text-sm">{r.show_info}</td>
                <td><span className={`badge ${r.slot_type === 'PRE_SHOW' ? 'badge-info' : 'badge-warning'}`}>{r.slot_type.replace('_', ' ')}</span></td>
                <td><strong>{r.advertiser_name}</strong></td>
                <td>{r.duration_seconds}s</td>
                <td><strong style={{ color: 'var(--success)' }}>₹{parseFloat(r.amount).toLocaleString('en-IN')}</strong></td>
                <td className="text-muted">{r.invoice_number || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
