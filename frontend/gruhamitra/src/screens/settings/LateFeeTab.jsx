import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const LateFeeTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    bill_due_days: 5, // Due date of month
    late_payment_grace_days: 10,
    late_payment_penalty_type: 'fixed', // 'fixed' or 'percentage'
    late_payment_penalty_value: 5,
    late_fee_frequency: 'one-time', // Not in API, keeping for UI
    interest_on_overdue: false,
    interest_rate: 1.5,
    max_penalty_cap: 1000, // Not in API, keeping for UI
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
          bill_due_days: settings.bill_due_days || 5,
          late_payment_grace_days: settings.late_payment_grace_days || 10,
          late_payment_penalty_type: settings.late_payment_penalty_type || 'fixed',
          late_payment_penalty_value: settings.late_payment_penalty_value || 5,
          late_fee_frequency: 'one-time', // Not in API
          interest_on_overdue: settings.interest_on_overdue || false,
          interest_rate: settings.interest_rate || 1.5,
          max_penalty_cap: 1000, // Not in API
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
      // Validate penalty value if penalty type is set
      if (formData.late_payment_penalty_type && (!formData.late_payment_penalty_value || formData.late_payment_penalty_value <= 0)) {
        setMessage({ type: 'error', text: 'Late Fee Amount/Percentage must be greater than 0' });
        setSaving(false);
        return;
      }

      // Validate interest rate if interest is enabled
      if (formData.interest_on_overdue && (!formData.interest_rate || formData.interest_rate <= 0)) {
        setMessage({ type: 'error', text: 'Interest Rate must be greater than 0 when interest on arrears is enabled' });
        setSaving(false);
        return;
      }

      const settingsData = {
        bill_due_days: parseInt(formData.bill_due_days) || 5,
        late_payment_grace_days: parseInt(formData.late_payment_grace_days) || 0,
        late_payment_penalty_type: formData.late_payment_penalty_type,
        late_payment_penalty_value: parseFloat(formData.late_payment_penalty_value) || undefined,
        interest_on_overdue: formData.interest_on_overdue,
        interest_rate: formData.interest_on_overdue ? parseFloat(formData.interest_rate) : undefined,
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Late fee & penalties configuration saved successfully!' });
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
        <h2 className="settings-tab-title">Late Fee & Penalties</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading late fee configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Late Fee & Penalties</h2>
      <p className="settings-tab-description">Configure late payment charges</p>

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
          <label>Due Date of Every Month</label>
          <input
            type="number"
            min="1"
            max="31"
            value={formData.bill_due_days}
            onChange={(e) => setFormData(prev => ({ ...prev, bill_due_days: e.target.value }))}
          />
          <small>Day of month when bills are due</small>
        </div>

        <div className="settings-form-group">
          <label>Grace Period (days)</label>
          <input
            type="number"
            min="0"
            value={formData.late_payment_grace_days}
            onChange={(e) => setFormData(prev => ({ ...prev, late_payment_grace_days: e.target.value }))}
          />
          <small>Days after due date before late fee applies</small>
        </div>

        <div className="settings-form-group">
          <label>Late Fee Type</label>
          <select
            value={formData.late_payment_penalty_type}
            onChange={(e) => setFormData(prev => ({ ...prev, late_payment_penalty_type: e.target.value }))}
          >
            <option value="fixed">Flat Amount</option>
            <option value="percentage">Percentage of Bill</option>
          </select>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Late Fee Amount / Percentage</label>
            <input
              type="number"
              placeholder={formData.late_payment_penalty_type === 'fixed' ? "500" : "5"}
              step={formData.late_payment_penalty_type === 'percentage' ? "0.01" : "1"}
              value={formData.late_payment_penalty_value}
              onChange={(e) => setFormData(prev => ({ ...prev, late_payment_penalty_value: e.target.value }))}
            />
            <small>{formData.late_payment_penalty_type === 'fixed' ? 'Enter amount in ' : 'Enter percentage (e.g., 5 for 5%)'}</small>
          </div>
          <div className="settings-form-group">
            <label>Late Fee Frequency</label>
            <select
              value={formData.late_fee_frequency}
              onChange={(e) => setFormData(prev => ({ ...prev, late_fee_frequency: e.target.value }))}
            >
              <option value="one-time">One-time</option>
              <option value="monthly">Monthly</option>
              <option value="daily">Daily</option>
            </select>
            <small style={{ color: '#666', fontSize: '11px' }}>Note: Frequency setting is for display only</small>
          </div>
        </div>

        <div className="settings-checkbox-group">
          <label className="settings-checkbox">
            <input
              type="checkbox"
              checked={formData.interest_on_overdue}
              onChange={(e) => setFormData(prev => ({ ...prev, interest_on_overdue: e.target.checked }))}
            />
            <span>Apply interest on arrears</span>
          </label>
        </div>

        <div className="settings-form-group">
          <label>Interest Rate on Arrears (% per month)</label>
          <input
            type="number"
            step="0.1"
            placeholder="1.5"
            value={formData.interest_rate}
            onChange={(e) => setFormData(prev => ({ ...prev, interest_rate: e.target.value }))}
            disabled={!formData.interest_on_overdue}
            style={{ opacity: formData.interest_on_overdue ? 1 : 0.6 }}
          />
        </div>

        <div className="settings-form-group">
          <label>Maximum Penalty Cap ()</label>
          <input
            type="number"
            placeholder="5000"
            value={formData.max_penalty_cap}
            onChange={(e) => setFormData(prev => ({ ...prev, max_penalty_cap: e.target.value }))}
          />
          <small>Maximum total penalty that can be charged (Note: This setting is for display only)</small>
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

export default LateFeeTab;
