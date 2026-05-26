/**
 * Web-compatible Login Screen
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../services/authService';
import api from '../services/api';

const LoginScreen = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const isLocalHost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const showAnimatedLogo = isLocalHost;

  useEffect(() => {
    // Warm up cloud backend (Render) while user is on login screen.
    // This reduces perceived delay on first authenticated request after inactivity.
    const controller = new AbortController();
    const baseURL = api.defaults.baseURL || '';
    const healthUrl = baseURL.replace(/\/api\/?$/, '/health');

    fetch(healthUrl, {
      method: 'GET',
      signal: controller.signal,
      cache: 'no-store',
      headers: { 'X-App-Key': (import.meta?.env?.VITE_APP_KEY || 'gruhamitra').trim() },
    })
      .catch(() => {
        // Intentionally ignore warm-up failures.
      });

    return () => controller.abort();
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please enter email and password');
      return;
    }

    setLoading(true);
    try {
      const response = await authService.login({ email, password });
      if (onLoginSuccess) {
        onLoginSuccess(response?.user || null);
      }
      navigate('/dashboard', { replace: true });
    } catch (err) {
      let errorMessage = 'Login failed. Please try again.';

      if (err.name === 'SupabaseAuthError') {
        errorMessage = err.message || errorMessage;
      } else if (err.response) {
        const status = err.response.status;
        const detail = err.response.data?.detail || err.response.data?.message;

        if (status === 401) {
          errorMessage = detail || 'Incorrect email or password';
        } else if (status >= 500) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          errorMessage = detail || errorMessage;
        }
      } else if (err.message) {
        if (err.message.includes('CONNECTION_ERROR') || err.code === 'ECONNREFUSED') {
          errorMessage = 'Cannot connect to server. Please check:\n1. Backend is running\n2. Correct API URL in config';
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        {/* Logo Video */}
        <div className="login-logo-container">
          {showAnimatedLogo ? (
            <video
              autoPlay
              loop
              muted
              playsInline
              preload="metadata"
              className="login-logo-video"
            >
              <source src="/gruhamitra/GruhaMitra_Logo.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          ) : (
            <img
              src="/gruhamitra/GruhaMitra_Logo.png"
              alt="GruhaMitra Logo"
              className="login-logo"
              width={120}
              height={120}
              loading="eager"
              decoding="async"
            />
          )}
        </div>
        <h1 className="login-title">GruhaMitra</h1>
        <p className="login-subtitle">Your Society, Digitally Simplified</p>

        {error && (
          <div className="login-error">
            <div className="login-error-text">{error}</div>
          </div>
        )}

        <form onSubmit={handleLogin} className="login-form">
          <div className="login-input-container">
            <label className="login-label">Email</label>
            <input
              type="email"
              className="login-input"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                className="login-input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '16px',
                  color: '#666'
                }}
              >
                {showPassword ? '🙈' : '👁'}
              </button>
            </div>
            <div className="login-inline-action">
              <a href="/gruhamitra/forgot-password" className="login-link">Forgot Password?</a>
            </div>
          </div>

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-footer-text">
            Don't have an account?{' '}
            <Link to="/register" className="login-link">Register Options</Link>
          </p>
          <p className="login-footer-text" style={{ marginTop: '8px' }}>
            New society?{' '}
            <Link to="/onboard-society" className="login-link">Onboard Society</Link>
          </p>
          <p className="login-footer-text" style={{ marginTop: '8px' }}>
            Resident join request?{' '}
            <Link to="/resident-signup" className="login-link">Resident Registration</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;
