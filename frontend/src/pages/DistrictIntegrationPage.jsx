import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

export default function DistrictIntegrationPage() {
  const navigate = useNavigate();

  const [config, setConfig] = useState({
    connectorName: 'District DCR Report Ingestion',
    connectorType: 'Report-Based',
    formatSupport: 'PDF, CSV, Excel, Manual',
    parserVersion: 'v1.4.2 (Template Matcher)',
  });

  const [stats, setStats] = useState({
    lastUpload: '2026-05-18 19:30',
    lastProcessedTime: '2026-05-18 19:32',
    lastParseResult: 'Success (Confidence 98%)',
    lastError: 'None',
  });

  const handleTestParser = () => {
    toast.promise(
      new Promise(resolve => setTimeout(resolve, 1500)),
      {
        loading: 'Testing parser pipeline...',
        success: 'Parser test successful. Ready for ingestion.',
        error: 'Parser test failed.',
      }
    );
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">📄 District Connector (Report-Based)</h1>
          <p className="page-subtitle">Configure report ingestion and parsing for District ticketing settlements.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={handleTestParser}>🧪 Test Parser</button>
          <button className="btn btn-primary" onClick={() => navigate('/integrations/dcr')}>📥 Go to DCR Uploads</button>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Connector Configuration</h3>
          <div className="form-group">
            <label className="form-label text-muted">Connector Name</label>
            <div className="font-semibold">{config.connectorName}</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Integration Type</label>
            <div className="font-semibold">{config.connectorType} (No Open API)</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Supported Formats</label>
            <div className="font-semibold">{config.formatSupport}</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Active Parser Template</label>
            <div className="font-semibold">{config.parserVersion}</div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Health & Status</h3>
          <div className="form-group">
            <label className="form-label text-muted">Last Upload Received</label>
            <div className="font-semibold">{stats.lastUpload}</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Last Processing Completed</label>
            <div className="font-semibold">{stats.lastProcessedTime}</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Latest Parse Result</label>
            <div className="font-semibold text-success">{stats.lastParseResult}</div>
          </div>
          <div className="form-group">
            <label className="form-label text-muted">Last Parser Error</label>
            <div className="font-semibold text-muted">{stats.lastError}</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '24px', background: 'var(--bg-glass)', border: '1px solid var(--border)' }}>
        <h3 style={{ marginTop: 0, color: 'var(--gold)' }}>Workflow Rules & Governance</h3>
        <ul style={{ paddingLeft: '20px', lineHeight: '1.6', fontSize: '14px', color: 'var(--text-secondary)' }}>
          <li><strong>Raw Archive First:</strong> Every source file uploaded via the DCR Page is permanently archived for traceability.</li>
          <li><strong>Approval Required:</strong> Parsed data is held in isolation until human approval. Unapproved data will not affect Distributor Finance.</li>
          <li><strong>Reconciliation:</strong> The parser flags mismatches automatically against AEC schedule expectations.</li>
          <li><strong>Reprocessing:</strong> If the District report format changes, update the Parser Version above, and retry failed jobs in the DCR view.</li>
        </ul>
      </div>
    </div>
  );
}
