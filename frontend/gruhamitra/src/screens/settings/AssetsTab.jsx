import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const AssetsTab = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const [assets, setAssets] = useState([]);
  const [vendors, setVendors] = useState([]);

  const [assetForm, setAssetForm] = useState({
    name: '',
    type: 'Lift',
    installationDate: '',
    warrantyExpiry: ''
  });

  const [vendorForm, setVendorForm] = useState({
    name: '',
    serviceType: 'Security',
    startDate: '',
    endDate: '',
    reminderDays: 30
  });

  const [notifications, setNotifications] = useState({
    sendAMCReminders: true,
    sendExpiryAlerts: true
  });

  useEffect(() => {
    loadAssetConfig();
  }, []);

  const loadAssetConfig = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings && settings.asset_config) {
        const config = settings.asset_config;
        setAssets(config.assets || []);
        setVendors(config.vendors || []);
        setNotifications({
          sendAMCReminders: config.sendAMCReminders ?? true,
          sendExpiryAlerts: config.sendExpiryAlerts ?? true
        });
      }
    } catch (error) {
      console.error('Error loading asset config:', error);
      setMessage({ type: 'error', text: 'Failed to load asset configuration.' });
    } finally {
      setLoading(false);
    }
  };

  const handleAddAsset = () => {
    if (!assetForm.name.trim()) {
      setMessage({ type: 'error', text: 'Asset Name is required' });
      return;
    }
    setAssets([...assets, { ...assetForm, id: Date.now() }]);
    setAssetForm({
      name: '',
      type: 'Lift',
      installationDate: '',
      warrantyExpiry: ''
    });
    setMessage({ type: 'info', text: 'Asset added to list. Click Save Changes to persist.' });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleAddVendor = () => {
    if (!vendorForm.name.trim()) {
      setMessage({ type: 'error', text: 'Vendor Name is required' });
      return;
    }
    setVendors([...vendors, { ...vendorForm, id: Date.now() }]);
    setVendorForm({
      name: '',
      serviceType: 'Security',
      startDate: '',
      endDate: '',
      reminderDays: 30
    });
    setMessage({ type: 'info', text: 'Vendor added to list. Click Save Changes to persist.' });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleRemoveAsset = (id) => {
    setAssets(assets.filter(a => a.id !== id));
  };

  const handleRemoveVendor = (id) => {
    setVendors(vendors.filter(v => v.id !== id));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      const asset_config = {
        assets,
        vendors,
        ...notifications
      };
      await settingsService.saveSocietySettings({ asset_config });
      setMessage({ type: 'success', text: 'Asset & Vendor settings saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving asset config:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Assets & Vendor Management</h2>
      <p className="settings-tab-description">Manage society assets and vendors</p>

      {message.text && (
        <div className={`settings-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <p>Loading configuration...</p>
      ) : (
        <>
          <div className="settings-section">
            <h3>Society Assets</h3>

            {/* Asset List */}
            {assets.length > 0 && (
              <div className="settings-table-container" style={{ marginBottom: '20px' }}>
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Installation</th>
                      <th>Warranty</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map(asset => (
                      <tr key={asset.id}>
                        <td>{asset.name}</td>
                        <td>{asset.type}</td>
                        <td>{asset.installationDate || '-'}</td>
                        <td>{asset.warrantyExpiry || '-'}</td>
                        <td>
                          <button onClick={() => handleRemoveAsset(asset.id)} style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer' }}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Asset Name</label>
                  <input
                    type="text"
                    placeholder="Lift 1, Generator, etc"
                    value={assetForm.name}
                    onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Asset Type</label>
                  <select
                    value={assetForm.type}
                    onChange={(e) => setAssetForm({ ...assetForm, type: e.target.value })}
                  >
                    <option>Lift</option>
                    <option>Generator</option>
                    <option>Water Pump</option>
                    <option>CCTV</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Installation Date</label>
                  <input
                    type="date"
                    value={assetForm.installationDate}
                    onChange={(e) => setAssetForm({ ...assetForm, installationDate: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Warranty Expiry</label>
                  <input
                    type="date"
                    value={assetForm.warrantyExpiry}
                    onChange={(e) => setAssetForm({ ...assetForm, warrantyExpiry: e.target.value })}
                  />
                </div>
              </div>
              <button
                type="button"
                className="settings-add-btn"
                onClick={handleAddAsset}
                style={{ width: 'fit-content' }}
              >
                + Add Asset to List
              </button>
            </div>
          </div>

          <div className="settings-section">
            <h3>Vendor Management</h3>

            {/* Vendor List */}
            {vendors.length > 0 && (
              <div className="settings-table-container" style={{ marginBottom: '20px' }}>
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Service</th>
                      <th>Contract End</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vendors.map(vendor => (
                      <tr key={vendor.id}>
                        <td>{vendor.name}</td>
                        <td>{vendor.serviceType}</td>
                        <td>{vendor.endDate || '-'}</td>
                        <td>
                          <button onClick={() => handleRemoveVendor(vendor.id)} style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer' }}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Vendor Name</label>
                  <input
                    type="text"
                    placeholder="Vendor name"
                    value={vendorForm.name}
                    onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Service Type</label>
                  <select
                    value={vendorForm.serviceType}
                    onChange={(e) => setVendorForm({ ...vendorForm, serviceType: e.target.value })}
                  >
                    <option>Security</option>
                    <option>Housekeeping</option>
                    <option>AMC</option>
                    <option>Maintenance</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Contract Start Date</label>
                  <input
                    type="date"
                    value={vendorForm.startDate}
                    onChange={(e) => setVendorForm({ ...vendorForm, startDate: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Contract End Date</label>
                  <input
                    type="date"
                    value={vendorForm.endDate}
                    onChange={(e) => setVendorForm({ ...vendorForm, endDate: e.target.value })}
                  />
                </div>
              </div>
              <div className="settings-form-group">
                <label>Reminder Before Expiry (days)</label>
                <input
                  type="number"
                  value={vendorForm.reminderDays}
                  onChange={(e) => setVendorForm({ ...vendorForm, reminderDays: parseInt(e.target.value) || 0 })}
                />
              </div>
              <button
                type="button"
                className="settings-add-btn"
                onClick={handleAddVendor}
                style={{ width: 'fit-content' }}
              >
                + Add Vendor to List
              </button>
            </div>
          </div>

          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={notifications.sendAMCReminders}
                onChange={(e) => setNotifications({ ...notifications, sendAMCReminders: e.target.checked })}
              />
              <span>Send AMC renewal reminders</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={notifications.sendExpiryAlerts}
                onChange={(e) => setNotifications({ ...notifications, sendExpiryAlerts: e.target.checked })}
              />
              <span>Send contract expiry alerts</span>
            </label>
          </div>

          <div className="settings-form-actions" style={{ marginTop: '30px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
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

export default AssetsTab;
