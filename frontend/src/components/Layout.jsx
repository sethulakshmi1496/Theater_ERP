import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const NAV_ITEMS = [
  { section: 'Overview', items: [
    { path: '/dashboard', icon: '📊', label: 'Executive Suite', roles: ['MD', 'ADMIN'] },
  ]},
  { section: 'Revenue', items: [
    { path: '/shows', icon: '🎬', label: 'Movies' },
    { path: '/bookings', icon: '🎟️', label: 'Bookings' },
    { path: '/canteen', icon: '🍿', label: 'Cafe Sales', module: 'CAFE' },
    { path: '/advertising', icon: '📺', label: 'Advertising', module: 'ADVERTISING' },
  ]},
  { section: 'Operations', items: [
    { path: '/electricity', icon: '⚡', label: 'Utility Readings' },
    { path: '/generator', icon: '🔋', label: 'Generator' },
    { path: '/lamps', icon: '💡', label: 'Projection Lamps' },
    { path: '/assets', icon: '🏗️', label: 'Asset Registry' },
  ]},
  { section: 'Finance & HR', items: [
    { path: '/finance', icon: '🎭', label: 'Film Finance', roles: ['MD', 'ADMIN'], module: 'FINANCE' },
    { path: '/integrations/district-config', icon: '⚙️', label: 'District Setup', roles: ['MD', 'ADMIN'] },
    { path: '/integrations/dcr', icon: '📄', label: 'District DCR', roles: ['MD', 'ADMIN'], module: 'DISTRICT_BRIDGE' },
    { path: '/integrations/petpooja', icon: '🔌', label: 'Petpooja POS', roles: ['MD', 'ADMIN'] },
    { path: '/staff', icon: '👥', label: 'Staff Report', roles: ['MD', 'ADMIN'] },
  ]},
  { section: 'Intelligence', items: [
    { path: '/ai-center', icon: '🧠', label: 'AI Intelligence', roles: ['MD', 'ADMIN'] },
    { path: '/reports', icon: '📈', label: 'P&L Reports', roles: ['MD', 'ADMIN'] },
    { path: '/audit', icon: '🛡️', label: 'Audit Shield', roles: ['MD', 'ADMIN'], module: 'AUDIT' },
    { path: '/builder', icon: '🏗️', label: 'Screen Builder', roles: ['MD', 'ADMIN'], module: 'SCREEN_BUILDER' },
    { path: '/settings', icon: '⚙️', label: 'Settings', roles: ['MD'] },
  ]},
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    toast.success('Logged out successfully');
  };

  const getRoleColor = (role) => {
    if (role === 'MD') return 'badge-warning';
    if (role === 'ADMIN') return 'badge-info';
    return 'badge-neutral';
  };

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo" style={{ padding: '24px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginBottom: '8px' }}>
            <path d="M50 10C27.9 10 10 27.9 10 50C10 72.1 27.9 90 50 90C68.4 90 83.8 77.5 88.5 60.5H74.7C70.6 70.3 61 77 50 77C35.1 77 23 64.9 23 50C23 35.1 35.1 23 50 23C61.4 23 71.1 30.1 75 40.5H88.8C84.4 22.8 68.6 10 50 10Z" fill="#F5A623"/>
            <path d="M50 40H75V60H50V40Z" fill="#F5A623"/>
          </svg>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#F5A623', letterSpacing: '2px', lineHeight: 1 }}>AEC</div>
          <div style={{ fontSize: '14px', fontWeight: 300, color: '#FFFFFF', letterSpacing: '4px', marginTop: '4px' }}>CINEMAS</div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(section => {
            const visibleItems = section.items.filter(item => {
              if (item.roles && !item.roles.includes(user?.role)) return false;
              if (item.module && user?.active_modules && !user.active_modules.includes(item.module)) return false;
              return true;
            });
            if (visibleItems.length === 0) return null;
            return (
              <div key={section.section}>
                <div className="nav-section-label">{section.section}</div>
                {visibleItems.map(item => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    {item.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div className="user-badge" style={{ marginBottom: '10px' }}>
            <div className="user-avatar">{user?.full_name?.charAt(0) || 'U'}</div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{user?.full_name}</div>
              <div className={`badge ${getRoleColor(user?.role)}`} style={{ fontSize: '10px', padding: '1px 6px' }}>
                {user?.role}
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={handleLogout}>
            🚪 Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="main-content">
        <div style={{ padding: '32px' }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
