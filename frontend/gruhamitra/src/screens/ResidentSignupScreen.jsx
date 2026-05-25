import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import membershipV2Service from '../services/membershipV2Service';

const ResidentSignupScreen = () => {
  const navigate = useNavigate();
  const [searchForm, setSearchForm] = useState({ q: '', city: '', pin_code: '' });
  const [societies, setSocieties] = useState([]);
  const [selectedSociety, setSelectedSociety] = useState(null);
  const [unitOptions, setUnitOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    mobile: '',
    requested_unit_label: '',
    requested_notes: '',
  });

  const canSubmit = useMemo(() => {
    return Boolean(selectedSociety && formData.full_name && formData.email);
  }, [selectedSociety, formData.full_name, formData.email]);

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const results = await membershipV2Service.searchSocieties(searchForm);
      setSocieties(results || []);
      if (!results?.length) {
        setMessage({ type: 'error', text: 'No society found. Try different search filters.' });
      }
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to search societies.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSociety = async (society) => {
    setSelectedSociety(society);
    setMessage({ type: '', text: '' });
    setLoading(true);
    try {
      const units = await membershipV2Service.listSocietyUnits(society.id);
      setUnitOptions(units || []);
    } catch (error) {
      setUnitOptions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      await membershipV2Service.createPublicJoinRequest(selectedSociety.id, {
        full_name: formData.full_name,
        email: formData.email,
        mobile: formData.mobile || undefined,
        requested_unit_label: formData.requested_unit_label || undefined,
        requested_notes: formData.requested_notes || undefined,
      });
      setMessage({
        type: 'success',
        text: 'Join request submitted. Admin approval is required before you can complete registration.',
      });
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      setMessage({ type: 'error', text: detail || 'Failed to submit join request.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: '560px' }}>
        <h1 className="login-title">Resident Registration</h1>
        <p className="login-subtitle">Search your society and submit join request</p>

        <form onSubmit={handleSearch} className="login-form">
          <div className="login-input-container">
            <label className="login-label">Society Name</label>
            <input
              className="login-input"
              type="text"
              value={searchForm.q}
              onChange={(e) => setSearchForm((p) => ({ ...p, q: e.target.value }))}
              placeholder="e.g., GruhaMitra Society"
            />
          </div>
          <div className="login-input-container">
            <label className="login-label">City (optional)</label>
            <input
              className="login-input"
              type="text"
              value={searchForm.city}
              onChange={(e) => setSearchForm((p) => ({ ...p, city: e.target.value }))}
              placeholder="e.g., Pune"
            />
          </div>
          <div className="login-input-container">
            <label className="login-label">PIN Code (optional)</label>
            <input
              className="login-input"
              type="text"
              value={searchForm.pin_code}
              onChange={(e) => setSearchForm((p) => ({ ...p, pin_code: e.target.value }))}
              placeholder="e.g., 411001"
            />
          </div>
          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Searching...' : 'Search Society'}
          </button>
        </form>

        {societies.length > 0 && (
          <div style={{ marginTop: '14px' }}>
            <div style={{ fontWeight: 600, marginBottom: '8px' }}>Select Society</div>
            <div style={{ display: 'grid', gap: '8px' }}>
              {societies.map((society) => (
                <button
                  key={society.id}
                  type="button"
                  className="login-button"
                  style={{ background: selectedSociety?.id === society.id ? '#8f4e14' : '#c06a1c' }}
                  onClick={() => handleSelectSociety(society)}
                >
                  {society.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedSociety && (
          <form onSubmit={handleSubmit} className="login-form" style={{ marginTop: '16px' }}>
            <div className="login-input-container">
              <label className="login-label">Full Name *</label>
              <input
                className="login-input"
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData((p) => ({ ...p, full_name: e.target.value }))}
                required
              />
            </div>

            <div className="login-input-container">
              <label className="login-label">Email *</label>
              <input
                className="login-input"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                required
              />
            </div>

            <div className="login-input-container">
              <label className="login-label">Mobile Number</label>
              <input
                className="login-input"
                type="tel"
                value={formData.mobile}
                onChange={(e) => setFormData((p) => ({ ...p, mobile: e.target.value }))}
              />
            </div>

            <div className="login-input-container">
              <label className="login-label">Flat / Unit (optional)</label>
              <select
                className="login-input"
                value={formData.requested_unit_label}
                onChange={(e) => setFormData((p) => ({ ...p, requested_unit_label: e.target.value }))}
              >
                <option value="">Not sure / will be assigned by admin</option>
                {unitOptions.map((u) => (
                  <option key={`${u.id}-${u.unit_label}`} value={u.unit_label}>
                    {u.unit_label}
                  </option>
                ))}
              </select>
            </div>

            <div className="login-input-container">
              <label className="login-label">Notes (optional)</label>
              <input
                className="login-input"
                type="text"
                value={formData.requested_notes}
                onChange={(e) => setFormData((p) => ({ ...p, requested_notes: e.target.value }))}
                placeholder="Any message for admin"
              />
            </div>

            <button type="submit" className="login-button" disabled={!canSubmit || loading}>
              {loading ? 'Submitting...' : 'Submit Join Request'}
            </button>
          </form>
        )}

        {message.text && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px',
              borderRadius: '8px',
              background: message.type === 'error' ? '#FFECEC' : '#E8FFF1',
              border: `1px solid ${message.type === 'error' ? '#FFD6D6' : '#B9EBCB'}`,
              color: message.type === 'error' ? '#B00020' : '#1B5E20',
            }}
          >
            {message.text}
          </div>
        )}

        <div className="login-footer">
          <p className="login-footer-text">
            Already approved? <a href="/gruhamitra/complete-registration" className="login-link">Complete Registration</a>
          </p>
          <p className="login-footer-text">
            Back to <a href="/gruhamitra/register" className="login-link">Registration Options</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ResidentSignupScreen;

