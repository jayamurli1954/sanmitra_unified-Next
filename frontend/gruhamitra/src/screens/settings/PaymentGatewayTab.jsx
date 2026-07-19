import React from 'react';

const PaymentGatewayTab = () => (
  <div className="settings-tab-content">
    <h2 className="settings-tab-title">Payment Gateway</h2>
    <p className="settings-tab-description">Configure payment collection</p>

    <div className="settings-form">
      <div className="settings-form-group">
        <label>Payment Gateway Provider</label>
        <select>
          <option value="">Select Gateway</option>
          <option value="razorpay">Razorpay</option>
          <option value="payu">PayU</option>
          <option value="stripe">Stripe</option>
          <option value="upi">UPI Direct</option>
        </select>
      </div>

      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>API Key</label>
          <input type="password" placeholder="Enter API key" />
        </div>
        <div className="settings-form-group">
          <label>API Secret</label>
          <input type="password" placeholder="Enter API secret" />
        </div>
      </div>

      <div className="settings-form-group">
        <label>Society Bank Account Mapping</label>
        <select>
          <option>HDFC - Current (Primary)</option>
          <option>ICICI - Savings</option>
        </select>
      </div>

      <div className="settings-checkbox-group">
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Auto-generate payment receipts</span>
        </label>
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Auto-reconcile payments</span>
        </label>
      </div>

      <div className="settings-form-group">
        <label>Convenience Fee (%)</label>
        <input type="number" step="0.01" placeholder="0.00" />
        <small>Additional fee charged to members (if any)</small>
      </div>

      <div className="settings-form-actions">
        <button className="settings-save-btn">Save & Test Connection</button>
      </div>
    </div>
  </div>
);

export default PaymentGatewayTab;
