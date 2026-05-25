/**
 * GruhaMitra Profile Screen
 * User profile management with personal details and password reset
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import api from '../services/api';

const ProfileScreen = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    mobile: '',
    flat_number: '',
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const currentUser = await authService.getCurrentUser();
      if (!currentUser) {
        navigate('/login');
        return;
      }
      setUser(currentUser);
      setFormData({
        name: currentUser.name || '',
        email: currentUser.email || '',
        mobile: currentUser.mobile || currentUser.phone || '',
        flat_number: currentUser.flat_number || currentUser.apartment_number || '',
      });
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      // Map frontend fields (mobile, flat_number) to backend fields (phone_number, apartment_number)
      const payload = {
        name: formData.name,
        phone_number: formData.mobile,
        apartment_number: formData.flat_number
      };

      const response = await api.put('/auth/me', payload);
      const updatedUser = response.data;

      setUser(updatedUser);
      // Update storage so name/mobile change reflects everywhere without refresh
      if (authService.updateStoredUser) {
        await authService.updateStoredUser(updatedUser);
      }

      setMessage({ type: 'success', text: 'Profile updated successfully!' });
      setEditing(false);
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to update profile' });
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }
    if (passwordData.new_password.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters' });
      return;
    }
    try {
      await api.post('/auth/reset-password', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });
      setMessage({ type: 'success', text: 'Password reset successfully!' });
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to reset password' });
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-text">Loading profile...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <img
            src="/GruhaMitra_Logo.png"
            alt="GruhaMitra Logo"
            className="dashboard-logo"
          />
          <div className="dashboard-header-text">
            <div className="dashboard-society-name">
              {user?.society_name || 'GruhaMitra Demo Society'}
            </div>
            <div className="dashboard-tagline">
              Your Society, Digitally Simplified
            </div>
          </div>
        </div>
        <div className="dashboard-header-right">
          <span className="dashboard-header-icon" title="Notifications"></span>
          <div
            className="dashboard-user-info"
            onClick={() => navigate('/profile')}
            style={{ cursor: 'pointer' }}
          >
            <div className="dashboard-user-name">{user?.name || user?.email}</div>
            <div className="dashboard-user-role">{user?.role || 'Admin'}</div>
          </div>
          <button onClick={async () => {
            await authService.logout();
            window.location.href = '/gruhamitra/login';
          }} className="dashboard-logout-button">
             Logout
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '28px', color: 'var(--gm-deep-brown)', marginBottom: '8px' }}> My Profile</h1>
            <p style={{ color: 'var(--gm-text-muted)' }}>Manage your personal information and account settings</p>
          </div>
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
             Back to Dashboard
          </button>
        </div>

        {message.text && (
          <div className={`settings-section ${message.type === 'success' ? 'success-message' : 'error-message'}`} style={{
            background: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
            border: `2px solid ${message.type === 'success' ? '#4CAF50' : '#F44336'}`,
            color: message.type === 'success' ? '#2E7D32' : '#C62828',
            marginBottom: '20px'
          }}>
            {message.text}
          </div>
        )}

        {/* Profile Information */}
        <div className="settings-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 className="settings-tab-title">Personal Information</h2>
            {!editing && (
              <button className="settings-action-btn" onClick={() => setEditing(true)}>
                 Edit Profile
              </button>
            )}
          </div>

          {editing ? (
            <form className="settings-form" onSubmit={handleUpdateProfile}>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="settings-form-group">
                  <label>Email *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled
                    style={{ background: '#f5f5f5' }}
                  />
                  <small>Email cannot be changed</small>
                </div>
              </div>

              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Mobile Number *</label>
                  <input
                    type="tel"
                    value={formData.mobile}
                    onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                    placeholder="+91 9876543210"
                    required
                  />
                </div>
                <div className="settings-form-group">
                  <label>Flat Number *</label>
                  <input
                    type="text"
                    value={formData.flat_number}
                    onChange={(e) => setFormData({ ...formData, flat_number: e.target.value })}
                    placeholder="A-101"
                    required
                  />
                </div>
              </div>

              <div className="settings-form-actions">
                <button type="submit" className="settings-save-btn">Save Changes</button>
                <button type="button" className="settings-cancel-btn" onClick={() => {
                  setEditing(false);
                  loadProfile();
                }}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Full Name</label>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', color: 'var(--gm-text-dark)' }}>
                    {formData.name || 'Not set'}
                  </div>
                </div>
                <div className="settings-form-group">
                  <label>Email</label>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', color: 'var(--gm-text-dark)' }}>
                    {formData.email || 'Not set'}
                  </div>
                </div>
              </div>

              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Mobile Number</label>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', color: 'var(--gm-text-dark)' }}>
                    {formData.mobile || 'Not set'}
                  </div>
                </div>
                <div className="settings-form-group">
                  <label>Flat Number</label>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', color: 'var(--gm-text-dark)' }}>
                    {formData.flat_number || 'Not set'}
                  </div>
                </div>
              </div>

              <div className="settings-form-group">
                <label>Role</label>
                <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', color: 'var(--gm-text-dark)' }}>
                  {user?.role || 'Admin'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Reset Password */}
        <div className="settings-section">
          <h2 className="settings-tab-title">Reset Password</h2>
          <form className="settings-form" onSubmit={handleResetPassword}>
            <div className="settings-form-group">
              <label>Current Password *</label>
              <input
                type="password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                required
                placeholder="Enter current password"
              />
            </div>

            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>New Password *</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  required
                  placeholder="Enter new password"
                  minLength="6"
                />
                <small>Minimum 6 characters</small>
              </div>
              <div className="settings-form-group">
                <label>Confirm New Password *</label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                  required
                  placeholder="Confirm new password"
                  minLength="6"
                />
              </div>
            </div>

            <div className="settings-form-actions">
              <button type="submit" className="settings-save-btn">Reset Password</button>
              <button type="button" className="settings-cancel-btn" onClick={() => setPasswordData({
                current_password: '',
                new_password: '',
                confirm_password: '',
              })}>
                Clear
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfileScreen;



