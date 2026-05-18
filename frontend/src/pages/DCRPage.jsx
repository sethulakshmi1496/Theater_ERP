import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

const TODAY = format(new Date(), 'yyyy-MM-dd');

export default function DCRPage() {
  const navigate = useNavigate();
  const [showUpload, setShowUpload] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [selectedDcr, setSelectedDcr] = useState(null);
  const [reviewerNote, setReviewerNote] = useState('');

  // Sample static data for full compliance with fields & workflow
  const [dcrs, setDcrs] = useState([
    {
      id: 1,
      sourceFile: 'dcr_2026_05_18_screen1.pdf',
      uploadTime: '2026-05-18 09:15 AM',
      parserConfidence: 98.5,
      parsedGross: 52000.00,
      parsedOccupancy: 184,
      mismatchFlag: false,
      reviewStatus: 'Approved',
      reviewerNote: 'Data matches ticketing feed exactly.',
      rawArchiveLink: 'https://aec-archives.s3.amazonaws.com/dcr/dcr_2026_05_18_screen1.pdf',
      reprocessCount: 0,
      postingStatus: 'Posted to Film Finance'
    },
    {
      id: 2,
      sourceFile: 'dcr_2026_05_18_screen2.pdf',
      uploadTime: '2026-05-18 09:18 AM',
      parserConfidence: 74.2,
      parsedGross: 18500.00,
      parsedOccupancy: 72,
      mismatchFlag: true,
      reviewStatus: 'Pending Review',
      reviewerNote: '',
      rawArchiveLink: 'https://aec-archives.s3.amazonaws.com/dcr/dcr_2026_05_18_screen2.pdf',
      reprocessCount: 1,
      postingStatus: 'Draft'
    }
  ]);

  const [form, setForm] = useState({ file: null, sharePct: '50.0' });

  const handleUpload = (e) => {
    e.preventDefault();
    const newDcr = {
      id: dcrs.length + 1,
      sourceFile: form.file ? form.file.name : 'dcr_uploaded.pdf',
      uploadTime: format(new Date(), 'yyyy-MM-dd HH:mm a'),
      parserConfidence: 92.0,
      parsedGross: 24000.00,
      parsedOccupancy: 95,
      mismatchFlag: false,
      reviewStatus: 'Pending Review',
      reviewerNote: '',
      rawArchiveLink: 'https://aec-archives.s3.amazonaws.com/dcr/dcr_uploaded.pdf',
      reprocessCount: 0,
      postingStatus: 'Draft'
    };
    setDcrs([newDcr, ...dcrs]);
    toast.success('DCR PDF uploaded and parser confidence evaluated.');
    setShowUpload(false);
  };

  const handleReprocess = (id) => {
    setDcrs(dcrs.map(d => d.id === id ? {
      ...d,
      reprocessCount: d.reprocessCount + 1,
      parserConfidence: 99.1,
      mismatchFlag: false
    } : d));
    toast.success('DCR report re-queued through parser. Match resolved.');
  };

  const handleApproveData = (id) => {
    setDcrs(dcrs.map(d => d.id === id ? { ...d, reviewStatus: 'Approved' } : d));
    toast.success('DCR parsed details approved.');
  };

  const handleOpenReview = (dcr) => {
    setSelectedDcr(dcr);
    setReviewerNote(dcr.reviewerNote);
    setShowReview(true);
  };

  const handleSaveReview = (e) => {
    e.preventDefault();
    setDcrs(dcrs.map(d => d.id === selectedDcr.id ? {
      ...d,
      reviewerNote: reviewerNote,
      reviewStatus: 'Under Review'
    } : d));
    toast.success('Review note attached to DCR record.');
    setShowReview(false);
  };

  const handlePushToFinance = (id) => {
    setDcrs(dcrs.map(d => d.id === id ? { ...d, postingStatus: 'Posted to Film Finance' } : d));
    toast.success('DCR data pushed into Settlements and Film Finance ledgers successfully.');
  };

  const handleArchiveRaw = (link) => {
    toast.success(`DCR raw PDF archived. Download URL: ${link}`);
  };

  return (
    <div>
      {/* PAGE HEADER */}
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">📊 District DCR Audit Desk</h1>
          <p className="page-subtitle">Exhibitor collection report parser, variance check, and settlement dispatch.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>Upload DCR</button>
      </div>

      {/* DCR INTERACTIVE WORKFLOW STEPPER */}
      <div className="card" style={{ marginBottom: '24px', background: 'var(--bg-glass)', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {['1. DCR Received (Upload)', '2. Parsed & Confidence Score Evaluated', '3. Mismatch Flag Review', '4. Approved Output to Settlements'].map((step, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className="badge badge-success" style={{ borderRadius: '50%', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{idx + 1}</span>
              <strong style={{ fontSize: '12px' }}>{step}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* CORE DATA TABLE */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source File</th>
              <th>Upload Time</th>
              <th>Confidence</th>
              <th>Parsed Gross</th>
              <th>Parsed Occupancy</th>
              <th>Mismatch Flag</th>
              <th>Review Status</th>
              <th>Reviewer Note</th>
              <th>Raw Archive</th>
              <th>Reprocess</th>
              <th>Posting Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {dcrs.map(d => (
              <tr key={d.id}>
                <td><strong>{d.sourceFile}</strong></td>
                <td>{d.uploadTime}</td>
                <td>
                  <span className={`badge ${d.parserConfidence > 90 ? 'badge-success' : 'badge-error'}`}>
                    {d.parserConfidence}%
                  </span>
                </td>
                <td>₹{d.parsedGross.toLocaleString('en-IN')}</td>
                <td>{d.parsedOccupancy} tickets</td>
                <td>
                  {d.mismatchFlag ? (
                    <span className="badge badge-error" onClick={() => handleOpenReview(d)} style={{ cursor: 'pointer' }}>⚠️ MISMATCH</span>
                  ) : (
                    <span className="badge badge-success">MATCH OK</span>
                  )}
                </td>
                <td>
                  <span className={`badge ${d.reviewStatus === 'Approved' ? 'badge-success' : 'badge-warning'}`}>
                    {d.reviewStatus}
                  </span>
                </td>
                <td className="text-xs text-muted" style={{ maxWidth: '150px' }}>{d.reviewerNote || '—'}</td>
                <td>
                  <button className="btn btn-secondary btn-xs" onClick={() => handleArchiveRaw(d.rawArchiveLink)}>🔗 Link</button>
                </td>
                <td>
                  <button className="btn btn-secondary btn-xs" onClick={() => handleReprocess(d.id)}>
                    🔄 Retry ({d.reprocessCount})
                  </button>
                </td>
                <td>
                  <span className={`badge ${d.postingStatus.includes('Posted') ? 'badge-success' : 'badge-neutral'}`}>
                    {d.postingStatus}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {d.reviewStatus !== 'Approved' && (
                      <button className="btn btn-success btn-xs" onClick={() => handleApproveData(d.id)}>Approve</button>
                    )}
                    {d.reviewStatus === 'Approved' && d.postingStatus !== 'Posted to Film Finance' && (
                      <button className="btn btn-primary btn-xs" onClick={() => handlePushToFinance(d.id)}>Push Finance</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* MODALS */}

      {/* UPLOAD DCR */}
      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">📄 Upload Daily Collection Report PDF</div>
            <form onSubmit={handleUpload}>
              <div className="form-group">
                <label className="form-label">DCR PDF Attachment</label>
                <input type="file" className="form-input" onChange={e => setForm({...form, file: e.target.files[0]})} required />
              </div>
              <div className="form-group">
                <label className="form-label">Exhibitor Split (Share %)</label>
                <input type="number" className="form-input" value={form.sharePct} onChange={e => setForm({...form, sharePct: e.target.value})} required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUpload(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">✅ Parse File</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REVIEW NOTE MODAL */}
      {showReview && (
        <div className="modal-overlay" onClick={() => setShowReview(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">⚠️ Review Discrepancy Note</div>
            <form onSubmit={handleSaveReview}>
              <div className="form-group">
                <label className="form-label">Variance Remarks</label>
                <textarea className="form-input" rows="3" value={reviewerNote} onChange={e => setReviewerNote(e.target.value)} required />
              </div>
              <div className="flex gap-12" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowReview(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Note</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REDIRECTIONS LINKS SECTION */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="font-semibold mb-3 text-sm" style={{ color: 'var(--gold)' }}>🔗 Redirection Desk</div>
        <div className="flex gap-12">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/finance')}>🤝 Settlements</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/audit')}>🛡️ Audit Shield</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard')}>🚨 Alert Center</button>
        </div>
      </div>
    </div>
  );
}
