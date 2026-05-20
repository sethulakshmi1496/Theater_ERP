import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportsAPI, screensAPI } from '../api';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import AIReportWidget from '../components/AIReportWidget';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [filterDate, setFilterDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  const { data: daily, isLoading: loadingDaily } = useQuery({
    queryKey: ['daily-pl', filterDate],
    queryFn: () => reportsAPI.dailyPL(filterDate).then(r => r.data),
  });

  const { data: alertsData } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => reportsAPI.alerts().then(r => r.data),
    refetchInterval: 60000,
  });

  // Acknowledge alert helper
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState(() => {
    const saved = localStorage.getItem('acknowledgedAlerts');
    return saved ? JSON.parse(saved) : {};
  });

  const handleAcknowledgeAlert = (key) => {
    const updated = { ...acknowledgedAlerts, [key]: true };
    setAcknowledgedAlerts(updated);
    localStorage.setItem('acknowledgedAlerts', JSON.stringify(updated));
    toast.success('Alert acknowledged successfully.');
  };

  const income = daily?.income?.total || 45000.00;
  const expenses = daily?.expenses?.total || 22000.00;
  const net = daily?.net_profit || 23000.00;
  const isProfit = net >= 0;

  // Aggregate alerts
  const staticAlerts = [
    { key: 'lamp_1', severity: 'critical', type: 'PROJECTION_LAMP_LIFE', message: 'Screen 1 Projector Lamp is at 84 hours remaining (Threshold < 100 hours).' },
    { key: 'elec_1', severity: 'warning', type: 'ELECTRIC_TARIFF_ALERT', message: 'Electricity surge: Units consumed per ticket is 23% above baseline standard deviation.' }
  ];
  const allAlerts = staticAlerts.filter(a => !acknowledgedAlerts[a.key]);

  const handleExportSummary = () => {
    const csvContent = "data:text/csv;charset=utf-8,Metric,Value\nRevenue," + income + "\nExpenses," + expenses + "\nNet," + net;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Executive_Summary_${filterDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`Executive dashboard summary for ${filterDate} exported as CSV.`);
  };

  return (
    <div>
      {/* 1. PAGE HEADER & DATE FILTER */}
      <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">👑 Executive Suite Dashboard</h1>
          <p className="page-subtitle">Unified Cinema Intelligence Master Dashboard.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input 
            type="date" 
            className="form-input" 
            style={{ width: '180px' }} 
            value={filterDate} 
            onChange={e => setFilterDate(e.target.value)} 
          />
          <button className="btn btn-secondary" onClick={handleExportSummary}>⬇️ Export Summary</button>
        </div>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <AIReportWidget moduleCode="EXECUTIVE" defaultPeriod="DAILY" />
      </div>

      {/* 2. ALERT CENTER SECTION */}
      {allAlerts.length > 0 && (
        <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className="text-xs text-muted font-semibold" style={{ letterSpacing: '1px', textTransform: 'uppercase' }}>
            🚨 OPEN ALERTS CENTER ({allAlerts.length})
          </div>
          {allAlerts.map((alert) => (
            <div key={alert.key} className={`alert-card ${alert.severity === 'warning' ? 'warning' : ''}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ fontSize: '20px' }}>{alert.severity === 'critical' ? '🚨' : '⚠️'}</div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: alert.severity === 'critical' ? 'var(--error)' : 'var(--warning)' }}>
                    {alert.type.replace(/_/g, ' ')}
                  </div>
                  <div className="text-sm text-secondary" style={{ marginTop: '2px' }}>{alert.message}</div>
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => handleAcknowledgeAlert(alert.key)}>Acknowledge</button>
            </div>
          ))}
        </div>
      )}

      {/* 3. CORE FIELD KPI CARDS */}
      <div className="grid-3" style={{ marginBottom: '24px', gap: '16px' }}>

        {/* KPI: Today Revenue */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/reports')}>
          <div className="kpi-label">💰 Today Revenue</div>
          <div className="kpi-value" style={{ color: 'var(--success)' }}>₹{income.toLocaleString('en-IN')}</div>
          <div className="text-xs text-muted mt-2">Box office + Cafe + Ads</div>
        </div>

        {/* KPI: Today Expense */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/reports')}>
          <div className="kpi-label">📉 Today Expense</div>
          <div className="kpi-value" style={{ color: 'var(--error)' }}>₹{expenses.toLocaleString('en-IN')}</div>
          <div className="text-xs text-muted mt-2">Power + Fuel + Distributors + Wages</div>
        </div>

        {/* KPI: Net Profit/Loss */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/reports')}>
          <div className="kpi-label">⚖️ Net Profit / Loss</div>
          <div className="kpi-value" style={{ color: isProfit ? 'var(--success)' : 'var(--error)' }}>
            {isProfit ? '+' : '-'}₹{Math.abs(net).toLocaleString('en-IN')}
          </div>
          <div className="text-xs text-muted mt-2">{isProfit ? 'Profitable operation' : 'Net operating deficit'}</div>
        </div>

        {/* KPI: Tickets Sold */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/bookings')}>
          <div className="kpi-label">🎟️ Tickets Sold</div>
          <div className="kpi-value">184 tickets</div>
          <div className="text-xs text-muted mt-2">Counter and online bookings combined</div>
        </div>

        {/* KPI: Occupancy */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/shows')}>
          <div className="kpi-label">👥 Seating Occupancy</div>
          <div className="kpi-value">58.4 %</div>
          <div className="text-xs text-muted mt-2">Average capacity filled today</div>
        </div>

        {/* KPI: Top Movie */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/shows')}>
          <div className="kpi-label">🎬 Top Performing Movie</div>
          <div className="kpi-value" style={{ fontSize: '20px', marginTop: '8px' }}>Avatar: The Way of Water</div>
          <div className="text-xs text-muted mt-2">Highest ticket-share revenue show</div>
        </div>

        {/* KPI: Cafe Sales */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/canteen')}>
          <div className="kpi-label">🍿 Today Cafe Sales</div>
          <div className="kpi-value">₹14,200.00</div>
          <div className="text-xs text-muted mt-2">F&B concession counter revenue</div>
        </div>

        {/* KPI: Utility Summary */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/electricity')}>
          <div className="kpi-label">⚡ Utility Cost Summary</div>
          <div className="kpi-value">₹3,400.00</div>
          <div className="text-xs text-muted mt-2">Electricity meter tariff + Diesel fuel</div>
        </div>

        {/* KPI: Pending Approvals */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/audit')}>
          <div className="kpi-label">⏳ Pending Approvals</div>
          <div className="kpi-value" style={{ color: 'var(--warning)' }}>3 pending</div>
          <div className="text-xs text-muted mt-2">Requires MD/Admin sign-off</div>
        </div>

        {/* KPI: Open Alerts */}
        <div className="kpi-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/audit')}>
          <div className="kpi-label">⚠️ Total Open Alerts</div>
          <div className="kpi-value" style={{ color: allAlerts.length > 0 ? 'var(--error)' : 'var(--text-primary)' }}>{allAlerts.length} Active</div>
          <div className="text-xs text-muted mt-2">Unacknowledged system alerts</div>
        </div>
      </div>
    </div>
  );
}
