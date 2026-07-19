import React from 'react';

const NotificationsTab = () => (
  <div className="settings-tab-content">
    <h2 className="settings-tab-title">Notifications & Communication</h2>
    <p className="settings-tab-description">Configure member engagement</p>

    <div className="settings-section">
      <h3>SMS Provider</h3>
      <div className="settings-form">
        <div className="settings-form-group">
          <label>Provider</label>
          <select>
            <option value="">Select Provider</option>
            <option value="twilio">Twilio</option>
            <option value="msg91">MSG91</option>
            <option value="textlocal">TextLocal</option>
          </select>
        </div>
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>API Key</label>
            <input type="password" />
          </div>
          <div className="settings-form-group">
            <label>Sender ID</label>
            <input type="text" />
          </div>
        </div>
      </div>
    </div>

    <div className="settings-section">
      <h3>WhatsApp Integration</h3>
      <div className="settings-form-group">
        <label>WhatsApp Business API</label>
        <input type="text" placeholder="API endpoint" />
      </div>
    </div>

    <div className="settings-section">
      <h3>Email Settings</h3>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>SMTP Server</label>
          <input type="text" placeholder="smtp.gmail.com" />
        </div>
        <div className="settings-form-group">
          <label>Port</label>
          <input type="number" placeholder="587" />
        </div>
      </div>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>Email</label>
          <input type="email" />
        </div>
        <div className="settings-form-group">
          <label>Password</label>
          <input type="password" />
        </div>
      </div>
    </div>

    <div className="settings-section">
      <h3>Notification Schedule</h3>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>Bill Reminder (days before due)</label>
          <input type="number" defaultValue="3" />
        </div>
        <div className="settings-form-group">
          <label>Due Alert (days after due)</label>
          <input type="number" defaultValue="1" />
        </div>
      </div>
      <div className="settings-checkbox-group">
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Send complaint status alerts</span>
        </label>
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Enable push notifications</span>
        </label>
      </div>
    </div>

    <div className="settings-form-actions">
      <button className="settings-save-btn">Save Changes</button>
    </div>
  </div>
);

export default NotificationsTab;
