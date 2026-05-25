/**
 * GruhaMitra Members Screen
 * Admin can onboard new members (owners/tenants) with flat assignment
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FaUsers,
  FaHome,
  FaKey,
  FaCheckCircle,
  FaArrowLeft,
  FaUserPlus,
  FaEdit,
  FaDoorOpen,
  FaFileAlt,
  FaUserShield,
  FaIdCard,
  FaFileSignature,
  FaPlus,
  FaSave,
  FaTimes,
  FaSpinner,
  FaUpload,
  FaDownload,
} from 'react-icons/fa';
import memberOnboardingService from '../services/memberOnboardingService';
import flatsService from '../services/flatsService';
import moveGovernanceService from '../services/moveGovernanceService';
import accountingService from '../services/accountingService';

const MembersScreen = () => {
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [importing, setImporting] = useState(false);
  const importInputRef = useRef(null);

  useEffect(() => {
    loadMembers();
  }, [statusFilter]);

  const loadMembers = async () => {
    setLoading(true);
    try {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const membersList = await memberOnboardingService.listMembers(filter);
      console.log(`Loaded ${membersList.length} members`);
      setMembers(membersList);

      // Debug: Check if we're getting data
      if (membersList.length === 0) {
        console.warn('No members found. Checking debug endpoint...');
        try {
          const debugRes = await api.get('/member-onboarding/debug');
          console.log('Debug info:', debugRes.data);
        } catch (debugError) {
          console.error('Debug endpoint error:', debugError);
        }
      }
    } catch (error) {
      console.error('Error loading members:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      alert(`Failed to load members: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const filteredMembers = members.filter(member => {
    const matchesSearch =
      member.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.flat_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (member.email && member.email.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSearch;
  }).sort((a, b) => {
    // Sort by flat number (A-101, A-102, A-103, etc.)
    return a.flat_number.localeCompare(b.flat_number, undefined, { numeric: true, sensitivity: 'base' });
  });

  const stats = {
    total: members.filter(m => m.status === 'active').reduce((sum, m) => sum + (m.total_occupants || 0), 0),
    owners: members.filter(m => m.status === 'active' && m.member_type === 'owner').length,
    tenants: members.filter(m => m.status === 'active' && m.member_type === 'tenant').length,
    active: members.filter(m => m.status === 'active').length,
  };

  const handleDownloadTemplate = async () => {
    try {
      const blob = await memberOnboardingService.downloadTemplate();
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'members_template.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to download template: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handlePickImportFile = () => {
    if (importInputRef.current) {
      importInputRef.current.value = '';
      importInputRef.current.click();
    }
  };

  const handleImportMembers = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const lowerName = file.name.toLowerCase();
    if (!(lowerName.endsWith('.csv') || lowerName.endsWith('.xlsx'))) {
      alert('Please select a CSV or XLSX file.');
      return;
    }
    setImporting(true);
    try {
      const result = await memberOnboardingService.bulkImportMembers(file);
      const summary = `Import completed.\nRows: ${result.total_rows}\nCreated: ${result.created}\nFailed: ${result.failed}`;
      if ((result.failed || 0) > 0) {
        const firstErrors = (result.errors || [])
          .slice(0, 5)
          .map((e) => `Row ${e.row}: ${e.error}`)
          .join('\n');
        alert(`${summary}\n\nTop errors:\n${firstErrors}`);
      } else {
        alert(summary);
      }
      await loadMembers();
    } catch (error) {
      alert(`Bulk import failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title"><FaUsers style={{ marginRight: 8 }} />Members</h1>
          <span className="dashboard-header-subtitle">Member Onboarding & Management</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
            <FaArrowLeft style={{ marginRight: 6 }} />Back to Dashboard
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {/* Stats Cards */}
        <div className="dashboard-metrics-grid">
          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon"><FaUsers /></span>
            <div className="dashboard-metric-label">Total Members</div>
            <div className="dashboard-metric-value">{stats.total}</div>
          </div>
          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon"><FaHome /></span>
            <div className="dashboard-metric-label">Owners</div>
            <div className="dashboard-metric-value">{stats.owners}</div>
          </div>
          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon"><FaKey /></span>
            <div className="dashboard-metric-label">Tenants</div>
            <div className="dashboard-metric-value">{stats.tenants}</div>
          </div>
          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon"><FaCheckCircle /></span>
            <div className="dashboard-metric-label">Active</div>
            <div className="dashboard-metric-value">{stats.active}</div>
          </div>
        </div>

        {/* Actions Bar */}
        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '24px',
          flexWrap: 'wrap',
          alignItems: 'center'
        }}>
          <button
            onClick={() => setShowAddForm(true)}
            className="login-button"
            style={{ maxWidth: '200px' }}
          >
            <FaUserPlus style={{ marginRight: 6 }} />Add New Member
          </button>
          <button
            onClick={handleDownloadTemplate}
            className="login-button"
            style={{ maxWidth: '190px', background: '#4C6EF5' }}
          >
            <FaDownload style={{ marginRight: 6 }} />Template CSV
          </button>
          <button
            onClick={handlePickImportFile}
            className="login-button"
            style={{ maxWidth: '240px', background: importing ? '#8a8a8a' : '#6F42C1' }}
            disabled={importing}
          >
            {importing ? (
              <><FaSpinner style={{ marginRight: 6 }} />Importing...</>
            ) : (
              <><FaUpload style={{ marginRight: 6 }} />Bulk Upload CSV/XLSX</>
            )}
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept=".csv,.xlsx"
            style={{ display: 'none' }}
            onChange={handleImportMembers}
          />

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
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="moved_out">Moved Out</option>
          </select>

          <input
            type="text"
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '10px 16px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '14px',
            }}
          />
        </div>

        {/* Members List */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div style={{ fontSize: '18px', color: '#666' }}>Loading members...</div>
          </div>
        ) : filteredMembers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}></div>
            <div style={{ fontSize: '18px', color: '#666', marginBottom: '8px' }}>
              {searchQuery ? 'No members found' : 'No members yet'}
            </div>
            {!searchQuery && (
              <button
                onClick={() => setShowAddForm(true)}
                className="login-button"
                style={{ maxWidth: '200px', marginTop: '16px' }}
              >
                Add First Member
              </button>
            )}
          </div>
        ) : (
          <div style={{
            background: '#fff',
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            border: '1px solid #E5E5EA',
          }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#F5F5F7', borderBottom: '2px solid #E5E5EA' }}>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '100px' }}>Flat</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '150px' }}>Name</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '120px' }}>Type</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '150px' }}>Email</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '120px' }}>Phone</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '80px' }}>Occupants</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '120px' }}>Move-In Date</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '100px' }}>Status</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: '14px', fontWeight: '600', color: '#666', minWidth: '120px' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMembers.map((member, index) => (
                    <MemberRow
                      key={member.id}
                      member={member}
                      onUpdate={loadMembers}
                      isEven={index % 2 === 0}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Add Member Modal */}
      {showAddForm && (
        <AddMemberModal
          onClose={() => {
            setShowAddForm(false);
            loadMembers();
          }}
        />
      )}
    </div>
  );
};

