import React from 'react';
import { useNavigate } from 'react-router-dom';

const MultiSocietyTab = () => {
  const navigate = useNavigate();

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Multi-Society Mode</h2>
      <p className="settings-tab-description">Search societies, manage memberships, and approvals</p>

      <div className="settings-section">
        <h3>Member Actions</h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button className="settings-action-btn" onClick={() => navigate('/onboarding/search')}>
             Search Society & Join
          </button>
          <button className="settings-action-btn" onClick={() => navigate('/onboarding/memberships')}>
             My Memberships
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h3>Admin Actions</h3>
        <p style={{ color: '#666', marginBottom: '12px' }}>
          Approve or reject join requests for your society.
        </p>
        <button className="settings-action-btn" onClick={() => navigate('/onboarding/requests')}>
           Review Join Requests
        </button>
      </div>

      <div className="settings-section">
        <h3>Society Switching</h3>
        <p style={{ color: '#666' }}>
          Society switching UI will be enabled after memberships are approved.
        </p>
      </div>
    </div>
  );
};

export default MultiSocietyTab;
