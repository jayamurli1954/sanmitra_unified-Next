import React, { useState } from 'react';
import { authService } from '../services/authService';

const ForgotPasswordScreen = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!email) {
      setError('Please enter your email');
      return;
    }

    setLoading(true);
    try {
      const redirectTo = `${window.location.origin}/reset-password`;
      await authService.requestPasswordReset(email, redirectTo);
      setSuccess('Password reset link sent. Please check your email inbox.');
    } catch (err) {
      setError(err?.message || 'Could not send reset link. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo-container">
          <img
            src="/gruhamitra/icons/icon-192.png"
            alt="GruhaMitra Logo"
            className="login-logo"
            width={120}
            height={120}
            loading="eager"
            decoding="async"
          />
        </div>
        <h1 className="login-title">Forgot Password</h1>
        <p className="login-subtitle">Get a secure reset link on your email</p>

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
            <label className="login-label">Email</label>
            <input
              type="email"
              className="login-input"
              placeholder="Enter your registered email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Sending link...' : 'Send Reset Link'}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-footer-text">
            Back to <a href="/gruhamitra/login" className="login-link">Login</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordScreen;

