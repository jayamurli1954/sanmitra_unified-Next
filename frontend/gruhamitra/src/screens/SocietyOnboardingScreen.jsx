import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { INDIAN_STATES_AND_UTS, matchIndianState } from '../constants/indiaAddress';
import api from '../services/api';
import { authService } from '../services/authService';

const EMPTY_FORM = {
  society_name: '',
  address_line1: '',
  address_line2: '',
  pincode: '',
  district: '',
  state: '',
  country: 'India',
  authority_designation: '',
  authority_designation_other: '',
  admin_name: '',
  admin_email: '',
  admin_phone: '',
  request_intent: 'register',
  selected_plan: 'Decide after demo',
  plan_timing: 'After demo/discussion',
  verification_channel: 'email',
  terms_accepted: false,
};

const SocietyOnboardingScreen = () => {
  const location = useLocation();
  const initialIntent = new URLSearchParams(location.search || '').get('intent') === 'demo' ? 'demo' : 'register';
  const [formData, setFormData] = useState({
    ...EMPTY_FORM,
    request_intent: initialIntent,
  });
  const [loading, setLoading] = useState(false);
  const [pincodeLookupBusy, setPincodeLookupBusy] = useState(false);
  const [pincodeLookupHint, setPincodeLookupHint] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const lookupPincode = async (pincode) => {
    if (!/^\d{6}$/.test(pincode)) {
      return;
    }
    setPincodeLookupBusy(true);
    setPincodeLookupHint('');
    try {
      const response = await api.get(`/public/location/pincode/${pincode}`, {
        skipAuthRedirect: true,
      });
      const data = response?.data || {};
      if (!data.found) {
        setPincodeLookupHint('Could not auto-fill from this PIN. Enter district and state manually.');
        return;
      }
      const matchedState = matchIndianState(data.state);
      const district = String(data.district || data.city || '').trim();
      setFormData((prev) => ({
        ...prev,
        district: district || prev.district,
        state: matchedState || prev.state,
        country: 'India',
      }));
      if (!district || !matchedState) {
        setPincodeLookupHint('PIN found, but please confirm district and state.');
      }
    } catch (err) {
      // Keep manual district/state entry if lookup fails.
      console.warn('PIN code lookup failed', err);
      setPincodeLookupHint('Could not auto-fill from this PIN. Enter district and state manually.');
    } finally {
      setPincodeLookupBusy(false);
    }
  };

  const handlePincodeChange = (e) => {
    const digits = String(e.target.value || '').replace(/\D/g, '').slice(0, 6);
    setFormData((prev) => ({ ...prev, pincode: digits }));
    setPincodeLookupHint('');
    if (digits.length === 6) {
      lookupPincode(digits);
    }
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
    if (formData.authority_designation === 'Other' && !formData.authority_designation_other) {
      setError('Please enter the designation or authority for Other');
      return;
    }
    if (formData.pincode && !/^\d{6}$/.test(formData.pincode)) {
      setError('PIN code must be 6 digits');
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
        address_line1: formData.address_line1 || undefined,
        address_line2: formData.address_line2 || undefined,
        pincode: formData.pincode || undefined,
        district: formData.district || undefined,
        state: formData.state || undefined,
        country: formData.country || 'India',
        authority_designation: formData.authority_designation,
        authority_designation_other: formData.authority_designation === 'Other' ? formData.authority_designation_other : undefined,
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
      setFormData({ ...EMPTY_FORM, request_intent: initialIntent, country: 'India' });
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Society onboarding failed';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: '560px' }}>
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
            <label className="login-label">Address Line 1</label>
            <input
              type="text"
              name="address_line1"
              className="login-input"
              value={formData.address_line1}
              onChange={handleChange}
              placeholder="Door no. / Apartment name"
              maxLength={200}
            />
          </div>

          <div className="login-input-container">
            <label className="login-label">Address Line 2</label>
            <input
              type="text"
              name="address_line2"
              className="login-input"
              value={formData.address_line2}
              onChange={handleChange}
              placeholder="Complete address"
              maxLength={500}
            />
          </div>

          <div
            className="login-input-container"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}
          >
            <div>
              <label className="login-label">PIN Code</label>
              <input
                type="text"
                name="pincode"
                className="login-input"
                value={formData.pincode}
                onChange={handlePincodeChange}
                inputMode="numeric"
                autoComplete="postal-code"
                placeholder="6-digit PIN"
                maxLength={6}
              />
              {pincodeLookupBusy ? (
                <span className="login-footer-text" style={{ display: 'block', marginTop: 4 }}>
                  Looking up district and state…
                </span>
              ) : null}
              {!pincodeLookupBusy && pincodeLookupHint ? (
                <span className="login-footer-text" style={{ display: 'block', marginTop: 4 }}>
                  {pincodeLookupHint}
                </span>
              ) : null}
            </div>
            <div>
              <label className="login-label">District</label>
              <input
                type="text"
                name="district"
                className="login-input"
                value={formData.district}
                onChange={handleChange}
                placeholder="District"
                maxLength={120}
              />
            </div>
          </div>

          <div
            className="login-input-container"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}
          >
            <div>
              <label className="login-label">State</label>
              <select
                name="state"
                className="login-input"
                value={formData.state}
                onChange={handleChange}
              >
                <option value="">Select state</option>
                {INDIAN_STATES_AND_UTS.map((stateName) => (
                  <option key={stateName} value={stateName}>
                    {stateName}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="login-label">Country</label>
              <input
                type="text"
                name="country"
                className="login-input"
                value={formData.country}
                onChange={handleChange}
                placeholder="India"
                maxLength={80}
              />
            </div>
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
            <select
              name="authority_designation"
              className="login-input"
              value={formData.authority_designation}
              onChange={handleChange}
              required
            >
              <option value="">Select designation</option>
              <option value="President">President</option>
              <option value="Secretary">Secretary</option>
              <option value="Treasurer">Treasurer</option>
              <option value="Committee Member">Committee Member</option>
              <option value="Authorized Person">Authorized Person</option>
              <option value="Manager">Manager</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {formData.authority_designation === 'Other' && (
            <div className="login-input-container">
              <label className="login-label">Other Designation / Authority *</label>
              <input
                type="text"
                name="authority_designation_other"
                className="login-input"
                value={formData.authority_designation_other}
                onChange={handleChange}
                required
                maxLength={120}
              />
            </div>
          )}

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
