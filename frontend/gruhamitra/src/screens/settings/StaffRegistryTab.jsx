import React, { useState, useEffect } from 'react';
import staffService from '../../services/staffService';
import { getErrorMessage } from './settingsHelpers';

const StaffRegistryTab = () => {
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  // Form fields
  const [form, setForm] = useState({
    name: '',
    phone_number: '',
    role: 'Housekeeping',
    flat_number: '',
    vehicle_type: 'none',
    vehicle_number: ''
  });

  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    loadStaff();
  }, []);

  const loadStaff = async () => {
    setLoading(true);
    try {
      const list = await staffService.listStaff();
      setStaffList(list);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load staff directory.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.phone_number.trim()) return;
    setLoading(true);
    setMessage({ type: '', text: '' });

    const data = {
      name: form.name.trim(),
      phone_number: form.phone_number.trim(),
      role: form.role.trim(),
      flat_number: form.flat_number.trim() || null,
      vehicle_type: form.vehicle_type,
      vehicle_number: form.vehicle_type !== 'none' ? form.vehicle_number.trim() : null
    };

    try {
      if (editingId) {
        await staffService.updateStaff(editingId, data);
        setMessage({ type: 'success', text: 'Staff member updated!' });
      } else {
        await staffService.createStaff(data);
        setMessage({ type: 'success', text: 'Staff member registered successfully!' });
      }
      
      setForm({
        name: '',
        phone_number: '',
        role: 'Housekeeping',
        flat_number: '',
        vehicle_type: 'none',
        vehicle_number: ''
      });
      setEditingId(null);
      await loadStaff();
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (staff) => {
    setEditingId(staff.id);
    setForm({
      name: staff.name,
      phone_number: staff.phone_number,
      role: staff.role,
      flat_number: staff.flat_number || '',
      vehicle_type: staff.vehicle_type || 'none',
      vehicle_number: staff.vehicle_number || ''
    });
  };

  const handleDelete = async (staffId) => {
    if (!window.confirm('Are you sure you want to deactivate this staff member?')) return;
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      await staffService.deleteStaff(staffId);
      setMessage({ type: 'success', text: 'Staff member deactivated.' });
      await loadStaff();
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Staff Registry</h2>
      <p className="settings-tab-description">Pre-register security guards, maintenance workers, housekeeping cleaners, and flat-specific helper staff.</p>

      {message.text && (
        <div className={`message ${message.type}`} style={{
          marginBottom: '20px',
          padding: '12px 14px',
          borderRadius: '8px',
          backgroundColor: message.type === 'error' ? '#fee' : '#efe',
          color: message.type === 'error' ? '#c00' : '#0c0',
          border: `1px solid ${message.type === 'error' ? '#f44' : '#4f4'}`
        }}>
          {message.text}
        </div>
      )}

      {/* Form Section */}
      <div className="settings-section">
        <h3>{editingId ? 'Edit Staff Member' : 'Register Staff Member'}</h3>
        <form onSubmit={handleSubmit} className="settings-form">
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Full Name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                placeholder="e.g. Rajesh Kumar"
              />
            </div>
            <div className="settings-form-group">
              <label>Mobile Number *</label>
              <input
                value={form.phone_number}
                onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                required
                placeholder="e.g. 9876543210"
              />
            </div>
          </div>

          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Role / Type</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="Housekeeping">Housekeeping / Cleaner</option>
                <option value="Security">Security / Watchman</option>
                <option value="Maintenance">Maintenance / Plumber / Electrician</option>
                <option value="Maid">Maid / Cook</option>
                <option value="Driver">Personal Driver</option>
                <option value="Gardener">Gardener</option>
                <option value="Other">Other Helper</option>
              </select>
            </div>
            <div className="settings-form-group">
              <label>Flat Assignment (Optional)</label>
              <input
                value={form.flat_number}
                onChange={(e) => setForm({ ...form, flat_number: e.target.value })}
                placeholder="e.g. A-101 (leave empty if common staff)"
              />
            </div>
          </div>

          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Vehicle Type</label>
              <select
                value={form.vehicle_type}
                onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}
              >
                <option value="none">None / Walking</option>
                <option value="bike">Two Wheeler (Bike/Scooter)</option>
                <option value="car">Car</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="settings-form-group">
              <label>Vehicle Number</label>
              <input
                value={form.vehicle_number}
                onChange={(e) => setForm({ ...form, vehicle_number: e.target.value })}
                disabled={form.vehicle_type === 'none'}
                placeholder={form.vehicle_type === 'none' ? 'N/A' : 'e.g. KA-03-HA-1234'}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="settings-save-btn" type="submit" disabled={loading} style={{ width: 'auto' }}>
              {editingId ? 'Update Staff' : 'Register Staff'}
            </button>
            {editingId && (
              <button
                type="button"
                className="settings-action-btn"
                onClick={() => {
                  setEditingId(null);
                  setForm({ name: '', phone_number: '', role: 'Housekeeping', flat_number: '', vehicle_type: 'none', vehicle_number: '' });
                }}
                style={{ width: 'auto' }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Directory List */}
      <div className="settings-section">
        <h3>Staff Directory</h3>
        {staffList.length === 0 ? (
          <p style={{ color: '#666' }}>No staff members registered yet.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '600px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd', paddingBottom: '8px' }}>
                  <th style={{ padding: '12px 8px' }}>Name</th>
                  <th style={{ padding: '12px 8px' }}>Role</th>
                  <th style={{ padding: '12px 8px' }}>Phone</th>
                  <th style={{ padding: '12px 8px' }}>Flat</th>
                  <th style={{ padding: '12px 8px' }}>Status</th>
                  <th style={{ padding: '12px 8px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {staffList.map((staff) => (
                  <tr key={staff.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px 8px', fontWeight: '600' }}>{staff.name}</td>
                    <td style={{ padding: '12px 8px' }}>{staff.role}</td>
                    <td style={{ padding: '12px 8px' }}>{staff.phone_number}</td>
                    <td style={{ padding: '12px 8px' }}>{staff.flat_number || 'Common'}</td>
                    <td style={{ padding: '12px 8px' }}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: 'bold',
                        color: staff.status === 'active' ? '#2F855A' : '#718096',
                        background: staff.status === 'active' ? '#e6fffa' : '#edf2f7'
                      }}>
                        {staff.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                      {staff.status === 'active' && (
                        <>
                          <button
                            onClick={() => handleEdit(staff)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#007AFF',
                              cursor: 'pointer',
                              fontWeight: '600',
                              marginRight: '12px'
                            }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(staff.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#c53030',
                              cursor: 'pointer',
                              fontWeight: '600'
                            }}
                          >
                            Deactivate
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default StaffRegistryTab;
