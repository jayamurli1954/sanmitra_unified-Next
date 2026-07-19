import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { getErrorMessage } from './settingsHelpers';

const RolesTab = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [roleChanges, setRoleChanges] = useState({});

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/users/');
      setUsers(response.data);
      // Initialize role changes state with current roles
      const initialRoles = {};
      response.data.forEach(user => {
        initialRoles[user.id] = user.role;
      });
      setRoleChanges(initialRoles);
    } catch (error) {
      console.error('Error loading users:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = (userId, newRole) => {
    setRoleChanges(prev => ({
      ...prev,
      [userId]: newRole
    }));
  };

  const handleSaveRole = async (userId, userName) => {
    const newRole = roleChanges[userId];
    const user = users.find(u => u.id === userId);

    if (newRole === user.role) {
      setMessage({ type: 'info', text: 'No changes to save' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      return;
    }

    try {
      await api.patch(`/users/${userId}/role`, { role: newRole });
      setMessage({ type: 'success', text: `Role updated for ${userName}` });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      // Reload users to get updated data
      await loadUsers();
    } catch (error) {
      console.error('Error updating role:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Roles & Permissions</h2>
      <p className="settings-tab-description">Define access control</p>

      {message.text && (
        <div className={`settings-message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <h3>Role Management</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Approve Members</th>
                <th>Generate Bills</th>
                <th>Edit Accounting</th>
                <th>View Reports</th>
                <th>Close Complaints</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Admin</strong></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr>
                <td><strong>Treasurer</strong></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr>
                <td><strong>Secretary</strong></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr>
                <td><strong>Auditor</strong></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr>
                <td><strong>Resident</strong></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
        <button className="settings-action-btn" style={{ marginTop: '15px' }}>
          Edit Permissions
        </button>
      </div>

      <div className="settings-section">
        <h3>Assign Roles</h3>
        {loading ? (
          <p>Loading users...</p>
        ) : users.length === 0 ? (
          <p>No users found. Please add users from the Members screen first.</p>
        ) : (
          <div className="settings-table-container">
            <table className="settings-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Flat Number</th>
                  <th>Current Role</th>
                  <th>New Role</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.name}</td>
                    <td>{user.email}</td>
                    <td>{user.apartment_number || '-'}</td>
                    <td><span className="settings-badge">{user.role}</span></td>
                    <td>
                      <select
                        value={roleChanges[user.id] || user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                        className="settings-select"
                      >
                        <option value="admin">Admin</option>
                        <option value="treasurer">Treasurer</option>
                        <option value="secretary">Secretary</option>
                        <option value="auditor">Auditor</option>
                        <option value="resident">Resident</option>
                      </select>
                    </td>
                    <td>
                      <button
                        className="settings-action-btn"
                        onClick={() => handleSaveRole(user.id, user.name)}
                        disabled={roleChanges[user.id] === user.role}
                        style={{
                          opacity: roleChanges[user.id] === user.role ? 0.5 : 1,
                          cursor: roleChanges[user.id] === user.role ? 'not-allowed' : 'pointer'
                        }}
                      >
                        Save
                      </button>
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

export default RolesTab;
