import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import flatsService from '../services/flatsService';
import facilityBookingService from '../services/facilityBookingService';

const emptyFacilityForm = {
  name: '',
  description: '',
  location: '',
  capacity: '',
  booking_fee: 0,
  deposit_amount: 0,
  booking_slot_minutes: 60,
  advance_booking_days: 30,
  open_time: '',
  close_time: '',
  terms: '',
  status: 'active',
};

const emptyBookingForm = {
  facility_id: '',
  flat_number: '',
  resident_name: '',
  resident_phone: '',
  purpose: '',
  start_time: '',
  end_time: '',
  attendee_count: '',
};

const managerRoles = new Set(['admin', 'super_admin', 'tenant_admin', 'secretary', 'chairman', 'committee']);

const formatDateTime = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value);
  }
};

const formatCurrency = (value) => {
  const amount = Number(value || 0);
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
};

const toLocalInputValue = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const offsetMs = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
};

const FacilityBookingScreen = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [facilities, setFacilities] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [flats, setFlats] = useState([]);
  const [facilityForm, setFacilityForm] = useState(emptyFacilityForm);
  const [bookingForm, setBookingForm] = useState(emptyBookingForm);
  const [filter, setFilter] = useState('active');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const canManage = useMemo(() => managerRoles.has(String(user?.role || '').trim().toLowerCase()), [user]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const currentUser = await authService.getCurrentUser();
      if (!currentUser) {
        navigate('/login');
        return;
      }
      setUser(currentUser);
      const [facilityRows, bookingRows, flatRows] = await Promise.all([
        facilityBookingService.listFacilities(canManage),
        facilityBookingService.listBookings(),
        flatsService.getFlats().catch(() => []),
      ]);
      setFacilities(facilityRows);
      setBookings(bookingRows);
      setFlats(flatRows || []);
      setBookingForm((prev) => ({
        ...prev,
        facility_id: prev.facility_id || facilityRows[0]?.id || '',
        flat_number: prev.flat_number || currentUser?.flat_number || currentUser?.unit_number || flatRows?.[0]?.flat_number || '',
        resident_name: prev.resident_name || currentUser?.name || currentUser?.full_name || '',
        resident_phone: prev.resident_phone || currentUser?.phone_number || '',
      }));
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not load facility bookings.' });
    } finally {
      setLoading(false);
    }
  };

  const handleFacilitySubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      const payload = {
        ...facilityForm,
        capacity: facilityForm.capacity ? Number(facilityForm.capacity) : null,
        booking_fee: Number(facilityForm.booking_fee || 0),
        deposit_amount: Number(facilityForm.deposit_amount || 0),
        booking_slot_minutes: Number(facilityForm.booking_slot_minutes || 60),
        advance_booking_days: Number(facilityForm.advance_booking_days || 30),
        open_time: facilityForm.open_time || null,
        close_time: facilityForm.close_time || null,
      };
      await facilityBookingService.createFacility(payload);
      setFacilityForm(emptyFacilityForm);
      setMessage({ type: 'success', text: 'Facility added successfully.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not save facility.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleBookingSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      const payload = {
        ...bookingForm,
        attendee_count: bookingForm.attendee_count ? Number(bookingForm.attendee_count) : null,
        start_time: new Date(bookingForm.start_time).toISOString(),
        end_time: new Date(bookingForm.end_time).toISOString(),
      };
      await facilityBookingService.createBooking(payload);
      setBookingForm((prev) => ({
        ...emptyBookingForm,
        facility_id: prev.facility_id,
        flat_number: user?.flat_number || user?.unit_number || prev.flat_number,
        resident_name: user?.name || user?.full_name || '',
        resident_phone: user?.phone_number || '',
      }));
      setMessage({ type: 'success', text: canManage ? 'Facility booking approved.' : 'Facility booking requested.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not create booking.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    const reason = window.prompt('Cancellation reason', '');
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      await facilityBookingService.cancelBooking(bookingId, reason || '');
      setMessage({ type: 'success', text: 'Booking cancelled.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not cancel booking.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveBooking = async (bookingId) => {
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      const approved = await facilityBookingService.approveBooking(bookingId);
      setMessage({ type: 'success', text: approved.confirmation_message || 'Booking approved.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not approve booking.' });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredBookings = bookings.filter((booking) => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['pending', 'approved'].includes(booking.status);
    return booking.status === filter;
  });

  const selectedFacility = facilities.find((facility) => facility.id === bookingForm.facility_id);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-text">Loading facility bookings...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <img src="/gruhamitra/GruhaMitra_Logo.png" alt="GruhaMitra Logo" className="dashboard-logo" />
          <div className="dashboard-header-text">
            <div className="dashboard-society-name">{user?.society_name || 'GruhaMitra'}</div>
            <div className="dashboard-tagline">Facility and Amenity Booking</div>
          </div>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
            Back to Dashboard
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {message.text && (
          <div
            className={`message ${message.type}`}
            style={{
              marginBottom: '20px',
              padding: '12px 14px',
              borderRadius: '8px',
              backgroundColor: message.type === 'error' ? '#fee' : '#efe',
              color: message.type === 'error' ? '#c00' : '#0c0',
              border: `1px solid ${message.type === 'error' ? '#f44' : '#4f4'}`,
            }}
          >
            {message.text}
          </div>
        )}

        <div className="dashboard-metrics-grid" style={{ marginBottom: '24px' }}>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Facilities</div>
            <div className="dashboard-metric-value">{facilities.length}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Active Bookings</div>
            <div className="dashboard-metric-value">{bookings.filter((row) => ['pending', 'approved'].includes(row.status)).length}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">Pending Approval</div>
            <div className="dashboard-metric-value" style={{ color: '#E8842A' }}>{bookings.filter((row) => row.status === 'pending').length}</div>
          </div>
          <div className="dashboard-metric-card">
            <div className="dashboard-metric-label">This Month Income Booked</div>
            <div className="dashboard-metric-value">{formatCurrency(bookings.reduce((sum, row) => sum + Number(row.amount || 0), 0))}</div>
          </div>
        </div>

        <div className="dashboard-main-grid" style={{ alignItems: 'start' }}>
          <div className="settings-section">
            <h2 className="settings-section-title">Book Amenity</h2>
            {facilities.length === 0 ? (
              <div style={{ padding: '24px', background: '#f9f9f9', borderRadius: '8px', color: '#666' }}>
                No active facilities are configured yet.
              </div>
            ) : (
              <form onSubmit={handleBookingSubmit} className="settings-form">
                <div className="settings-form-group">
                  <label>Facility *</label>
                  <select value={bookingForm.facility_id} onChange={(e) => setBookingForm({ ...bookingForm, facility_id: e.target.value })} required>
                    {facilities.map((facility) => (
                      <option key={facility.id} value={facility.id}>{facility.name}</option>
                    ))}
                  </select>
                  {selectedFacility && (
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
                      {selectedFacility.location || 'Society premises'} | Fee {formatCurrency(selectedFacility.booking_fee)}
                    </div>
                  )}
                </div>

                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Flat Number *</label>
                    {canManage ? (
                      <select value={bookingForm.flat_number} onChange={(e) => setBookingForm({ ...bookingForm, flat_number: e.target.value })} required>
                        <option value="">Select Flat</option>
                        {flats.map((flat) => (
                          <option key={flat.id || flat.flat_number} value={flat.flat_number}>{flat.flat_number}</option>
                        ))}
                      </select>
                    ) : (
                      <input value={bookingForm.flat_number} readOnly style={{ backgroundColor: '#F2F2F7' }} />
                    )}
                  </div>
                  <div className="settings-form-group">
                    <label>Attendee Count</label>
                    <input type="number" min="1" value={bookingForm.attendee_count} onChange={(e) => setBookingForm({ ...bookingForm, attendee_count: e.target.value })} />
                  </div>
                </div>

                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Start *</label>
                    <input type="datetime-local" value={bookingForm.start_time} onChange={(e) => setBookingForm({ ...bookingForm, start_time: e.target.value })} required />
                  </div>
                  <div className="settings-form-group">
                    <label>End *</label>
                    <input type="datetime-local" value={bookingForm.end_time} onChange={(e) => setBookingForm({ ...bookingForm, end_time: e.target.value })} required />
                  </div>
                </div>

                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Resident Name</label>
                    <input value={bookingForm.resident_name} onChange={(e) => setBookingForm({ ...bookingForm, resident_name: e.target.value })} />
                  </div>
                  <div className="settings-form-group">
                    <label>Phone</label>
                    <input value={bookingForm.resident_phone} onChange={(e) => setBookingForm({ ...bookingForm, resident_phone: e.target.value })} />
                  </div>
                </div>

                <div className="settings-form-group">
                  <label>Purpose</label>
                  <textarea rows={2} value={bookingForm.purpose} onChange={(e) => setBookingForm({ ...bookingForm, purpose: e.target.value })} />
                </div>

                <button className="settings-save-btn" type="submit" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Submit Booking'}
                </button>
              </form>
            )}
          </div>

          {canManage && (
            <div className="settings-section">
              <h2 className="settings-section-title">Facility Setup</h2>
              <form onSubmit={handleFacilitySubmit} className="settings-form">
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Name *</label>
                    <input value={facilityForm.name} onChange={(e) => setFacilityForm({ ...facilityForm, name: e.target.value })} required />
                  </div>
                  <div className="settings-form-group">
                    <label>Location</label>
                    <input value={facilityForm.location} onChange={(e) => setFacilityForm({ ...facilityForm, location: e.target.value })} />
                  </div>
                </div>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Capacity</label>
                    <input type="number" min="1" value={facilityForm.capacity} onChange={(e) => setFacilityForm({ ...facilityForm, capacity: e.target.value })} />
                  </div>
                  <div className="settings-form-group">
                    <label>Booking Fee</label>
                    <input type="number" min="0" step="0.01" value={facilityForm.booking_fee} onChange={(e) => setFacilityForm({ ...facilityForm, booking_fee: e.target.value })} />
                  </div>
                </div>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Open Time</label>
                    <input type="time" value={facilityForm.open_time} onChange={(e) => setFacilityForm({ ...facilityForm, open_time: e.target.value })} />
                  </div>
                  <div className="settings-form-group">
                    <label>Close Time</label>
                    <input type="time" value={facilityForm.close_time} onChange={(e) => setFacilityForm({ ...facilityForm, close_time: e.target.value })} />
                  </div>
                </div>
                <div className="settings-form-group">
                  <label>Description / Terms</label>
                  <textarea rows={2} value={facilityForm.description} onChange={(e) => setFacilityForm({ ...facilityForm, description: e.target.value })} />
                </div>
                <button className="settings-save-btn" type="submit" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Add Facility'}
                </button>
              </form>
            </div>
          )}
        </div>

        <div className="settings-section" style={{ marginTop: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
            <h2 className="settings-section-title" style={{ margin: 0 }}>Booking Register</h2>
            <button className="settings-action-btn" type="button" style={{ width: 'auto', padding: '6px 14px' }} onClick={loadData}>Refresh</button>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
            {['active', 'all', 'pending', 'approved', 'cancelled', 'completed'].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '20px',
                  border: '1px solid #ddd',
                  backgroundColor: filter === item ? '#007AFF' : '#fff',
                  color: filter === item ? '#fff' : '#444',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  fontSize: '12px',
                  fontWeight: 600,
                }}
              >
                {item}
              </button>
            ))}
          </div>
          {filteredBookings.length === 0 ? (
            <div style={{ padding: '24px', background: '#f9f9f9', borderRadius: '8px', textAlign: 'center', color: '#666' }}>
              No facility bookings match this filter.
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '12px' }}>
              {filteredBookings.map((booking) => (
                <div key={booking.id} className="dashboard-metric-card" style={{ alignItems: 'stretch', flexDirection: 'column', padding: '16px', border: '1px solid #E5E5EA' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                    <div>
                      <strong>{booking.facility_name}</strong>
                      <div style={{ color: '#666', fontSize: '13px', marginTop: '4px' }}>Flat {booking.flat_number} | {booking.resident_name || 'Resident'}</div>
                    </div>
                    <span style={{ alignSelf: 'flex-start', backgroundColor: booking.status === 'cancelled' ? '#718096' : booking.status === 'pending' ? '#E8842A' : '#2F855A', color: '#fff', borderRadius: '999px', padding: '4px 10px', fontSize: '11px', fontWeight: 'bold', textTransform: 'capitalize' }}>
                      {booking.status}
                    </span>
                  </div>
                  <div style={{ marginTop: '10px', color: '#555', fontSize: '13px', lineHeight: 1.5 }}>
                    <div>Start: {formatDateTime(booking.start_time)}</div>
                    <div>End: {formatDateTime(booking.end_time)}</div>
                    <div>Amount: {formatCurrency(booking.amount)} | Payment: {String(booking.payment_status || '').replace(/_/g, ' ')}</div>
                    {booking.purpose && <div>Purpose: {booking.purpose}</div>}
                    {booking.confirmation_message && <div style={{ color: '#2F855A', fontWeight: 700 }}>Confirmation: {booking.confirmation_message}</div>}
                    {booking.cancellation_reason && <div>Cancel reason: {booking.cancellation_reason}</div>}
                  </div>
                  {['pending', 'approved'].includes(booking.status) && (
                    <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {canManage && booking.status === 'pending' && (
                        <button className="settings-save-btn" type="button" disabled={submitting} onClick={() => handleApproveBooking(booking.id)} style={{ width: 'auto', padding: '6px 14px', margin: 0 }}>
                          Approve
                        </button>
                      )}
                      <button className="settings-action-btn" type="button" disabled={submitting} onClick={() => handleCancelBooking(booking.id)} style={{ width: 'auto', padding: '6px 14px', margin: 0 }}>
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FacilityBookingScreen;
