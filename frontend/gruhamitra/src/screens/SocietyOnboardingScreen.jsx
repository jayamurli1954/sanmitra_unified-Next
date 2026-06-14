import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { authService } from '../services/authService';

const SocietyOnboardingScreen = () => {
  const location = useLocation();
  const initialIntent = new URLSearchParams(location.search || '').get('intent') === 'demo' ? 'demo' : 'register';
  const [formData, setFormData] = useState({
    society_name: '',
    society_address: '',
    authority_designation: '',
    admin_name: '',
    admin_email: '',
    admin_phone: '',
    request_intent: initialIntent,
    selected_plan: 'Decide after demo',
    plan_timing: 'After demo/discussion',
    verification_channel: 'email',
    terms_accepted: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.society_name || !formData.admin_name || !formData.admin_email || !formData.admin_phone) {
      setError('Please fill society name, authorized person name, email, and mobile number');
      return;
    }
    if (!formData.authority_designation) {
      setError('Designation or authority is required');
      return;
    }
    if (!formData.terms_accepted) {
      setError('Please confirm authority and accept the Terms of Service and Privacy Policy');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        society_name: formData.society_name,
        society_address: formData.society_address || undefined,
        authority_designation: formData.authority_designation,
        admin_name: formData.admin_name,
        admin_email: formData.admin_email,
        admin_phone: formData.admin_phone || undefined,
        request_intent: formData.request_intent,
        selected_plan: formData.selected_plan,
        plan_timing: formData.plan_timing,
        verification_channel: formData.verification_channel,
        terms_accepted: formData.terms_accepted,
      };

      await authService.registerSociety(payload);
      setError('');
      setSuccess('Request submitted. Contact verification, plan/payment approval, and activation are required before login access is enabled.');
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
        <h1 className="login-title">GruhaMitra Onboarding</h1>
        <p className="login-subtitle">Register or request a demo for your society</p>

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
            <label className="login-label">Society / Apartment Association Name *</label>
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
            <label className="login-label">Address</label>
            <input
              type="text"
              name="society_address"
              className="login-input"
              value={formData.society_address}
              onChange={handleChange}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Authorized Person Name *</label>
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
            <label className="login-label">Email Address *</label>
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
            <label className="login-label">Mobile Number *</label>
            <input
              type="tel"
              name="admin_phone"
              className="login-input"
              value={formData.admin_phone}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Designation / Authority *</label>
            <input
              type="text"
              name="authority_designation"
              className="login-input"
              placeholder="President, Secretary, Treasurer, Authorized Person"
              value={formData.authority_designation}
              onChange={handleChange}
              required
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Request Type</label>
            <select name="request_intent" className="login-input" value={formData.request_intent} onChange={handleChange}>
              <option value="register">Register</option>
              <option value="demo">Request Demo</option>
            </select>
          </div>

          <div className="login-input-container">
            <label className="login-label">Plan</label>
            <select name="selected_plan" className="login-input" value={formData.selected_plan} onChange={handleChange}>
              <option value="Decide after demo">Decide after demo</option>
              <option value="Starter">Starter</option>
              <option value="Growth">Growth</option>
              <option value="Professional">Professional</option>
            </select>
          </div>

          <div className="login-input-container">
            <label className="login-label">Plan Finalization</label>
            <select name="plan_timing" className="login-input" value={formData.plan_timing} onChange={handleChange}>
              <option value="After demo/discussion">After demo/discussion</option>
              <option value="Ready to activate">Ready to activate</option>
            </select>
          </div>

          <div className="login-input-container">
            <label className="login-label">OTP / Verification Channel</label>
            <select name="verification_channel" className="login-input" value={formData.verification_channel} onChange={handleChange}>
              <option value="email">Email</option>
              <option value="mobile">Mobile</option>
            </select>
          </div>

          <label className="login-consent">
            <input
              type="checkbox"
              name="terms_accepted"
              checked={formData.terms_accepted}
              onChange={handleChange}
              required
            />
            <span>
              I confirm I am authorized to register this society and agree to the{' '}
              <a href="/gruhamitra/terms.html" className="login-link">Terms of Service</a> and{' '}
              <a href="/gruhamitra/privacy.html" className="login-link">Privacy Policy</a>.
            </span>
          </label>

          <div className="login-notice">
            Login credentials are issued only after contact verification, plan/payment approval, and tenant activation.
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Submitting Request...' : 'Submit Request'}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-footer-text">
            Completed onboarding? <Link to="/login" className="login-link">Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SocietyOnboardingScreen;
