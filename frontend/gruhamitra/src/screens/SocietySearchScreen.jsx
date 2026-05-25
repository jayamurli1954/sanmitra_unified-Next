/**
 * Society Search & Join Request (Onboarding v2)
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import membershipV2Service from '../services/membershipV2Service';

const SocietySearchScreen = () => {
  const navigate = useNavigate();
  const [searchForm, setSearchForm] = useState({ q: '', city: '', pin_code: '' });
  const [loading, setLoading] = useState(false);
  const [societies, setSocieties] = useState([]);
  const [selectedSociety, setSelectedSociety] = useState(null);
  const [joinForm, setJoinForm] = useState({ requested_unit_label: '', requested_notes: '' });
  const [message, setMessage] = useState({ type: '', text: '' });

  const handleSearchChange = (e) => {
    const { name, value } = e.target;
    setSearchForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleJoinChange = (e) => {
    const { name, value } = e.target;
    setJoinForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });
    setLoading(true);
    try {
      const results = await membershipV2Service.searchSocieties(searchForm);
      setSocieties(results || []);
    } catch (error) {
      console.error('Failed to search societies:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to search societies.' });
    } finally {
      setLoading(false);
    }
  };

  const handleJoinRequest = async (e) => {
    e.preventDefault();
    if (!selectedSociety) return;
    setMessage({ type: '', text: '' });
    setLoading(true);
    try {
      await membershipV2Service.createJoinRequest(selectedSociety.id, {
        role: 'resident',
        requested_unit_label: joinForm.requested_unit_label || undefined,
        requested_notes: joinForm.requested_notes || undefined,
      });
      setMessage({ type: 'success', text: 'Join request submitted successfully.' });
      setSelectedSociety(null);
      setJoinForm({ requested_unit_label: '', requested_notes: '' });
    } catch (error) {
      console.error('Failed to create join request:', error);
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to submit join request.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title"> Society Search</h1>
          <span className="dashboard-header-subtitle">Find your society and request to join</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/settings')} className="dashboard-logout-button">
             Back to Settings
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="settings-section" style={{ marginBottom: '24px' }}>
          <h3>Search Criteria</h3>
          <form onSubmit={handleSearch} className="settings-form">
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Society Name</label>
                <input
                  type="text"
                  name="q"
                  placeholder="e.g., GreenView"
                  value={searchForm.q}
                  onChange={handleSearchChange}
                />
              </div>
              <div className="settings-form-group">
                <label>City</label>
                <input
                  type="text"
                  name="city"
                  placeholder="e.g., Pune"
                  value={searchForm.city}
                  onChange={handleSearchChange}
                />
              </div>
              <div className="settings-form-group">
                <label>PIN Code</label>
                <input
                  type="text"
                  name="pin_code"
                  placeholder="e.g., 411001"
                  value={searchForm.pin_code}
                  onChange={handleSearchChange}
                />
              </div>
            </div>
            <button type="submit" className="settings-action-btn" disabled={loading}>
              {loading ? 'Searching...' : 'Search Societies'}
            </button>
          </form>
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

        <div className="settings-section">
          <h3>Results</h3>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '32px', color: '#666' }}>Loading...</div>
          ) : societies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: '#666' }}>
              No societies found. Try a different search.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '16px',
              }}
            >
              {societies.map((society) => (
                <div
                  key={society.id}
                  style={{
                    background: '#fff',
                    borderRadius: '12px',
                    border: '1px solid #E5E5EA',
                    padding: '16px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  }}
                >
                  <div style={{ fontWeight: '600', fontSize: '16px', marginBottom: '6px' }}>
                    {society.name}
                  </div>
                  <div style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>
                    {(society.city || '') + (society.city && society.state ? ', ' : '') + (society.state || '')}
                    {society.pin_code ? `  ${society.pin_code}` : ''}
                  </div>
                  <button
                    className="settings-action-btn"
                    onClick={() => {
                      setSelectedSociety(society);
                      setMessage({ type: '', text: '' });
                    }}
                  >
                    Request to Join
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedSociety && (
          <div className="settings-section" style={{ marginTop: '24px' }}>
            <h3>Join Request for {selectedSociety.name}</h3>
            <form onSubmit={handleJoinRequest} className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Flat/Unit Label</label>
                  <input
                    type="text"
                    name="requested_unit_label"
                    placeholder="e.g., A-101"
                    value={joinForm.requested_unit_label}
                    onChange={handleJoinChange}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Notes (optional)</label>
                  <input
                    type="text"
                    name="requested_notes"
                    placeholder="Any clarification for admin"
                    value={joinForm.requested_notes}
                    onChange={handleJoinChange}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button type="submit" className="settings-action-btn" disabled={loading}>
                  {loading ? 'Submitting...' : 'Submit Join Request'}
                </button>
                <button
                  type="button"
                  className="settings-action-btn"
                  style={{ background: '#f0f0f0', color: '#333' }}
                  onClick={() => setSelectedSociety(null)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};

export default SocietySearchScreen;

