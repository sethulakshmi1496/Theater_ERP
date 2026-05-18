import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.full_name}!`);
      navigate('/dashboard');
    } catch (err) {
      toast.error('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '32px' }}>
          <svg width="80" height="80" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginBottom: '12px' }}>
            <path d="M50 10C27.9 10 10 27.9 10 50C10 72.1 27.9 90 50 90C68.4 90 83.8 77.5 88.5 60.5H74.7C70.6 70.3 61 77 50 77C35.1 77 23 64.9 23 50C23 35.1 35.1 23 50 23C61.4 23 71.1 30.1 75 40.5H88.8C84.4 22.8 68.6 10 50 10Z" fill="#F5A623"/>
            <path d="M50 40H75V60H50V40Z" fill="#F5A623"/>
          </svg>
          <div style={{ fontSize: '36px', fontWeight: 900, color: '#F5A623', letterSpacing: '3px', lineHeight: 1 }}>AEC</div>
          <div style={{ fontSize: '20px', fontWeight: 300, color: '#FFFFFF', letterSpacing: '6px', marginTop: '6px' }}>CINEMAS</div>
          <p style={{ marginTop: '16px', color: 'var(--text-muted)' }}>ERP System</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              placeholder="you@aeccinemas.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>
          <button id="login-btn" type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }} disabled={loading}>
            {loading ? '🔄 Signing in...' : '🚀 Sign In to Dashboard'}
          </button>
        </form>

        <div style={{ marginTop: '24px', padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <div className="text-xs text-muted" style={{ marginBottom: '8px', fontWeight: 600 }}>DEMO CREDENTIALS</div>
          <div className="text-sm" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span>🎯 MD: md@aeccinemas.com / AEC@md2026</span>
            <span>👤 Admin: admin@aeccinemas.com / AEC@admin2026</span>
            <span>🧑 Staff: staff@aeccinemas.com / AEC@staff2026</span>
          </div>
        </div>
      </div>
    </div>
  );
}
