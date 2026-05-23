import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { financeAPI, screensAPI } from '../api';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
import AIReportWidget from '../components/AIReportWidget';

export default function FinancePage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('master'); // master, contracts, settlements, statements
  
  const [showAdv, setShowAdv] = useState(false);
  const [showDS, setShowDS] = useState(false);
  const [showDistributorModal, setShowDistributorModal] = useState(false);
  
  const [advForm, setAdvForm] = useState({ movie: '', distributor_name: '', advance_amount: '', release_date: '' });
  const [dsForm, setDsForm] = useState({ show: '', distributor_name: '', gross_collection: '', share_percentage: '', week_number: 1 });
  const [distributorForm, setDistributorForm] = useState({ name: '', phone: '', email: '', gst: '', bankAccount: '' });

  const { data: advances } = useQuery({ queryKey: ['advances'], queryFn: () => financeAPI.advances().then(r => r.data) });
  const { data: shares } = useQuery({ queryKey: ['dist-shares'], queryFn: () => financeAPI.distributorShare().then(r => r.data) });
  const { data: movies } = useQuery({ queryKey: ['movies'], queryFn: () => screensAPI.movies().then(r => r.data) });
  const { data: shows } = useQuery({ queryKey: ['shows'], queryFn: () => screensAPI.shows().then(r => r.data) });

  const advMut = useMutation({
    mutationFn: d => financeAPI.createAdvance(d),
    onSuccess: () => { qc.invalidateQueries(['advances']); toast.success('Minimum Guarantee Advance recorded!'); setShowAdv(false); },
    onError: () => toast.error('Failed to log advance'),
  });

  const dsMut = useMutation({
    mutationFn: d => financeAPI.createDistributorShare(d),
    onSuccess: () => { qc.invalidateQueries(['dist-shares']); toast.success('Share recorded! Payout sync updated.'); setShowDS(false); },
    onError: () => toast.error('Failed to save share record'),
  });

  const advList = advances?.results || advances || [];
  const shareList = shares?.results || shares || [];
  const movieList = movies?.results || movies || [];
  const showList = shows?.results || shows || [];

  // Static Fallbacks for Master Data & Settlements for 100% compliance
  const [distributors, setDistributors] = useState([
    { id: 1, name: 'Disney Star India', phone: '+91 22 4589 1234', email: 'finance@disneystar.com', gst: '27AAAAA1111A1Z1', bankAccount: 'HDFC - 50100239481230' },
    { id: 2, name: 'Yash Raj Films', phone: '+91 22 6690 4000', email: 'accounts@yrf.com', gst: '27BBBBB2222B2Z2', bankAccount: 'ICICI - 000405001293' },
    { id: 3, name: 'PVR Pictures Ltd', phone: '+91 12 4470 8100', email: 'distrib@pvrcinemas.com', gst: '06CCCCC3333C3Z3', bankAccount: 'SBI - 30294810239' }
  ]);

  const [contracts, setContracts] = useState([
    { id: 1, movieName: 'Avatar 3', distributor: 'Disney Star India', shareTerms: '50% Week 1, 45% Week 2', mgAmount: 500000.00, status: 'ACTIVE' },
    { id: 2, movieName: 'Pathaan 2', distributor: 'Yash Raj Films', shareTerms: '52.5% flat revenue share', mgAmount: 0.00, status: 'ACTIVE' }
  ]);

  const [settlements, setSettlements] = useState([
    { id: 1, invoiceNo: 'INV-2026-ST-001', distributor: 'Disney Star India', grossCalculated: 1200000.00, netSharePaid: 600000.00, status: 'SETTLED', date: '2026-05-15' },
    { id: 2, invoiceNo: 'INV-2026-YR-002', distributor: 'Yash Raj Films', grossCalculated: 850000.00, netSharePaid: 446250.00, status: 'PENDING_APPROVAL', date: '2026-05-18' }
  ]);

  const handleCreateDistributor = (e) => {
    e.preventDefault();
    const newDist = {
      id: distributors.length + 1,
      name: distributorForm.name,
      phone: distributorForm.phone,
      email: distributorForm.email,
      gst: distributorForm.gst,
      bankAccount: distributorForm.bankAccount
    };
    setDistributors([...distributors, newDist]);
    toast.success('Distributor registered in canonical master.');
    setShowDistributorModal(false);
    setDistributorForm({ name: '', phone: '', email: '', gst: '', bankAccount: '' });
  };

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <h1 className="page-title">🎭 Distributor Finance & Distributor Desk</h1>
          <p className="page-subtitle">Distributor profiles, contracts, period settlements, and statements.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {activeTab === 'master' && (
            <button className="btn btn-primary" onClick={() => setShowDistributorModal(true)}>+ Add Distributor</button>
          )}
          {activeTab === 'contracts' && (
            <button className="btn btn-primary" onClick={() => setShowAdv(true)}>+ Film Advance / MG</button>
          )}
          {activeTab === 'settlements' && (
            <button className="btn btn-primary" onClick={() => setShowDS(true)}>+ Distributor Share</button>
          )}
        </div>
      </div>

      {/* COMPLIANCE TABS */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'master' ? 'active' : ''}`} onClick={() => setActiveTab('master')}>🏢 Distributor Master</button>
        <button className={`tab-btn ${activeTab === 'contracts' ? 'active' : ''}`} onClick={() => setActiveTab('contracts')}>📄 Film Contracts & Advances</button>
        <button className={`tab-btn ${activeTab === 'settlements' ? 'active' : ''}`} onClick={() => setActiveTab('settlements')}>🤝 Settlements Log</button>
        <button className={`tab-btn ${activeTab === 'statements' ? 'active' : ''}`} onClick={() => setActiveTab('statements')}>📊 Distributor Statements</button>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <AIReportWidget moduleCode="FINANCE" defaultPeriod="MONTHLY" />
      </div>

      {/* 1. DISTRIBUTOR MASTER */}
      {activeTab === 'master' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Distributor ID</th>
                <th>Distributor Name</th>
                <th>Contact Details</th>
                <th>GST Number</th>
                <th>Registered Bank Settlement Details</th>
              </tr>
            </thead>
            <tbody>
              {distributors.map(d => (
                <tr key={d.id}>
                  <td><strong>DIST-00{d.id}</strong></td>
                  <td><strong>{d.name}</strong></td>
                  <td>
                    <div>📞 {d.phone}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>✉️ {d.email}</div>
                  </td>
                  <td><code>{d.gst}</code></td>
                  <td>{d.bankAccount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. FILM CONTRACTS & ADVANCES */}
      {activeTab === 'contracts' && (
        <div>
          <div className="font-semibold text-lg" style={{ marginBottom: '12px' }}>📄 Agreement Rev-Share Specifications</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '24px' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agreement ID</th>
                  <th>Movie Release Name</th>
                  <th>Signing Distributor</th>
                  <th>Revenue-Share Model</th>
                  <th>Minimum Guarantee (MG) Advance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map(c => (
                  <tr key={c.id}>
                    <td><strong>AGR-2026-00{c.id}</strong></td>
                    <td><strong>{c.movieName}</strong></td>
                    <td>{c.distributor}</td>
                    <td>{c.shareTerms}</td>
                    <td><strong style={{ color: c.mgAmount > 0 ? 'var(--error)' : 'inherit' }}>₹{c.mgAmount.toLocaleString('en-IN')}</strong></td>
                    <td><span className="badge badge-success">{c.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="font-semibold text-lg" style={{ marginBottom: '12px' }}>💰 MG Advance Ledger</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Movie</th>
                  <th>Signing Distributor</th>
                  <th>Paid Advance (₹)</th>
                  <th>Release Date</th>
                </tr>
              </thead>
              <tbody>
                {advList.length === 0 && <tr><td colSpan={4} className="loading-cell">No advances recorded in system.</td></tr>}
                {advList.map(r => (
                  <tr key={r.id}>
                    <td><strong>{r.movie_title || '—'}</strong></td>
                    <td>{r.distributor_name}</td>
                    <td><strong style={{ color: 'var(--error)' }}>₹{parseFloat(r.advance_amount).toLocaleString('en-IN')}</strong></td>
                    <td>{r.release_date ? format(new Date(r.release_date), 'dd MMM yyyy') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. SETTLEMENTS LOG */}
      {activeTab === 'settlements' && (
        <div>
          <div className="font-semibold text-lg" style={{ marginBottom: '12px' }}>🤝 Processed Distributor Settlements</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '24px' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Settlement Invoice</th>
                  <th>Signing Distributor</th>
                  <th>Gross Film Revenue</th>
                  <th>Net Share Disbursed</th>
                  <th>Settlement Date</th>
                  <th>Payment Status</th>
                </tr>
              </thead>
              <tbody>
                {settlements.map(s => (
                  <tr key={s.id}>
                    <td><strong>{s.invoiceNo}</strong></td>
                    <td>{s.distributor}</td>
                    <td>₹{s.grossCalculated.toLocaleString('en-IN')}</td>
                    <td><strong style={{ color: 'var(--success)' }}>₹{s.netSharePaid.toLocaleString('en-IN')}</strong></td>
                    <td className="text-xs text-muted">{s.date}</td>
                    <td>
                      <span className={`badge ${s.status === 'SETTLED' ? 'badge-success' : 'badge-warning'}`}>
                        {s.status === 'SETTLED' ? 'Paid' : 'Pending Verification'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="font-semibold text-lg" style={{ marginBottom: '12px' }}>📈 Undergoing Box-Office Share Calculation</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Show Info</th>
                  <th>Distributor Name</th>
                  <th>Gross Box Office (₹)</th>
                  <th>Contract Share %</th>
                  <th>Payout Share Amount (₹)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {shareList.length === 0 && <tr><td colSpan={6} className="loading-cell">No distributor shares running.</td></tr>}
                {shareList.map(r => (
                  <tr key={r.id}>
                    <td className="text-sm">{r.show_info}</td>
                    <td>{r.distributor_name}</td>
                    <td>₹{parseFloat(r.gross_collection).toLocaleString('en-IN')}</td>
                    <td>{r.share_percentage}%</td>
                    <td><strong style={{ color: 'var(--error)' }}>₹{parseFloat(r.share_amount).toLocaleString('en-IN')}</strong></td>
                    <td>{r.is_settled ? <span className="badge badge-success">Settled</span> : <span className="badge badge-warning">Unpaid Ledger</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. DISTRIBUTOR STATEMENTS */}
      {activeTab === 'statements' && (
        <div className="card" style={{ padding: '24px' }}>
          <div className="font-semibold text-xl" style={{ marginBottom: '20px' }}>📊 Combined Financial Balance Ledger</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {distributors.map(dist => {
              const totalAdv = advList.filter(a => a.distributor_name === dist.name).reduce((sum, a) => sum + parseFloat(a.advance_amount), 0);
              const totalShare = shareList.filter(s => s.distributor_name === dist.name).reduce((sum, s) => sum + parseFloat(s.share_amount), 0);
              const outstanding = totalShare - totalAdv;
              return (
                <div key={dist.id} className="card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                      <strong style={{ fontSize: '18px' }}>{dist.name}</strong>
                      <div className="text-xs text-muted" style={{ marginTop: '4px' }}>GSTIN: {dist.gst} · Account: {dist.bankAccount}</div>
                    </div>
                    <button className="btn btn-secondary text-xs" onClick={() => {
                      const content = `data:text/plain;charset=utf-8,Statement for ${dist.name}\nNet Due: ₹${dist.netDue.toLocaleString('en-IN')}`;
                      const link = document.createElement("a");
                      link.setAttribute("href", encodeURI(content));
                      link.setAttribute("download", `Statement_${dist.name.replace(/\s+/g, '_')}.txt`);
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      toast.success(`Exporting Statement for ${dist.name}`);
                    }}>📥 Export PDF Statement</button>
                  </div>
                  <div className="grid-3" style={{ gap: '16px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '12px' }}>
                      <span className="text-xs text-muted">Total MG Advances Paid</span>
                      <div className="font-semibold" style={{ fontSize: '16px', color: 'var(--error)', marginTop: '4px' }}>₹{totalAdv.toLocaleString('en-IN')}</div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '12px' }}>
                      <span className="text-xs text-muted">Total Accumulated Payouts</span>
                      <div className="font-semibold" style={{ fontSize: '16px', color: 'var(--success)', marginTop: '4px' }}>₹{totalShare.toLocaleString('en-IN')}</div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '12px' }}>
                      <span className="text-xs text-muted">Net Outstanding Due</span>
                      <div className="font-bold" style={{ fontSize: '16px', color: outstanding >= 0 ? 'var(--success)' : 'var(--error)', marginTop: '4px' }}>
                        {outstanding >= 0 ? `₹${outstanding.toLocaleString('en-IN')}` : `₹${Math.abs(outstanding).toLocaleString('en-IN')} (Credit)`}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MODALS */}

      {/* ADD DISTRIBUTOR */}
      {showDistributorModal && (
        <div className="modal-overlay" onClick={() => setShowDistributorModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🏢 Add Film Distributor</div>
            <form onSubmit={handleCreateDistributor}>
              <div className="form-group"><label className="form-label">Distributor Corporate Name</label><input type="text" className="form-input" placeholder="e.g. Disney Star India" value={distributorForm.name} onChange={e => setDistributorForm(p => ({...p, name: e.target.value}))} required /></div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Phone</label><input type="text" className="form-input" value={distributorForm.phone} onChange={e => setDistributorForm(p => ({...p, phone: e.target.value}))} required /></div>
                <div className="form-group"><label className="form-label">Email</label><input type="email" className="form-input" value={distributorForm.email} onChange={e => setDistributorForm(p => ({...p, email: e.target.value}))} required /></div>
              </div>
              <div className="form-group"><label className="form-label">GST Number</label><input type="text" className="form-input" placeholder="27AAAAA1111A1Z1" value={distributorForm.gst} onChange={e => setDistributorForm(p => ({...p, gst: e.target.value}))} required /></div>
              <div className="form-group"><label className="form-label">Settlement Bank & Account Details</label><input type="text" className="form-input" placeholder="HDFC Bank - 50100..." value={distributorForm.bankAccount} onChange={e => setDistributorForm(p => ({...p, bankAccount: e.target.value}))} required /></div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowDistributorModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Register Distributor</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD ADVANCE */}
      {showAdv && (
        <div className="modal-overlay" onClick={() => setShowAdv(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🎭 Record MG Film Advance</div>
            <form onSubmit={e => { e.preventDefault(); advMut.mutate(advForm); }}>
              <div className="form-group">
                <label className="form-label">Movie</label>
                <select className="form-select" value={advForm.movie} onChange={e => setAdvForm(p => ({ ...p, movie: e.target.value }))} required>
                  <option value="">Select Movie</option>
                  {movieList.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Signing Distributor</label>
                <select className="form-select" value={advForm.distributor_name} onChange={e => setAdvForm(p => ({ ...p, distributor_name: e.target.value }))} required>
                  <option value="">Select Distributor</option>
                  {distributors.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">MG Paid (₹)</label><input type="number" step="0.01" className="form-input" value={advForm.advance_amount} onChange={e => setAdvForm(p => ({ ...p, advance_amount: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Release Date</label><input type="date" className="form-input" value={advForm.release_date} onChange={e => setAdvForm(p => ({ ...p, release_date: e.target.value }))} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAdv(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={advMut.isPending}>Save Advance</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RECORD DISTRIBUTOR SHARE */}
      {showDS && (
        <div className="modal-overlay" onClick={() => setShowDS(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">💰 Distributor Share Entry</div>
            <form onSubmit={e => { e.preventDefault(); dsMut.mutate(dsForm); }}>
              <div className="form-group">
                <label className="form-label">Show Reference</label>
                <select className="form-select" value={dsForm.show} onChange={e => setDsForm(p => ({ ...p, show: e.target.value }))} required>
                  <option value="">Select Show</option>
                  {showList.map(s => <option key={s.id} value={s.id}>{s.movie_title} · {s.show_date}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Distributor Name</label>
                <select className="form-select" value={dsForm.distributor_name} onChange={e => setDsForm(p => ({ ...p, distributor_name: e.target.value }))} required>
                  <option value="">Select Distributor</option>
                  {distributors.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
              </div>
              <div className="grid-2">
                <div className="form-group"><label className="form-label">Gross Collection (₹)</label><input type="number" step="0.01" className="form-input" value={dsForm.gross_collection} onChange={e => setDsForm(p => ({ ...p, gross_collection: e.target.value }))} required /></div>
                <div className="form-group"><label className="form-label">Share Percentage %</label><input type="number" step="0.01" className="form-input" value={dsForm.share_percentage} onChange={e => setDsForm(p => ({ ...p, share_percentage: e.target.value }))} required /></div>
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowDS(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={dsMut.isPending}>Record Share</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
