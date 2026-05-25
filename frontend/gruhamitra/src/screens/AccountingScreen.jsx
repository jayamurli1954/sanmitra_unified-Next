/**
 * GruhaMitra Accounting Screen
 * Complete accounting system with Chart of Accounts, Quick Entry, Journal Voucher, and Reports
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import accountingService from '../services/accountingService';
import journalService from '../services/journalService';
import transactionsService from '../services/transactionsService';
import flatsService from '../services/flatsService';
import attachmentService from '../services/attachmentService';

// Helper function to safely extract error message from API errors
const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (Array.isArray(detail)) {
      // Pydantic validation errors - extract messages
      return detail.map(err => {
        if (typeof err === 'string') return err;
        if (typeof err === 'object' && err.msg) return err.msg;
        if (typeof err === 'object' && err.message) return err.message;
        return JSON.stringify(err);
      }).join(', ');
    } else if (typeof detail === 'string') {
      return detail;
    } else if (typeof detail === 'object') {
      return detail.msg || detail.message || 'Validation error occurred';
    }
  }
  if (error.message) {
    return error.message;
  }
  return 'An error occurred. Please try again.';
};

// Helper function to format current month/year as "January, 2026"
const EDIT_WARNING_MSG = "This voucher is already posted. It cannot be edited.\n\nDo you want to create a reversal and a new corrected voucher?";

// --- REUSABLE COMPONENTS FOR ATTACHMENTS ---

const VoucherAttachmentsModal = ({ isOpen, onClose, journalEntryId, onDeleted }) => {
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && journalEntryId) {
      loadAttachments();
    }
  }, [isOpen, journalEntryId]);

  const loadAttachments = async () => {
    setLoading(true);
    try {
      const data = await attachmentService.listAttachments(journalEntryId);
      setAttachments(data);
    } catch (e) {
      console.error('Error loading attachments:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this attachment?')) return;
    try {
      await attachmentService.deleteAttachment(id);
      setAttachments(attachments.filter(a => a.id !== id));
      if (onDeleted) onDeleted();
    } catch (e) {
      alert('Failed to delete attachment');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ backgroundColor: '#fff', padding: '24px', borderRadius: '12px', width: '500px', maxWidth: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3> Voucher Attachments</h3>
          <button onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '24px', cursor: 'pointer' }}></button>
        </div>

        {loading ? <p>Loading...</p> : attachments.length === 0 ? <p>No attachments found.</p> : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {attachments.map(att => (
              <div key={att.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ fontWeight: 'bold', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{att.file_name}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>{(att.file_size / 1024).toFixed(1)} KB | {new Date(att.created_at).toLocaleDateString()}</div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => attachmentService.downloadAttachment(att.id, att.file_name)}
                    className="settings-action-btn"
                    style={{ padding: '4px 8px', fontSize: '12px' }}
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleDelete(att.id)}
                    className="settings-action-btn"
                    style={{ padding: '4px 8px', fontSize: '12px', color: '#C62828', borderColor: '#FFEBEE' }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '20px', textAlign: 'right' }}>
          <button className="settings-cancel-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

const FileList = ({ files, onRemove }) => {
  if (!files || files.length === 0) return null;
  return (
    <div style={{ marginTop: '8px', border: '1px solid #eee', borderRadius: '8px', padding: '8px' }}>
      {files.map((file, idx) => (
        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', padding: '4px 0', borderBottom: idx < files.length - 1 ? '1px solid #eee' : 'none' }}>
          <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button type="button" onClick={() => onRemove(idx)} style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer', padding: '0 4px' }}></button>
        </div>
      ))}
    </div>
  );
};

const getCurrentMonthYear = () => {
  const now = new Date();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  return `${monthNames[now.getMonth()]}, ${now.getFullYear()}`;
};

const AccountingScreen = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('chart-of-accounts');
  const [loading, setLoading] = useState(false);

  const accountingTabs = [
    { id: 'chart-of-accounts', label: ' Chart of Accounts', icon: '' },
    { id: 'receipt-voucher', label: ' Receipt Voucher', icon: '' },
    { id: 'payment-voucher', label: ' Payment Voucher', icon: '' },
    { id: 'journal-voucher', label: ' Journal Voucher', icon: '' },
    { id: 'transfer-voucher', label: ' Transfer Voucher', icon: '' },
    { id: 'reports', label: ' Accounting Reports', icon: '' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chart-of-accounts':
        return <ChartOfAccountsTab />;
      case 'receipt-voucher':
        return <ReceiptVoucherTab />;
      case 'payment-voucher':
        return <PaymentVoucherTab />;
      case 'journal-voucher':
        return <JournalVoucherTab />;
      case 'transfer-voucher':
        return <TransferVoucherTab />;
      case 'reports':
        return <ReportsTab />;
      default:
        return <ChartOfAccountsTab />;
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title"> Accounting</h1>
          <span className="dashboard-header-subtitle">Financial Management System</span>
        </div>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
             Back to Dashboard
          </button>
        </div>
      </div>

      <div className="settings-container">
        {/* Sidebar Navigation */}
        <div className="settings-sidebar">
          <div className="settings-sidebar-header">
            <h3>Accounting Menu</h3>
          </div>
          <nav className="settings-nav">
            {accountingTabs.map((tab) => (
              <button
                key={tab.id}
                className={`settings-nav-item ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="settings-nav-icon">{tab.icon}</span>
                <span className="settings-nav-label">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content Area */}
        <div className="settings-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

// Chart of Accounts Tab
const ChartOfAccountsTab = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('');
  const [editingAccount, setEditingAccount] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newAccount, setNewAccount] = useState({
    code: '',
    name: '',
    type: 'asset',
    description: '',
    opening_balance: 0
  });

  const getClassificationForType = (accountType) => {
    switch ((accountType || '').toLowerCase()) {
      case 'asset':
        return 'real';
      case 'liability':
      case 'equity':
        return 'personal';
      case 'income':
      case 'expense':
      default:
        return 'nominal';
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setLoading(true);
    try {
      const accountsList = await accountingService.getAccounts();
      setAccounts(accountsList || []);
      // Clear any previous error messages if successful
      if (accountsList && accountsList.length > 0) {
        setMessage({ type: '', text: '' });
      }
    } catch (error) {
      console.error('Error loading accounts:', error);
      let errorMsg = 'Failed to load accounts. Please try again.';

      if (error.response) {
        // Server responded with error status
        if (error.response.status === 401) {
          errorMsg = 'Authentication required. Please login again.';
        } else if (error.response.status === 403) {
          errorMsg = 'You do not have permission to view accounts.';
        } else if (error.response.status === 404) {
          errorMsg = 'Accounts endpoint not found. Please check backend configuration.';
        } else {
          errorMsg = getErrorMessage(error) || errorMsg;
        }
      } else {
        errorMsg = getErrorMessage(error) || errorMsg;
      }

      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const handleInitialize = async () => {
    if (!window.confirm('This will initialize the chart of accounts with predefined accounts from the master list. Continue?')) {
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      const result = await accountingService.initializeChartOfAccounts();
      setMessage({ type: 'success', text: `Chart of accounts initialized successfully! ${result.accounts_created} accounts created.` });
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
      await loadAccounts();
    } catch (error) {
      console.error('Error initializing accounts:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to initialize chart of accounts.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateStandardAccounts = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      const result = await accountingService.initializeChartOfAccounts();
      setMessage({
        type: 'success',
        text: result.accounts_created > 0
          ? `Standard chart updated. ${result.accounts_created} missing accounts added.`
          : 'Standard chart is already up to date.'
      });
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
      await loadAccounts();
    } catch (error) {
      console.error('Error updating standard accounts:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to update standard accounts.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  const handleEditName = (account) => {
    setEditingAccount(account.code);
    setEditingName(account.name);
  };

  const handleSaveName = async (code) => {
    if (!editingName.trim()) {
      setMessage({ type: 'error', text: 'Account name cannot be empty.' });
      return;
    }

    setSaving(true);
    try {
      await accountingService.updateAccount(code, { name: editingName });
      setMessage({ type: 'success', text: 'Account name updated successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      setEditingAccount(null);
      await loadAccounts();
    } catch (error) {
      console.error('Error updating account:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to update account name.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingAccount(null);
    setEditingName('');
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();

    // Validation
    if (!newAccount.code.trim()) {
      setMessage({ type: 'error', text: 'Account code is required.' });
      return;
    }
    if (!newAccount.name.trim()) {
      setMessage({ type: 'error', text: 'Account name is required.' });
      return;
    }
    if (!newAccount.type) {
      setMessage({ type: 'error', text: 'Account type is required.' });
      return;
    }

    // Validate code format (should be numeric, 4-10 digits)
    if (!/^\d{4,10}$/.test(newAccount.code.trim())) {
      setMessage({ type: 'error', text: 'Account code must be 4-10 digits (e.g., 1000, 1010, 5001).' });
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      await accountingService.createAccount({
        code: newAccount.code.trim(),
        name: newAccount.name.trim(),
        type: newAccount.type,
        classification: getClassificationForType(newAccount.type),
        description: newAccount.description.trim() || null,
        opening_balance: parseFloat(newAccount.opening_balance) || 0
      });

      setMessage({ type: 'success', text: 'Account created successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);

      // Reset form
      setNewAccount({
        code: '',
        name: '',
        type: 'asset',
        description: '',
        opening_balance: 0
      });
      setShowAddForm(false);

      // Reload accounts
      await loadAccounts();
    } catch (error) {
      console.error('Error creating account:', error);
      let errorMsg = 'Failed to create account. Please try again.';

      if (error.response) {
        if (error.response.status === 400) {
          errorMsg = getErrorMessage(error) || 'Invalid account data. Account code may already exist.';
        } else if (error.response.status === 401) {
          errorMsg = 'Authentication required. Please login again.';
        } else if (error.response.status === 403) {
          errorMsg = 'You do not have permission to create accounts.';
        } else {
          errorMsg = getErrorMessage(error) || errorMsg;
        }
      } else {
        errorMsg = getErrorMessage(error) || errorMsg;
      }

      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  // Filter accounts
  const filteredAccounts = accounts.filter(account => {
    const matchesSearch = !searchTerm ||
      account.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      account.code.includes(searchTerm);
    const matchesType = !filterType || account.type.toLowerCase() === filterType.toLowerCase();
    return matchesSearch && matchesType;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // TODO: API call to create account
      console.log('Creating account:', formData);
      setShowAddForm(false);
      setFormData({ code: '', name: '', type: 'Asset', parent_code: '', opening_balance: 0 });
      loadAccounts();
    } catch (error) {
      console.error('Error creating account:', error);
    }
  };

  const accountTypes = ['asset', 'liability', 'equity', 'income', 'expense'];

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title"> Chart of Accounts</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading chart of accounts...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 className="settings-tab-title"> Chart of Accounts</h2>
          <p className="settings-tab-description">Manage your accounting chart of accounts. Account names are editable, codes are read-only.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="settings-add-btn"
            onClick={() => setShowAddForm(!showAddForm)}
            disabled={saving}
          >
            {showAddForm ? ' Cancel' : '+ Add Account'}
          </button>
          {accounts.length === 0 ? (
            <button
              className="settings-add-btn"
              onClick={handleInitialize}
              disabled={saving}
              style={{ backgroundColor: '#4CAF50' }}
            >
              {saving ? 'Initializing...' : ' Initialize Chart of Accounts'}
            </button>
          ) : (
            <button
              className="settings-add-btn"
              onClick={handleUpdateStandardAccounts}
              disabled={saving}
              style={{ backgroundColor: '#4CAF50', borderColor: '#388E3C' }}
            >
              {saving ? 'Updating...' : ' Update Standard Accounts'}
            </button>
          )}
        </div>
      </div>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
        }}>
          {message.text}
        </div>
      )}

      {/* Add Account Form */}
      {showAddForm && (
        <div className="settings-section" style={{ marginBottom: '20px', backgroundColor: '#f9f9f9', padding: '20px', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Add New Account</h3>
          <form className="settings-form" onSubmit={handleAddAccount}>
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Account Code *</label>
                <input
                  type="text"
                  value={newAccount.code}
                  onChange={(e) => setNewAccount({ ...newAccount, code: e.target.value })}
                  placeholder="e.g., 1000, 1010, 5001"
                  required
                  pattern="[0-9]{4,10}"
                  title="Account code must be 4-10 digits"
                  disabled={saving}
                />
                <small style={{ color: '#666', fontSize: '12px' }}>
                  Must be 4-10 digits. Follow standard ranges: 1000-1999 (Assets), 2000-2999 (Liabilities), 3000-3999 (Capital), 4000-4999 (Income), 5000-5999 (Expenses)
                </small>
              </div>
              <div className="settings-form-group">
                <label>Account Name *</label>
                <input
                  type="text"
                  value={newAccount.name}
                  onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
                  placeholder="e.g., Cash in Hand, Bank Account, etc."
                  required
                  disabled={saving}
                />
              </div>
              <div className="settings-form-group">
                <label>Account Type *</label>
                <select
                  value={newAccount.type}
                  onChange={(e) => setNewAccount({ ...newAccount, type: e.target.value })}
                  required
                  disabled={saving}
                >
                  <option value="asset">Asset</option>
                  <option value="liability">Liability</option>
                  <option value="equity">Capital/Equity</option>
                  <option value="income">Income</option>
                  <option value="expense">Expense</option>
                </select>
              </div>
            </div>
            <div className="settings-form-row">
              <div className="settings-form-group" style={{ flex: 2 }}>
                <label>Description (Optional)</label>
                <textarea
                  value={newAccount.description}
                  onChange={(e) => setNewAccount({ ...newAccount, description: e.target.value })}
                  placeholder="Brief description of the account..."
                  rows="2"
                  disabled={saving}
                />
              </div>
              <div className="settings-form-group">
                <label>Opening Balance ()</label>
                <input
                  type="number"
                  value={newAccount.opening_balance}
                  onChange={(e) => setNewAccount({ ...newAccount, opening_balance: e.target.value })}
                  step="0.01"
                  placeholder="0.00"
                  disabled={saving}
                />
              </div>
            </div>
            <div className="settings-form-actions">
              <button type="submit" className="settings-save-btn" disabled={saving}>
                {saving ? 'Creating...' : 'Create Account'}
              </button>
              <button
                type="button"
                className="settings-cancel-btn"
                onClick={() => {
                  setShowAddForm(false);
                  setNewAccount({
                    code: '',
                    name: '',
                    type: 'asset',
                    description: '',
                    opening_balance: 0
                  });
                }}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="settings-section" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <h3 style={{ color: '#666', marginBottom: '20px' }}>No accounts found</h3>
          <p style={{ color: '#999', marginBottom: '30px' }}>
            Click "Initialize Chart of Accounts" to load the predefined chart of accounts with proper account codes.
          </p>
        </div>
      ) : (
        <div className="settings-section">
          <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
            <input
              type="text"
              placeholder="Search by code or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ flex: 1, padding: '10px', border: '2px solid #e0e0e0', borderRadius: '8px' }}
            />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              style={{ padding: '10px', border: '2px solid #e0e0e0', borderRadius: '8px' }}
            >
              <option value="">All Types</option>
              {accountTypes.map(type => (
                <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
              ))}
            </select>
          </div>

          <div className="settings-table-container">
            <table className="settings-table">
              <thead>
                <tr>
                  <th style={{ width: '100px' }}>Code</th>
                  <th>Account Name</th>
                  <th style={{ width: '120px' }}>Type</th>
                  <th style={{ width: '150px' }}>Balance ()</th>
                  <th style={{ width: '120px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAccounts.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                      No accounts found matching your search.
                    </td>
                  </tr>
                ) : (
                  filteredAccounts.map((account) => (
                    <tr key={account.code}>
                      <td>
                        <strong style={{ color: '#666' }}>{account.code}</strong>
                      </td>
                      <td>
                        {editingAccount === account.code ? (
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <input
                              type="text"
                              value={editingName}
                              onChange={(e) => setEditingName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveName(account.code);
                                if (e.key === 'Escape') handleCancelEdit();
                              }}
                              style={{ flex: 1, padding: '6px', border: '2px solid #4CAF50', borderRadius: '4px' }}
                              autoFocus
                            />
                            <button
                              onClick={() => handleSaveName(account.code)}
                              disabled={saving}
                              style={{ padding: '6px 12px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                            >
                              Save
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              style={{ padding: '6px 12px', backgroundColor: '#999', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <span>{account.name}</span>
                        )}
                      </td>
                      <td>
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '600',
                          background: account.type === 'asset' ? '#E8F5E9' :
                            account.type === 'liability' ? '#FFEBEE' :
                              account.type === 'income' ? '#E3F2FD' :
                                account.type === 'equity' ? '#F3E5F5' : '#FFF3E0',
                          color: account.type === 'asset' ? '#2E7D32' :
                            account.type === 'liability' ? '#C62828' :
                              account.type === 'income' ? '#1565C0' :
                                account.type === 'equity' ? '#7B1FA2' : '#E65100'
                        }}>
                          {account.type.charAt(0).toUpperCase() + account.type.slice(1)}
                        </span>
                      </td>
                      <td style={{ fontWeight: '600', color: (account.current_balance || 0) >= 0 ? '#2E7D32' : '#C62828' }}>
                        {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(account.current_balance || 0)}
                      </td>
                      <td>
                        {editingAccount !== account.code && (
                          <button
                            className="settings-action-btn"
                            onClick={() => handleEditName(account)}
                            disabled={saving}
                          >
                            Edit Name
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '15px', color: '#666', fontSize: '14px' }}>
            Showing {filteredAccounts.length} of {accounts.length} accounts
          </div>
        </div>
      )}
    </div>
  );
};

// Voucher Print Handler (Reusable)
const handlePrintVoucher = async (journalEntryId) => {
  if (!journalEntryId) return;
  try {
    const blob = await transactionsService.downloadVoucherPdf(journalEntryId);
    if (!blob) throw new Error("No data received");
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Voucher_${journalEntryId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error printing voucher:', error);
    alert('Failed to generate voucher PDF. Please try again.');
  }
};

// Robust Searchable Select Component for Accounting
const SearchableSelect = ({
  label,
  options,
  value,
  onChange,
  placeholder,
  required = false,
  displayKey = 'name',
  valueKey = 'id',
  minCharsForSearch = 0,
  clearable = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const wrapperRef = React.useRef(null);
  const searchInputRef = React.useRef(null);

  // Find the currently selected option based on the `value` prop
  const selectedOption = React.useMemo(() => {
    if (value === null || value === undefined) return null;
    if (!options || !Array.isArray(options)) return null;
    return options.find(opt => String(opt[valueKey]) === String(value));
  }, [options, value, valueKey]);

  // Determine what string should be shown in the main box.
  const displayString = selectedOption
    ? `${selectedOption.code ? selectedOption.code + ' - ' : ''}${selectedOption[displayKey]}`
    : '';

  // Filter options based on the user's typed search term
  const filteredOptions = React.useMemo(() => {
    if (!options || !Array.isArray(options)) return [];

    const searchLower = searchTerm.toLowerCase().trim();
    
    // If they haven't typed anything yet
    if (!searchLower) {
       return options.slice(0, 2000); // just show all (up to 2000)
    }

    return options.filter(opt => {
      const name = String(opt[displayKey] || '').toLowerCase();
      const code = String(opt.code || '').toLowerCase();
      const cat = String(opt.category || opt.type || '').toLowerCase();
      return name.includes(searchLower) || code.includes(searchLower) || cat.includes(searchLower);
    });
  }, [options, searchTerm, displayKey]);

  // Handle clicking outside the component to close it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm(''); // Reset search term when clicking away
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // When dropdown opens, focus the search input inside it
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  // Reset highlight when the filtered list changes
  useEffect(() => {
    setHighlightedIndex(0);
  }, [filteredOptions]);

  // Handle user selecting an option
  const handleSelect = (option) => {
    onChange(option[valueKey]);
    setIsOpen(false);
    setSearchTerm('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(prev => (prev < filteredOptions.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredOptions[highlightedIndex]) handleSelect(filteredOptions[highlightedIndex]);
    } else if (e.key === 'Tab') {
      if (filteredOptions[highlightedIndex]) handleSelect(filteredOptions[highlightedIndex]);
      else setIsOpen(false);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setSearchTerm('');
    }
  };

  return (
    <div className="settings-form-group" style={{ position: 'relative', width: '100%' }} ref={wrapperRef}>
      {label && <label>{label} {required && <span style={{ color: 'red' }}>*</span>}</label>}
      
      {/* Main Select Button Wrapper */}
      <div
        style={{ 
          position: 'relative',
          width: '100%',
          padding: '12px 10px',
          borderRadius: '8px',
          border: `2px solid ${isOpen ? '#E8842A' : '#e0e0e0'}`,
          backgroundColor: '#fff',
          fontSize: '14px',
          transition: 'all 0.2s',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minHeight: '46px'
        }}
        onClick={() => {
          if (!isOpen) {
            setIsOpen(true);
            setSearchTerm('');
          } else {
            setIsOpen(false);
          }
        }}
      >
        <span style={{ color: displayString ? '#333' : '#999', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {displayString || placeholder || 'Select an option...'}
        </span>
        {clearable && (value !== '' && value !== null && value !== undefined) ? (
          <button
            type="button"
            title="Clear selection"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onChange('');
              setIsOpen(false);
              setSearchTerm('');
            }}
            style={{
              border: 'none',
              background: 'transparent',
              color: '#999',
              cursor: 'pointer',
              fontSize: '16px',
              lineHeight: 1,
              marginLeft: '8px',
              padding: 0
            }}
          >
            x
          </button>
        ) : null}
      </div>
      
      {/* Dropdown Menu */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          zIndex: 1000,
          width: 'max-content',
          minWidth: '100%',
          maxWidth: '500px',
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '8px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          marginTop: '5px',
          left: 0,
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Search Input INSIDE Dropdown */}
          <div style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
            <input
              ref={searchInputRef}
              type="text"
              placeholder={`Type to search ${label ? label.toLowerCase() : 'options'}...`}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #ccc',
                outline: 'none',
                fontSize: '14px'
              }}
            />
          </div>

          {/* Options List */}
          <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt, idx) => (
                <div
                  key={String(opt[valueKey])}
                  style={{
                    padding: '12px 15px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f5f5f5',
                    backgroundColor: idx === highlightedIndex ? '#FFF3E0' : '#fff',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'background-color 0.1s'
                  }}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSelect(opt)}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                >
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {opt.code ? <strong style={{ color: '#E8842A', minWidth: '60px', flexShrink: 0 }}>{opt.code}</strong> : ''}
                    <span style={{ color: '#333', fontWeight: idx === highlightedIndex ? '600' : '400', flex: 1 }}>{String(opt[displayKey])}</span>
                  </div>
                  {(opt.category || opt.type) && (
                    <span style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#F5F5F5',
                      color: '#888',
                      textTransform: 'uppercase',
                      fontWeight: 'bold',
                      marginLeft: '8px'
                    }}>
                      {opt.category || opt.type}
                    </span>
                  )}
                </div>
              ))
            ) : (
              <div style={{ padding: '20px', color: '#999', textAlign: 'center', fontSize: '14px' }}>
                No matches found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const resolveFlatOwnerName = (flat) => {
  if (!flat || typeof flat !== 'object') return '';
  return String(
    flat.owner_name ||
    flat.owner ||
    flat.current_owner_name ||
    flat.primary_member_name ||
    flat.member_name ||
    flat.resident_name ||
    flat.current_occupier_name ||
    ''
  ).trim();
};

const buildBankAccountOptions = (accounts) => {
  const list = Array.isArray(accounts) ? accounts : [];
  let banks = list.filter(a => {
    const type = String(a.type || a.account_type || '').toLowerCase();
    const name = String(a.name || a.account_name || '').toLowerCase();
    const isCashBank = a?.is_cash_bank === true;
    return isCashBank ||
      name.includes('bank') ||
      name.includes('cash') ||
      name.includes('current account') ||
      name.includes('savings') ||
      name.includes('od/cc');
  });

  if (banks.length === 0) {
    banks = list.filter(a => String(a.type || a.account_type || '').toLowerCase() === 'asset');
  }

  // Final safety fallback: never leave dropdown empty in tenant-specific CoA setups.
  if (banks.length === 0) {
    banks = list;
  }
  return banks;
};

const normalizeTrialBalanceReport = (data) => {
  const lines = Array.isArray(data?.lines) ? data.lines : [];
  const totalDebit = Number(data?.total_debit || 0);
  const totalCredit = Number(data?.total_credit || 0);
  return {
    ...data,
    as_on_date: data?.as_on_date || data?.as_of,
    total_debit: totalDebit,
    total_credit: totalCredit,
    difference: Math.abs(totalDebit - totalCredit),
    is_balanced: data?.is_balanced ?? data?.balanced ?? totalDebit === totalCredit,
    items: lines.map((line) => {
      const debitTotal = Number(line.debit_total || 0);
      const creditTotal = Number(line.credit_total || 0);
      const netBalance = debitTotal - creditTotal;
      return {
        ...line,
        debit_balance: netBalance > 0 ? netBalance : 0,
        credit_balance: netBalance < 0 ? Math.abs(netBalance) : 0
      };
    })
  };
};

const formatAmount = (value) => {
  const amount = Number(value || 0);
  return amount.toLocaleString('en-IN', { minimumFractionDigits: 2 });
};

const getVoucherAmount = (txn) => {
  if (!txn || typeof txn !== 'object') return 0;
  return txn.amount ?? txn.total_amount ?? txn.total_debit ?? txn.total_credit ?? 0;
};

const getVoucherDate = (txn) => {
  return txn?.date || txn?.voucher_date || txn?.created_at || '';
};

const getVoucherDescription = (txn) => {
  return txn?.description || txn?.narration || txn?.lines?.find?.(line => line?.description)?.description || '';
};

const VoucherViewModal = ({ voucher, onClose, onPrint }) => {
  if (!voucher) return null;
  const lines = Array.isArray(voucher.lines) ? voucher.lines : [];
  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1200 }}>
      <div className="modal-content" style={{ backgroundColor: '#fff', borderRadius: '10px', width: '760px', maxWidth: '92vw', maxHeight: '86vh', overflowY: 'auto', padding: '22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0 }}>Voucher Details</h3>
            <div style={{ color: '#666', marginTop: '4px' }}>{voucher.voucher_number || '-'}</div>
          </div>
          <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', fontSize: '22px', cursor: 'pointer' }}>x</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px 18px', marginBottom: '18px' }}>
          <div><strong>Date:</strong> {getVoucherDate(voucher) || '-'}</div>
          <div><strong>Status:</strong> {voucher.status || '-'}</div>
          <div><strong>Type:</strong> {voucher.voucher_type || '-'}</div>
          <div><strong>Amount:</strong> {formatAmount(getVoucherAmount(voucher))}</div>
          <div><strong>Reference:</strong> {voucher.reference || '-'}</div>
          <div><strong>Journal ID:</strong> {voucher.journal_entry_id || '-'}</div>
        </div>

        <div style={{ marginBottom: '18px' }}>
          <strong>Narration:</strong>
          <div style={{ marginTop: '6px', padding: '10px', border: '1px solid #eee', borderRadius: '6px', backgroundColor: '#fafafa' }}>
            {getVoucherDescription(voucher) || '-'}
          </div>
        </div>

        <div className="settings-table-container" style={{ marginBottom: '18px' }}>
          <table className="settings-table">
            <thead>
              <tr>
                <th>Account</th>
                <th>Description</th>
                <th style={{ textAlign: 'right' }}>Debit</th>
                <th style={{ textAlign: 'right' }}>Credit</th>
              </tr>
            </thead>
            <tbody>
              {lines.length > 0 ? lines.map((line, idx) => (
                <tr key={`${line.account_code || 'line'}-${idx}`}>
                  <td>{line.account_code || '-'}</td>
                  <td>{line.description || '-'}</td>
                  <td style={{ textAlign: 'right' }}>{formatAmount(line.debit || line.debit_amount || 0)}</td>
                  <td style={{ textAlign: 'right' }}>{formatAmount(line.credit || line.credit_amount || 0)}</td>
                </tr>
              )) : (
                <tr><td colSpan="4" style={{ textAlign: 'center', color: '#999' }}>No voucher lines available</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button type="button" className="settings-cancel-btn" onClick={onClose}>Close</button>
          <button type="button" className="settings-save-btn" onClick={() => onPrint(voucher.journal_entry_id)} disabled={!voucher.journal_entry_id}>Print PDF</button>
        </div>
      </div>
    </div>
  );
};

const NARRATION_HISTORY_LIMIT = 3;

const loadNarrationHistory = (key) => {
  if (typeof window === 'undefined') return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(key) || '[]');
    return Array.isArray(parsed) ? parsed.filter(Boolean).slice(0, NARRATION_HISTORY_LIMIT) : [];
  } catch (error) {
    return [];
  }
};

const saveNarrationHistory = (key, narration) => {
  if (typeof window === 'undefined') return [];
  const text = String(narration || '').trim();
  if (!text) return loadNarrationHistory(key);
  const current = loadNarrationHistory(key);
  const next = [text, ...current.filter((item) => item !== text)].slice(0, NARRATION_HISTORY_LIMIT);
  window.localStorage.setItem(key, JSON.stringify(next));
  return next;
};


// --- Receipt Voucher Tab ---
const ReceiptVoucherTab = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [allAccounts, setAllAccounts] = useState([]);
  const [flats, setFlats] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    account_code: '1100', // Maintenance Dues (Default)
    amount: '',
    qty: '',
    unit_price: '',
    payment_method: 'bank',
    description: '',
    flat_id: '',
    received_from: '',
    reference: '',
    bank_account_code: ''
  });
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [receiptsPerPage] = useState(20);
  const [totalReceipts, setTotalReceipts] = useState(0);
  const [narrationHistory, setNarrationHistory] = useState(() => loadNarrationHistory('gruhamitra.receiptNarrations'));
  const [viewVoucher, setViewVoucher] = useState(null);

  useEffect(() => { loadInitialData(); }, [currentPage]);

  const loadInitialData = async () => {
    try {
      const offset = (currentPage - 1) * receiptsPerPage;
      const [acctsRes, fltsRes, txnsRes] = await Promise.allSettled([
        accountingService.getAccounts(), // Get ALL accounts for flexibility
        flatsService.getFlats(),
        transactionsService.getTransactions({ type: 'income', limit: 100 }) // Fetch more to handle grouping
      ]);

      const accts = acctsRes.status === 'fulfilled' ? (acctsRes.value || []) : [];
      const flts = fltsRes.status === 'fulfilled' ? (fltsRes.value || []) : [];
      const txns = txnsRes.status === 'fulfilled' ? (txnsRes.value || []) : [];

      setAllAccounts(Array.isArray(accts) ? accts : []);
      setFlats(Array.isArray(flts) ? flts : []);

      // Group transactions by journal_entry_id to show only one line per receipt
      const grouped = {};
      (Array.isArray(txns) ? txns : []).forEach(txn => {
        if (txn.journal_entry_id && !grouped[txn.journal_entry_id]) {
          grouped[txn.journal_entry_id] = txn;
        }
      });

      // Convert back to array and paginate
      const uniqueTransactions = Object.values(grouped);
      const paginatedTxns = uniqueTransactions.slice(offset, offset + receiptsPerPage);
      setTransactions(paginatedTxns);
      setTotalReceipts(uniqueTransactions.length)

      const banks = buildBankAccountOptions(accts || []);
      setBankAccounts(banks);

      // Auto-select first bank if none selected
      if (banks.length > 0 && !formData.bank_account_code) {
        setFormData(prev => ({ ...prev, bank_account_code: banks[0].code }));
      }
      if (acctsRes.status === 'rejected' || fltsRes.status === 'rejected' || txnsRes.status === 'rejected') {
        const failed = [];
        if (acctsRes.status === 'rejected') failed.push('accounts');
        if (fltsRes.status === 'rejected') failed.push('flats');
        if (txnsRes.status === 'rejected') failed.push('transactions');
        setMessage({
          type: 'error',
          text: `Some data failed to load (${failed.join(', ')}). You can still continue with available data.`
        });
      }
    } catch (error) {
      console.error('Error loading receipt data:', error);
      setMessage({ type: 'error', text: 'Failed to load receipt data.' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.payment_method === 'bank' && !formData.bank_account_code) {
      setMessage({ type: 'error', text: 'Please select a Bank Account' });
      return;
    }

    let reversalReason = null;
    if (editingId) {
      // Prompt for reason instead of just confirm
      reversalReason = window.prompt("This voucher is already posted. It cannot be edited.\n\nDo you want to create a reversal and a new corrected voucher?\n\nIf YES, please enter a reason for this correction:", "Correction");
      if (reversalReason === null) {
        return; // User cancelled
      }
    }

    setLoading(true);
    try {
      // If editing, reverse the old one first with reason
      if (editingId) {
        await transactionsService.reverseTransaction(editingId, `Update: ${reversalReason}`);
      }

      // If narration is empty, provide a fallback but don't hardcode it in the input
      const finalDescription = formData.description || 'Receipt';
      const resp = await transactionsService.createReceipt({
        ...formData,
        amount: parseFloat(formData.amount),
        quantity: formData.qty ? parseFloat(formData.qty) : undefined,
        unit_price: formData.unit_price ? parseFloat(formData.unit_price) : undefined,
        account_code: String(formData.account_code),
        bank_account_code: formData.bank_account_code ? String(formData.bank_account_code) : undefined,
        flat_id: formData.flat_id || undefined,
        description: finalDescription
      });

      // Handle Multiple Attachment Uploads
      if (selectedFiles.length > 0 && resp.journal_entry_id) {
        const uploadPromises = selectedFiles.map(file =>
          attachmentService.uploadAttachment(resp.journal_entry_id, file)
        );
        try {
          await Promise.all(uploadPromises);
        } catch (attachError) {
          console.error('Some attachments failed to upload:', attachError);
          setMessage({ type: 'success', text: editingId ? 'Receipt updated successfully!' : `Receipt created! (Note: Some attachments failed to upload)` });
          return;
        }
      }

      setMessage({ type: 'success', text: editingId ? 'Receipt updated successfully!' : `Receipt created! Voucher: ${resp.voucher_number}. Auto-allocated: ${resp.allocated_amount || 0}` });
      setNarrationHistory(saveNarrationHistory('gruhamitra.receiptNarrations', formData.description));
      setFormData({ ...formData, amount: '', qty: '', unit_price: '', description: '', flat_id: '', reference: '', received_from: '' });
      setSelectedFiles([]); // Reset files
      setEditingId(null);
      loadInitialData();
    } catch (error) { setMessage({ type: 'error', text: getErrorMessage(error) }); }
    finally { setLoading(false); }
  };

  const handleEditReceipt = async (txn) => {
    // 1. Confirm with user before starting edit
    if (!window.confirm(EDIT_WARNING_MSG)) {
      return;
    }

    setLoading(true);
    try {
      // 1. Fetch full JV details to find Bank Account (for Receipt: Debit side is Bank)
      let bankCode = txn.bank_account_code || '';
      if (!bankCode && txn.journal_entry_id) {
        try {
          const jv = await journalService.getJournalEntry(txn.journal_entry_id);
          if (jv && jv.entries) {
            // Receipt: Dr Asset (Bank), Cr Income (Account Code)
            // Typically finding entry with debit > 0
            const bankEntry = jv.entries.find(e =>
              parseFloat(e.debit_amount) > 0 &&
              e.account_code !== txn.account_code
            );
            if (bankEntry) bankCode = bankEntry.account_code;
          }
        } catch (e) { console.error("JV fetch error", e); }
      }

      // Populate form with transaction data for editing
      setFormData({
        date: txn.date,
        account_code: txn.account_code || '',
        amount: txn.amount || '',
        qty: txn.quantity || '',
        unit_price: txn.unit_price || '',
        payment_method: 'bank', // Default, should ideally come from txn
        description: txn.description || '',
        expense_month: txn.expense_month ? convertMonthYearToInput(txn.expense_month) : '',
        flat_id: txn.flat_id || '',
        reference: txn.reference || '',
        received_from: txn.received_from || '',
        bank_account_code: bankCode
      });
      setEditingId(txn.id);
      setMessage({ type: 'info', text: `Editing ${txn.voucher_number}. Modify the form and submit to update.` });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      console.error(e);
      setMessage({ type: 'error', text: 'Error loading for edit' });
    } finally {
      setLoading(false);
    }
  };

  const handleReverseReceipt = async (txn) => {
    const reason = window.prompt(`Are you sure you want to reverse ${txn.voucher_number}?\n\nThis will create reversing entries.\n\nPlease enter a reason for reversal:`, "Incorrect Info");
    if (reason === null) {
      return;
    }
    try {
      setLoading(true);
      await transactionsService.reverseTransaction(txn.id, reason);
      setMessage({ type: 'success', text: `Receipt ${txn.voucher_number} reversed successfully!` });
      loadInitialData();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to reverse receipt: ${getErrorMessage(error)}` });
    } finally {
      setLoading(false);
    }
  };

  // Use full CoA for receipt credit selection (tenant-specific complete chart)
  const primaryAccounts = allAccounts;

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title"> Receipt Voucher <span style={{ fontSize: '12px', fontWeight: 'normal', color: '#888' }}>(Loaded: {primaryAccounts.length} Accounts, {flats.length} Flats)</span></h2>
      <p className="settings-tab-description">Record maintenance collections, corpus funds, or other income</p>

      {message.text && (
        <div style={{ padding: '12px', borderRadius: '8px', marginBottom: '20px', backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE', color: message.type === 'success' ? '#2E7D32' : '#C62828' }}>
          {message.text}
        </div>
      )}

      <VoucherViewModal voucher={viewVoucher} onClose={() => setViewVoucher(null)} onPrint={handlePrintVoucher} />

      <div className="settings-section">
        <form className="settings-form" onSubmit={handleSubmit}>
          <div className="settings-form-row">
            <div className="settings-form-group"><label>Date *</label><input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} required /></div>
            <div className="settings-form-group"><label>Quantity</label><input type="number" step="any" placeholder="e.g. 1" value={formData.qty} onChange={(e) => {
              const qty = e.target.value;
              const total = (qty && formData.unit_price) ? (parseFloat(qty) * parseFloat(formData.unit_price)).toFixed(2) : formData.amount;
              setFormData(prev => ({ ...prev, qty, amount: total }));
            }} /></div>
            <div className="settings-form-group"><label>Unit Price ()</label><input type="number" step="any" placeholder="e.g. 100" value={formData.unit_price} onChange={(e) => {
              const unit_price = e.target.value;
              const total = (formData.qty && unit_price) ? (parseFloat(formData.qty) * parseFloat(unit_price)).toFixed(2) : formData.amount;
              setFormData(prev => ({ ...prev, unit_price, amount: total }));
            }} /></div>
            <div className="settings-form-group"><label>Total Amount () *</label><input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} required /></div>
          </div>

          <div className="settings-form-row">
            <SearchableSelect
              label="Account (Credit)"
              options={primaryAccounts}
              value={formData.account_code}
              onChange={(val) => setFormData(prev => ({ ...prev, account_code: val }))}
              placeholder="Search account code or name..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />

            <SearchableSelect
              label="Flat (For Auto-Allocation)"
              options={flats.map(f => ({
                ...f,
                id: String(f.id || f._id || ''),
                displayName: `${f.flat_number} - ${resolveFlatOwnerName(f) || 'No Owner'}`
              }))}
              value={formData.flat_id}
              onChange={(val) => {
                console.log('Selected Flat:', val);
                const flat = flats.find(f => String(f.id || f._id) === String(val));
                setFormData(prev => ({
                  ...prev,
                  flat_id: val,
                  received_from: flat ? (resolveFlatOwnerName(flat) || '') : ''
                }));
              }}
              placeholder="Search flat number or owner..."
              valueKey="id"
              displayKey="displayName"
              minCharsForSearch={0}
              clearable={true}
            />
          </div>

          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Received From</label>
              <input
                type="text"
                placeholder="Name to print on receipt"
                value={formData.received_from}
                onChange={(e) => setFormData(prev => ({ ...prev, received_from: e.target.value }))}
              />
            </div>

            <div className="settings-form-group">
              <label>Payment Method</label>
              <select value={formData.payment_method} onChange={(e) => setFormData(prev => ({ ...prev, payment_method: e.target.value }))}>
                <option value="bank">Bank</option>
                <option value="cash">Cash</option>
              </select>
            </div>

            <div className="settings-form-group">
              <label>Reference # (Cheque/UTR/Trans ID)</label>
              <input type="text" placeholder="e.g. CHQ 123456" value={formData.reference} onChange={(e) => setFormData(prev => ({ ...prev, reference: e.target.value }))} />
            </div>
          </div>

          <div className="settings-form-row">
            <SearchableSelect
              label="Received In (Bank/Cash Account)"
              options={(allAccounts || []).map((acc) => ({
                ...acc,
                code: String(acc.code || ''),
                name: String(acc.name || '')
              }))}
              value={formData.bank_account_code}
              onChange={(val) => setFormData(prev => ({ ...prev, bank_account_code: val }))}
              placeholder="Search bank/cash account code or name..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />
          </div>

          <div className="settings-form-group">
            <label>Narration/Description</label>
            <input
              type="text"
              list="receipt-narration-history"
              placeholder="Enter receipt details..."
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            />
            <datalist id="receipt-narration-history">
              {narrationHistory.map((item) => (
                <option key={item} value={item} />
              ))}
            </datalist>
          </div>

          <div className="settings-form-group" style={{ marginBottom: '20px' }}>
            <label>Voucher Attachments (Bills/Receipts - Max 5MB each)</label>
            <input
              type="file"
              onChange={(e) => setSelectedFiles([...selectedFiles, ...Array.from(e.target.files)])}
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              multiple
              style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '2px solid #e0e0e0', backgroundColor: '#fff' }}
            />
            <FileList files={selectedFiles} onRemove={(idx) => {
              const newFiles = [...selectedFiles];
              newFiles.splice(idx, 1);
              setSelectedFiles(newFiles);
            }} />
          </div>

          <div className="settings-form-actions" style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" className="settings-save-btn" disabled={loading}>
              {loading ? 'Processing...' : (editingId ? 'Update Receipt' : ' Post Receipt')}
            </button>
            {editingId && (
              <button
                type="button"
                className="settings-action-btn"
                onClick={() => {
                  setEditingId(null);
                  setFormData({ ...formData, amount: '', qty: '', unit_price: '', description: '', flat_id: '', reference: '', received_from: '' });
                  setMessage({ type: '', text: '' });
                }}
                style={{ backgroundColor: '#666' }}
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </div >

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Recent Receipts (Page {currentPage})</h3>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #ddd', backgroundColor: currentPage === 1 ? '#f5f5f5' : '#fff', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
            >
               Previous
            </button>
            <span style={{ color: '#666', fontSize: '14px' }}>
              Showing {transactions.length} receipts
            </span>
            <button
              onClick={() => setCurrentPage(p => p + 1)}
              disabled={transactions.length < receiptsPerPage}
              style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #ddd', backgroundColor: transactions.length < receiptsPerPage ? '#f5f5f5' : '#fff', cursor: transactions.length < receiptsPerPage ? 'not-allowed' : 'pointer' }}
            >
              Next 
            </button>
          </div>
        </div>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr><th>Date</th><th>Voucher #</th><th>Description</th><th style={{ textAlign: 'right' }}>Amount</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {transactions.length > 0 ? transactions.map(txn => (
                <tr key={txn.id}>
                  <td>{getVoucherDate(txn)}</td>
                  <td>
                    <button type="button" onClick={() => setViewVoucher(txn)} style={{ border: 'none', background: 'transparent', color: '#0B63CE', cursor: 'pointer', fontWeight: 700, padding: 0 }}>
                      {txn.voucher_number}
                    </button>
                  </td>
                  <td>{getVoucherDescription(txn)}</td>
                  <td style={{ textAlign: 'right' }}>{formatAmount(getVoucherAmount(txn))}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '5px', flexWrap: 'nowrap', whiteSpace: 'nowrap' }}>
                      <button className="settings-action-btn" onClick={() => handlePrintVoucher(txn.journal_entry_id)} style={{ padding: '6px 10px', fontSize: '12px' }}>Print</button>
                      <button className="settings-action-btn" onClick={() => setViewVoucher(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#607D8B' }}>View</button>
                      <button className="settings-action-btn" onClick={() => handleEditReceipt(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#2196F3' }}>Edit</button>
                      <button className="settings-action-btn" onClick={() => handleReverseReceipt(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#f44336' }}>Reversal</button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#999' }}>No recent receipts found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div >
  );
};

// Helper functions for Month formating
const formatMonthYear = (val) => {
  if (!val) return undefined;
  // val is "YYYY-MM" from input type="month"
  const [y, m] = val.split('-');
  const date = new Date(parseInt(y), parseInt(m) - 1, 1);
  return date.toLocaleString('default', { month: 'long', year: 'numeric' }); // Returns "December, 2025"
};

const convertMonthYearToInput = (val) => {
  if (!val) return '';
  // val is "December, 2025" from backend
  try {
    const parts = val.split(', ');
    if (parts.length !== 2) return '';
    const date = new Date(`${parts[0]} 1, ${parts[1]}`);
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    return `${y}-${m}`;
  } catch (e) { return ''; }
};

// --- Payment Voucher Tab ---
const PaymentVoucherTab = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [allAccounts, setAllAccounts] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [flats, setFlats] = useState([]);
  const [transactions, setTransactions] = useState([]);
  // Helper to get current month in YYYY-MM format for type="month" input
  const getCurrentMonthInput = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  };

  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    account_code: '',
    amount: '',
    qty: '',
    unit_price: '',
    payment_method: 'bank',
    description: '',
    expense_month: getCurrentMonthInput(), // Default to current month
    flat_id: '',
    reference: '',
    bank_account_code: '',
    paid_to: ''
  });
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [narrationHistory, setNarrationHistory] = useState(() => loadNarrationHistory('gruhamitra.paymentNarrations'));
  const [viewVoucher, setViewVoucher] = useState(null);

  useEffect(() => { loadInitialData(); }, []);

  const loadInitialData = async () => {
    try {
      const [acctsRes, fltsRes, txnsRes] = await Promise.allSettled([
        accountingService.getAccounts(),
        flatsService.getFlats(),
        transactionsService.getTransactions({ type: 'expense', limit: 100 })
      ]);
      const accts = acctsRes.status === 'fulfilled' ? (acctsRes.value || []) : [];
      const flts = fltsRes.status === 'fulfilled' ? (fltsRes.value || []) : [];
      const txns = txnsRes.status === 'fulfilled' ? (txnsRes.value || []) : [];
      setAllAccounts(Array.isArray(accts) ? accts : []);
      setFlats(Array.isArray(flts) ? flts : []);

      // Group transactions by journal_entry_id to show only one line per payment
      const grouped = {};
      (Array.isArray(txns) ? txns : []).forEach(txn => {
        if (txn.journal_entry_id && !grouped[txn.journal_entry_id]) {
          grouped[txn.journal_entry_id] = txn;
        }
      });

      // Convert back to array and take first 10
      const uniqueTransactions = Object.values(grouped).slice(0, 10);
      setTransactions(uniqueTransactions);

      const banks = buildBankAccountOptions(accts || []);
      setBankAccounts(banks);

      if (banks.length > 0 && !formData.bank_account_code) {
        setFormData(prev => ({ ...prev, bank_account_code: banks[0].code }));
      }
      if (acctsRes.status === 'rejected' || fltsRes.status === 'rejected' || txnsRes.status === 'rejected') {
        const failed = [];
        if (acctsRes.status === 'rejected') failed.push('accounts');
        if (fltsRes.status === 'rejected') failed.push('flats');
        if (txnsRes.status === 'rejected') failed.push('transactions');
        setMessage({
          type: 'error',
          text: `Some data failed to load (${failed.join(', ')}). You can still continue with available data.`
        });
      }
    } catch (error) {
      console.error('Error loading payment data:', error);
      setMessage({ type: 'error', text: 'Failed to load payment data.' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.payment_method === 'bank' && !formData.bank_account_code) {
      setMessage({ type: 'error', text: 'Please select a Bank Account' });
      return;
    }

    let reversalReason = null;
    if (editingId) {
      // Prompt for reason instead of just confirm
      reversalReason = window.prompt("This voucher is already posted. It cannot be edited.\n\nDo you want to create a reversal and a new corrected voucher?\n\nIf YES, please enter a reason for this correction:", "Correction");
      if (reversalReason === null) {
        return; // User cancelled
      }
    }

    setLoading(true);
    try {
      // If editing, reverse the old one first with reason
      if (editingId) {
        await transactionsService.reverseTransaction(editingId, `Update: ${reversalReason}`);
      }

      const finalDescription = formData.description || 'Payment';
      const paymentData = {
        ...formData,
        amount: parseFloat(formData.amount),
        quantity: formData.qty ? parseFloat(formData.qty) : undefined,
        unit_price: formData.unit_price ? parseFloat(formData.unit_price) : undefined,
        expense_month: formData.expense_month ? formatMonthYear(formData.expense_month) : undefined,
        description: finalDescription
      };
      console.log('Creating payment with expense_month:', paymentData.expense_month, 'from input:', formData.expense_month);
      const resp = await transactionsService.createPayment(paymentData);

      // Handle Multiple Attachment Uploads
      if (selectedFiles.length > 0 && resp.journal_entry_id) {
        const uploadPromises = selectedFiles.map(file =>
          attachmentService.uploadAttachment(resp.journal_entry_id, file)
        );
        try {
          await Promise.all(uploadPromises);
        } catch (attachError) {
          console.error('Some attachments failed to upload:', attachError);
          setMessage({ type: 'success', text: editingId ? 'Payment updated successfully!' : `Payment created! (Note: Some attachments failed to upload)` });
          return;
        }
      }

      setMessage({ type: 'success', text: editingId ? 'Payment updated successfully!' : `Payment created! Voucher: ${resp.voucher_number}` });
      setNarrationHistory(saveNarrationHistory('gruhamitra.paymentNarrations', formData.description));
      setFormData({ ...formData, amount: '', qty: '', unit_price: '', description: '', reference: '' });
      setSelectedFiles([]); // Reset files
      setEditingId(null);
      loadInitialData();
    } catch (error) { setMessage({ type: 'error', text: getErrorMessage(error) }); }
    finally { setLoading(false); }
  };

  const handleEditPayment = async (txn) => {
    // 1. Confirm with user before starting edit
    if (!window.confirm(EDIT_WARNING_MSG)) {
      return;
    }

    setLoading(true);
    try {
      // Fetch full JV details to find the Bank Account
      let bankCode = txn.bank_account_code || '';

      if (!bankCode && txn.journal_entry_id) {
        try {
          const jv = await journalService.getJournalEntry(txn.journal_entry_id);
          if (jv && jv.entries) {
            // For Payment: Credit side is usually Bank
            // Exclude the account that matches txn.account_code (Expense side)
            const bankEntry = jv.entries.find(e =>
              parseFloat(e.credit_amount) > 0 &&
              e.account_code !== txn.account_code
            );
            if (bankEntry) {
              bankCode = bankEntry.account_code;
            }
          }
        } catch (e) {
          console.error("Failed to fetch JV details for edit:", e);
        }
      }

      // Populate form with transaction data for editing
      setFormData({
        date: txn.date,
        account_code: txn.account_code || '',
        amount: txn.amount || '',
        qty: txn.quantity || '',
        unit_price: txn.unit_price || '',
        payment_method: 'bank',
        description: txn.description || '',
        expense_month: txn.expense_month ? convertMonthYearToInput(txn.expense_month) : '',
        flat_id: txn.flat_id || '',
        reference: txn.reference || '',
        bank_account_code: bankCode,
        paid_to: txn.paid_to || ''
      });
      setEditingId(txn.id);
      setMessage({ type: 'info', text: `Editing ${txn.voucher_number}. Modify the form and submit to update.` });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      console.error("Edit error:", e);
      setMessage({ type: 'error', text: "Failed to load voucher for editing" });
    } finally {
      setLoading(false);
    }
  };

  const handleReversePayment = async (txn) => {
    const reason = window.prompt(`Are you sure you want to reverse ${txn.voucher_number}?\n\nThis will create reversing entries.\n\nPlease enter a reason for reversal:`, "Incorrect Info");
    if (reason === null) {
      return;
    }
    try {
      setLoading(true);
      await transactionsService.reverseTransaction(txn.id, reason);
      setMessage({ type: 'success', text: `Payment ${txn.voucher_number} reversed successfully!` });
      loadInitialData();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to reverse payment: ${getErrorMessage(error)}` });
    } finally {
      setLoading(false);
    }
  };

  // Use full CoA for payment debit selection
  const primaryAccounts = allAccounts;

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title"> Payment Voucher</h2>
      <p className="settings-tab-description">Record society expenses, utility payments, or vendor settled</p>

      {message.text && (
        <div style={{ padding: '12px', borderRadius: '8px', marginBottom: '20px', backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE', color: message.type === 'success' ? '#2E7D32' : '#C62828' }}>
          {message.text}
        </div>
      )}

      <VoucherViewModal voucher={viewVoucher} onClose={() => setViewVoucher(null)} onPrint={handlePrintVoucher} />

      <div className="settings-section">
        <form className="settings-form" onSubmit={handleSubmit}>
          <div className="settings-form-row">
            <div className="settings-form-group"><label>Date *</label><input type="date" value={formData.date} onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))} required /></div>
            <div className="settings-form-group"><label>Quantity</label><input type="number" step="any" placeholder="e.g. 75" value={formData.qty} onChange={(e) => {
              const qty = e.target.value;
              const total = (qty && formData.unit_price) ? (parseFloat(qty) * parseFloat(formData.unit_price)).toFixed(2) : formData.amount;
              setFormData(prev => ({ ...prev, qty, amount: total }));
            }} /></div>
            <div className="settings-form-group"><label>Unit Price ()</label><input type="number" step="any" placeholder="e.g. 450" value={formData.unit_price} onChange={(e) => {
              const unit_price = e.target.value;
              const total = (formData.qty && unit_price) ? (parseFloat(formData.qty) * parseFloat(unit_price)).toFixed(2) : formData.amount;
              setFormData(prev => ({ ...prev, unit_price, amount: total }));
            }} /></div>
            <div className="settings-form-group"><label>Total Amount () *</label><input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData(prev => ({ ...prev, amount: e.target.value }))} required /></div>
            <div className="settings-form-group">
              <label>For Month</label>
              <input
                type="month"
                value={formData.expense_month}
                onChange={(e) => setFormData(prev => ({ ...prev, expense_month: e.target.value }))}
                title="Select the month this expense belongs to (optional). Defaults to voucher date month if empty."
              />
            </div>
          </div>

          <div className="settings-form-row">
            <SearchableSelect
              label="Account (Debit)"
              options={primaryAccounts}
              value={formData.account_code}
              onChange={(val) => setFormData(prev => ({ ...prev, account_code: val }))}
              placeholder="Search account code or name..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />
            <SearchableSelect
              label="Flat (Optional tracking)"
              options={flats.map(f => ({
                ...f,
                id: String(f.id || f._id || ''),
                displayName: `${f.flat_number} - ${resolveFlatOwnerName(f) || 'No Owner'}`
              }))}
              value={formData.flat_id}
              onChange={(val) => setFormData(prev => ({ ...prev, flat_id: val }))}
              placeholder="Search flat number or owner..."
              valueKey="id"
              displayKey="displayName"
              minCharsForSearch={0}
              clearable={true}
            />
          </div>

          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Paid To</label>
              <input
                type="text"
                placeholder="Name to print on payment voucher"
                value={formData.paid_to}
                onChange={(e) => setFormData(prev => ({ ...prev, paid_to: e.target.value }))}
              />
            </div>
            <div className="settings-form-group">
              <label>Payment Method</label>
              <select value={formData.payment_method} onChange={(e) => setFormData(prev => ({ ...prev, payment_method: e.target.value }))}>
                <option value="bank">Bank</option>
                <option value="cash">Cash</option>
              </select>
            </div>
          </div>

          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Reference # (Cheque/UTR/Trans ID)</label>
              <input type="text" placeholder="e.g. UTR12345" value={formData.reference} onChange={(e) => setFormData(prev => ({ ...prev, reference: e.target.value }))} />
            </div>
          </div>

          <div className="settings-form-row">
            <SearchableSelect
              label="Paid From (Bank/Cash Account)"
              options={(allAccounts || []).map((acc) => ({
                ...acc,
                code: String(acc.code || ''),
                name: String(acc.name || '')
              }))}
              value={formData.bank_account_code}
              onChange={(val) => setFormData(prev => ({ ...prev, bank_account_code: val }))}
              placeholder="Search bank/cash account code or name..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />
          </div>

          <div className="settings-form-group">
            <label>Narration/Description</label>
            <input
              type="text"
              list="payment-narration-history"
              placeholder="Enter payment details..."
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            />
            <datalist id="payment-narration-history">
              {narrationHistory.map((item) => (
                <option key={item} value={item} />
              ))}
            </datalist>
          </div>

          <div className="settings-form-group" style={{ marginBottom: '20px' }}>
            <label>Voucher Attachments (Bills/Receipts - Max 5MB each)</label>
            <input
              type="file"
              onChange={(e) => setSelectedFiles([...selectedFiles, ...Array.from(e.target.files)])}
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              multiple
              style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '2px solid #e0e0e0', backgroundColor: '#fff' }}
            />
            <FileList files={selectedFiles} onRemove={(idx) => {
              const newFiles = [...selectedFiles];
              newFiles.splice(idx, 1);
              setSelectedFiles(newFiles);
            }} />
          </div>

          <div className="settings-form-actions" style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" className="settings-save-btn" disabled={loading}>
              {loading ? 'Processing...' : (editingId ? 'Update Payment' : ' Post Payment')}
            </button>
            {editingId && (
              <button
                type="button"
                className="settings-action-btn"
                onClick={() => {
                  setEditingId(null);
                  setFormData({ ...formData, amount: '', qty: '', unit_price: '', description: '', reference: '' });
                  setMessage({ type: '', text: '' });
                }}
                style={{ backgroundColor: '#666' }}
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Recent Payments</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr><th>Date</th><th>Voucher #</th><th>Description</th><th style={{ textAlign: 'right' }}>Amount</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {transactions.length > 0 ? transactions.map(txn => (
                <tr key={txn.id}>
                  <td>{getVoucherDate(txn)}</td>
                  <td>
                    <button type="button" onClick={() => setViewVoucher(txn)} style={{ border: 'none', background: 'transparent', color: '#0B63CE', cursor: 'pointer', fontWeight: 700, padding: 0 }}>
                      {txn.voucher_number}
                    </button>
                  </td>
                  <td>{getVoucherDescription(txn)}</td>
                  <td style={{ textAlign: 'right' }}>{formatAmount(getVoucherAmount(txn))}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '5px', flexWrap: 'nowrap', whiteSpace: 'nowrap' }}>
                      <button className="settings-action-btn" onClick={() => handlePrintVoucher(txn.journal_entry_id)} style={{ padding: '6px 10px', fontSize: '12px' }}>Print</button>
                      <button className="settings-action-btn" onClick={() => setViewVoucher(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#607D8B' }}>View</button>
                      <button className="settings-action-btn" onClick={() => handleEditPayment(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#2196F3' }}>Edit</button>
                      <button className="settings-action-btn" onClick={() => handleReversePayment(txn)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#f44336' }}>Reversal</button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#999' }}>No recent payments found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div >
  );
};

// --- Journal Voucher Tab ---
const JournalVoucherTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [vouchers, setVouchers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [flats, setFlats] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingVoucher, setEditingVoucher] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    expense_for_month: getCurrentMonthYear(),
    description: '',
    entries: [{ account_code: '', debit_amount: '', credit_amount: '', description: '', flat_id: '' }, { account_code: '', debit_amount: '', credit_amount: '', description: '', flat_id: '' }]
  });
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [existingAttachments, setExistingAttachments] = useState([]);

  useEffect(() => { loadInitialData(); }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [accts, flts, vchs] = await Promise.all([
        accountingService.getAccounts(),
        flatsService.getFlats(),
        journalService.getJournalEntries()
      ]);
      console.log('Journal Voucher - Loaded accounts:', accts?.length || 0);
      console.log('Journal Voucher - Loaded flats:', flts?.length || 0);
      console.log('Journal Voucher - Loaded vouchers:', vchs?.length || 0);
      setAccounts(accts || []);
      setFlats(flts || []);
      setVouchers(vchs || []);
      if (!accts || accts.length === 0) {
        setMessage({ type: 'error', text: 'No accounts found. Please initialize Chart of Accounts first from the Chart of Accounts tab.' });
      }
    } catch (e) {
      console.error('Error loading journal data:', e);
      console.error('Error response:', e.response?.data);
      const errorDetail = e.response?.data?.detail || e.message;
      setMessage({ type: 'error', text: `Failed to load data: ${JSON.stringify(errorDetail)}` });
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (voucher) => {
    // 1. Confirm with user before starting edit
    if (!window.confirm(EDIT_WARNING_MSG)) {
      return;
    }

    try {
      const full = await journalService.getJournalEntry(voucher.id);
      setEditingVoucher(voucher.id);
      setFormData({
        date: full.date,
        expense_for_month: full.expense_month || getCurrentMonthYear(),
        description: full.description,
        entries: full.entries.map(e => ({
          account_code: e.account_code,
          debit_amount: e.debit_amount.toString(),
          credit_amount: e.credit_amount.toString(),
          description: e.description || '',
          flat_id: e.flat_id || ''
        }))
      });
      setShowForm(true);
      setMessage({ type: 'info', text: `Editing ${voucher.entry_number}. Modify the form and submit to update.` });

      // Fetch existing attachments
      try {
        const attachments = await attachmentService.listAttachments(voucher.id);
        setExistingAttachments(attachments);
      } catch (attError) {
        console.error('Error fetching attachments in edit mode:', attError);
      }
    } catch (e) { console.error('Error fetching journal:', e); }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingVoucher(null);
    setFormData({
      date: new Date().toISOString().split('T')[0],
      expense_for_month: getCurrentMonthYear(),
      description: '',
      entries: [{ account_code: '', debit_amount: '', credit_amount: '', description: '', flat_id: '' }, { account_code: '', debit_amount: '', credit_amount: '', description: '', flat_id: '' }]
    });
    setSelectedFiles([]);
    setMessage({ type: '', text: '' });
    setExistingAttachments([]);
  };

  const handleReverseJournal = async (voucher) => {
    if (!window.confirm(`Are you sure you want to reverse ${voucher.entry_number}?\n\nThis will create reversing entries and cannot be undone.`)) {
      return;
    }
    try {
      setLoading(true);
      await journalService.reverseJournalEntry(voucher.id);
      setMessage({ type: 'success', text: `Journal entry ${voucher.entry_number} reversed successfully!` });
      loadInitialData();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to reverse journal entry: ${getErrorMessage(error)}` });
    } finally {
      setLoading(false);
    }
  };

  const calculateTotal = () => {
    const td = formData.entries.reduce((s, e) => s + (parseFloat(e.debit_amount) || 0), 0);
    const tc = formData.entries.reduce((s, e) => s + (parseFloat(e.credit_amount) || 0), 0);
    return { td, tc, balanced: Math.abs(td - tc) < 0.01 && td > 0 };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { balanced } = calculateTotal();
    if (!balanced) { setMessage({ type: 'error', text: 'Voucher is not balanced!' }); return; }

    setSaving(true);
    try {
      const data = {
        date: formData.date,
        expense_month: formData.entries.some(e => e.account_code?.startsWith('5')) ? formData.expense_for_month : null,
        description: formData.description,
        entries: formData.entries.map(e => ({
          account_code: e.account_code,
          debit_amount: parseFloat(e.debit_amount) || 0,
          credit_amount: parseFloat(e.credit_amount) || 0,
          description: e.description,
          flat_id: e.flat_id || null
        }))
      };

      let resp;
      if (editingVoucher) resp = await journalService.updateJournalEntry(editingVoucher, data);
      else resp = await journalService.createJournalEntry(data);

      // Handle Multiple Attachment Uploads
      if (selectedFiles.length > 0 && resp.id) {
        const uploadPromises = selectedFiles.map(file =>
          attachmentService.uploadAttachment(resp.id, file)
        );
        try {
          await Promise.all(uploadPromises);
        } catch (attachError) {
          console.error('Some attachments failed to upload:', attachError);
          setMessage({ type: 'success', text: 'Journal Voucher saved! (Note: Some attachments failed to upload)' });
          return;
        }
      }

      setMessage({ type: 'success', text: 'Journal Voucher saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      handleCancel();
      loadInitialData();
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const addEntry = () => {
    setFormData({ ...formData, entries: [...formData.entries, { account_code: '', debit_amount: '', credit_amount: '', description: '', flat_id: '' }] });
  };

  const removeEntry = (index) => {
    if (formData.entries.length <= 2) return;
    const newEntries = [...formData.entries];
    newEntries.splice(index, 1);
    setFormData({ ...formData, entries: newEntries });
  };

  const handleEntryChange = (index, field, value) => {
    const newEntries = [...formData.entries];
    newEntries[index][field] = value;
    setFormData({ ...formData, entries: newEntries });
  };

  const { td, tc, balanced } = calculateTotal();

  if (loading) return <div>Loading...</div>;

  return (
    <div className="settings-tab-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
        <h2 className="settings-tab-title"> Journal Voucher</h2>
        <button className="settings-add-btn" onClick={() => { if (showForm) handleCancel(); else setShowForm(true); }}>
          {showForm ? 'Cancel' : '+ New Journal Entry'}
        </button>
      </div>

      {message.text && (
        <div style={{ padding: '12px', borderRadius: '8px', marginBottom: '20px', backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE', color: message.type === 'success' ? '#2E7D32' : '#C62828' }}>
          {message.text}
        </div>
      )}

      {showForm && (
        <div className="settings-section">
          <form className="settings-form" onSubmit={handleSubmit}>
            <div className="settings-form-row">
              <div className="settings-form-group"><label>Voucher Date *</label><input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} required /></div>
              <div className="settings-form-group"><label>Expense For Month</label><input type="text" placeholder="Jan 2026" value={formData.expense_for_month} onChange={(e) => setFormData({ ...formData, expense_for_month: e.target.value })} /></div>
            </div>

            <div className="settings-form-group"><label>General Narration *</label><textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required rows="2" /></div>

            <div className="settings-form-group" style={{ marginBottom: '20px' }}>
              <label>Voucher Attachments (Bills/Receipts - Max 5MB each)</label>
              {existingAttachments.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <label style={{ fontSize: '12px', color: '#666' }}>Existing Attachments:</label>
                  {existingAttachments.map(att => (
                    <div key={att.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', padding: '4px 8px', backgroundColor: '#f9f9f9', borderRadius: '4px', marginBottom: '4px' }}>
                      <span> {att.file_name}</span>
                      <button type="button" onClick={() => {
                        if (window.confirm('Delete this attachment?')) {
                          attachmentService.deleteAttachment(att.id).then(() => {
                            setExistingAttachments(existingAttachments.filter(a => a.id !== att.id));
                          });
                        }
                      }} style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer' }}></button>
                    </div>
                  ))}
                </div>
              )}
              <input
                type="file"
                onChange={(e) => setSelectedFiles([...selectedFiles, ...Array.from(e.target.files)])}
                accept=".pdf,.jpg,.jpeg,.png,.docx"
                multiple
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '2px solid #e0e0e0', backgroundColor: '#fff' }}
              />
              <FileList files={selectedFiles} onRemove={(idx) => {
                const newFiles = [...selectedFiles];
                newFiles.splice(idx, 1);
                setSelectedFiles(newFiles);
              }} />
            </div>

            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th style={{ width: '25%' }}>Account *</th>
                    <th style={{ width: '15%' }}>Debit</th>
                    <th style={{ width: '15%' }}>Credit</th>
                    <th>Description</th>
                    <th style={{ width: '80px' }}>Flat</th>
                    <th style={{ width: '50px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {formData.entries.map((entry, idx) => (
                    <tr key={idx}>
                      <td>
                        <SearchableSelect
                          label=""
                          options={accounts}
                          value={entry.account_code}
                          onChange={(val) => handleEntryChange(idx, 'account_code', val)}
                          placeholder="Acc Code/Name"
                          required={true}
                          valueKey="code"
                          displayKey="name"
                          minCharsForSearch={0}
                        />
                      </td>
                      <td><input type="number" step="0.01" value={entry.debit_amount} onChange={(e) => handleEntryChange(idx, 'debit_amount', e.target.value)} /></td>
                      <td><input type="number" step="0.01" value={entry.credit_amount} onChange={(e) => handleEntryChange(idx, 'credit_amount', e.target.value)} /></td>
                      <td><input type="text" value={entry.description} onChange={(e) => handleEntryChange(idx, 'description', e.target.value)} placeholder="Entry level narration" /></td>
                      <td>
                        <SearchableSelect
                          label=""
                          options={flats.map(f => ({
                            ...f,
                            id: String(f.id || f._id || ''),
                            displayName: f.flat_number
                          }))}
                          value={entry.flat_id}
                          onChange={(val) => handleEntryChange(idx, 'flat_id', val)}
                          placeholder="Flat"
                          valueKey="id"
                          displayKey="displayName"
                          minCharsForSearch={0}
                        />
                      </td>
                      <td><button type="button" onClick={() => removeEntry(idx)} style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer' }}></button></td>
                    </tr>
                  ))}
                  <tr style={{ background: '#f9f9f9', fontWeight: 'bold' }}>
                    <td>TOTAL</td>
                    <td style={{ color: balanced ? 'green' : 'red' }}>{td.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td style={{ color: balanced ? 'green' : 'red' }}>{tc.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td colSpan="3">{balanced ? ' Balanced' : ' Unbalanced'}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: '10px' }}>
              <button type="button" className="settings-action-btn" onClick={addEntry}>+ Add Line</button>
            </div>

            <div className="settings-form-actions">
              <button type="submit" className="settings-save-btn" disabled={!balanced || saving}>{saving ? 'Saving...' : (editingVoucher ? 'Update Voucher' : 'Post Journal Voucher')}</button>
              <button type="button" className="settings-cancel-btn" onClick={handleCancel}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="settings-section">
        <h3>Journal Entries</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr><th>Voucher #</th><th>Date</th><th>Entries</th><th style={{ textAlign: 'right' }}>Total</th><th>Narration</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {vouchers.map(v => (
                <tr key={v.id}>
                  <td><strong>{v.entry_number}</strong></td>
                  <td>{v.date}</td>
                  <td>{v.entries?.length || 0} items</td>
                  <td style={{ textAlign: 'right' }}>{(v.total_debit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                  <td>{v.description}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '5px', flexWrap: 'nowrap', whiteSpace: 'nowrap' }}>
                      <button className="settings-action-btn" onClick={() => handlePrintVoucher(v.id)} style={{ padding: '6px 10px', fontSize: '12px' }}>Print</button>
                      <button className="settings-action-btn" onClick={() => handleEdit(v)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#2196F3' }}>Edit</button>
                      <button className="settings-action-btn" onClick={() => handleReverseJournal(v)} style={{ padding: '6px 10px', fontSize: '12px', backgroundColor: '#f44336' }}>Reversal</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// --- Transfer Voucher Tab ---
const TransferVoucherTab = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [allAccounts, setAllAccounts] = useState([]);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    from_account_code: '',
    to_account_code: '',
    amount: '',
    description: '',
    reference: ''
  });
  const [selectedFiles, setSelectedFiles] = useState([]);

  useEffect(() => { loadInitialData(); }, []);

  const loadInitialData = async () => {
    try {
      const resp = await accountingService.getAccounts();
      setAllAccounts(resp || []);
    } catch (e) { console.error('Error loading accounts:', e); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = {
        date: formData.date,
        description: formData.description || 'Transfer',
        entries: [
          { account_code: formData.from_account_code, credit_amount: parseFloat(formData.amount), debit_amount: 0, description: formData.description },
          { account_code: formData.to_account_code, debit_amount: parseFloat(formData.amount), credit_amount: 0, description: formData.description }
        ]
      };

      const resp = await journalService.createJournalEntry(data);

      if (selectedFiles.length > 0 && resp.id) {
        await Promise.all(selectedFiles.map(file => attachmentService.uploadAttachment(resp.id, file)));
      }

      setMessage({ type: 'success', text: 'Transfer Voucher posted successfully!' });
      setFormData({ ...formData, amount: '', description: '', reference: '' });
      setSelectedFiles([]);
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title"> Transfer Voucher</h2>
      <p className="settings-tab-description">Internal transfers between society bank/cash accounts</p>

      {message.text && (
        <div style={{ padding: '12px', borderRadius: '8px', marginBottom: '20px', backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE', color: message.type === 'success' ? '#2E7D32' : '#C62828' }}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <form className="settings-form" onSubmit={handleSubmit}>
          <div className="settings-form-row">
            <div className="settings-form-group"><label>Date *</label><input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} required /></div>
            <div className="settings-form-group"><label>Amount () *</label><input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} required /></div>
          </div>

          <div className="settings-form-row">
            <SearchableSelect
              label="From Account (Credit) *"
              options={allAccounts}
              value={formData.from_account_code}
              onChange={(val) => setFormData({ ...formData, from_account_code: val })}
              placeholder="Source account..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />
            <SearchableSelect
              label="To Account (Debit) *"
              options={allAccounts}
              value={formData.to_account_code}
              onChange={(val) => setFormData({ ...formData, to_account_code: val })}
              placeholder="Destination account..."
              required={true}
              valueKey="code"
              displayKey="name"
              minCharsForSearch={0}
            />
          </div>

          <div className="settings-form-group">
            <label>Narration/Description</label>
            <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} rows="2" />
          </div>

          <div className="settings-form-group" style={{ marginBottom: '20px' }}>
            <label>Voucher Attachments (Max 5MB each)</label>
            <input
              type="file"
              onChange={(e) => setSelectedFiles([...selectedFiles, ...Array.from(e.target.files)])}
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              multiple
              style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '2px solid #e0e0e0', backgroundColor: '#fff' }}
            />
            <FileList files={selectedFiles} onRemove={(idx) => {
              const newFiles = [...selectedFiles];
              newFiles.splice(idx, 1);
              setSelectedFiles(newFiles);
            }} />
          </div>

          <div className="settings-form-actions">
            <button type="submit" className="settings-save-btn" disabled={loading || !formData.amount}>{loading ? 'Posting...' : ' Post Transfer'}</button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Reports Tab
const ReportsTab = () => {
  const [selectedReport, setSelectedReport] = useState('');
  // Default as_on_date to today (YYYY-MM-DD) so Trial Balance / Balance Sheet "As On Date" prefills with today
  const _todayIso = new Date().toISOString().slice(0, 10);
  const [reportParams, setReportParams] = useState({
    from_date: '',
    to_date: '',
    account: '',
    as_on_date: _todayIso, // For trial balance and balance sheet (defaults to today)
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [reportData, setReportData] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [accountsWithBalance, setAccountsWithBalance] = useState([]);

  const [showAttachments, setShowAttachments] = useState(false);
  const [activeVoucherId, setActiveVoucherId] = useState(null);

  const handleViewAttachment = (journalEntryId) => {
    setActiveVoucherId(journalEntryId);
    setShowAttachments(true);
  };

  const [recentReports, setRecentReports] = useState([
    {
      id: 'recent-1',
      type: 'trial-balance',
      label: 'Trial Balance',
      generatedOn: '2026-01-05 10:30 AM',
      period: 'Jan 2026',
      params: { as_on_date: '2026-01-14', from_date: '2026-01-01', to_date: '2026-01-14' }
    }
  ]);

  useEffect(() => {
    const loadAccountsAndBalances = async () => {
      try {
        // Load all accounts
        const data = await accountingService.getAccounts();
        setAccounts(data || []);

        // Load trial balance to get accounts with non-zero balances
        try {
          const today = new Date().toISOString().split('T')[0];
          const trialBalance = await api.get('/reports/trial-balance', {
            params: { as_on_date: today }
          });

          // Filter accounts that have non-zero debit or credit balance
          const accountsWithActivity = trialBalance.data.items
            .filter(item => item.debit_balance > 0 || item.credit_balance > 0)
            .map(item => {
              // Find the full account object from accounts list
              const fullAccount = data.find(acc => acc.code === item.account_code);
              return fullAccount || { code: item.account_code, name: item.account_name };
            });

          setAccountsWithBalance(accountsWithActivity);
        } catch (tbError) {
          console.error('Error loading trial balance:', tbError);
          // If trial balance fails, use all accounts
          setAccountsWithBalance(data || []);
        }
      } catch (error) {
        console.error('Error loading accounts for reports:', error);
      }
    };
    loadAccountsAndBalances();
  }, []);

  const reports = [
    { id: 'trial-balance', label: 'Trial Balance', icon: '' },
    { id: 'profit-loss', label: 'Profit & Loss', icon: '' },
    { id: 'balance-sheet', label: 'Balance Sheet', icon: '' },
    { id: 'ledger', label: 'Ledger Statement', icon: '' },
    { id: 'daybook', label: 'Day Book', icon: '' },
    { id: 'cash-flow', label: 'Cash Flow', icon: '' },
  ];

  const handleGenerateReport = async () => {
    if (!selectedReport) {
      setError('Please select a report type');
      setSuccess('');
      return;
    }

    // Validate date for trial balance
    if (selectedReport === 'trial-balance' || selectedReport === 'balance-sheet') {
      const asOnDate = reportParams.as_on_date || reportParams.to_date || reportParams.from_date;
      if (!asOnDate) {
        setError('Please select a date (As On Date)');
        setSuccess('');
        return;
      }
    } else {
      if (!reportParams.from_date || !reportParams.to_date) {
        setError('Please select both From Date and To Date');
        setSuccess('');
        return;
      }
    }

    setLoading(true);
    setError('');
    setSuccess('');
    setReportData(null);

    try {
      let response;

      if (selectedReport === 'trial-balance') {
        const asOnDate = reportParams.as_on_date || reportParams.to_date || reportParams.from_date;
        response = await api.get('/accounting/reports/trial-balance', {
          params: { as_of: asOnDate }
        });
        response = { ...response, data: normalizeTrialBalanceReport(response.data) };
        setReportData(response.data);
        setSuccess(`Trial Balance generated successfully for ${asOnDate}`);
      } else if (selectedReport === 'ledger') {
        if (!reportParams.account) {
          setError('Please select an account for the Ledger Statement');
          setLoading(false);
          return;
        }
        response = await api.get('/reports/ledger', {
          params: {
            from_date: reportParams.from_date,
            to_date: reportParams.to_date,
            account_code: reportParams.account
          }
        });
        setReportData(response.data);
        setSuccess(
          reportParams.account === 'all'
            ? 'Ledger Statement generated successfully for all accounts with activity'
            : `Ledger Statement generated successfully for ${response.data.account_name}`
        );
      } else if (selectedReport === 'balance-sheet') {
        if (!reportParams.as_on_date) {
          setError('Please select an "As On Date" for Balance Sheet report');
          setLoading(false);
          return;
        }
        response = await api.get('/reports/balance-sheet', {
          params: {
            as_on_date: reportParams.as_on_date
          }
        });
        setReportData(response.data);
        setSuccess(`Balance Sheet generated successfully`);
      } else if (selectedReport === 'profit-loss') {
        response = await api.get('/reports/income-and-expenditure', {
          params: {
            from_date: reportParams.from_date,
            to_date: reportParams.to_date
          }
        });
        setReportData(response.data);
        setSuccess(`Income & Expenditure report generated successfully`);
      } else if (selectedReport === 'cash-flow') {
        response = await api.get('/reports/receipts-and-payments', {
          params: {
            from_date: reportParams.from_date,
            to_date: reportParams.to_date
          }
        });
        setReportData(response.data);
        setSuccess(`Receipts & Payments report generated successfully`);
      } else {
        setError(`${reports.find(r => r.id === selectedReport)?.label} report generation is not yet implemented`);
        setLoading(false);
        return;
      }

      // Add to recent reports if successful
      if (response && response.data) {
        setReportData(response.data);
        const newReport = {
          id: Date.now(),
          type: selectedReport,
          label: reports.find(r => r.id === selectedReport)?.label || selectedReport,
          generatedOn: new Date().toLocaleString(),
          period: reportParams.as_on_date || `${reportParams.from_date} to ${reportParams.to_date}`,
          params: { ...reportParams }
        };
        setRecentReports(prev => [newReport, ...prev.slice(0, 4)]);
      }

      setLoading(false);
    } catch (err) {
      setLoading(false);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to generate report. Please try again.';
      setError(errorMessage);
      setReportData(null);
      console.error('Error generating report:', err);
    }
  };

  const handleExportPDF = async (reportType = selectedReport, params = reportParams) => {
    if (!reportType) return;
    try {
      let url = '';
      let exportParams = {};

      const asOnDate = params.as_on_date || params.to_date || params.from_date;

      if (reportType === 'trial-balance') {
        url = '/reports/trial-balance/export/pdf';
        exportParams = { as_on_date: asOnDate };
      } else if (reportType === 'ledger') {
        url = '/reports/general-ledger/export/pdf';
        exportParams = { from_date: params.from_date, to_date: params.to_date, account_code: params.account };
      } else if (reportType === 'profit-loss') {
        url = '/reports/income-and-expenditure/export/pdf';
        exportParams = { from_date: params.from_date, to_date: params.to_date };
      } else if (reportType === 'balance-sheet') {
        url = '/reports/balance-sheet/export/pdf';
        exportParams = { as_on_date: asOnDate };
      } else if (reportType === 'cash-flow') {
        url = '/reports/receipts-and-payments/export/pdf';
        exportParams = { from_date: params.from_date, to_date: params.to_date };
      }

      if (!url) {
        setError('Export for this report is not yet implemented');
        return;
      }

      setLoading(true);
      const response = await api.get(url, { params: exportParams, responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `${reportType}_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setLoading(false);
    } catch (err) {
      setLoading(false);
      console.error('Export error:', err);
      setError('Failed to export PDF');
    }
  };

  const handleViewRecentReport = async (report) => {
    setSelectedReport(report.type);
    setReportParams(report.params);

    // Trigger generation
    setLoading(true);
    setError('');
    setSuccess('');
    setReportData(null);

    try {
      let response;
      const params = report.params;

      if (report.type === 'trial-balance') {
        const asOnDate = params.as_on_date || params.to_date || params.from_date;
        response = await api.get('/accounting/reports/trial-balance', {
          params: { as_of: asOnDate }
        });
        response = { ...response, data: normalizeTrialBalanceReport(response.data) };
      } else if (report.type === 'ledger') {
        response = await api.get('/reports/ledger', {
          params: {
            from_date: params.from_date,
            to_date: params.to_date,
            account_code: params.account
          }
        });
      } else if (report.type === 'balance-sheet') {
        response = await api.get('/reports/balance-sheet', {
          params: {
            from_date: params.from_date || params.as_on_date,
            to_date: params.to_date || params.as_on_date
          }
        });
      } else if (report.type === 'profit-loss') {
        response = await api.get('/reports/income-and-expenditure', {
          params: {
            from_date: params.from_date,
            to_date: params.to_date
          }
        });
      } else if (report.type === 'cash-flow') {
        response = await api.get('/reports/receipts-and-payments', {
          params: {
            from_date: params.from_date,
            to_date: params.to_date
          }
        });
      }

      if (response) {
        setReportData(response.data);
        setSuccess(`${report.label} loaded from history`);
        // Scroll to report results
        window.scrollTo({ top: 400, behavior: 'smooth' });
      }
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load historic report');
      console.error(err);
    }
  };

  const handleExportExcel = async (reportType = selectedReport, params = reportParams) => {
    if (!reportType) return;
    try {
      let url = '';
      let exportParams = {};

      const asOnDate = params.as_on_date || params.to_date || params.from_date;

      if (reportType === 'trial-balance') {
        url = '/reports/trial-balance/export/excel';
        exportParams = { as_on_date: asOnDate };
      } else if (reportType === 'ledger') {
        url = '/reports/general-ledger/export/excel';
        exportParams = { from_date: params.from_date, to_date: params.to_date, account_code: params.account };
      } else if (reportType === 'profit-loss') {
        url = '/reports/income-and-expenditure/export/excel';
        exportParams = { from_date: params.from_date, to_date: params.to_date };
      } else if (reportType === 'balance-sheet') {
        url = '/reports/balance-sheet/export/excel';
        exportParams = { as_on_date: asOnDate };
      } else if (reportType === 'cash-flow') {
        url = '/reports/receipts-and-payments/export/excel';
        exportParams = { from_date: params.from_date, to_date: params.to_date };
      }

      if (!url) {
        setError('Export for this report is not yet implemented');
        return;
      }

      setLoading(true);
      const response = await api.get(url, { params: exportParams, responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `${reportType}_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setLoading(false);
    } catch (err) {
      setLoading(false);
      console.error('Export error:', err);
      setError('Failed to export Excel');
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title"> Accounting Reports</h2>
      <p className="settings-tab-description">Generate financial reports and statements</p>

      <div className="settings-section">
        <h3>Select Report Type</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
          {reports.map((report) => (
            <button
              key={report.id}
              onClick={() => {
                setSelectedReport(report.id);
                setReportData(null);
                setError('');
                setSuccess('');
              }}
              style={{
                padding: '20px',
                border: `3px solid ${selectedReport === report.id ? 'var(--gm-orange)' : '#e0e0e0'}`,
                borderRadius: '12px',
                background: selectedReport === report.id ? 'var(--gm-bg-light)' : 'white',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s'
              }}
            >
              <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>{report.icon}</span>
              <strong>{report.label}</strong>
            </button>
          ))}
        </div>

        {selectedReport && (
          <div className="settings-form">
            <h4 style={{ marginBottom: '15px' }}>Report Parameters</h4>

            {/* Trial Balance and Balance Sheet use As On Date */}
            {(selectedReport === 'trial-balance' || selectedReport === 'balance-sheet') ? (
              <div className="settings-form-group">
                <label>As On Date <span style={{ color: 'red' }}>*</span></label>
                <input
                  type="date"
                  value={reportParams.as_on_date || reportParams.to_date || reportParams.from_date}
                  onChange={(e) => {
                    const date = e.target.value;
                    setReportParams({ ...reportParams, as_on_date: date, to_date: date, from_date: date });
                  }}
                  required
                />
              </div>
            ) : (
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>From Date <span style={{ color: 'red' }}>*</span></label>
                  <input
                    type="date"
                    value={reportParams.from_date}
                    onChange={(e) => setReportParams({ ...reportParams, from_date: e.target.value })}
                    required
                  />
                </div>
                <div className="settings-form-group">
                  <label>To Date <span style={{ color: 'red' }}>*</span></label>
                  <input
                    type="date"
                    value={reportParams.to_date}
                    onChange={(e) => setReportParams({ ...reportParams, to_date: e.target.value })}
                    required
                  />
                </div>
              </div>
            )}

            {(selectedReport === 'ledger' || selectedReport === 'daybook') && (
              <SearchableSelect
                label="Account"
                options={[
                  { code: 'all', name: 'All Accounts (with non-zero activity)', id: 'all' },
                  ...accountsWithBalance
                ]}
                value={reportParams.account}
                onChange={(val) => setReportParams({ ...reportParams, account: val })}
                placeholder="Search account code or name..."
                valueKey="code"
                displayKey="name"
                minCharsForSearch={0}
              />
            )}

            {/* Error and Success Messages */}
            {error && (
              <div style={{
                padding: '12px',
                backgroundColor: '#fee',
                border: '1px solid #fcc',
                borderRadius: '6px',
                color: '#c33',
                marginBottom: '15px'
              }}>
                <strong>Error:</strong> {error}
              </div>
            )}
            {success && (
              <div style={{
                padding: '12px',
                backgroundColor: '#efe',
                border: '1px solid #cfc',
                borderRadius: '6px',
                color: '#3c3',
                marginBottom: '15px'
              }}>
                <strong>Success:</strong> {success}
              </div>
            )}

            <div className="settings-form-actions">
              <button
                className="settings-save-btn"
                onClick={handleGenerateReport}
                disabled={loading}
              >
                {loading ? 'Generating...' : 'Generate Report'}
              </button>
              {reportData && (
                <>
                  <button
                    className="settings-action-btn"
                    onClick={() => handleExportPDF()}
                    disabled={loading}
                  >
                    Export PDF
                  </button>
                  <button
                    className="settings-action-btn"
                    onClick={() => handleExportExcel()}
                    disabled={loading}
                  >
                    Export Excel
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Report Results Display */}
        {reportData && selectedReport === 'trial-balance' && (
          <div className="settings-section" style={{ marginTop: '30px' }}>
            <h3>Trial Balance Report</h3>
            <div style={{ marginBottom: '15px', color: '#666' }}>
              <strong>As On Date:</strong> {reportData.as_on_date} |
              <strong> Total Debit:</strong> {reportData.total_debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })} |
              <strong> Total Credit:</strong> {reportData.total_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })} |
              <strong> Difference:</strong> {reportData.difference.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              {reportData.is_balanced ? (
                <span style={{ color: 'green', marginLeft: '10px' }}> Balanced</span>
              ) : (
                <span style={{ color: 'red', marginLeft: '10px' }}> Not Balanced</span>
              )}
            </div>
            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>Account Code</th>
                    <th>Account Name</th>
                    <th style={{ textAlign: 'right' }}>Debit Balance</th>
                    <th style={{ textAlign: 'right' }}>Credit Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.items && reportData.items.length > 0 ? (
                    reportData.items.map((item, index) => (
                      <tr key={index}>
                        <td>{item.account_code}</td>
                        <td>{item.account_name}</td>
                        <td style={{ textAlign: 'right' }}>
                          {item.debit_balance > 0 ? `${item.debit_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {item.credit_balance > 0 ? `${item.credit_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                        No accounts with balances found
                      </td>
                    </tr>
                  )}
                  {/* Totals Row */}
                  {reportData.items && reportData.items.length > 0 && (
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                      <td colSpan="2">Total</td>
                      <td style={{ textAlign: 'right' }}>
                        {reportData.total_debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {reportData.total_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {reportData && selectedReport === 'balance-sheet' && (() => {
          const isBalanced = reportData.is_balanced !== false;
          const formatCurrency = (amount) => `${(amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

          return (
            <div className="settings-section" style={{ marginTop: '30px' }}>
              <h3 style={{ textAlign: 'center', marginBottom: '20px' }}>
                Balance Sheet as on {reportData.as_on_date || reportParams.as_on_date}
              </h3>

              {/* Balance Check Message */}
              {isBalanced ? (
                <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#d4edda', borderRadius: '8px', color: '#155724', textAlign: 'center' }}>
                   Balance Sheet is balanced: Assets = Liabilities
                </div>
              ) : (
                <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f8d7da', borderRadius: '8px', color: '#721c24', textAlign: 'center' }}>
                   Balance Sheet mismatch detected. Assets: {formatCurrency(reportData.total_assets)}  Liabilities: {formatCurrency(reportData.total_liabilities)}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginTop: '20px' }}>
                {/* LIABILITIES SIDE */}
                <div>
                  <h4 style={{ color: '#FF3B30', marginBottom: '15px', borderBottom: '3px solid #FF3B30', paddingBottom: '8px', fontSize: '18px', fontWeight: 'bold' }}>
                     LIABILITIES
                  </h4>

                  {/* A. Capital & Funds */}
                  <div style={{ marginBottom: '20px' }}>
                    <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>A. Capital & Funds</h5>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Particulars</th>
                            <th style={{ textAlign: 'right' }}>Amount ()</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.capital_funds && reportData.capital_funds.length > 0 ? (
                            reportData.capital_funds.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.name}</td>
                                <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No capital & funds recorded</td>
                            </tr>
                          )}
                        </tbody>
                        <tfoot>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                            <td>Total Funds</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(reportData.total_capital_funds || 0)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* B. Current Liabilities & Provisions */}
                  <div style={{ marginBottom: '20px' }}>
                    <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>B. Current Liabilities & Provisions</h5>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Particulars</th>
                            <th style={{ textAlign: 'right' }}>Amount ()</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.current_liabilities && reportData.current_liabilities.length > 0 ? (
                            reportData.current_liabilities.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.name}</td>
                                <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No current liabilities recorded</td>
                            </tr>
                          )}
                        </tbody>
                        <tfoot>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                            <td>Total Current Liabilities</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(reportData.total_current_liabilities || 0)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* TOTAL LIABILITIES */}
                  <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff9e6', borderRadius: '8px', border: '2px solid #FF3B30' }}>
                    <h4 style={{ margin: 0, textAlign: 'center', fontWeight: 'bold', fontSize: '16px' }}>
                      TOTAL LIABILITIES
                    </h4>
                    <div style={{ textAlign: 'center', fontSize: '18px', fontWeight: 'bold', marginTop: '10px' }}>
                      {formatCurrency(reportData.total_liabilities || 0)}
                    </div>
                  </div>
                </div>

                {/* ASSETS SIDE */}
                <div>
                  <h4 style={{ color: '#007AFF', marginBottom: '15px', borderBottom: '3px solid #007AFF', paddingBottom: '8px', fontSize: '18px', fontWeight: 'bold' }}>
                     ASSETS
                  </h4>

                  {/* A. Fixed Assets */}
                  <div style={{ marginBottom: '20px' }}>
                    <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>A. Fixed Assets</h5>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Particulars</th>
                            <th style={{ textAlign: 'right' }}>Amount ()</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.fixed_assets && reportData.fixed_assets.length > 0 ? (
                            reportData.fixed_assets.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.name}</td>
                                <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No fixed assets recorded</td>
                            </tr>
                          )}
                        </tbody>
                        <tfoot>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                            <td>Net Fixed Assets</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(reportData.total_fixed_assets || 0)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* B. Investments */}
                  <div style={{ marginBottom: '20px' }}>
                    <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>B. Investments</h5>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Particulars</th>
                            <th style={{ textAlign: 'right' }}>Amount ()</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.investments && reportData.investments.length > 0 ? (
                            reportData.investments.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.name}</td>
                                <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No investments recorded</td>
                            </tr>
                          )}
                        </tbody>
                        <tfoot>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                            <td>Total Investments</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(reportData.total_investments || 0)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* C. Current Assets */}
                  <div style={{ marginBottom: '20px' }}>
                    <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>C. Current Assets</h5>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Particulars</th>
                            <th style={{ textAlign: 'right' }}>Amount ()</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.current_assets && reportData.current_assets.length > 0 ? (
                            reportData.current_assets.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.name}</td>
                                <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No current assets recorded</td>
                            </tr>
                          )}
                        </tbody>
                        <tfoot>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                            <td>Total Current Assets</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(reportData.total_current_assets || 0)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* TOTAL ASSETS */}
                  <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e6f3ff', borderRadius: '8px', border: '2px solid #007AFF' }}>
                    <h4 style={{ margin: 0, textAlign: 'center', fontWeight: 'bold', fontSize: '16px' }}>
                      TOTAL ASSETS
                    </h4>
                    <div style={{ textAlign: 'center', fontSize: '18px', fontWeight: 'bold', marginTop: '10px' }}>
                      {formatCurrency(reportData.total_assets || 0)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {reportData && selectedReport === 'profit-loss' && (
          <div className="settings-section" style={{ marginTop: '30px' }}>
            <h3>Income & Expenditure Report</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
              <div style={{ padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0, color: '#007AFF' }}>Total Income</h4>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#007AFF' }}>
                  {reportData.total_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div style={{ padding: '15px', backgroundColor: '#fff0f0', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0, color: '#FF3B30' }}>Total Expenditure</h4>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#FF3B30' }}>
                  {reportData.total_expenditure.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
            <div style={{ padding: '15px', backgroundColor: reportData.net_income >= 0 ? '#f0fff0' : '#fff0f0', borderRadius: '8px', marginBottom: '20px' }}>
              <h4 style={{ marginTop: 0 }}>Net Income / (Loss)</h4>
              <div style={{ fontSize: '28px', fontWeight: 'bold', color: reportData.net_income >= 0 ? '#34C759' : '#FF3B30' }}>
                {reportData.net_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>
            {reportData.income_items && reportData.income_items.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4>Income Details</h4>
                <div className="settings-table-container">
                  <table className="settings-table">
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Description</th>
                        <th style={{ textAlign: 'right' }}>Amount ()</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.income_items.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.account_code}</td>
                          <td>{item.account_name}</td>
                          <td style={{ textAlign: 'right' }}>{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f8ff', borderTop: '2px solid #007AFF' }}>
                        <td colSpan="2">Total Income</td>
                        <td style={{ textAlign: 'right', color: '#007AFF' }}>{reportData.total_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}
            {reportData.expenditure_items && reportData.expenditure_items.length > 0 && (
              <div>
                <h4>Expenditure Details</h4>
                <div className="settings-table-container">
                  <table className="settings-table">
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Description</th>
                        <th style={{ textAlign: 'right' }}>Amount ()</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.expenditure_items.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.account_code}</td>
                          <td>{item.account_name}</td>
                          <td style={{ textAlign: 'right' }}>{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ fontWeight: 'bold', backgroundColor: '#fff0f0', borderTop: '2px solid #FF3B30' }}>
                        <td colSpan="2">Total Expenditure</td>
                        <td style={{ textAlign: 'right', color: '#FF3B30' }}>{reportData.total_expenditure.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {reportData && selectedReport === 'cash-flow' && (
          <div className="settings-section" style={{ marginTop: '30px' }}>
            <h3>Receipts & Payments Report</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
              <div style={{ padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0, color: '#007AFF' }}>Receipts</h4>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#007AFF' }}>
                  {reportData.total_receipts.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div style={{ padding: '15px', backgroundColor: '#fff0f0', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0, color: '#FF3B30' }}>Payments</h4>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#FF3B30' }}>
                  {reportData.total_payments.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
            {reportData.receipts && reportData.receipts.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4>Receipts Details</h4>
                <div className="settings-table-container">
                  <table className="settings-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th style={{ textAlign: 'right' }}>Amount ()</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.receipts.map((item, idx) => (
                        <tr key={idx}>
                          <td>{new Date(item.date).toLocaleDateString()}</td>
                          <td>{item.description}</td>
                          <td style={{ textAlign: 'right' }}>{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {reportData.payments && reportData.payments.length > 0 && (
              <div>
                <h4>Payments Details</h4>
                <div className="settings-table-container">
                  <table className="settings-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th style={{ textAlign: 'right' }}>Amount ()</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.payments.map((item, idx) => (
                        <tr key={idx}>
                          <td>{new Date(item.date).toLocaleDateString()}</td>
                          <td>{item.description}</td>
                          <td style={{ textAlign: 'right' }}>{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {reportData && selectedReport === 'ledger' && (
          <div className="settings-section" style={{ marginTop: '30px' }}>
            {reportData.ledgers ? (
              // Bulk Ledger Rendering
              <div>
                <h3>Bulk Ledger Statements</h3>
                <div style={{ marginBottom: '20px', color: '#666' }}>
                  <strong>Period:</strong> {reportData.from_date} to {reportData.to_date} |
                  <strong> Total Accounts:</strong> {reportData.ledgers.length}
                </div>
                {reportData.ledgers.map((ledger, idx) => (
                  <div key={idx} style={{ marginBottom: '40px', borderBottom: '2px solid #eee', paddingBottom: '20px' }}>
                    <h4 style={{ color: '#d35400' }}>{ledger.account_code} - {ledger.account_name}</h4>
                    <div style={{ marginBottom: '10px', fontSize: '14px' }}>
                      <strong>Opening:</strong> {ledger.opening_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })} |
                      <strong> Closing:</strong> {ledger.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                    <div className="settings-table-container">
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Description</th>
                            <th>Reference</th>
                            <th style={{ textAlign: 'right' }}>Debit</th>
                            <th style={{ textAlign: 'right' }}>Credit</th>
                            <th style={{ textAlign: 'right' }}>Balance</th>
                            <th style={{ textAlign: 'center' }}>Attach.</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr style={{ backgroundColor: '#f9f9f9', fontStyle: 'italic' }}>
                            <td colSpan="5">Opening Balance</td>
                            <td style={{ textAlign: 'right' }}>{ledger.opening_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          </tr>
                          {ledger.entries.map((entry, eIdx) => (
                            <tr key={eIdx}>
                              <td>{entry.date}</td>
                              <td>{entry.description}</td>
                              <td>{entry.reference || '-'}</td>
                              <td style={{ textAlign: 'right' }}>{entry.debit > 0 ? `${entry.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                              <td style={{ textAlign: 'right' }}>{entry.credit > 0 ? `${entry.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                              <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{entry.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                              <td style={{ textAlign: 'center' }}>
                                {entry.has_attachment && (
                                  <button
                                    onClick={() => handleViewAttachment(entry.journal_entry_id)}
                                    style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '18px' }}
                                    title="View Attachment"
                                  >
                                    
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                            <td colSpan="3">Totals</td>
                            <td style={{ textAlign: 'right' }}>{ledger.total_debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                            <td style={{ textAlign: 'right' }}>{ledger.total_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                            <td style={{ textAlign: 'right' }}>Closing: {ledger.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              // Single Ledger Rendering (original logic)
              <div>
                <h3>Ledger Statement: {reportData.account_name} ({reportData.account_code})</h3>
                <div style={{ marginBottom: '15px', color: '#666' }}>
                  <strong>Period:</strong> {reportData.from_date} to {reportData.to_date} |
                  <strong> Opening Balance:</strong> {reportData.opening_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="settings-table-container">
                  <table className="settings-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Reference</th>
                        <th style={{ textAlign: 'right' }}>Debit</th>
                        <th style={{ textAlign: 'right' }}>Credit</th>
                        <th style={{ textAlign: 'right' }}>Balance</th>
                        <th style={{ textAlign: 'center' }}>Attach.</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ backgroundColor: '#f9f9f9', fontStyle: 'italic' }}>
                        <td colSpan="5">Opening Balance</td>
                        <td style={{ textAlign: 'right' }}>
                          {reportData.opening_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                      {reportData.entries && reportData.entries.length > 0 ? (
                        reportData.entries.map((entry, index) => (
                          <tr key={index}>
                            <td>{entry.date}</td>
                            <td>{entry.description}</td>
                            <td>{entry.reference || '-'}</td>
                            <td style={{ textAlign: 'right' }}>
                              {entry.debit > 0 ? `${entry.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              {entry.credit > 0 ? `${entry.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                            </td>
                            <td style={{ textAlign: 'right', fontWeight: 'bold' }}>
                              {entry.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {entry.has_attachment && (
                                <button
                                  onClick={() => handleViewAttachment(entry.journal_entry_id)}
                                  style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '18px' }}
                                  title="View Attachment"
                                >
                                  
                                </button>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                            No transactions found for this period
                          </td>
                        </tr>
                      )}
                      <tr style={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                        <td colSpan="3">Total Movements</td>
                        <td style={{ textAlign: 'right' }}>
                          {reportData.total_debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {reportData.total_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          Closing: {reportData.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <VoucherAttachmentsModal
        isOpen={showAttachments}
        onClose={() => setShowAttachments(false)}
        journalEntryId={activeVoucherId}
      />

      <div className="settings-section">
        <h3>Recent Reports</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Report Type</th>
                <th>Generated On</th>
                <th>Period</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recentReports.length > 0 ? (
                recentReports.map((report) => (
                  <tr key={report.id}>
                    <td>{report.label}</td>
                    <td>{report.generatedOn}</td>
                    <td>{report.period}</td>
                    <td>
                      <button
                        className="settings-action-btn"
                        onClick={() => handleViewRecentReport(report)}
                        disabled={loading}
                      >
                        View
                      </button>
                      <button
                        className="settings-action-btn"
                        onClick={() => handleExportPDF(report.type, report.params)}
                        disabled={loading}
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                    No recent reports generated yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AccountingScreen;



