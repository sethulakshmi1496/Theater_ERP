import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ShowsPage from './pages/ShowsPage';
import BookingsPage from './pages/BookingsPage';
import ElectricityPage from './pages/ElectricityPage';
import GeneratorPage from './pages/GeneratorPage';
import LampsPage from './pages/LampsPage';
import AssetRegistryPage from './pages/AssetRegistryPage';
import CanteenPage from './pages/CanteenPage';
import AdvertisingPage from './pages/AdvertisingPage';
import FinancePage from './pages/FinancePage';
import StaffReportPage from './pages/StaffReportPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import AuditPage from './pages/AuditPage';
import ScreenBuilderPage from './pages/ScreenBuilderPage';
import ScreenLayoutPage from './pages/ScreenLayoutPage';
import DCRPage from './pages/DCRPage';
import AIIntelligenceCenter from './pages/AIIntelligenceCenter';
import PetpoojaIntegrationPage from './pages/PetpoojaIntegrationPage';
import Layout from './components/Layout';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
});

function ProtectedRoute({ children, roles, module }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    if (user.role === 'STAFF') return <Navigate to="/shows" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  if (module && user.active_modules && !user.active_modules.includes(module)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function RoleBasedDefaultRoute() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'STAFF') return <Navigate to="/shows" replace />;
  return <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Toaster
            position="top-right"
            toastOptions={{
              style: { background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #313244' },
              success: { iconTheme: { primary: '#a6e3a1', secondary: '#1e1e2e' } },
              error: { iconTheme: { primary: '#f38ba8', secondary: '#1e1e2e' } },
            }}
          />
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Admin Protected */}
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<RoleBasedDefaultRoute />} />
              <Route path="dashboard" element={<ProtectedRoute roles={['MD', 'ADMIN']}><DashboardPage /></ProtectedRoute>} />
              <Route path="shows" element={<ShowsPage />} />
              <Route path="bookings" element={<BookingsPage />} />
              <Route path="electricity" element={<ElectricityPage />} />
              <Route path="generator" element={<GeneratorPage />} />
              <Route path="lamps" element={<LampsPage />} />
              <Route path="assets" element={<AssetRegistryPage />} />
              <Route path="canteen" element={<ProtectedRoute module="CAFE"><CanteenPage /></ProtectedRoute>} />
              <Route path="advertising" element={<ProtectedRoute module="ADVERTISING"><AdvertisingPage /></ProtectedRoute>} />
              <Route path="finance" element={<ProtectedRoute roles={['MD', 'ADMIN']} module="FINANCE"><FinancePage /></ProtectedRoute>} />
              <Route path="staff" element={<ProtectedRoute roles={['MD', 'ADMIN']}><StaffReportPage /></ProtectedRoute>} />
              <Route path="integrations/dcr" element={<ProtectedRoute roles={['MD', 'ADMIN']} module="DISTRICT_BRIDGE"><DCRPage /></ProtectedRoute>} />
              <Route path="reports" element={<ProtectedRoute roles={['MD', 'ADMIN']}><ReportsPage /></ProtectedRoute>} />
              <Route path="ai-center" element={<ProtectedRoute roles={['MD', 'ADMIN']}><AIIntelligenceCenter /></ProtectedRoute>} />
              <Route path="integrations/petpooja" element={<ProtectedRoute roles={['MD', 'ADMIN']}><PetpoojaIntegrationPage /></ProtectedRoute>} />
              <Route path="audit" element={<ProtectedRoute roles={['MD', 'ADMIN']} module="AUDIT"><AuditPage /></ProtectedRoute>} />
              <Route path="builder" element={<ProtectedRoute roles={['MD', 'ADMIN']} module="SCREEN_BUILDER"><ScreenBuilderPage /></ProtectedRoute>} />
              <Route path="builder/screen/:screenId" element={<ProtectedRoute roles={['MD', 'ADMIN']} module="SCREEN_BUILDER"><ScreenLayoutPage /></ProtectedRoute>} />
              <Route path="settings" element={<ProtectedRoute roles={['MD']}><SettingsPage /></ProtectedRoute>} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
