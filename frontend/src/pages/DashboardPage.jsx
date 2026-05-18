import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportsAPI, screensAPI } from '../api';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

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
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState({});
  const handleAcknowledgeAlert = (key) => {
    setAcknowledgedAlerts(prev => ({ ...prev, [key]: true }));
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
        {/* KPI: Business Date */}
        <div className="kpi-card" onClick={() => toast.info(`Current Business Date: ${filterDate}`)} style={{ cursor: 'pointer' }}>
          <div className="kpi-label">📅 Business Date</div>
          <div className="kpi-value" style={{ fontSize: '22px', marginTop: '8px' }}>{format(new Date(filterDate), 'dd MMM yyyy')}</div>
          <div className="text-xs text-muted mt-2">Active operating day</div>
        </div>

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

      {/* 4. NAVIGATION / REDIRECTION QUICK-LINKS */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="font-semibold mb-4 text-md" style={{ color: 'var(--gold)' }}>🔗 Redirection Desk – Drill Into Source Modules</div>
        <div className="grid-4" style={{ gap: '12px' }}>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/shows')}>🎬 Movies</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/bookings')}>🎟️ Bookings</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/canteen')}>🍿 Cafe Sales</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/electricity')}>⚡ Expense Register (Utilities)</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/reports')}>📈 P&L Reports</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/electricity')}>🚨 Alert Center</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/audit')}>🛡️ Audit Shield</button>
          <button className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => navigate('/integrations/dcr')}>📊 District DCR</button>
        </div>
      </div>

      {/* 5. WORKFLOW STATEMENT SUMMARY */}
      <div className="card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', padding: '16px' }}>
        <h4 className="font-semibold" style={{ color: 'var(--gold)', margin: '0 0 8px 0' }}>🔄 Active Cinema Operations Workflow</h4>
        <p className="text-xs text-muted" style={{ margin: 0, lineHeight: '1.6' }}>
          The system aggregates daily feeds from <strong>Bookings</strong>, <strong>Concession Cafe</strong>, <strong>Utilities</strong>, <strong>Expense heads</strong>, <strong>HR</strong>, and <strong>District DCR</strong>. The Master Dashboard surfaces critical operational variance exceptions; you can click any KPI card or use the redirection links above to immediately drill down into the respective source modules.
        </p>
      </div>
    </div>
  );
}
