import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const ComplaintsTab = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [categories, setCategories] = useState(['Lift', 'Water', 'Security', 'Plumbing', 'Electricity']);
  const [newCategory, setNewCategory] = useState('');

  const [formData, setFormData] = useState({
    sla_low_priority_days: 7,
    sla_medium_priority_days: 3,
    sla_high_priority_hours: 24,
    escalation_days: 5,
    escalate_to: 'Secretary',
    auto_close_resolved: false
  });

  useEffect(() => {
    loadComplaintSettings();
  }, []);

  const loadComplaintSettings = async () => {
    setLoading(true);
    try {
      const response = await settingsService.getSocietySettings();
      const complaintConfig = response.complaint_config || {};

      if (complaintConfig.categories) {
        setCategories(complaintConfig.categories);
      }

      setFormData({
        sla_low_priority_days: complaintConfig.sla_low_priority_days || 7,
        sla_medium_priority_days: complaintConfig.sla_medium_priority_days || 3,
        sla_high_priority_hours: complaintConfig.sla_high_priority_hours || 24,
        escalation_days: complaintConfig.escalation_days || 5,
        escalate_to: complaintConfig.escalate_to || 'Secretary',
        auto_close_resolved: complaintConfig.auto_close_resolved || false
      });
    } catch (error) {
      console.error('Error loading complaint settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCategory = () => {
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setCategories([...categories, newCategory.trim()]);
      setNewCategory('');
    }
  };

  const handleRemoveCategory = (category) => {
    setCategories(categories.filter(c => c !== category));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const complaintConfig = {
        categories: categories,
        sla_low_priority_days: parseInt(formData.sla_low_priority_days) || 7,
        sla_medium_priority_days: parseInt(formData.sla_medium_priority_days) || 3,
        sla_high_priority_hours: parseInt(formData.sla_high_priority_hours) || 24,
        escalation_days: parseInt(formData.escalation_days) || 5,
        escalate_to: formData.escalate_to,
        auto_close_resolved: formData.auto_close_resolved
      };

      await settingsService.saveSocietySettings({ complaint_config: complaintConfig });
      setMessage({ type: 'success', text: 'Complaint settings saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving complaint settings:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Complaints & Helpdesk</h2>
      <p className="settings-tab-description">Configure complaint management</p>

      {message.text && (
        <div className={`settings-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <p>Loading settings...</p>
      ) : (
        <>
          <div className="settings-section">
            <h3>Complaint Categories</h3>
            <div className="settings-form-row" style={{ marginBottom: '10px' }}>
              <div className="settings-form-group" style={{ flex: 1 }}>
                <input
                  type="text"
                  placeholder="Category name (e.g., Lift, Water, Security)"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCategory()}
                />
              </div>
              <button className="settings-add-btn" onClick={handleAddCategory}>+ Add Category</button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
              {categories.map((category, index) => (
                <div key={index} className="settings-badge" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
                  <span>{category}</span>
                  <button
                    onClick={() => handleRemoveCategory(category)}
                    style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer', fontSize: '16px', padding: '0', lineHeight: '1' }}
                  >
                    
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <h3>SLA Timelines</h3>
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Low Priority (days)</label>
                <input
                  type="number"
                  value={formData.sla_low_priority_days}
                  onChange={(e) => setFormData({ ...formData, sla_low_priority_days: e.target.value })}
                />
              </div>
              <div className="settings-form-group">
                <label>Medium Priority (days)</label>
                <input
                  type="number"
                  value={formData.sla_medium_priority_days}
                  onChange={(e) => setFormData({ ...formData, sla_medium_priority_days: e.target.value })}
                />
              </div>
              <div className="settings-form-group">
                <label>High Priority (hours)</label>
                <input
                  type="number"
                  value={formData.sla_high_priority_hours}
                  onChange={(e) => setFormData({ ...formData, sla_high_priority_hours: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="settings-section">
            <h3>Escalation Rules</h3>
            <div className="settings-form-group">
              <label>Auto-escalate after (days)</label>
              <input
                type="number"
                value={formData.escalation_days}
                onChange={(e) => setFormData({ ...formData, escalation_days: e.target.value })}
              />
            </div>
            <div className="settings-form-group">
              <label>Escalate to</label>
              <select
                value={formData.escalate_to}
                onChange={(e) => setFormData({ ...formData, escalate_to: e.target.value })}
              >
                <option>Secretary</option>
                <option>Committee</option>
                <option>Admin</option>
              </select>
            </div>
          </div>

          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.auto_close_resolved}
                onChange={(e) => setFormData({ ...formData, auto_close_resolved: e.target.checked })}
              />
              <span>Auto-close resolved complaints after 7 days</span>
            </label>
          </div>

          <div className="settings-form-actions">
            <button
              className="settings-save-btn"
              onClick={handleSave}
              disabled={saving}
              style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ComplaintsTab;
