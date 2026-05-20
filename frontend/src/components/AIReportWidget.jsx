import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function AIReportWidget({ moduleCode, defaultPeriod = 'DAILY' }) {
  const [period, setPeriod] = useState(defaultPeriod);
  const token = localStorage.getItem('access_token');
  
  const { data: reports, isLoading } = useQuery({
    queryKey: ['ai-reports', moduleCode, period],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/api/reports/ai/reports/?module=${moduleCode}&period_type=${period}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return res.data;
    }
  });

  const latestReport = reports?.results?.[0];

  const exportReport = () => {
    if (!latestReport) return toast.error('No report to export');
    const content = `AI Insight Report (${period})\n\nSummary:\n${latestReport.summary}\n\nBenchmarks:\n${latestReport.benchmark_notes || 'N/A'}`;
    const encodedUri = encodeURI("data:text/plain;charset=utf-8," + content);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `AI_Insight_Report_${moduleCode}_${period}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Report exported successfully');
  };

  if (isLoading) return <div className="card loading-cell">Loading AI Insights...</div>;

  return (
    <div className="card" style={{ border: '1px solid rgba(139, 92, 246, 0.3)', background: 'linear-gradient(145deg, rgba(139, 92, 246, 0.05) 0%, rgba(0,0,0,0) 100%)' }}>
      <div className="flex-between" style={{ marginBottom: '16px' }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          🧠 Perplexity AI Insight
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select 
            className="form-input" 
            style={{ width: '120px', padding: '4px 8px' }}
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="DAILY">Daily</option>
            <option value="MONTHLY">Monthly</option>
            <option value="YEARLY">Yearly</option>
          </select>
          <button className="btn btn-secondary" onClick={exportReport} style={{ padding: '4px 8px' }}>Export</button>
        </div>
      </div>

      {!latestReport ? (
        <div className="text-secondary">No {period.toLowerCase()} AI report available for this period. Background generation may be pending.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Summary Panel */}
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)' }}>Executive Summary</h4>
            <p className="text-secondary" style={{ margin: 0, lineHeight: '1.5' }}>{latestReport.summary}</p>
          </div>
          
          {/* Benchmark Panel */}
          {latestReport.benchmark_notes && (
            <div style={{ padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', borderLeft: '4px solid #3b82f6' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#60a5fa' }}>🌍 Real-World Benchmark</h4>
              <p style={{ margin: 0, fontSize: '0.9em' }}>{latestReport.benchmark_notes}</p>
            </div>
          )}

          {/* Compare Panel */}
          <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px 0' }}>Trend & Exceptions</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.9em', color: 'var(--text-secondary)' }}>
              {latestReport.risks?.map((r, i) => <li key={i} style={{ color: 'var(--error)' }}>{r}</li>)}
              {latestReport.opportunities?.map((o, i) => <li key={i} style={{ color: 'var(--success)' }}>{o}</li>)}
            </ul>
          </div>

          {/* Suggestions Panel */}
          <div>
            <h4 style={{ margin: '0 0 8px 0' }}>💡 Business Improvements</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {latestReport.suggestions?.map((s, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '8px 12px', borderRadius: '6px' }}>
                  <span style={{ fontSize: '0.9em' }}>{s}</span>
                  <button className="btn btn-secondary" style={{ fontSize: '0.8em', padding: '4px 8px' }} onClick={() => toast.success('Action marked as pending')}>Take Action</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
