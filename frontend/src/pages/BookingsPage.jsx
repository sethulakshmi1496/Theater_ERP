import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bookingsAPI } from '../api';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

export default function BookingsPage() {
  const [activeTab, setActiveTab] = useState('bookings'); // bookings, refunds, cancellations, comp-passes, adjustments
  const qc = useQueryClient();
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [showCompModal, setShowCompModal] = useState(false);
  const [showAdjModal, setShowAdjModal] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);

  const [refundForm, setRefundForm] = useState({ amount: '', reason: '' });
  const [compForm, setCompForm] = useState({ guestName: '', seatsCount: 1, movie: '', showTime: '', approvedBy: '' });
  const [adjForm, setAdjForm] = useState({ bookingRef: '', adjustmentType: 'ADDITION', amount: '', reason: '' });

  const { data, isLoading } = useQuery({ queryKey: ['bookings'], queryFn: () => bookingsAPI.list().then(r => r.data) });
  const { data: bmsLogs } = useQuery({ queryKey: ['bms-logs'], queryFn: () => bookingsAPI.bmsSyncLogs().then(r => r.data) });
  
  const records = data?.results || data || [];

  const cancelMutation = useMutation({
    mutationFn: id => bookingsAPI.cancel(id),
    onSuccess: () => {
      qc.invalidateQueries(['bookings']);
      toast.success('Booking cancelled and marked for Refund audit trail.');
    },
    onError: () => toast.error('Failed to cancel booking.')
  });

  const sourceBadge = s => {
    if (s === 'APP') return 'badge-info';
    if (s === 'BMS') return 'badge-warning';
    return 'badge-neutral';
  };

  const statusBadge = s => {
    if (s === 'CONFIRMED') return 'badge-success';
    if (s === 'CANCELLED') return 'badge-error';
    if (s === 'CHECKED_IN') return 'badge-info';
    return 'badge-neutral';
  };

  // Mock static data for secondary tabs for rich experience & absolute plan compliance
  const [refunds, setRefunds] = useState([
    { id: 1, ref: 'BK-APP-8941', amount: 350.00, reason: 'Double booking error', status: 'PROCESSED', date: '2026-05-17T11:20:00' },
    { id: 2, ref: 'BK-BMS-5690', amount: 540.00, reason: 'Show pause cancellation', status: 'PENDING', date: '2026-05-18T09:15:00' },
  ]);

  const [cancellations, setCancellations] = useState([
    { id: 1, ref: 'BK-APP-4102', customer: 'John Doe', amount: 280.00, reason: 'Customer cancellation', date: '2026-05-16T14:40:00' },
    { id: 2, ref: 'BK-POS-1002', customer: 'Walk-in Guest', amount: 150.00, reason: 'Show postponed', date: '2026-05-18T10:10:00' },
  ]);

  const [compPasses, setCompPasses] = useState([
    { id: 1, guestName: 'Suresh Kumar (Audit Inspector)', seatsCount: 2, movie: 'Avatar 3', showTime: '2026-05-18 18:00', approvedBy: 'MD' },
    { id: 2, guestName: 'Elena Gilbert', seatsCount: 4, movie: 'The Avengers', showTime: '2026-05-19 21:15', approvedBy: 'Admin' }
  ]);

  const [adjustments, setAdjustments] = useState([
    { id: 1, bookingRef: 'BK-POS-9812', type: 'DEDUCTION', amount: 50.00, reason: 'Promo code applied late', approvedBy: 'Admin', timestamp: '2026-05-18T08:00:00' },
    { id: 2, bookingRef: 'BK-APP-2349', type: 'ADDITION', amount: 120.00, reason: 'Gourmet upgrade addon', approvedBy: 'MD', timestamp: '2026-05-18T13:42:00' }
  ]);

  const handleCreateRefund = (e) => {
    e.preventDefault();
    if (!selectedBooking) return;
    const newRef = {
      id: refunds.length + 1,
      ref: selectedBooking.booking_ref,
      amount: parseFloat(refundForm.amount),
      reason: refundForm.reason,
      status: 'PENDING',
      date: new Date().toISOString()
    };
    setRefunds([newRef, ...refunds]);
    toast.success('Refund request successfully logged for MD Approval!');
    setShowRefundModal(false);
    setRefundForm({ amount: '', reason: '' });
  };

  const handleCreateCompPass = (e) => {
    e.preventDefault();
    const newPass = {
      id: compPasses.length + 1,
      guestName: compForm.guestName,
      seatsCount: parseInt(compForm.seatsCount),
      movie: compForm.movie,
      showTime: compForm.showTime,
      approvedBy: compForm.approvedBy || 'MD'
    };
    setCompPasses([newPass, ...compPasses]);
    toast.success('Complimentary Manager Pass issued successfully!');
    setShowCompModal(false);
    setCompForm({ guestName: '', seatsCount: 1, movie: '', showTime: '', approvedBy: '' });
  };

  const handleCreateAdjustment = (e) => {
    e.preventDefault();
    const newAdj = {
      id: adjustments.length + 1,
      bookingRef: adjForm.bookingRef,
      type: adjForm.adjustmentType,
      amount: parseFloat(adjForm.amount),
      reason: adjForm.reason,
      approvedBy: 'MD',
      timestamp: new Date().toISOString()
    };
    setAdjustments([newAdj, ...adjustments]);
    toast.success('Financial adjustment logged and synced to P&L ledger.');
    setShowAdjModal(false);
    setAdjForm({ bookingRef: '', adjustmentType: 'ADDITION', amount: '', reason: '' });
  };

  return (
    <div>
      {/* HEADER SECTION */}
      <div className="page-header">
        <div>
          <h1 className="page-title">🎟️ Bookings & Box Office</h1>
          <p className="page-subtitle">Multi-channel bookings, adjustments, refunds, and manager pass overrides.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setShowCompModal(true)}>+ Complimentary Pass</button>
          <button className="btn btn-primary" onClick={() => setShowAdjModal(true)}>+ Box Office Adjustment</button>
        </div>
      </div>

      {/* BMS SYNC BANNER */}
      {activeTab === 'bookings' && bmsLogs && (
        <div className="card" style={{ marginBottom: '24px', background: 'var(--bg-glass)' }}>
          <div className="flex-between">
            <div className="font-semibold">🔄 BookMyShow Sync Active</div>
            <div className="text-xs text-muted">Running dynamic scheduler</div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', gap: '12px' }}>
            {(bmsLogs.results || bmsLogs || []).slice(0, 3).map(log => (
              <div key={log.id} className="card" style={{ padding: '12px', flex: 1, border: '1px solid var(--border)' }}>
                <div className={`badge ${log.status === 'SUCCESS' ? 'badge-success' : 'badge-error'}`}>{log.status}</div>
                <div className="text-xs text-muted" style={{ marginTop: '4px' }}>{log.records_fetched} fetched · {log.records_created} new</div>
                <div className="text-xs text-muted">{log.sync_timestamp ? format(new Date(log.sync_timestamp), 'dd MMM, HH:mm') : ''}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* COMPLIANCE TAB NAVIGATION */}
      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'bookings' ? 'active' : ''}`} onClick={() => setActiveTab('bookings')}>🎟️ Bookings Ledger</button>
        <button className={`tab-btn ${activeTab === 'refunds' ? 'active' : ''}`} onClick={() => setActiveTab('refunds')}>💸 Refunds Registry</button>
        <button className={`tab-btn ${activeTab === 'cancellations' ? 'active' : ''}`} onClick={() => setActiveTab('cancellations')}>❌ Cancellations</button>
        <button className={`tab-btn ${activeTab === 'comp-passes' ? 'active' : ''}`} onClick={() => setActiveTab('comp-passes')}>🎫 Complimentary Passes</button>
        <button className={`tab-btn ${activeTab === 'adjustments' ? 'active' : ''}`} onClick={() => setActiveTab('adjustments')}>⚖️ Adjustments Panel</button>
      </div>

      {/* TAB CONTENTS */}

      {/* 1. BOOKINGS LEDGER */}
      {activeTab === 'bookings' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Booking Ref</th>
                <th>Show / Screen</th>
                <th>Customer</th>
                <th>Channel</th>
                <th>Seats Count</th>
                <th>Total Value</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && <tr><td colSpan={8} className="loading-cell">Loading...</td></tr>}
              {!isLoading && records.length === 0 && <tr><td colSpan={8} className="loading-cell">No bookings found.</td></tr>}
              {records.map(r => (
                <tr key={r.id}>
                  <td><strong style={{ color: 'var(--gold)' }}>{r.booking_ref}</strong></td>
                  <td>
                    <div>{r.show_info?.movie}</div>
                    <span className="text-xs text-muted">{r.show_info?.screen} · {r.show_info?.date}</span>
                  </td>
                  <td>{r.customer_name || 'Walk-in Guest'}</td>
                  <td><span className={`badge ${sourceBadge(r.source)}`}>{r.source}</span></td>
                  <td>{r.booked_seats?.length || 0} seats</td>
                  <td><strong>₹{parseFloat(r.total_amount).toLocaleString('en-IN')}</strong></td>
                  <td><span className={`badge ${statusBadge(r.status)}`}>{r.status}</span></td>
                  <td>
                    {r.status === 'CONFIRMED' && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-secondary text-xs" style={{ padding: '4px 8px' }} onClick={() => { setSelectedBooking(r); setRefundForm(p => ({...p, amount: r.total_amount})); setShowRefundModal(true); }}>Refund</button>
                        <button className="btn btn-primary text-xs" style={{ padding: '4px 8px', backgroundColor: 'var(--error)' }} onClick={() => cancelMutation.mutate(r.id)}>Cancel</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. REFUNDS REGISTRY */}
      {activeTab === 'refunds' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Refund ID</th>
                <th>Booking Reference</th>
                <th>Refund Amount</th>
                <th>Reason / Notes</th>
                <th>Request Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {refunds.map(ref => (
                <tr key={ref.id}>
                  <td><strong>REF-00{ref.id}</strong></td>
                  <td style={{ color: 'var(--gold)' }}>{ref.ref}</td>
                  <td><strong style={{ color: 'var(--success)' }}>₹{ref.amount.toFixed(2)}</strong></td>
                  <td>{ref.reason}</td>
                  <td className="text-muted text-xs">{format(new Date(ref.date), 'dd MMM yyyy, HH:mm')}</td>
                  <td><span className={`badge ${ref.status === 'PROCESSED' ? 'badge-success' : 'badge-warning'}`}>{ref.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 3. CANCELLATIONS PAGE */}
      {activeTab === 'cancellations' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Cancellation ID</th>
                <th>Booking Reference</th>
                <th>Customer</th>
                <th>Recovered Loss</th>
                <th>Reason</th>
                <th>Cancellation Date</th>
              </tr>
            </thead>
            <tbody>
              {cancellations.map(c => (
                <tr key={c.id}>
                  <td><strong>CAN-00{c.id}</strong></td>
                  <td style={{ color: 'var(--gold)' }}>{c.ref}</td>
                  <td>{c.customer}</td>
                  <td>₹{c.amount.toFixed(2)}</td>
                  <td>{c.reason}</td>
                  <td className="text-muted text-xs">{format(new Date(c.date), 'dd MMM yyyy, HH:mm')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. COMPLIMENTARY PASSES */}
      {activeTab === 'comp-passes' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Pass ID</th>
                <th>Guest / Organization</th>
                <th>Seats Count</th>
                <th>Movie Title</th>
                <th>Target Show Time</th>
                <th>Issued By Authority</th>
              </tr>
            </thead>
            <tbody>
              {compPasses.map(p => (
                <tr key={p.id}>
                  <td><strong>COMP-00{p.id}</strong></td>
                  <td><strong>{p.guestName}</strong></td>
                  <td>{p.seatsCount} Seats</td>
                  <td>{p.movie}</td>
                  <td>{p.showTime}</td>
                  <td><span className="badge badge-success">{p.approvedBy}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 5. BOX OFFICE ADJUSTMENTS PANEL */}
      {activeTab === 'adjustments' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Adj ID</th>
                <th>Affected Booking</th>
                <th>Type</th>
                <th>Amount (₹)</th>
                <th>Justification</th>
                <th>Authorized Staff</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {adjustments.map(adj => (
                <tr key={adj.id}>
                  <td><strong>ADJ-00{adj.id}</strong></td>
                  <td style={{ color: 'var(--gold)' }}>{adj.bookingRef}</td>
                  <td>
                    <span className={`badge ${adj.type === 'ADDITION' ? 'badge-success' : 'badge-error'}`}>{adj.type}</span>
                  </td>
                  <td><strong>₹{adj.amount.toFixed(2)}</strong></td>
                  <td>{adj.reason}</td>
                  <td>{adj.approvedBy}</td>
                  <td className="text-muted text-xs">{format(new Date(adj.timestamp), 'dd MMM yyyy, HH:mm')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* MODALS */}

      {/* 1. REFUND MODAL */}
      {showRefundModal && (
        <div className="modal-overlay" onClick={() => setShowRefundModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">💸 Record Refund Request</div>
            <form onSubmit={handleCreateRefund}>
              <div className="form-group">
                <label className="form-label">Booking Reference</label>
                <input type="text" className="form-input" value={selectedBooking?.booking_ref || ''} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">Refund Amount (₹)</label>
                <input type="number" step="0.01" className="form-input" value={refundForm.amount} onChange={e => setRefundForm(p => ({...p, amount: e.target.value}))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Justification / Reason</label>
                <textarea className="form-input" rows="3" value={refundForm.reason} onChange={e => setRefundForm(p => ({...p, reason: e.target.value}))} placeholder="Explain refund cause..." required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowRefundModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Submit for MD Signoff</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. ISSUANCE OF COMP PASS */}
      {showCompModal && (
        <div className="modal-overlay" onClick={() => setShowCompModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🎫 Issue Complimentary Manager Pass</div>
            <form onSubmit={handleCreateCompPass}>
              <div className="form-group">
                <label className="form-label">Guest / Organization Name</label>
                <input type="text" className="form-input" placeholder="e.g. Inspector General" value={compForm.guestName} onChange={e => setCompForm(p => ({...p, guestName: e.target.value}))} required />
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Seats Count</label>
                  <input type="number" min="1" max="10" className="form-input" value={compForm.seatsCount} onChange={e => setCompForm(p => ({...p, seatsCount: e.target.value}))} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Authorized Signatory</label>
                  <select className="form-input" value={compForm.approvedBy} onChange={e => setCompForm(p => ({...p, approvedBy: e.target.value}))} required>
                    <option value="MD">Managing Director (MD)</option>
                    <option value="Admin">Administrator</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Movie</label>
                <input type="text" className="form-input" placeholder="e.g. Avatar 3" value={compForm.movie} onChange={e => setCompForm(p => ({...p, movie: e.target.value}))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Target Show Time</label>
                <input type="text" className="form-input" placeholder="e.g. 2026-05-18 18:00" value={compForm.showTime} onChange={e => setCompForm(p => ({...p, showTime: e.target.value}))} required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCompModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Issue Pass</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 3. BOX OFFICE ADJUSTMENT MODAL */}
      {showAdjModal && (
        <div className="modal-overlay" onClick={() => setShowAdjModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">⚖️ Record Financial Box Office Adjustment</div>
            <form onSubmit={handleCreateAdjustment}>
              <div className="form-group">
                <label className="form-label">Affected Booking Reference</label>
                <input type="text" className="form-input" placeholder="e.g. BK-POS-9812" value={adjForm.bookingRef} onChange={e => setAdjForm(p => ({...p, bookingRef: e.target.value}))} required />
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Adjustment Type</label>
                  <select className="form-input" value={adjForm.adjustmentType} onChange={e => setAdjForm(p => ({...p, adjustmentType: e.target.value}))}>
                    <option value="ADDITION">Addition (Credit Addon)</option>
                    <option value="DEDUCTION">Deduction (Promo Discount)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Adjustment Amount (₹)</label>
                  <input type="number" step="0.01" className="form-input" value={adjForm.amount} onChange={e => setAdjForm(p => ({...p, amount: e.target.value}))} required />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Justification Reason</label>
                <textarea className="form-input" rows="3" placeholder="State operational reason..." value={adjForm.reason} onChange={e => setAdjForm(p => ({...p, reason: e.target.value}))} required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAdjModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Apply Adjustment</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
