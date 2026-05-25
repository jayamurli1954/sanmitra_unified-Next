/**
 * My Memberships (Onboarding v2)
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import membershipV2Service from '../services/membershipV2Service';

const MyMembershipsScreen = () => {
  const navigate = useNavigate();
  const [memberships, setMemberships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [societyNames, setSocietyNames] = useState({});

  const loadMemberships = async () => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const data = await membershipV2Service.listMyMemberships();
      setMemberships(data || []);
      const uniqueSocietyIds = [...new Set((data || []).map((m) => m.society_id).filter(Boolean))];
      if (uniqueSocietyIds.length > 0) {
        const entries = await Promise.all(
          uniqueSocietyIds.map(async (societyId) => {
            try {
              const society = await membershipV2Service.getSocietyById(societyId);
              const name = society?.name || society?.society_name || `Society ${societyId}`;
              return [societyId, name];
            } catch (error) {
              console.warn('Failed to load society name:', societyId, error);
              return [societyId, `Society ${societyId}`];
            }
          })
        );
        setSocietyNames(Object.fromEntries(entries));
      }
    } catch (error) {
      console.error('Failed to load memberships:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to load memberships.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemberships();
  }, []);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title"> My Memberships</h1>
          <span className="dashboard-header-subtitle">Track your society access</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/settings')} className="dashboard-logout-button">
             Back to Settings
          </button>
        </div>
      </div>

      <div className="dashboard-content">
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
                    Society
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Role
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Unit
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Status
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                    Requested Unit
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
                ) : memberships.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: '#666' }}>
                      No memberships found. Submit a join request first.
                    </td>
                  </tr>
                ) : (
                  memberships.map((membership) => (
                    <tr key={membership.id} style={{ borderBottom: '1px solid #E5E5EA' }}>
                      <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                        <div style={{ fontWeight: '600' }}>
                          {societyNames[membership.society_id] || `Society ${membership.society_id}`}
                        </div>
                        <div style={{ fontSize: '12px', color: '#888' }}>ID: {membership.society_id}</div>
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '14px', textTransform: 'capitalize' }}>
                        {membership.role}
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                        {membership.unit_label || '-'}
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '14px', textTransform: 'capitalize' }}>
                        {membership.status}
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                        {membership.requested_unit_label || '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MyMembershipsScreen;

