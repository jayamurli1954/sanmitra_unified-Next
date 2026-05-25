/**
 * Registration entry point with two clear options:
 * 1) Society onboarding
 * 2) Resident join request
 */
import React from 'react';
import { useNavigate, Link } from 'react-router-dom';

const RegisterScreen = () => {
  const navigate = useNavigate();

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: '520px' }}>
        <div className="login-logo-container">
          <img
            src="/GruhaMitra_Logo.png"
            alt="GruhaMitra Logo"
            className="login-logo"
            style={{ width: '120px', height: '120px', borderRadius: '20px' }}
          />
        </div>
        <h1 className="login-title">Register with GruhaMitra</h1>
        <p className="login-subtitle">Choose the onboarding flow</p>

        <div style={{ display: 'grid', gap: '14px', marginTop: '16px' }}>
          <button
            type="button"
            className="login-button"
            onClick={() => navigate('/onboard-society')}
            style={{ height: '54px' }}
          >
            New Society Registration
          </button>

          <button
            type="button"
            className="login-button"
            onClick={() => navigate('/resident-signup')}
            style={{ height: '54px', background: '#c06a1c' }}
          >
            Resident / Member Registration
          </button>

          <button
            type="button"
            className="login-button"
            onClick={() => navigate('/complete-registration')}
            style={{ height: '54px', background: '#8f4e14' }}
          >
            Complete Registration After Approval
          </button>
        </div>

        <div className="login-footer" style={{ marginTop: '14px' }}>
          <p className="login-footer-text">
            Already have an account? <Link to="/login" className="login-link">Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterScreen;
