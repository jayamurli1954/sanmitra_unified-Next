import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { authService } from '../../services/authService';
import { getErrorMessage, uploadSocietyLogoWithFallback } from './settingsHelpers';

const SocietyProfileTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    society_name: '',
    registration_number: '',
    registration_date: '',
    pan: '',
    gst_number: '',
    address: '',
    city: '',
    state: '',
    pin_code: '',
    contact_email: '',
    contact_phone: '',
    bank_account_number: '',
    bank_account_name: '',
    bank_ifsc: '',
    bank_name: '',
    financial_year_start: 'apr-mar',
    logo_url: '',
  });

  const [logoFile, setLogoFile] = useState(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          society_name: settings.society_name || '',
          registration_number: settings.registration_number || '',
          registration_date: '', // Not in API response
          pan: '', // Not in API response
          gst_number: settings.gst_number || '',
          address: settings.society_address || '',
          city: settings.city || '',
          state: settings.state || '',
          pin_code: settings.pin_code || '',
          contact_email: settings.contact_email || '',
          contact_phone: settings.contact_phone || '',
          bank_account_number: settings.bank_accounts?.[0]?.account_number || '',
          bank_account_name: settings.bank_accounts?.[0]?.account_name || '',
          bank_ifsc: settings.bank_accounts?.[0]?.ifsc_code || '',
          bank_name: settings.bank_accounts?.[0]?.bank_name || '',
          financial_year_start: settings.financial_year_start || 'apr-mar',
          logo_url: settings.logo_url || '',
        });
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to load settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const handleLogoUpload = async () => {
    if (!logoFile) {
      setMessage({ type: 'error', text: 'Please select a logo file first' });
      return;
    }

    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(logoFile.type)) {
      setMessage({ type: 'error', text: 'Only PNG and JPG files are allowed' });
      return;
    }

    if (logoFile.size > 2 * 1024 * 1024) {
      setMessage({ type: 'error', text: 'Logo file must be less than 2MB' });
      return;
    }

    setUploadingLogo(true);
    setMessage({ type: 'info', text: 'Uploading logo...' });

    try {
      const result = await uploadSocietyLogoWithFallback(logoFile);
      setMessage({ type: 'success', text: 'Logo uploaded successfully!' });

      if (result.logo_url) {
        setFormData(prev => ({ ...prev, logo_url: result.logo_url }));
      }

      setLogoFile(null);
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Logo upload failed:', error);
      setMessage({ type: 'error', text: 'Upload failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    if (!formData.society_name.trim()) {
      setMessage({ type: 'error', text: 'Society Name is required' });
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const settingsData = {
        society_name: formData.society_name.trim(),
        registration_number: formData.registration_number.trim() || undefined,
        society_address: formData.address.trim() || undefined,
        city: formData.city.trim() || undefined,
        state: formData.state.trim() || undefined,
        pin_code: formData.pin_code.trim() || undefined,
        pan_no: formData.pan.trim() || undefined,
        contact_email: formData.contact_email.trim() || undefined,
        contact_phone: formData.contact_phone.trim() || undefined,
        gst_number: formData.gst_number.trim() || undefined,
        logo_url: formData.logo_url.trim() || undefined,
      };

      // Add bank account if provided
      if (formData.bank_account_number || formData.bank_ifsc || formData.bank_name) {
        settingsData.bank_accounts = [{
          account_name: (formData.bank_account_name || formData.society_name).trim(),
          account_number: formData.bank_account_number.trim(),
          ifsc_code: formData.bank_ifsc.trim(),
          bank_name: formData.bank_name.trim(),
        }];
      }

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Society profile saved successfully!' });

      // Keep header/UI in sync without requiring logout/login.
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser && authService.updateStoredUser) {
          await authService.updateStoredUser({
            ...currentUser,
            society_name: settingsData.society_name,
          });
        }
      } catch (syncError) {
        console.warn('Could not sync updated society name to local user cache:', syncError);
      }

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Society Profile</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading society profile...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Society Profile</h2>
      <p className="settings-tab-description">Basic legal & identity information</p>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{message.type === 'success' ? '' : ''}</span>
          <span>{message.text}</span>
        </div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-form-group">
          <label>Society Name *</label>
          <input
            type="text"
            placeholder="Enter society name"
            value={formData.society_name}
            onChange={(e) => setFormData(prev => ({ ...prev, society_name: e.target.value }))}
            required
          />
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Registration Number</label>
            <input
              type="text"
              placeholder="Registration number"
              value={formData.registration_number}
              onChange={(e) => setFormData(prev => ({ ...prev, registration_number: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Registration Date</label>
            <input
              type="date"
              value={formData.registration_date}
              onChange={(e) => setFormData(prev => ({ ...prev, registration_date: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>PAN</label>
            <input
              type="text"
              placeholder="PAN number"
              maxLength="10"
              value={formData.pan}
              onChange={(e) => setFormData(prev => ({ ...prev, pan: e.target.value.toUpperCase() }))}
            />
          </div>
          <div className="settings-form-group">
            <label>GST (if applicable)</label>
            <input
              type="text"
              placeholder="GST number"
              value={formData.gst_number}
              onChange={(e) => setFormData(prev => ({ ...prev, gst_number: e.target.value.toUpperCase() }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Address</label>
          <textarea
            rows="3"
            placeholder="Complete address"
            value={formData.address}
            onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
          ></textarea>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>City</label>
            <input
              type="text"
              placeholder="City"
              value={formData.city}
              onChange={(e) => setFormData(prev => ({ ...prev, city: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>State</label>
            <input
              type="text"
              placeholder="State"
              value={formData.state}
              onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>PIN Code</label>
            <input
              type="text"
              placeholder="PIN"
              maxLength="6"
              value={formData.pin_code}
              onChange={(e) => setFormData(prev => ({ ...prev, pin_code: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Contact Email</label>
            <input
              type="email"
              placeholder="society@example.com"
              value={formData.contact_email}
              onChange={(e) => setFormData(prev => ({ ...prev, contact_email: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Contact Phone</label>
            <input
              type="tel"
              placeholder="+91 9876543210"
              value={formData.contact_phone}
              onChange={(e) => setFormData(prev => ({ ...prev, contact_phone: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Bank Account Details</label>
          <div className="settings-form-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            <input
              type="text"
              placeholder="Account Name (e.g. Society Name)"
              value={formData.bank_account_name}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_account_name: e.target.value }))}
            />
            <input
              type="text"
              placeholder="Account Number"
              value={formData.bank_account_number}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_account_number: e.target.value }))}
            />
            <input
              type="text"
              placeholder="IFSC Code"
              value={formData.bank_ifsc}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_ifsc: e.target.value.toUpperCase() }))}
            />
            <input
              type="text"
              placeholder="Bank Name"
              value={formData.bank_name}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_name: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Society Logo</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg"
            onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
          />
          <button
            type="button"
            onClick={handleLogoUpload}
            disabled={!logoFile || uploadingLogo}
            className="settings-action-btn"
            style={{
              marginTop: '10px',
              backgroundColor: uploadingLogo ? '#ccc' : '#4CAF50',
              cursor: uploadingLogo || !logoFile ? 'not-allowed' : 'pointer',
            }}
          >
            {uploadingLogo ? 'Uploading...' : 'Upload Logo'}
          </button>
          <small>Upload society logo (PNG, JPG, max 2MB). The logo will appear on receipts and reports.</small>
        </div>

        <div className="settings-form-group">
          <label>Financial Year Start</label>
          <select
            value={formData.financial_year_start}
            onChange={(e) => setFormData(prev => ({ ...prev, financial_year_start: e.target.value }))}
          >
            <option value="apr-mar">April - March</option>
            <option value="jan-dec">January - December</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <div className="settings-form-actions">
          <button
            type="submit"
            className="settings-save-btn"
            disabled={saving}
            style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            className="settings-cancel-btn"
            onClick={() => loadSettings()}
            disabled={saving}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default SocietyProfileTab;
