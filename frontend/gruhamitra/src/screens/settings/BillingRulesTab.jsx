import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const BillingRulesTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    maintenance_calculation_logic: 'mixed', // 'sqft', 'fixed', 'water_based', 'mixed'
    maintenance_rate_sqft: 0,
    maintenance_rate_flat: 0,
    sinking_fund_rate: 0,
    repair_fund_rate: 0,
    association_fund_rate: 0,
    corpus_fund_rate: 0,
    water_calculation_type: 'person', // 'flat', 'person', 'meter'
    water_rate_per_person: 0,
    water_min_charge: 0,
    expense_distribution_logic: 'equal', // 'equal', 'sqft'
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
          maintenance_calculation_logic: settings.maintenance_calculation_logic || 'mixed',
          maintenance_rate_sqft: settings.maintenance_rate_sqft || 0,
          maintenance_rate_flat: settings.maintenance_rate_flat || 0,
          sinking_fund_rate: settings.sinking_fund_rate || 0,
          repair_fund_rate: settings.repair_fund_rate || 0,
          association_fund_rate: settings.association_fund_rate || 0,
          corpus_fund_rate: settings.corpus_fund_rate || 0,
          water_calculation_type: settings.water_calculation_type || 'person',
          water_rate_per_person: settings.water_rate_per_person || 0,
          water_min_charge: settings.water_min_charge || 0,
          expense_distribution_logic: settings.expense_distribution_logic || 'equal',
        });
      }
    } catch (error) {
      console.error('Error loading billing rules:', error);
      setMessage({ type: 'error', text: 'Failed to load billing rules. Please try again.' });
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
        maintenance_calculation_logic: formData.maintenance_calculation_logic,
        maintenance_rate_sqft: parseFloat(formData.maintenance_rate_sqft) || 0,
        maintenance_rate_flat: parseFloat(formData.maintenance_rate_flat) || 0,
        sinking_fund_rate: parseFloat(formData.sinking_fund_rate) || 0,
        repair_fund_rate: parseFloat(formData.repair_fund_rate) || 0,
        association_fund_rate: parseFloat(formData.association_fund_rate) || 0,
        corpus_fund_rate: parseFloat(formData.corpus_fund_rate) || 0,
        water_calculation_type: formData.water_calculation_type,
        water_rate_per_person: parseFloat(formData.water_rate_per_person) || 0,
        water_min_charge: parseFloat(formData.water_min_charge) || 0,
        expense_distribution_logic: formData.expense_distribution_logic,
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Billing rules saved successfully!' });
      await loadSettings();

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving billing rules:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save billing rules. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Billing Rules</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading billing rules...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Billing Rules</h2>
      <p className="settings-tab-description">Configure billing and charges</p>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
        }}>
          {message.text}
        </div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-section">
          <h3>Maintenance Calculation Method</h3>
          <div className="settings-form-group">
            <label>Calculation Logic *</label>
            <select
              value={formData.maintenance_calculation_logic}
              onChange={(e) => setFormData({ ...formData, maintenance_calculation_logic: e.target.value })}
              required
            >
              <option value="sqft">Square Feet Based</option>
              <option value="fixed">Fixed per Flat</option>
              <option value="water_based">Water Based</option>
              <option value="mixed">Mixed (Sqft + Water + Fixed Expenses)</option>
            </select>
            <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
              Mixed method: Maintenance (sqft) + Water (per person) + Fixed Expenses + Funds
            </small>
          </div>
        </div>

        <div className="settings-section">
          <h3>Fixed Charges</h3>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Rate per Sq.ft ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.maintenance_rate_sqft}
                onChange={(e) => setFormData({ ...formData, maintenance_rate_sqft: e.target.value })}
                placeholder="5.00"
              />
            </div>
            <div className="settings-form-group">
              <label>Maintenance per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.maintenance_rate_flat}
                onChange={(e) => setFormData({ ...formData, maintenance_rate_flat: e.target.value })}
                placeholder="500"
              />
            </div>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Sinking Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.sinking_fund_rate}
                onChange={(e) => setFormData({ ...formData, sinking_fund_rate: e.target.value })}
                placeholder="200"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
            <div className="settings-form-group">
              <label>Repair Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.repair_fund_rate}
                onChange={(e) => setFormData({ ...formData, repair_fund_rate: e.target.value })}
                placeholder="300"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Association Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.association_fund_rate}
                onChange={(e) => setFormData({ ...formData, association_fund_rate: e.target.value })}
                placeholder="100"
              />
            </div>
            <div className="settings-form-group">
              <label>Corpus Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.corpus_fund_rate}
                onChange={(e) => setFormData({ ...formData, corpus_fund_rate: e.target.value })}
                placeholder="150"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3>Water Billing</h3>
          <div className="settings-form-group">
            <label>Water Calculation Type</label>
            <select
              value={formData.water_calculation_type}
              onChange={(e) => setFormData({ ...formData, water_calculation_type: e.target.value })}
            >
              <option value="flat">Per Flat</option>
              <option value="person">Per Person</option>
              <option value="meter">Per Meter</option>
            </select>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Water Rate per Person ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.water_rate_per_person}
                onChange={(e) => setFormData({ ...formData, water_rate_per_person: e.target.value })}
                placeholder="200"
              />
            </div>
            <div className="settings-form-group">
              <label>Minimum Charge per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.water_min_charge}
                onChange={(e) => setFormData({ ...formData, water_min_charge: e.target.value })}
                placeholder="200"
              />
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3>Shared Expense Distribution</h3>
          <div className="settings-form-group">
            <label>Distribution Method</label>
            <select
              value={formData.expense_distribution_logic}
              onChange={(e) => setFormData({ ...formData, expense_distribution_logic: e.target.value })}
            >
              <option value="equal">Equal to all flats</option>
              <option value="sqft">Proportionate to sq.ft</option>
            </select>
          </div>
        </div>

        <div className="settings-form-actions">
          <button type="submit" className="settings-save-btn" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default BillingRulesTab;
