import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function AIIntelligenceCenter() {
  const [activeTab, setActiveTab] = useState('daily'); // daily, monthly, yearly, archive, actions
  const token = localStorage.getItem('access_token');

  const { data: reports, isLoading } = useQuery({
    queryKey: ['ai-reports-center', activeTab],
    queryFn: async () => {
      let url = `http://localhost:8000/api/reports/ai/reports/`;
      if (activeTab === 'daily') url += `?period_type=DAILY`;
      else if (activeTab === 'monthly') url += `?period_type=MONTHLY`;
      else if (activeTab === 'yearly') url += `?period_type=YEARLY`;
      
      if (activeTab !== 'actions') {
        const res = await axios.get(url, { headers: { Authorization: `Bearer ${token}` } });
        return res.data;
      }
      return null;
    }
  });

  const { data: actions, isLoading: actsLoading } = useQuery({
    queryKey: ['ai-actions'],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/api/reports/ai/actions/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return res.data;
    },
    enabled: activeTab === 'actions'
  });

  const handleActionStatus = async (id, status) => {
    try {
      await axios.patch(`http://localhost:8000/api/reports/ai/actions/${id}/`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Action marked as ${status}`);
    } catch (e) {
      toast.error('Failed to update action');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🧠 Perplexity AI Intelligence</h1>
          <p className="page-subtitle">Centralized reporting, benchmarking, and business recommendations across all operations.</p>
        </div>
        <button className="btn btn-primary" onClick={() => toast.success('Forced sync queued')}>🔄 Run Intelligence Sync</button>
      </div>

      <div className="tab-container" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button className={`tab-btn ${activeTab === 'daily' ? 'active' : ''}`} onClick={() => setActiveTab('daily')}>☀️ Daily Intelligence Center</button>
        <button className={`tab-btn ${activeTab === 'monthly' ? 'active' : ''}`} onClick={() => setActiveTab('monthly')}>📅 Monthly Review Center</button>
        <button className={`tab-btn ${activeTab === 'yearly' ? 'active' : ''}`} onClick={() => setActiveTab('yearly')}>🏆 Yearly Business Review</button>
        <button className={`tab-btn ${activeTab === 'archive' ? 'active' : ''}`} onClick={() => setActiveTab('archive')}>🗄️ AI Reports Archive</button>
        <button className={`tab-btn ${activeTab === 'actions' ? 'active' : ''}`} onClick={() => setActiveTab('actions')}>🎯 Action Recommendation Queue</button>
      </div>

      {activeTab === 'actions' ? (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Recommendation</th>
                <th>Source Report</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {actions?.results?.map(action => (
                <tr key={action.id}>
                  <td>{action.description}</td>
                  <td>AI Insight #{action.report}</td>
                  <td><span className={`badge badge-${action.status === 'COMPLETED' ? 'success' : action.status === 'IN_PROGRESS' ? 'warning' : 'default'}`}>{action.status}</span></td>
                  <td>
                    {action.status !== 'COMPLETED' && (
                      <button className="btn btn-secondary" onClick={() => handleActionStatus(action.id, 'COMPLETED')}>Mark Done</button>
                    )}
                  </td>
                </tr>
              ))}
              {(!actions?.results || actions.results.length === 0) && !actsLoading && (
                <tr><td colSpan="4" className="text-center text-secondary py-4">No pending recommendations.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid-2">
          {isLoading ? <div className="loading-cell col-span-2">Loading reports...</div> : 
            reports?.results?.map(report => (
              <div key={report.id} className="card">
                <div className="flex-between" style={{ marginBottom: '12px' }}>
                  <h3 style={{ margin: 0 }}>{report.report_type}</h3>
                  <span className={`badge badge-${report.severity === 'CRITICAL' ? 'error' : 'default'}`}>{report.severity}</span>
                </div>
                <div className="text-secondary" style={{ fontSize: '0.85em', marginBottom: '16px' }}>
                  Module: {report.module} | Period: {report.period_type} | Generated: {new Date(report.created_at).toLocaleDateString()}
                </div>
                
                <p style={{ lineHeight: '1.5', fontSize: '0.95em' }}>{report.summary}</p>
                
                {report.benchmark_notes && (
                  <div style={{ padding: '10px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '6px', marginTop: '12px', borderLeft: '3px solid #3b82f6' }}>
                    <strong>Benchmark: </strong> <span style={{ fontSize: '0.9em' }}>{report.benchmark_notes}</span>
                  </div>
                )}
                
                {report.suggestions?.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <strong>Suggestions:</strong>
                    <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', fontSize: '0.9em' }}>
                      {report.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ))
          }
          {(!reports?.results || reports.results.length === 0) && !isLoading && (
            <div className="col-span-2 card text-center text-secondary">
              No AI reports generated for this period yet. Background jobs will generate them automatically.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
