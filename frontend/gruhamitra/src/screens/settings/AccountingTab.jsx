import React, { useState, useEffect } from 'react';
import financialYearService from '../../services/financialYearService';
import { getErrorMessage } from './settingsHelpers';

const AccountingTab = () => {
  const [financialYears, setFinancialYears] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showAddForm, setShowAddForm] = useState(false);
  const [newYear, setNewYear] = useState({
    year_name: '',
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    loadFinancialYears();
  }, []);

  const loadFinancialYears = async () => {
    setLoading(true);
    try {
      const years = await financialYearService.listFinancialYears();
      setFinancialYears(years);
    } catch (error) {
      console.error('Error loading financial years:', error);
      setMessage({ type: 'error', text: 'Failed to load financial years' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateYear = async (e) => {
    e.preventDefault();
    if (!newYear.year_name || !newYear.start_date || !newYear.end_date) {
      setMessage({ type: 'error', text: 'Please fill all fields' });
      return;
    }

    setSaving(true);
    try {
      await financialYearService.createFinancialYear(newYear);
      setMessage({ type: 'success', text: 'Financial year created successfully!' });
      setShowAddForm(false);
      setNewYear({ year_name: '', start_date: '', end_date: '' });
      loadFinancialYears();
    } catch (error) {
      console.error('Error creating financial year:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: 'Error: ' + errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Accounting Settings</h2>
      <p className="settings-tab-description">Financial year management & controls</p>

      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : (message.type === 'error' ? '#FFEBEE' : '#E3F2FD'),
          color: message.type === 'success' ? '#2E7D32' : (message.type === 'error' ? '#C62828' : '#1565C0'),
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : (message.type === 'error' ? '#EF5350' : '#2196F3')}`,
        }}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Financial Years</h3>
          <button
            className="settings-add-btn"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : '+ Add New Financial Year'}
          </button>
        </div>

        {showAddForm && (
          <form className="settings-form" onSubmit={handleCreateYear} style={{ marginBottom: '25px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Year Name (e.g. FY 2025-26)</label>
                <input
                  type="text"
                  value={newYear.year_name}
                  onChange={(e) => setNewYear({ ...newYear, year_name: e.target.value })}
                  placeholder="FY 2025-26"
                  required
                />
              </div>
              <div className="settings-form-group">
                <label>Start Date</label>
                <input
                  type="date"
                  value={newYear.start_date}
                  onChange={(e) => setNewYear({ ...newYear, start_date: e.target.value })}
                  required
                />
              </div>
              <div className="settings-form-group">
                <label>End Date</label>
                <input
                  type="date"
                  value={newYear.end_date}
                  onChange={(e) => setNewYear({ ...newYear, end_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <button type="submit" className="settings-save-btn" disabled={saving}>
              {saving ? 'Creating...' : 'Create Financial Year'}
            </button>
          </form>
        )}

        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Year Name</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Status</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="5" style={{ textAlign: 'center' }}>Loading...</td></tr>
              ) : financialYears.length === 0 ? (
                <tr><td colSpan="5" style={{ textAlign: 'center' }}>No financial years found. Create one to start accounting.</td></tr>
              ) : (
                financialYears.map(year => (
                  <tr key={year.id}>
                    <td><strong>{year.year_name}</strong></td>
                    <td>{year.start_date}</td>
                    <td>{year.end_date}</td>
                    <td>
                      <span className={`settings-badge status-${year.status.toLowerCase()}`}>
                        {year.status}
                      </span>
                    </td>
                    <td>
                      {year.is_active ? ' Active' : 'Inactive'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="settings-section">
        <h3>Accounting Controls</h3>
        <div className="settings-checkbox-group">
          <label className="settings-checkbox">
            <input type="checkbox" readOnly checked={financialYears.some(y => y.is_active && y.is_closed)} />
            <span>Lock current financial year (prevent modifications)</span>
          </label>
        </div>
      </div>
    </div>
  );
};

export default AccountingTab;
