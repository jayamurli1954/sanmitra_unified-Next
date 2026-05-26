import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';

const SocietyOnboardingScreen = ({ onRegisterSuccess }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    society_name: '',
    society_address: '',
    registration_no: '',
    pan_no: '',
    accounting_type: 'cash',
    admin_name: '',
    admin_email: '',
    admin_phone: '',
    admin_password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.society_name || !formData.admin_name || !formData.admin_email || !formData.admin_password) {
      setError('Please fill Society Name, Admin Name, Email, and Password');
      return;
    }

    if (formData.admin_password.length < 6) {
      setError('Admin password must be at least 6 characters');
      return;
    }

    if (formData.admin_password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        society_name: formData.society_name,
        society_address: formData.society_address || undefined,
        registration_no: formData.registration_no || undefined,
        pan_no: formData.pan_no || undefined,
        accounting_type: formData.accounting_type,
        admin_name: formData.admin_name,
        admin_email: formData.admin_email,
        admin_phone: formData.admin_phone || undefined,
        admin_password: formData.admin_password,
      };

      await authService.registerSociety(payload);
      setError('');
      alert('Society onboarding request submitted. Platform admin approval is required before first login.');
      navigate('/login');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Society onboarding failed';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: '520px' }}>
        <div className="login-logo-container">
          <img
            src="/gruhamitra/GruhaMitra_Logo.png"
            alt="GruhaMitra Logo"
            className="login-logo"
            style={{ width: '120px', height: '120px', borderRadius: '20px' }}
          />
        </div>
        <h1 className="login-title">Onboard New Society</h1>
        <p className="login-subtitle">Create society and first Super Admin account</p>

        {error && (
          <div className="login-error">
            <div className="login-error-text">{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-input-container">
            <label className="login-label">Society Name *</label>
            <input
              type="text"
              name="society_name"
              className="login-input"
              value={formData.society_name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Society Address</label>
            <input
              type="text"
              name="society_address"
              className="login-input"
              value={formData.society_address}
              onChange={handleChange}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Registration Number</label>
            <input
              type="text"
              name="registration_no"
              className="login-input"
              value={formData.registration_no}
              onChange={handleChange}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">PAN Number</label>
            <input
              type="text"
              name="pan_no"
              className="login-input"
              value={formData.pan_no}
              onChange={handleChange}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Accounting Type</label>
            <select
              name="accounting_type"
              className="login-input"
              value={formData.accounting_type}
              onChange={handleChange}
            >
              <option value="cash">Cash</option>
              <option value="accrual">Accrual</option>
            </select>
          </div>

          <div className="login-input-container">
            <label className="login-label">Admin Name *</label>
            <input
              type="text"
              name="admin_name"
              className="login-input"
              value={formData.admin_name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Admin Email *</label>
            <input
              type="email"
              name="admin_email"
              className="login-input"
              value={formData.admin_email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Admin Phone</label>
            <input
              type="tel"
              name="admin_phone"
              className="login-input"
              value={formData.admin_phone}
              onChange={handleChange}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Admin Password *</label>
            <input
              type="password"
              name="admin_password"
              className="login-input"
              value={formData.admin_password}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Confirm Password *</label>
            <input
              type="password"
              name="confirmPassword"
              className="login-input"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Creating Society...' : 'Create Society'}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-footer-text">
            Already have an account? <a href="/gruhamitra/login" className="login-link">Login</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SocietyOnboardingScreen;

