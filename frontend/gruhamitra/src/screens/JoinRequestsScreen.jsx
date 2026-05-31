/**
 * Join Requests (Onboarding v2) - Admin approvals
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import membershipV2Service from '../services/membershipV2Service';
import { authService } from '../services/authService';

const resolveAdminSocietyId = (user) => {
  const candidates = [
    user?.society_id,
    user?.tenant_id,
    typeof window !== 'undefined' ? window.localStorage.getItem('gruhamitra_tenant_id') : null,
  ];
  return candidates
    .map((value) => String(value || '').trim())
    .find(Boolean) || null;
};

const roleOptions = [
  { value: 'resident', label: 'Resident' },
  { value: 'chairman', label: 'Chairman' },
  { value: 'secretary', label: 'Secretary' },
  { value: 'treasurer', label: 'Treasurer' },
  { value: 'auditor', label: 'Auditor' },
  { value: 'security', label: 'Security' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'admin', label: 'Admin' },
];

const JoinRequestsScreen = () => {
  const navigate = useNavigate();
  const [societyId, setSocietyId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [requests, setRequests] = useState([]);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [actionState, setActionState] = useState({});

  const loadRequests = async (society, status) => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const data = await membershipV2Service.listJoinRequests(society, status);
      setRequests(data || []);
    } catch (error) {
      console.error('Failed to load join requests:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to load join requests.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const user = await authService.getCurrentUser();
      const userSocietyId = resolveAdminSocietyId(user);
      if (!userSocietyId) {
        setMessage({ type: 'error', text: 'No society assigned to this admin account.' });
        setLoading(false);
        return;
      }
      setSocietyId(userSocietyId);
      await loadRequests(userSocietyId, statusFilter);
    };
    init();
  }, []);

  useEffect(() => {
    if (societyId) {
      loadRequests(societyId, statusFilter);
    }
  }, [societyId, statusFilter]);

  const handleActionChange = (membershipId, field, value) => {
    setActionState((prev) => ({
      ...prev,
      [membershipId]: {
        ...prev[membershipId],
        [field]: value,
      },
    }));
  };

  const handleApprove = async (membershipId) => {
    const state = actionState[membershipId] || {};
    setLoading(true);
    try {
      await membershipV2Service.approveJoinRequest(membershipId, {
        role: state.role || 'resident',
        unit_label: state.unit_label || undefined,
      });
      setMessage({ type: 'success', text: 'Join request approved.' });
      await loadRequests(societyId, statusFilter);
    } catch (error) {
      console.error('Failed to approve request:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to approve request.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async (membershipId) => {
    const state = actionState[membershipId] || {};
    setLoading(true);
    try {
      await membershipV2Service.rejectJoinRequest(membershipId, {
        reason: state.reason || undefined,
      });
      setMessage({ type: 'success', text: 'Join request rejected.' });
      await loadRequests(societyId, statusFilter);
    } catch (error) {
      console.error('Failed to reject request:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to reject request.' });
    } finally {
      setLoading(false);
    }
  };

  const emptyStateText = useMemo(() => {
    if (loading) return 'Loading join requests...';
    if (statusFilter === 'pending') return 'No pending join requests.';
    if (statusFilter === 'active') return 'No active memberships listed here.';
    if (statusFilter === 'rejected') return 'No rejected requests found.';
    return 'No join requests found.';
  }, [loading, statusFilter]);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title"> Join Requests</h1>
          <span className="dashboard-header-subtitle">Approve or reject new members</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/settings')} className="dashboard-logout-button">
             Back to Settings
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '14px',
              cursor: 'pointer',
            }}
          >
            <option value="pending">Pending</option>
            <option value="active">Active</option>
            <option value="rejected">Rejected</option>
          </select>
          <button className="settings-action-btn" onClick={() => loadRequests(societyId, statusFilter)}>
            Refresh
          </button>
        </div>

        {message.text && (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
              background: message.type === 'error' ? '#FFECEC' : '#E8FFF1',
              color: message.type === 'error' ? '#B00020' : '#1B5E20',
              border: `1px solid ${message.type === 'error' ? '#FFD6D6' : '#B9EBCB'}`,
            }}
          >
            {message.text}
          </div>
        )}

        <div
          style={{
            background: '#fff',
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            border: '1px solid #E5E5EA',
          }}
        >
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#F5F5F7', borderBottom: '2px solid #E5E5EA' }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Member ID
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    User ID
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Requested Unit
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Status
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: '#666' }}>
                      Loading...
                    </td>
                  </tr>
                ) : requests.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: '#666' }}>
                      {emptyStateText}
                    </td>
                  </tr>
                ) : (
                  requests.map((request) => {
                    const state = actionState[request.id] || {};
                    return (
                      <tr key={request.id} style={{ borderBottom: '1px solid #E5E5EA' }}>
                        <td style={{ padding: '12px 16px', fontSize: '14px' }}>{request.id}</td>
                        <td style={{ padding: '12px 16px', fontSize: '14px' }}>{request.user_id}</td>
                        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                          {request.unit_label || request.requested_unit_label || '-'}
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '14px', textTransform: 'capitalize' }}>
                          {request.status}
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                          {statusFilter === 'pending' ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <input
                                type="text"
                                placeholder="Unit label to approve"
                                value={state.unit_label || ''}
                                onChange={(e) => handleActionChange(request.id, 'unit_label', e.target.value)}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                              />
                              <select
                                value={state.role || 'resident'}
                                onChange={(e) => handleActionChange(request.id, 'role', e.target.value)}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                              >
                                {roleOptions.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                <button className="settings-action-btn" onClick={() => handleApprove(request.id)}>
                                  Approve
                                </button>
                                <button
                                  className="settings-action-btn"
                                  style={{ background: '#FFECEC', color: '#B00020' }}
                                  onClick={() => handleReject(request.id)}
                                >
                                  Reject
                                </button>
                                <input
                                  type="text"
                                  placeholder="Reject reason (optional)"
                                  value={state.reason || ''}
                                  onChange={(e) => handleActionChange(request.id, 'reason', e.target.value)}
                                  style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: '#888' }}>No actions</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JoinRequestsScreen;

