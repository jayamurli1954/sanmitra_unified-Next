import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import membershipV2Service from '../services/membershipV2Service';

const CompleteRegistrationScreen = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    terms_accepted: true,
    privacy_accepted: true,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (formData.password.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters.' });
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match.' });
      return;
    }
    if (!formData.terms_accepted || !formData.privacy_accepted) {
      setMessage({ type: 'error', text: 'Please accept Terms and Privacy Policy.' });
      return;
    }

    setLoading(true);
    try {
      await membershipV2Service.completeResidentRegistration({
        email: formData.email,
        password: formData.password,
        terms_accepted: formData.terms_accepted,
        privacy_accepted: formData.privacy_accepted,
      });
      setMessage({
        type: 'success',
        text: 'Registration completed. You can now login with your email and password.',
      });
      setTimeout(() => navigate('/login'), 1200);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to complete registration.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: '480px' }}>
        <h1 className="login-title">Complete Registration</h1>
        <p className="login-subtitle">After admin approval, set your login password</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-input-container">
            <label className="login-label">Email *</label>
            <input
              className="login-input"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
              required
            />
          </div>
          <div className="login-input-container">
            <label className="login-label">Password *</label>
            <input
              className="login-input"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((p) => ({ ...p, password: e.target.value }))}
              required
            />
          </div>
          <div className="login-input-container">
            <label className="login-label">Confirm Password *</label>
            <input
              className="login-input"
              type="password"
              value={formData.confirmPassword}
              onChange={(e) => setFormData((p) => ({ ...p, confirmPassword: e.target.value }))}
              required
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '14px' }}>
              <input
                type="checkbox"
                checked={formData.terms_accepted}
                onChange={(e) => setFormData((p) => ({ ...p, terms_accepted: e.target.checked }))}
              />
              I accept Terms of Service
            </label>
          </div>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '14px' }}>
              <input
                type="checkbox"
                checked={formData.privacy_accepted}
                onChange={(e) => setFormData((p) => ({ ...p, privacy_accepted: e.target.checked }))}
              />
              I accept Privacy Policy
            </label>
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Submitting...' : 'Complete Registration'}
          </button>
        </form>

        {message.text && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px',
              borderRadius: '8px',
              background: message.type === 'error' ? '#FFECEC' : '#E8FFF1',
              border: `1px solid ${message.type === 'error' ? '#FFD6D6' : '#B9EBCB'}`,
              color: message.type === 'error' ? '#B00020' : '#1B5E20',
            }}
          >
            {message.text}
          </div>
        )}

        <div className="login-footer">
          <p className="login-footer-text">
            Need to submit request first? <a href="/gruhamitra/resident-signup" className="login-link">Resident Registration</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default CompleteRegistrationScreen;

