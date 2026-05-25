import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';

const ResetPasswordScreen = () => {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [canReset, setCanReset] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const checkRecoverySession = async () => {
      setChecking(true);
      try {
        await authService.initAuthListener();
        const hasSession = await authService.hasRecoverySession();
        setCanReset(hasSession);
      } catch (err) {
        setCanReset(false);
      } finally {
        setChecking(false);
      }
    };

    checkRecoverySession();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!password || !confirmPassword) {
      setError('Please fill both password fields');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await authService.updatePassword(password);
      setSuccess('Password updated successfully. Redirecting to login...');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err) {
      setError(err?.message || 'Could not reset password. Please request a new link.');
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1 className="login-title">Reset Password</h1>
          <p className="login-subtitle">Checking reset link...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">Reset Password</h1>
        <p className="login-subtitle">Set your new password</p>

        {!canReset && (
          <div className="login-error">
            <div className="login-error-text">
              Reset link is invalid or expired. Please request a new password reset link.
            </div>
          </div>
        )}

        {error && (
          <div className="login-error">
            <div className="login-error-text">{error}</div>
          </div>
        )}

        {success && (
          <div className="login-success">
            <div className="login-success-text">{success}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-input-container">
            <label className="login-label">New Password</label>
            <input
              type="password"
              className="login-input"
              placeholder="Enter new password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              disabled={!canReset}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Confirm Password</label>
            <input
              type="password"
              className="login-input"
              placeholder="Re-enter new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              disabled={!canReset}
              required
            />
          </div>

          <button type="submit" className="login-button" disabled={loading || !canReset}>
            {loading ? 'Updating password...' : 'Update Password'}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-footer-text">
            Need a new link?{' '}
            <a href="/gruhamitra/forgot-password" className="login-link">Forgot Password</a>
          </p>
          <p className="login-footer-text" style={{ marginTop: '8px' }}>
            Back to <a href="/gruhamitra/login" className="login-link">Login</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordScreen;
