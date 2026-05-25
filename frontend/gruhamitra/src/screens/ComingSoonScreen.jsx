/**
 * Coming Soon placeholder screen
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';

const ComingSoonScreen = ({ title, description }) => {
  const navigate = useNavigate();

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-header-title">{title || 'Coming Soon'}</h1>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
            Back to Dashboard
          </button>
        </div>
      </div>

      <div className="dashboard-content" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 600 }}>
          <h2 style={{ fontSize: '32px', color: '#007AFF', marginBottom: '16px' }}> Coming Soon</h2>
          <p style={{ fontSize: '18px', color: '#666', marginBottom: '32px' }}>
            {description || 'This feature is under development and will be available soon.'}
          </p>
          <button 
            onClick={() => navigate('/dashboard')} 
            className="login-button"
            style={{ maxWidth: '200px' }}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default ComingSoonScreen;


