import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import visitorsService from '../services/visitorsService';

const VISITOR_TYPES = [
  { value: 'guest', label: 'Guest' },
  { value: 'delivery', label: 'Delivery' },
  { value: 'cab', label: 'Cab' },
  { value: 'vendor', label: 'Vendor' },
  { value: 'service_staff', label: 'Service Staff' },
  { value: 'domestic_help', label: 'Domestic Help' },
  { value: 'other', label: 'Other' },
];

const STATUS_COLORS = {
  pending: '#E8842A',
  approved: '#007AFF',
  rejected: '#C53030',
  inside: '#2F855A',
  exited: '#718096',
  cancelled: '#718096',
};

const canManageVisitors = (role) => {
  const normalized = String(role || '').toLowerCase();
  return ['admin', 'super_admin', 'tenant_admin', 'secretary', 'chairman', 'security', 'security_guard', 'guard', 'gate', 'watchman'].includes(normalized);
};

const formatDateTime = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value);
  }
};

const VisitorsScreen = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [visitors, setVisitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [message, setMessage] = useState({ type: '', text: '' });
  const [formData, setFormData] = useState({
    visitor_name: '',
    phone_number: '',
    visitor_type: 'guest',
    flat_number: '',
    vehicle_number: '',
    vendor_name: '',
    purpose: '',
  });

  const isManager = canManageVisitors(user?.role);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      setFormData((prev) => ({
        ...prev,
        flat_number: prev.flat_number || currentUser?.flat_number || currentUser?.unit_number || '',
      }));
      const rows = await visitorsService.listVisitors();
      setVisitors(rows);
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not load visitor register.' });
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    return {
      pending: visitors.filter((row) => row.status === 'pending').length,
      inside: visitors.filter((row) => row.status === 'inside').length,
      approved: visitors.filter((row) => row.status === 'approved').length,
      today: visitors.filter((row) => {
        if (!row.created_at) return false;
        return new Date(row.created_at).toDateString() === new Date().toDateString();
      }).length,
    };
  }, [visitors]);

  const filteredVisitors = visitors.filter((row) => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['pending', 'approved', 'inside'].includes(row.status);
    return row.status === filter;
  });

  const handleCreateVisitor = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      await visitorsService.createVisitor(formData);
      setFormData({
        visitor_name: '',
        phone_number: '',
        visitor_type: 'guest',
        flat_number: user?.flat_number || user?.unit_number || '',
        vehicle_number: '',
        vendor_name: '',
        purpose: '',
      });
      setMessage({ type: 'success', text: isManager ? 'Visitor entry created.' : 'Expected visitor added and approved for your flat.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not create visitor entry.' });
    } finally {
      setSubmitting(false);
    }
  };

  const runAction = async (action, visitorId) => {
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      if (action === 'approve') await visitorsService.approveVisitor(visitorId);
      if (action === 'reject') await visitorsService.rejectVisitor(visitorId);
      if (action === 'check_in') await visitorsService.checkInVisitor(visitorId);
      if (action === 'check_out') await visitorsService.checkOutVisitor(visitorId);
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not update visitor entry.' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && visitors.length === 0) {
    return <div className="loading-container"><div className="loading-text">Loading visitors...</div></div>;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-header-left" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>
          <img src="/gruhamitra/GruhaMitra_Logo.png" alt="GruhaMitra Logo" className="dashboard-logo" />
          <div className="dashboard-header-text">
            <div className="dashboard-society-name">{user?.society_name || 'GruhaMitra'}</div>
            <div className="dashboard-tagline">Visitors and Delivery Register</div>
          </div>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">Back to Dashboard</button>
        </div>
      </div>

      <div className="dashboard-content">
        {message.text && (
          <div className={`message ${message.type}`} style={{
            marginBottom: '20px',
            padding: '12px 14px',
            borderRadius: '8px',
            backgroundColor: message.type === 'error' ? '#fee' : '#efe',
            color: message.type === 'error' ? '#c00' : '#0c0',
            border: `1px solid ${message.type === 'error' ? '#f44' : '#4f4'}`,
          }}>
            {message.text}
          </div>
        )}

        <div className="dashboard-metrics-grid">
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Pending Approval</div>
            <div className="dashboard-metric-value" style={{ color: '#E8842A' }}>{stats.pending}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Currently Inside</div>
            <div className="dashboard-metric-value" style={{ color: '#2F855A' }}>{stats.inside}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Approved</div>
            <div className="dashboard-metric-value">{stats.approved}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Today</div>
            <div className="dashboard-metric-value">{stats.today}</div>
          </div>
        </div>

        <div className="dashboard-main-grid" style={{ alignItems: 'start' }}>
          <div className="settings-section">
            <h2 className="settings-section-title">{isManager ? 'New Gate Entry' : 'Expected Visitor'}</h2>
            <form onSubmit={handleCreateVisitor} className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Visitor Name *</label>
                  <input
                    value={formData.visitor_name}
                    onChange={(e) => setFormData({ ...formData, visitor_name: e.target.value })}
                    required
                  />
                </div>
                <div className="settings-form-group">
                  <label>Phone</label>
                  <input
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  />
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Type</label>
                  <select
                    value={formData.visitor_type}
                    onChange={(e) => setFormData({ ...formData, visitor_type: e.target.value })}
                  >
                    {VISITOR_TYPES.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                </div>
                <div className="settings-form-group">
                  <label>Flat Number *</label>
                  <input
                    value={formData.flat_number}
                    onChange={(e) => setFormData({ ...formData, flat_number: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Vendor / Platform</label>
                  <input
                    value={formData.vendor_name}
                    onChange={(e) => setFormData({ ...formData, vendor_name: e.target.value })}
                    placeholder="Amazon, Swiggy, plumber, cab service"
                  />
                </div>
                <div className="settings-form-group">
                  <label>Vehicle Number</label>
                  <input
                    value={formData.vehicle_number}
                    onChange={(e) => setFormData({ ...formData, vehicle_number: e.target.value })}
                  />
                </div>
              </div>
              <div className="settings-form-group">
                <label>Purpose</label>
                <textarea
                  rows={3}
                  value={formData.purpose}
                  onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                />
              </div>
              <button className="settings-save-btn" type="submit" disabled={submitting}>
                {submitting ? 'Saving...' : (isManager ? 'Create Entry' : 'Add Expected Visitor')}
              </button>
            </form>
          </div>

          <div className="settings-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <h2 className="settings-section-title" style={{ margin: 0 }}>Visitor Register</h2>
              <button className="settings-action-btn" type="button" onClick={loadData}>Refresh</button>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              {['all', 'active', 'pending', 'approved', 'inside', 'exited', 'rejected'].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 20,
                    border: '1px solid #ddd',
                    backgroundColor: filter === item ? '#007AFF' : '#fff',
                    color: filter === item ? '#fff' : '#444',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {item}
                </button>
              ))}
            </div>

            {filteredVisitors.length === 0 ? (
              <div style={{ padding: 24, background: '#f9f9f9', borderRadius: 8, textAlign: 'center', color: '#666' }}>
                No visitor entries found.
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 12 }}>
                {filteredVisitors.map((entry) => (
                  <div key={entry.id} className="dashboard-metric-card" style={{ alignItems: 'stretch', flexDirection: 'column', padding: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <div>
                        <strong>{entry.visitor_name}</strong>
                        <div style={{ color: '#666', marginTop: 4 }}>
                          {entry.visitor_type?.replace(/_/g, ' ')} for Flat {entry.flat_number}
                        </div>
                      </div>
                      <span style={{
                        alignSelf: 'flex-start',
                        color: 'white',
                        backgroundColor: STATUS_COLORS[entry.status] || '#718096',
                        borderRadius: 999,
                        padding: '4px 10px',
                        textTransform: 'capitalize',
                        fontSize: 12,
                        fontWeight: 700,
                      }}>
                        {entry.status}
                      </span>
                    </div>
                    <div style={{ marginTop: 10, color: '#555', fontSize: 14 }}>
                      {entry.vendor_name && <div>Vendor: {entry.vendor_name}</div>}
                      {entry.phone_number && <div>Phone: {entry.phone_number}</div>}
                      {entry.vehicle_number && <div>Vehicle: {entry.vehicle_number}</div>}
                      {entry.purpose && <div>Purpose: {entry.purpose}</div>}
                      <div>Created: {formatDateTime(entry.created_at)}</div>
                      {entry.checked_in_at && <div>In: {formatDateTime(entry.checked_in_at)}</div>}
                      {entry.checked_out_at && <div>Out: {formatDateTime(entry.checked_out_at)}</div>}
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                      {entry.status === 'pending' && (
                        <>
                          <button className="settings-save-btn" type="button" disabled={submitting} onClick={() => runAction('approve', entry.id)}>Approve</button>
                          <button className="settings-action-btn" type="button" disabled={submitting} onClick={() => runAction('reject', entry.id)}>Reject</button>
                        </>
                      )}
                      {isManager && ['pending', 'approved'].includes(entry.status) && (
                        <button className="settings-save-btn" type="button" disabled={submitting} onClick={() => runAction('check_in', entry.id)}>Check In</button>
                      )}
                      {isManager && entry.status === 'inside' && (
                        <button className="settings-action-btn" type="button" disabled={submitting} onClick={() => runAction('check_out', entry.id)}>Check Out</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VisitorsScreen;
