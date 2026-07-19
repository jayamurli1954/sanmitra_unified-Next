import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const MemberConfigTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    max_members_per_flat: 4,
    messaging_members_per_flat: 3,
    pan_mandatory: true,
    aadhaar_mandatory: true,
    sale_deed_required: true,
    rent_agreement_required: true,
    tenant_expiry_reminder_days: 30,
    approval_workflow: 'auto', // 'auto' or 'admin'
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          max_members_per_flat: settings.max_members_per_flat || 4,
          messaging_members_per_flat: settings.messaging_members_per_flat || 3,
          pan_mandatory: settings.pan_mandatory ?? true,
          aadhaar_mandatory: settings.aadhaar_mandatory ?? true,
          sale_deed_required: settings.sale_deed_required ?? true,
          rent_agreement_required: settings.rent_agreement_required ?? true,
          tenant_expiry_reminder_days: settings.tenant_expiry_reminder_days || 30,
          approval_workflow: settings.member_approval_required ? 'admin' : 'auto',
        });
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const settingsData = {
        max_members_per_flat: parseInt(formData.max_members_per_flat) || 4,
        messaging_members_per_flat: parseInt(formData.messaging_members_per_flat) || 3,
        pan_mandatory: !!formData.pan_mandatory,
        aadhaar_mandatory: !!formData.aadhaar_mandatory,
        sale_deed_required: !!formData.sale_deed_required,
        rent_agreement_required: !!formData.rent_agreement_required,
        tenant_expiry_reminder_days: parseInt(formData.tenant_expiry_reminder_days) || 30,
        member_approval_required: formData.approval_workflow === 'admin',
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Member configuration saved successfully!' });
      await loadSettings();

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
        <h2 className="settings-tab-title">Member Configuration</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading member configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Member Configuration</h2>
      <p className="settings-tab-description">Resident governance rules</p>

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
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Allowed Family Members per Flat</label>
            <input
              type="number"
              min="1"
              value={formData.max_members_per_flat}
              onChange={(e) => setFormData(prev => ({ ...prev, max_members_per_flat: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Messaging Members per Flat (default)</label>
            <input
              type="number"
              min="1"
              value={formData.messaging_members_per_flat}
              onChange={(e) => setFormData(prev => ({ ...prev, messaging_members_per_flat: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-section">
          <h3>Document Requirements</h3>
          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.pan_mandatory}
                onChange={(e) => setFormData(prev => ({ ...prev, pan_mandatory: e.target.checked }))}
              />
              <span>PAN mandatory for owners</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.aadhaar_mandatory}
                onChange={(e) => setFormData(prev => ({ ...prev, aadhaar_mandatory: e.target.checked }))}
              />
              <span>Aadhaar mandatory</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.sale_deed_required}
                onChange={(e) => setFormData(prev => ({ ...prev, sale_deed_required: e.target.checked }))}
              />
              <span>Sale deed required for owners</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.rent_agreement_required}
                onChange={(e) => setFormData(prev => ({ ...prev, rent_agreement_required: e.target.checked }))}
              />
              <span>Rent agreement required for tenants</span>
            </label>
          </div>
        </div>

        <div className="settings-form-group">
          <label>Tenant Validity Expiry Reminder (days before)</label>
          <input
            type="number"
            min="1"
            value={formData.tenant_expiry_reminder_days}
            onChange={(e) => setFormData(prev => ({ ...prev, tenant_expiry_reminder_days: e.target.value }))}
          />
        </div>

        <div className="settings-form-group">
          <label>Approval Workflow</label>
          <select
            value={formData.approval_workflow}
            onChange={(e) => setFormData(prev => ({ ...prev, approval_workflow: e.target.value }))}
          >
            <option value="auto">Auto-approve</option>
            <option value="admin">Admin approval required</option>
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

export default MemberConfigTab;