// Member Row Component (Table Row with Editable Fields)
const MemberRow = ({ member, onUpdate, isEven }) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [moveOutDate, setMoveOutDate] = useState('');
  const [showArrearsModal, setShowArrearsModal] = useState(false);
  const [showFlatTransferModal, setShowFlatTransferModal] = useState(false);
  const [showChecklistModal, setShowChecklistModal] = useState(false);
  const [finalBill, setFinalBill] = useState(null);
  const [flatBalance, setFlatBalance] = useState(0);
  const [showMoveOut, setShowMoveOut] = useState(false);
  const [showDamageForm, setShowDamageForm] = useState(false);
  const [damageAmount, setDamageAmount] = useState('');
  const [damageDesc, setDamageDesc] = useState('');
  const [instantPost, setInstantPost] = useState(true);
  const resolvedFlatId = member.flat_id || member.flat_number;

  const [editData, setEditData] = useState({
    name: member.name || '',
    email: member.email || '',
    phone_number: member.phone_number || '',
    total_occupants: member.total_occupants || 1,
  });

  const isActive = member.status === 'active' || (!member.move_out_date && member.status !== 'inactive');

  const handleSave = async () => {
    setSaving(true);
    try {
      await memberOnboardingService.updateMember(member.id, editData);
      alert('Member updated successfully!');
      setEditing(false);
      onUpdate();
    } catch (error) {
      console.error('Error updating member:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to update member';
      alert(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditData({
      name: member.name || '',
      email: member.email || '',
      phone_number: member.phone_number || '',
      total_occupants: member.total_occupants || 1,
    });
    setEditing(false);
  };

  const handleMoveOut = async () => {
    if (!moveOutDate) {
      alert('Please enter move-out date');
      return;
    }

    setSaving(true);
    try {
      await memberOnboardingService.updateMember(member.id, {
        status: 'moved_out',
        move_out_date: moveOutDate,
      });
      alert('Member marked as moved out successfully!');
      setShowMoveOut(false);
      setMoveOutDate('');
      onUpdate();
    } catch (error) {
      console.error('Error updating member:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to update member';
      alert(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleRaiseDamageClaim = async () => {
    if (!damageAmount || !damageDesc) {
      alert('Please enter both amount and description for the claim');
      return;
    }
    setSaving(true);
    try {
      await moveGovernanceService.raiseDamageClaim({
        flat_id: resolvedFlatId,
        amount: parseFloat(damageAmount),
        description: damageDesc,
        instant_post: instantPost
      });
      alert(instantPost ? 'Damage claim raised and ledger updated!' : 'Charge queued for next monthly bill!');
      setDamageAmount('');
      setDamageDesc('');
      setShowDamageForm(false);
      if (instantPost) await loadFlatBalance();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to raise damage claim');
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadNDC = async () => {
    try {
      await moveGovernanceService.downloadNDC(resolvedFlatId, member.flat_number);
    } catch (error) {
      alert(error?.message || "Failed to download NDC. Ensure flat balance is zero.");
    }
  };

  const handleDownloadPolice = async () => {
    try {
      await moveGovernanceService.downloadPoliceVerification(member.id, member.name);
    } catch (error) {
      alert(error?.message || "Failed to download Police Verification Form.");
    }
  };

  const handleDownloadTenantId = async () => {
    try {
      await moveGovernanceService.downloadTenantIdForm(member.id, member.name);
    } catch (error) {
      alert(error?.message || "Failed to download Tenant ID Form.");
    }
  };

  const loadFlatBalance = async () => {
    try {
      // Fetch final bill calculation from move governance service
      const data = await moveGovernanceService.calculateFinalBill(resolvedFlatId);
      setFinalBill(data);
      setFlatBalance(data.total_payable);
    } catch (error) {
      console.error("Error loading balance:", error);
      // Fallback to simple balance if calculation fails
      try {
        const bills = await accountingService.getUnpaidBills(resolvedFlatId);
        const total = bills.reduce((sum, b) => sum + (b.total_amount || 0), 0);
        setFlatBalance(total);
      } catch (e) {
        setFlatBalance(0);
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#34C759';
      case 'inactive': return '#8E8E93';
      case 'moved_out': return '#FF9500';
      default: return '#8E8E93';
    }
  };

  const getMemberTypeIcon = (type) => {
    return type === 'owner' ? <FaHome style={{ marginRight: 6 }} /> : <FaKey style={{ marginRight: 6 }} />;
  };

  return (
    <>
      <tr style={{
        backgroundColor: isEven ? '#FAFAFA' : '#FFF',
        borderBottom: '1px solid #E5E5EA',
      }}>
        <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: '600', color: '#1D1D1F' }}>
          {member.flat_number}
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
          {editing ? (
            <input
              type="text"
              value={editData.name}
              onChange={(e) => setEditData({ ...editData, name: e.target.value })}
              style={{
                width: '100%',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
            />
          ) : (
            <span style={{ color: '#1D1D1F' }}>{member.name}</span>
          )}
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
          <span style={{
            display: 'inline-block',
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: '600',
            backgroundColor: member.member_type === 'owner' ? '#007AFF20' : '#34C75920',
            color: member.member_type === 'owner' ? '#007AFF' : '#34C759',
            textTransform: 'capitalize',
          }}>
            {getMemberTypeIcon(member.member_type)} {member.member_type}
          </span>
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
          {editing ? (
            <input
              type="email"
              value={editData.email}
              onChange={(e) => setEditData({ ...editData, email: e.target.value })}
              style={{
                width: '100%',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
            />
          ) : (
            <span style={{ color: '#666' }}>{member.email || '-'}</span>
          )}
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
          {editing ? (
            <input
              type="tel"
              value={editData.phone_number}
              onChange={(e) => setEditData({ ...editData, phone_number: e.target.value })}
              style={{
                width: '100%',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
            />
          ) : (
            <span style={{ color: '#666' }}>{member.phone_number && member.phone_number !== 'Private' ? member.phone_number : '-'}</span>
          )}
        </td>
        <td style={{ padding: '12px 16px', textAlign: 'center', fontSize: '14px' }}>
          {editing ? (
            <input
              type="number"
              value={editData.total_occupants}
              onChange={(e) => setEditData({ ...editData, total_occupants: parseInt(e.target.value) || 1 })}
              min="1"
              style={{
                width: '60px',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                fontSize: '14px',
                textAlign: 'center',
              }}
            />
          ) : (
            <span style={{ color: '#666' }}>{member.total_occupants || '-'}</span>
          )}
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>
          {member.move_in_date ? new Date(member.move_in_date).toLocaleDateString('en-GB') : '-'}
        </td>
        <td style={{ padding: '12px 16px', fontSize: '14px' }}>
          <span style={{
            display: 'inline-block',
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: '600',
            backgroundColor: getStatusColor(member.status) + '20',
            color: getStatusColor(member.status),
            textTransform: 'uppercase',
          }}>
            {member.status}
          </span>
        </td>
        <td style={{ padding: '12px 16px', textAlign: 'center' }}>
          {editing ? (
            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: '#34C759',
                  color: '#FFF',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? <FaSpinner /> : <FaSave />}
              </button>
              <button
                onClick={handleCancel}
                disabled={saving}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  backgroundColor: '#FFF',
                  color: '#666',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: saving ? 'not-allowed' : 'pointer',
                }}
              >
                <FaTimes />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => setEditing(true)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #007AFF',
                  backgroundColor: '#FFF',
                  color: '#007AFF',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <FaEdit style={{ marginRight: 6 }} />Edit
              </button>
              {(() => {
                // Show Move Out button for active members who haven't moved out yet
                const isActive = member.status === 'active' || member.status === 'ACTIVE';

                // Check if member has moved out:
                // - No move_out_date means they haven't moved out
                // - If move_out_date exists, check if it's in the future (scheduled but not moved yet)
                // - If move_out_date is in the past, they've already moved out
                const hasMovedOut = member.move_out_date &&
                  member.move_out_date !== null &&
                  member.move_out_date !== '' &&
                  new Date(member.move_out_date) <= new Date();

                // Show button if active AND not moved out yet
                const shouldShow = isActive && !hasMovedOut;

                // Debug for A-304
                if (member.flat_number === 'A-304' || (member.flat_number || '').includes('A-304')) {
                  console.log(' A-304 Move Out Button Check:', {
                    status: member.status,
                    isActive: isActive,
                    move_out_date: member.move_out_date,
                    hasMovedOut: hasMovedOut,
                    shouldShow: shouldShow,
                    currentDate: new Date().toISOString(),
                    moveOutDateParsed: member.move_out_date ? new Date(member.move_out_date).toISOString() : null,
                    dateComparison: member.move_out_date ? new Date(member.move_out_date) <= new Date() : null
                  });
                }

                return shouldShow;
              })() && (
                  <button
                    onClick={() => {
                      setShowMoveOut(!showMoveOut);
                      if (!showMoveOut) loadFlatBalance();
                    }}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: '1px solid #FF9500',
                      backgroundColor: '#FFF',
                      color: '#FF9500',
                      fontSize: '12px',
                      fontWeight: '600',
                      cursor: 'pointer',
                    }}
                  >
                    <FaDoorOpen style={{ marginRight: 6 }} />Move Out
                  </button>
                )}
              <button
                onClick={() => setShowChecklistModal(true)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #007AFF',
                  backgroundColor: '#FFF',
                  color: '#007AFF',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <FaFileAlt style={{ marginRight: 6 }} />Docs
              </button>
              <button
                onClick={handleDownloadPolice}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #5856D6',
                  backgroundColor: '#FFF',
                  color: '#5856D6',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <FaUserShield style={{ marginRight: 6 }} />Police Form
              </button>
              <button
                onClick={handleDownloadTenantId}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #8E44AD',
                  backgroundColor: '#FFF',
                  color: '#8E44AD',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <FaIdCard style={{ marginRight: 6 }} />Tenant ID
              </button>
              <button
                onClick={handleDownloadNDC}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #34C759',
                  backgroundColor: '#FFF',
                  color: '#34C759',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <FaFileSignature style={{ marginRight: 6 }} />NDC
              </button>
              {isActive && (
                <button
                  onClick={() => setShowDamageForm(!showDamageForm)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    border: '1px solid #F57C00',
                    backgroundColor: '#FFF',
                    color: '#F57C00',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer',
                  }}
                >
                  <FaPlus style={{ marginRight: 6 }} />Charge
                </button>
              )}
            </div>
          )}
        </td>
      </tr>
      {showDamageForm && !showMoveOut && (
        <tr style={{ backgroundColor: '#FFF9C4' }}>
          <td colSpan="9" style={{ padding: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '600px' }}>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#F57C00' }}>ADD SUPPLEMENTARY CHARGE (DAMAGES/MISC)</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Description"
                  value={damageDesc}
                  onChange={(e) => setDamageDesc(e.target.value)}
                  style={{ flex: 2, padding: '8px', fontSize: '14px', border: '1px solid #CCC', borderRadius: '4px' }}
                />
                <input
                  type="number"
                  placeholder="Amount"
                  value={damageAmount}
                  onChange={(e) => setDamageAmount(e.target.value)}
                  style={{ flex: 1, padding: '8px', fontSize: '14px', border: '1px solid #CCC', borderRadius: '4px' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <label style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                  <input type="radio" checked={instantPost} onChange={() => setInstantPost(true)} />
                  Post Instantly (JV Entry)
                </label>
                <label style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                  <input type="radio" checked={!instantPost} onChange={() => setInstantPost(false)} />
                  Include in Next Monthly Bill
                </label>
                <div style={{ flex: 1 }} />
                <button
                  onClick={handleRaiseDamageClaim}
                  disabled={saving}
                  style={{ padding: '8px 20px', backgroundColor: '#F57C00', color: '#FFF', border: 'none', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }}
                >
                  {saving ? 'Adding...' : 'Add Charge'}
                </button>
                <button
                  onClick={() => setShowDamageForm(false)}
                  style={{ padding: '8px 12px', backgroundColor: '#EEE', color: '#666', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
      {showChecklistModal && (
        <DocumentChecklistModal
          member={member}
          onClose={() => setShowChecklistModal(false)}
        />
      )}
      {showArrearsModal && (
        <ArrearsTransferModal
          member={member}
          amount={flatBalance}
          onClose={() => {
            setShowArrearsModal(false);
            onUpdate();
          }}
        />
      )}
      {showFlatTransferModal && (
        <FlatTransferModal
          member={member}
          amount={flatBalance}
          onClose={() => {
            setShowFlatTransferModal(false);
            onUpdate();
          }}
        />
      )}
      {showMoveOut && (
        <tr style={{ backgroundColor: '#FFF3E0' }}>
          <td colSpan="9" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flex: 1, minWidth: '300px' }}>
                <label style={{ fontSize: '14px', fontWeight: '600', minWidth: '120px' }}>
                  Move-Out Date:
                </label>
                <input
                  type="date"
                  value={moveOutDate}
                  onChange={(e) => setMoveOutDate(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                  }}
                />
                <button
                  onClick={handleMoveOut}
                  disabled={saving}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: '#FF9500',
                    color: '#FFF',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: saving ? 'not-allowed' : 'pointer',
                    opacity: saving ? 0.6 : 1,
                  }}
                >
                  {saving ? 'Saving...' : 'Confirm'}
                </button>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                {flatBalance > 0 && (
                  <>
                    <button
                      onClick={() => setShowArrearsModal(true)}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '6px',
                        border: '1px solid #E44D26',
                        backgroundColor: '#FFF',
                        color: '#E44D26',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: 'pointer',
                      }}
                    >
                       Transfer to Personal Arrears
                    </button>
                    <button
                      onClick={() => setShowFlatTransferModal(true)}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '6px',
                        border: '1px solid #F57C00',
                        backgroundColor: '#FFF',
                        color: '#F57C00',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: 'pointer',
                      }}
                    >
                       Carry Dues to New Flat
                    </button>
                  </>
                )}
                <button
                  onClick={() => {
                    setShowMoveOut(false);
                    setMoveOutDate('');
                    setShowDamageForm(false);
                  }}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    backgroundColor: '#FFF',
                    color: '#666',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </div>

              {/* Damage Claim Section */}
              <div style={{ width: '100%', marginTop: '12px', padding: '12px', backgroundColor: '#FFF', borderRadius: '8px', border: '1px solid #FFD54F' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#F57C00' }}>ADD DAMAGE/MISC CLAIM</div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="text"
                      placeholder="Description of damage/claim"
                      value={damageDesc}
                      onChange={(e) => setDamageDesc(e.target.value)}
                      style={{ flex: 2, padding: '6px', fontSize: '13px', border: '1px solid #CCC', borderRadius: '4px' }}
                    />
                    <input
                      type="number"
                      placeholder="Amount"
                      value={damageAmount}
                      onChange={(e) => setDamageAmount(e.target.value)}
                      style={{ flex: 1, padding: '6px', fontSize: '13px', border: '1px solid #CCC', borderRadius: '4px' }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '4px' }}>
                    <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                      <input type="radio" checked={instantPost} onChange={() => setInstantPost(true)} />
                      Post Instantly
                    </label>
                    <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                      <input type="radio" checked={!instantPost} onChange={() => setInstantPost(false)} />
                      Queue for Monthly Bill
                    </label>
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={handleRaiseDamageClaim}
                      disabled={saving}
                      style={{ padding: '6px 16px', backgroundColor: '#F57C00', color: '#FFF', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}
                    >
                      {saving ? 'Adding...' : 'Confirm Claim'}
                    </button>
                    {showMoveOut && (
                      <button
                        onClick={() => setShowDamageForm(false)}
                        style={{ padding: '6px 12px', backgroundColor: '#EEE', color: '#666', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        X
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {flatBalance > 0 && (
                <div style={{ color: '#E44D26', fontSize: '12px', width: '100%', marginTop: '8px', fontWeight: 'bold' }}>
                  {finalBill ? (
                    <>
                      Outstanding: {finalBill.outstanding_arrears.toLocaleString()}
                      {finalBill.current_month_prorata > 0 && ` + Pro-rata: ${finalBill.current_month_prorata.toLocaleString()}`}
                      = <b>Total: {finalBill.total_payable.toLocaleString()}</b>
                      <div style={{ fontWeight: 'normal', color: '#666', marginTop: '4px' }}>{finalBill.calculation_notes}</div>
                    </>
                  ) : (
                    `Outstanding Dues: ${flatBalance.toLocaleString()}.`
                  )}
                  <br />Member status can only be set to INACTIVE if dues are paid or transferred to Personal Arrears.
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
};

// Add Member Modal Component
const AddMemberModal = ({ onClose }) => {
  const [flats, setFlats] = useState([]);
  const [members, setMembers] = useState([]);
  const [loadingFlats, setLoadingFlats] = useState(true);
  const [selectedFlat, setSelectedFlat] = useState(null);
  const [existingMember, setExistingMember] = useState(null);
  const [showFlatPicker, setShowFlatPicker] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [formData, setFormData] = useState({
    name: '',
    phone_number: '',
    email: '',
    member_type: 'owner',
    move_in_date: '',
    total_occupants: '1',
    name_prefix: 'Mr.',
    occupation: '',
    occupation_type: '',
    employment_type: '',
    professional_type: '',
    is_mobile_public: false,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoadingFlats(true);
    try {
      const [flatsList, membersList] = await Promise.all([
        flatsService.getFlats(),
        memberOnboardingService.listMembers()
      ]);
      setFlats(flatsList);
      setMembers(membersList);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Failed to load data. Please try again.');
    } finally {
      setLoadingFlats(false);
    }
  };

  // Check if flat has existing active member
  const checkExistingMember = (flat) => {
    const member = members.find(m =>
      m.flat_number === flat.flat_number &&
      m.status === 'active' &&
      !m.move_out_date
    );
    return member;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!selectedFlat) {
      alert('Please select a flat');
      return;
    }
    if (!formData.name.trim()) {
      alert('Please enter member name');
      return;
    }
    if (!formData.phone_number.trim() || formData.phone_number.length < 10) {
      alert('Please enter a valid phone number');
      return;
    }
    if (!formData.email.trim() || !formData.email.includes('@')) {
      alert('Please enter a valid email address');
      return;
    }
    if (!formData.move_in_date) {
      alert('Please enter move-in date (YYYY-MM-DD)');
      return;
    }
    if (!formData.total_occupants || parseInt(formData.total_occupants) < 1) {
      alert('Please enter valid number of occupants');
      return;
    }

    setSaving(true);
    try {
      const memberData = {
        flat_number: selectedFlat.flat_number,
        name: `${formData.name_prefix} ${formData.name.trim()}`,
        phone_number: formData.phone_number.trim(),
        email: formData.email.trim(),
        member_type: formData.member_type,
        move_in_date: formData.move_in_date,
        total_occupants: parseInt(formData.total_occupants),
        is_primary: true,
        occupation: formData.occupation_type === 'Professional'
          ? (formData.professional_type || 'Professional')
          : formData.occupation_type === 'Employed'
            ? (formData.employment_type ? `Employed (${formData.employment_type})` : 'Employed')
            : (formData.occupation_type || formData.occupation.trim() || undefined),
        is_mobile_public: formData.is_mobile_public,
      };

      await memberOnboardingService.createMember(memberData);
      alert('Member onboarded successfully!');
      onClose();
    } catch (error) {
      console.error('Error creating member:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to onboard member';
      alert(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
    }}>
      <div style={{
        background: '#fff',
        borderRadius: '12px',
        padding: '24px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#1D1D1F', margin: 0 }}>
            {existingMember ? 'Member Details' : 'Onboard New Member'}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#8E8E93',
              padding: '4px 8px',
            }}
          >
            
          </button>
        </div>

        {/* Show existing member data if available */}
        {existingMember ? (
          <div>
            <div style={{
              padding: '20px',
              backgroundColor: '#E8F5E9',
              borderRadius: '8px',
              marginBottom: '20px',
              border: '1px solid #4CAF50'
            }}>
              <div style={{ fontSize: '16px', fontWeight: '600', color: '#2E7D32', marginBottom: '12px' }}>
                 This flat already has a member onboarded
              </div>
              <div style={{ fontSize: '14px', color: '#666' }}>
                All member data is already captured. No need to onboard again.
              </div>
            </div>

            {/* Display Member Information */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ padding: '16px', backgroundColor: '#F5F5F7', borderRadius: '8px' }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#8E8E93', marginBottom: '8px', textTransform: 'uppercase' }}>
                  Flat Details
                </div>
                <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                  Flat {selectedFlat.flat_number}
                </div>
                <div style={{ fontSize: '14px', color: '#666', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <span> {selectedFlat.area_sqft} sq ft</span>
                  {selectedFlat.bedrooms && <span> {selectedFlat.bedrooms} BR</span>}
                </div>
              </div>

              <div style={{ padding: '16px', backgroundColor: '#F5F5F7', borderRadius: '8px' }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#8E8E93', marginBottom: '12px', textTransform: 'uppercase' }}>
                  Member Information
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Name</div>
                    <div style={{ fontSize: '16px', fontWeight: '600' }}>{existingMember.name}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Member Type</div>
                    <div style={{ fontSize: '16px', fontWeight: '600', textTransform: 'capitalize' }}>
                      {existingMember.member_type === 'owner' ? ' Owner' : ' Tenant'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Mobile Number</div>
                    <div style={{ fontSize: '16px' }}>{existingMember.phone_number || 'N/A'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Email Address</div>
                    <div style={{ fontSize: '16px' }}>{existingMember.email || 'N/A'}</div>
                  </div>
                  {existingMember.occupation && (
                    <div>
                      <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Occupation</div>
                      <div style={{ fontSize: '16px' }}>{existingMember.occupation}</div>
                    </div>
                  )}
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Total Occupants</div>
                    <div style={{ fontSize: '16px' }}>{existingMember.total_occupants}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Move-In Date</div>
                    <div style={{ fontSize: '16px' }}>
                      {new Date(existingMember.move_in_date).toLocaleDateString()}
                    </div>
                  </div>
                  {existingMember.move_out_date && (
                    <div>
                      <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Move-Out Date</div>
                      <div style={{ fontSize: '16px' }}>
                        {new Date(existingMember.move_out_date).toLocaleDateString()}
                      </div>
                    </div>
                  )}
                  <div>
                    <div style={{ fontSize: '12px', color: '#8E8E93', marginBottom: '4px' }}>Status</div>
                    <div style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '600',
                      backgroundColor: existingMember.status === 'active' ? '#34C75920' : '#8E8E9320',
                      color: existingMember.status === 'active' ? '#34C759' : '#8E8E93',
                      textTransform: 'uppercase',
                    }}>
                      {existingMember.status}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button
                onClick={() => {
                  setSelectedFlat(null);
                  setExistingMember(null);
                  setShowFlatPicker(true);
                }}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  backgroundColor: '#fff',
                  color: '#666',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                Select Different Flat
              </button>
              <button
                onClick={onClose}
                className="login-button"
                style={{ flex: 1 }}
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {/* Flat Selection */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Select Flat *
              </label>
              <button
                type="button"
                onClick={() => setShowFlatPicker(true)}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  backgroundColor: '#fff',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontSize: '14px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                {selectedFlat ? (
                  <span>
                    Flat {selectedFlat.flat_number} - {selectedFlat.area_sqft} sq ft
                    {selectedFlat.bedrooms && `  ${selectedFlat.bedrooms} BR`}
                  </span>
                ) : (
                  <span style={{ color: '#8E8E93' }}>Tap to select a flat</span>
                )}
                <span></span>
              </button>
            </div>

            {/* Member Details */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Full Name *
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  value={formData.name_prefix}
                  onChange={(e) => setFormData({ ...formData, name_prefix: e.target.value })}
                  style={{
                    width: '80px',
                    padding: '12px 8px',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: '#fff'
                  }}
                >
                  <option value="Mr.">Mr.</option>
                  <option value="Mrs.">Mrs.</option>
                  <option value="Ms.">Ms.</option>
                  <option value="Smt.">Smt.</option>
                  <option value="Shri">Shri</option>
                  <option value="Dr.">Dr.</option>
                </select>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="Enter Full Name"
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Phone Number *
              </label>
              <input
                type="tel"
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                required
                maxLength={15}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '14px',
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Email Address *
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '14px',
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Member Type *
              </label>
              <div style={{ display: 'flex', gap: '12px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    value="owner"
                    checked={formData.member_type === 'owner'}
                    onChange={(e) => setFormData({ ...formData, member_type: e.target.value })}
                  />
                  <span>Owner</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    value="tenant"
                    checked={formData.member_type === 'tenant'}
                    onChange={(e) => setFormData({ ...formData, member_type: e.target.value })}
                  />
                  <span>Tenant</span>
                </label>
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Occupation (Optional)
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <select
                  value={formData.occupation_type}
                  onChange={(e) => setFormData({
                    ...formData,
                    occupation_type: e.target.value,
                    professional_type: e.target.value === 'Professional' ? formData.professional_type : '',
                    employment_type: e.target.value === 'Employed' ? formData.employment_type : ''
                  })}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: '#fff'
                  }}
                >
                  <option value="">-- Select Occupation --</option>
                  <option value="Employed">Employed</option>
                  <option value="Business">Business</option>
                  <option value="Professional">Professional</option>
                  <option value="Homemaker">Homemaker</option>
                  <option value="Retired">Retired</option>
                  <option value="Student">Student</option>
                  <option value="Other">Other</option>
                </select>

                {formData.occupation_type === 'Employed' && (
                  <select
                    value={formData.employment_type}
                    onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid #34C759', // Different highlight for employment
                      fontSize: '14px',
                      backgroundColor: '#F0FFF4'
                    }}
                  >
                    <option value="">-- Select Employment Sector --</option>
                    <option value="Govt.">Govt.</option>
                    <option value="Private">Private</option>
                  </select>
                )}

                {formData.occupation_type === 'Professional' && (
                  <select
                    value={formData.professional_type}
                    onChange={(e) => setFormData({ ...formData, professional_type: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid #007AFF', // Highlight the sub-selection
                      fontSize: '14px',
                      backgroundColor: '#F0F8FF'
                    }}
                  >
                    <option value="">-- Select Profession --</option>
                    <option value="Doctor (Dr)">Doctor (Dr)</option>
                    <option value="Advocate (Adv)">Advocate (Adv)</option>
                    <option value="Chartered Accountant (CA)">Chartered Accountant (CA)</option>
                    <option value="Engineer">Engineer</option>
                    <option value="Architect">Architect</option>
                    <option value="Teaching">Teaching</option>
                    <option value="Other Professional">Other Professional</option>
                  </select>
                )}

                {(formData.occupation_type === 'Other' || (formData.occupation_type === 'Professional' && formData.professional_type === 'Other Professional')) && (
                  <input
                    type="text"
                    value={formData.occupation}
                    onChange={(e) => setFormData({ ...formData, occupation: e.target.value })}
                    placeholder="Specify details..."
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid #ddd',
                      fontSize: '14px',
                    }}
                  />
                )}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Move-In Date *
              </label>
              <input
                type="date"
                value={formData.move_in_date}
                onChange={(e) => setFormData({ ...formData, move_in_date: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '14px',
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                Total Occupants *
              </label>
              <input
                type="number"
                value={formData.total_occupants}
                onChange={(e) => setFormData({ ...formData, total_occupants: e.target.value })}
                required
                min="1"
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '14px',
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={formData.is_mobile_public}
                  onChange={(e) => setFormData({ ...formData, is_mobile_public: e.target.checked })}
                />
                <span style={{ fontSize: '14px' }}>Make mobile number visible to other members</span>
              </label>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  backgroundColor: '#fff',
                  color: '#666',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="login-button"
                style={{ flex: 1, opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
              >
                {saving ? 'Onboarding...' : 'Onboard Member'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Flat Picker Modal */}
      {showFlatPicker && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1001,
          padding: '20px',
        }}>
          <div style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            width: '100%',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>Select Flat</h3>
              <button
                onClick={() => setShowFlatPicker(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#8E8E93',
                }}
              >
                
              </button>
            </div>

            {loadingFlats ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>Loading flats...</div>
            ) : flats.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}></div>
                <div>No flats available. Please add flats first.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {flats.map((flat) => (
                  <button
                    key={flat.id}
                    onClick={() => {
                      // Check if flat already has an active member
                      const member = checkExistingMember(flat);

                      if (member) {
                        // Flat already has complete member data - show read-only view
                        setSelectedFlat(flat);
                        setExistingMember(member);
                        setShowFlatPicker(false);
                      } else {
                        // No member exists - show onboarding form with auto-filled data
                        setSelectedFlat(flat);
                        setExistingMember(null);
                        setFormData((prev) => {
                          // Derive default member type from occupancy status if available
                          let derivedMemberType = prev.member_type;
                          if (flat.occupancy_status) {
                            if (flat.occupancy_status === 'OWNER_OCCUPIED') {
                              derivedMemberType = 'owner';
                            } else if (flat.occupancy_status === 'TENANT_OCCUPIED') {
                              derivedMemberType = 'tenant';
                            }
                          }

                          return {
                            ...prev,
                            // Pre-fill core identity from flat owner data
                            name: flat.owner_name || prev.name,
                            phone_number: flat.owner_phone || prev.phone_number,
                            email: flat.owner_email || prev.email,
                            // If occupants already captured for the flat, use that as default
                            total_occupants:
                              flat.occupants && String(flat.occupants) !== '0'
                                ? String(flat.occupants)
                                : prev.total_occupants,
                            // Set sensible defaults where user shouldn't need to type again
                            member_type: derivedMemberType,
                            // Default move-in date if not already chosen (backend uses YYYY-MM-DD)
                            move_in_date: prev.move_in_date || '2025-12-01',
                          };
                        });
                        setShowFlatPicker(false);
                      }
                    }}
                    style={{
                      padding: '16px',
                      borderRadius: '8px',
                      border: selectedFlat?.id === flat.id ? '2px solid #007AFF' : '1px solid #ddd',
                      backgroundColor: selectedFlat?.id === flat.id ? '#E3F2FD' : '#fff',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                          <div style={{ fontSize: '16px', fontWeight: '600' }}>
                            Flat {flat.flat_number}
                          </div>
                          {checkExistingMember(flat) && (
                            <span style={{
                              fontSize: '11px',
                              padding: '2px 8px',
                              borderRadius: '10px',
                              backgroundColor: '#E8F5E9',
                              color: '#2E7D32',
                              fontWeight: '600'
                            }}>
                               Member Exists
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '14px', color: '#666', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                          <span> {flat.area_sqft} sq ft</span>
                          {flat.bedrooms && <span> {flat.bedrooms} BR</span>}
                          {flat.owner_name && <span> {flat.owner_name}</span>}
                        </div>
                      </div>
                      {selectedFlat?.id === flat.id && (
                        <span style={{ color: '#007AFF', fontSize: '20px' }}></span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ============ FLAT TRANSFER MODAL ============
const FlatTransferModal = ({ member, amount, onClose }) => {
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState('');
  const [flats, setFlats] = useState([]);
  const [destinationFlatId, setDestinationFlatId] = useState('');
  const [loadingFlats, setLoadingFlats] = useState(true);

  useEffect(() => {
    const loadFlats = async () => {
      try {
        const data = await flatsService.getAllFlats();
        // Filter out the current flat
        setFlats(data.filter(f => String(f.id) !== String(member.flat_id || member.flat_number)));
      } catch (err) {
        console.error('Error loading flats:', err);
      } finally {
        setLoadingFlats(false);
      }
    };
    loadFlats();
  }, [member.flat_id]);

  const handleTransfer = async () => {
    if (!destinationFlatId) {
      alert("Please select a destination flat.");
      return;
    }

    const destFlat = flats.find(f => String(f.id) === String(destinationFlatId));

    if (!window.confirm(`Are you sure you want to transfer ${amount.toLocaleString()} from Flat ${member.flat_number} directly to Flat ${destFlat?.flat_number}? This will clear the old flat's balance and carry the debt forward.`)) {
      return;
    }

    setSaving(true);
    try {
      await moveGovernanceService.transferFlatToFlatArrears({
        source_flat_id: member.flat_id || member.flat_number,
        destination_flat_id: destinationFlatId,
        amount: amount,
        notes: notes
      });
      alert(`Dues successfully carried over to Flat ${destFlat?.flat_number}.`);
      onClose();
    } catch (error) {
      console.error('Error transferring back-to-back dues:', error);
      alert(error.response?.data?.detail || 'Failed to transfer dues');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2000,
    }}>
      <div style={{
        backgroundColor: '#FFF',
        borderRadius: '12px',
        padding: '24px',
        maxWidth: '450px',
        width: '90%',
        boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
      }}>
        <h3 style={{ marginTop: 0, color: '#F57C00' }}> Carry Dues to New Flat</h3>
        <p style={{ fontSize: '14px', color: '#666', lineHeight: '1.5' }}>
          Moving <b>{amount.toLocaleString()}</b> from <b>Flat {member.flat_number}</b> to another flat within the society. This clears the balance on {member.flat_number}.
        </p>

        {loadingFlats ? (
          <p>Loading flats...</p>
        ) : (
          <div style={{ marginTop: '16px' }}>
            <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#8E8E93', textTransform: 'uppercase' }}>
              Select Destination Flat
            </label>
            <select
              value={destinationFlatId}
              onChange={(e) => setDestinationFlatId(e.target.value)}
              style={{
                width: '100%',
                marginTop: '8px',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #DDD',
                fontSize: '14px',
                backgroundColor: '#FFF'
              }}
            >
              <option value="">-- Select Flat --</option>
              {flats.map(flat => (
                <option key={flat.id} value={flat.id}>
                  Flat {flat.flat_number}
                </option>
              ))}
            </select>
          </div>
        )}

        <div style={{ marginTop: '16px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#8E8E93', textTransform: 'uppercase' }}>
            Transfer Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={`e.g. Member changing residence from ${member.flat_number}...`}
            style={{
              width: '100%',
              marginTop: '8px',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid #DDD',
              fontSize: '14px',
              height: '80px',
              resize: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
          <button
            onClick={handleTransfer}
            disabled={saving || !destinationFlatId}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '8px',
              backgroundColor: '#F57C00',
              color: '#FFF',
              border: 'none',
              fontWeight: 'bold',
              cursor: (saving || !destinationFlatId) ? 'not-allowed' : 'pointer',
              opacity: (saving || !destinationFlatId) ? 0.7 : 1
            }}
          >
            {saving ? 'Transferring...' : 'Transfer Dues'}
          </button>
          <button
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '12px 24px',
              borderRadius: '8px',
              backgroundColor: '#EEE',
              color: '#666',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

// ============ ARREARS TRANSFER MODAL ============
const ArrearsTransferModal = ({ member, amount, onClose }) => {
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState('');

  const handleTransfer = async () => {
    if (!window.confirm(`Are you sure you want to transfer ${amount.toLocaleString()} to ${member.name}'s personal arrears ledger? This will clear the flat balance and allow transfer/NDC.`)) {
      return;
    }

    setSaving(true);
    try {
      await moveGovernanceService.transferToArrears({
        member_id: member.id,
        flat_id: member.flat_id || member.flat_number,
        amount: amount,
        notes: notes
      });
      alert('Dues successfully transferred to Personal Arrears Ledger.');
      onClose();
    } catch (error) {
      console.error('Error transferring to arrears:', error);
      alert(error.response?.data?.detail || 'Failed to transfer dues');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2000,
    }}>
      <div style={{
        backgroundColor: '#FFF',
        borderRadius: '12px',
        padding: '24px',
        maxWidth: '450px',
        width: '90%',
        boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
      }}>
        <h3 style={{ marginTop: 0, color: '#E44D26' }}> Dispute Isolation</h3>
        <p style={{ fontSize: '14px', color: '#666', lineHeight: '1.5' }}>
          Transferring <b>{amount.toLocaleString()}</b> from <b>Flat {member.flat_number}</b> to a
          Personal Arrears Ledger for <b>{member.name}</b>.
        </p>

        <div style={{ marginTop: '16px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#8E8E93', textTransform: 'uppercase' }}>
            Dispute Notes / Reason
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Owner disputes the security deposit adjustment..."
            style={{
              width: '100%',
              marginTop: '8px',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid #DDD',
              fontSize: '14px',
              height: '80px',
              resize: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
          <button
            onClick={handleTransfer}
            disabled={saving}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '8px',
              backgroundColor: '#E44D26',
              color: '#FFF',
              border: 'none',
              fontWeight: 'bold',
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1
            }}
          >
            {saving ? 'Processing...' : 'Transfer to Arrears'}
          </button>
          <button
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '12px 24px',
              borderRadius: '8px',
              backgroundColor: '#EEE',
              color: '#666',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

// ============ DOCUMENT CHECKLIST MODAL ============
const DocumentChecklistModal = ({ member, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [checklist, setChecklist] = useState({
    aadhaar_status: 'pending',
    pan_card_status: 'pending',
    sale_deed_status: 'pending',
    rental_agreement_status: 'pending',
    police_verification_status: 'pending',
    notes: ''
  });

  useEffect(() => {
    loadChecklist();
  }, []);

  const loadChecklist = async () => {
    try {
      const data = await memberOnboardingService.getChecklist(member.id);
      if (data) setChecklist(data);
    } catch (error) {
      console.error('Error loading checklist:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await memberOnboardingService.updateChecklist(member.id, checklist);
      alert('Document checklist updated successfully!');
      onClose();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update checklist');
    } finally {
      setSaving(false);
    }
  };

  const StatusButton = ({ field, label, currentStatus }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', padding: '8px', backgroundColor: '#F9F9F9', borderRadius: '8px' }}>
      <span style={{ fontSize: '14px', fontWeight: '500' }}>{label}</span>
      <select
        value={currentStatus}
        onChange={(e) => setChecklist({ ...checklist, [field]: e.target.value })}
        style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #CCC', fontSize: '13px' }}
      >
        <option value="pending"> Pending</option>
        <option value="submitted"> Submitted</option>
        <option value="not_applicable"> N/A</option>
      </select>
    </div>
  );

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div style={{ backgroundColor: '#FFF', borderRadius: '12px', padding: '24px', maxWidth: '450px', width: '90%' }}>
        <h3 style={{ marginTop: 0 }}>Document Verification: {member.name}</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '20px' }}>Verify physical submission of original documents (Tracking only - no storage!)</p>

        {loading ? <p>Loading...</p> : (
          <>
            <StatusButton field="aadhaar_status" label="Aadhaar Card" currentStatus={checklist.aadhaar_status} />
            <StatusButton field="pan_card_status" label="PAN Card" currentStatus={checklist.pan_card_status} />
            {member.member_type === 'owner' ? (
              <StatusButton field="sale_deed_status" label="Sale Deed" currentStatus={checklist.sale_deed_status} />
            ) : (
              <>
                <StatusButton field="rental_agreement_status" label="Rental Agreement" currentStatus={checklist.rental_agreement_status} />
                <StatusButton field="police_verification_status" label="Police Verification Form" currentStatus={checklist.police_verification_status} />
              </>
            )}

            <div style={{ marginTop: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#666' }}>ADMIN NOTES</label>
              <textarea
                value={checklist.notes || ''}
                onChange={(e) => setChecklist({ ...checklist, notes: e.target.value })}
                style={{ width: '100%', marginTop: '4px', padding: '8px', borderRadius: '4px', border: '1px solid #CCC', height: '60px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button disabled={saving} onClick={handleSave} style={{ flex: 1, padding: '10px', borderRadius: '6px', backgroundColor: '#007AFF', color: '#FFF', border: 'none', fontWeight: 'bold' }}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button onClick={onClose} style={{ padding: '10px 20px', borderRadius: '6px', backgroundColor: '#EEE', border: 'none' }}>Cancel</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MembersScreen;



