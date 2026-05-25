/**
 * GruhaMitra Settings Screen
 * Master control panel with 14 sub-modules
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import settingsService from '../services/settingsService';
import flatsService from '../services/flatsService';
import memberOnboardingService from '../services/memberOnboardingService';
import financialYearService from '../services/financialYearService';
import api from '../services/api';
import onboardingImportService from '../services/onboardingImportService';
import { authService } from '../services/authService';

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

const uploadSocietyLogoWithFallback = async (file) => {
  if (typeof settingsService.uploadSocietyLogo === 'function') {
    return settingsService.uploadSocietyLogo(file);
  }

  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/society/upload-logo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

const uploadSocietyDocumentWithFallback = async (file, documentType = 'other') => {
  if (typeof settingsService.uploadSocietyDocument === 'function') {
    return settingsService.uploadSocietyDocument(file, documentType);
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);
  const response = await api.post('/society/upload-document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

const extractDocumentFileName = (url) => {
  if (!url || typeof url !== 'string') return '';
  const marker = '/society/documents/';
  const idx = url.indexOf(marker);
  const raw = idx >= 0 ? url.slice(idx + marker.length) : url.split('/').pop();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch (error) {
    return raw;
  }
};

const normalizeDocumentEndpoint = (url) => {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (raw.startsWith('/api/v1/')) return raw.replace('/api/v1', '');
  if (raw.startsWith('/v1/')) return raw.replace('/v1', '');
  return raw;
};

const SettingsScreen = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('society-profile');

  const settingsTabs = [
    { id: 'society-profile', label: 'Society Profile', icon: 'SP' },
    { id: 'flats-blocks', label: 'Flats & Blocks', icon: 'FB' },
    { id: 'member-config', label: 'Member Configuration', icon: 'MC' },
    { id: 'billing-rules', label: 'Billing Rules', icon: 'BR' },
    { id: 'late-fee', label: 'Late Fee & Penalties', icon: 'LF' },
    { id: 'accounting', label: 'Accounting Settings', icon: 'AC' },
    { id: 'payment-gateway', label: 'Payment Gateway', icon: 'PG' },
    { id: 'notifications', label: 'Notifications', icon: 'NT' },
    { id: 'roles', label: 'Roles & Permissions', icon: 'RP' },
    { id: 'complaints', label: 'Complaints & Helpdesk', icon: 'CH' },
    { id: 'assets', label: 'Assets & Vendors', icon: 'AV' },
    { id: 'legal', label: 'Legal & Compliance', icon: 'LC' },
    { id: 'data-security', label: 'Data & Security', icon: 'DS' },
    { id: 'multi-society', label: 'Multi-Society Mode', icon: 'MS' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'society-profile':
        return <SocietyProfileTab />;
      case 'flats-blocks':
        return <FlatsBlocksTab />;
      case 'member-config':
        return <MemberConfigTab />;
      case 'billing-rules':
        return <BillingRulesTab />;
      case 'late-fee':
        return <LateFeeTab />;
      case 'accounting':
        return <AccountingTab />;
      case 'payment-gateway':
        return <PaymentGatewayTab />;
      case 'notifications':
        return <NotificationsTab />;
      case 'roles':
        return <RolesTab />;
      case 'complaints':
        return <ComplaintsTab />;
      case 'assets':
        return <AssetsTab />;
      case 'legal':
        return <LegalTab />;
      case 'data-security':
        return <DataSecurityTab />;
      case 'multi-society':
        return <MultiSocietyTab />;
      default:
        return <SocietyProfileTab />;
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-header-title">Settings</h1>
          <span className="dashboard-header-subtitle">Master Control Panel</span>
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
            <h3>Settings Menu</h3>
          </div>
          <nav className="settings-nav">
            {settingsTabs.map((tab) => (
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

// Tab Components
const SocietyProfileTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    society_name: '',
    registration_number: '',
    registration_date: '',
    pan: '',
    gst_number: '',
    address: '',
    city: '',
    state: '',
    pin_code: '',
    contact_email: '',
    contact_phone: '',
    bank_account_number: '',
    bank_account_name: '',
    bank_ifsc: '',
    bank_name: '',
    financial_year_start: 'apr-mar',
    logo_url: '',
  });

  const [logoFile, setLogoFile] = useState(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          society_name: settings.society_name || '',
          registration_number: settings.registration_number || '',
          registration_date: '', // Not in API response
          pan: '', // Not in API response
          gst_number: settings.gst_number || '',
          address: settings.society_address || '',
          city: settings.city || '',
          state: settings.state || '',
          pin_code: settings.pin_code || '',
          contact_email: settings.contact_email || '',
          contact_phone: settings.contact_phone || '',
          bank_account_number: settings.bank_accounts?.[0]?.account_number || '',
          bank_account_name: settings.bank_accounts?.[0]?.account_name || '',
          bank_ifsc: settings.bank_accounts?.[0]?.ifsc_code || '',
          bank_name: settings.bank_accounts?.[0]?.bank_name || '',
          financial_year_start: settings.financial_year_start || 'apr-mar',
          logo_url: settings.logo_url || '',
        });
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to load settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const handleLogoUpload = async () => {
    if (!logoFile) {
      setMessage({ type: 'error', text: 'Please select a logo file first' });
      return;
    }

    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(logoFile.type)) {
      setMessage({ type: 'error', text: 'Only PNG and JPG files are allowed' });
      return;
    }

    if (logoFile.size > 2 * 1024 * 1024) {
      setMessage({ type: 'error', text: 'Logo file must be less than 2MB' });
      return;
    }

    setUploadingLogo(true);
    setMessage({ type: 'info', text: 'Uploading logo...' });

    try {
      const result = await uploadSocietyLogoWithFallback(logoFile);
      setMessage({ type: 'success', text: 'Logo uploaded successfully!' });

      if (result.logo_url) {
        setFormData(prev => ({ ...prev, logo_url: result.logo_url }));
      }

      setLogoFile(null);
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Logo upload failed:', error);
      setMessage({ type: 'error', text: 'Upload failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    if (!formData.society_name.trim()) {
      setMessage({ type: 'error', text: 'Society Name is required' });
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const settingsData = {
        society_name: formData.society_name.trim(),
        registration_number: formData.registration_number.trim() || undefined,
        society_address: formData.address.trim() || undefined,
        city: formData.city.trim() || undefined,
        state: formData.state.trim() || undefined,
        pin_code: formData.pin_code.trim() || undefined,
        pan_no: formData.pan.trim() || undefined,
        contact_email: formData.contact_email.trim() || undefined,
        contact_phone: formData.contact_phone.trim() || undefined,
        gst_number: formData.gst_number.trim() || undefined,
        logo_url: formData.logo_url.trim() || undefined,
      };

      // Add bank account if provided
      if (formData.bank_account_number || formData.bank_ifsc || formData.bank_name) {
        settingsData.bank_accounts = [{
          account_name: (formData.bank_account_name || formData.society_name).trim(),
          account_number: formData.bank_account_number.trim(),
          ifsc_code: formData.bank_ifsc.trim(),
          bank_name: formData.bank_name.trim(),
        }];
      }

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Society profile saved successfully!' });

      // Keep header/UI in sync without requiring logout/login.
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser && authService.updateStoredUser) {
          await authService.updateStoredUser({
            ...currentUser,
            society_name: settingsData.society_name,
          });
        }
      } catch (syncError) {
        console.warn('Could not sync updated society name to local user cache:', syncError);
      }

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Society Profile</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading society profile...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Society Profile</h2>
      <p className="settings-tab-description">Basic legal & identity information</p>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{message.type === 'success' ? '' : ''}</span>
          <span>{message.text}</span>
        </div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-form-group">
          <label>Society Name *</label>
          <input
            type="text"
            placeholder="Enter society name"
            value={formData.society_name}
            onChange={(e) => setFormData(prev => ({ ...prev, society_name: e.target.value }))}
            required
          />
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Registration Number</label>
            <input
              type="text"
              placeholder="Registration number"
              value={formData.registration_number}
              onChange={(e) => setFormData(prev => ({ ...prev, registration_number: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Registration Date</label>
            <input
              type="date"
              value={formData.registration_date}
              onChange={(e) => setFormData(prev => ({ ...prev, registration_date: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>PAN</label>
            <input
              type="text"
              placeholder="PAN number"
              maxLength="10"
              value={formData.pan}
              onChange={(e) => setFormData(prev => ({ ...prev, pan: e.target.value.toUpperCase() }))}
            />
          </div>
          <div className="settings-form-group">
            <label>GST (if applicable)</label>
            <input
              type="text"
              placeholder="GST number"
              value={formData.gst_number}
              onChange={(e) => setFormData(prev => ({ ...prev, gst_number: e.target.value.toUpperCase() }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Address</label>
          <textarea
            rows="3"
            placeholder="Complete address"
            value={formData.address}
            onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
          ></textarea>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>City</label>
            <input
              type="text"
              placeholder="City"
              value={formData.city}
              onChange={(e) => setFormData(prev => ({ ...prev, city: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>State</label>
            <input
              type="text"
              placeholder="State"
              value={formData.state}
              onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>PIN Code</label>
            <input
              type="text"
              placeholder="PIN"
              maxLength="6"
              value={formData.pin_code}
              onChange={(e) => setFormData(prev => ({ ...prev, pin_code: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Contact Email</label>
            <input
              type="email"
              placeholder="society@example.com"
              value={formData.contact_email}
              onChange={(e) => setFormData(prev => ({ ...prev, contact_email: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Contact Phone</label>
            <input
              type="tel"
              placeholder="+91 9876543210"
              value={formData.contact_phone}
              onChange={(e) => setFormData(prev => ({ ...prev, contact_phone: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Bank Account Details</label>
          <div className="settings-form-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            <input
              type="text"
              placeholder="Account Name (e.g. Society Name)"
              value={formData.bank_account_name}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_account_name: e.target.value }))}
            />
            <input
              type="text"
              placeholder="Account Number"
              value={formData.bank_account_number}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_account_number: e.target.value }))}
            />
            <input
              type="text"
              placeholder="IFSC Code"
              value={formData.bank_ifsc}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_ifsc: e.target.value.toUpperCase() }))}
            />
            <input
              type="text"
              placeholder="Bank Name"
              value={formData.bank_name}
              onChange={(e) => setFormData(prev => ({ ...prev, bank_name: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-form-group">
          <label>Society Logo</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg"
            onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
          />
          <button
            type="button"
            onClick={handleLogoUpload}
            disabled={!logoFile || uploadingLogo}
            className="settings-action-btn"
            style={{
              marginTop: '10px',
              backgroundColor: uploadingLogo ? '#ccc' : '#4CAF50',
              cursor: uploadingLogo || !logoFile ? 'not-allowed' : 'pointer',
            }}
          >
            {uploadingLogo ? 'Uploading...' : 'Upload Logo'}
          </button>
          <small>Upload society logo (PNG, JPG, max 2MB). The logo will appear on receipts and reports.</small>
        </div>

        <div className="settings-form-group">
          <label>Financial Year Start</label>
          <select
            value={formData.financial_year_start}
            onChange={(e) => setFormData(prev => ({ ...prev, financial_year_start: e.target.value }))}
          >
            <option value="apr-mar">April - March</option>
            <option value="jan-dec">January - December</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <div className="settings-form-actions">
          <button
            type="submit"
            className="settings-save-btn"
            disabled={saving}
            style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            className="settings-cancel-btn"
            onClick={() => loadSettings()}
            disabled={saving}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

const FlatsBlocksTab = () => {
  const [flats, setFlats] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [debugMessages, setDebugMessages] = useState([]);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [blocksConfig, setBlocksConfig] = useState([]);
  const [editingBlock, setEditingBlock] = useState(null);

  const addDebugMessage = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugMessages(prev => [...prev.slice(-19), { timestamp, message, type }]);
  };

  const sanitizeBlocksConfig = (blocks) => {
    if (!Array.isArray(blocks)) return [];
    return blocks
      .filter((entry) => entry && typeof entry === 'object')
      .map((entry, index) => {
        const name = String(entry.name || String.fromCharCode(65 + (index % 26)))
          .trim()
          .toUpperCase()
          .slice(0, 10) || 'A';
        const floors = Math.max(1, Math.min(200, parseInt(entry.floors, 10) || 1));
        const flatsPerFloor = Math.max(1, Math.min(200, parseInt(entry.flatsPerFloor, 10) || 1));
        const fromArray = Array.isArray(entry.flatsByFloor)
          ? entry.flatsByFloor
          : [];
        const fromText = !fromArray.length && typeof entry.flatsByFloorText === 'string'
          ? parseFlatsByFloorInput(entry.flatsByFloorText)
          : [];
        const flatsByFloor = (fromArray.length ? fromArray : fromText)
          .map((n) => Math.max(1, Math.min(200, parseInt(n, 10) || 0)))
          .filter((n) => n > 0)
          .slice(0, floors);
        return {
          name,
          floors,
          flatsPerFloor,
          flatsByFloor,
          customPerFloor: flatsByFloor.length > 0,
        };
      });
  };

  const parseFlatsByFloorInput = (value) => {
    if (!value || !String(value).trim()) return [];
    return String(value)
      .split(',')
      .map((n) => parseInt(n.trim(), 10))
      .filter((n) => Number.isInteger(n) && n > 0)
      .slice(0, 200);
  };

  const blockTotalFlats = (block) => {
    const custom = Array.isArray(block?.flatsByFloor) && block.flatsByFloor.length > 0
      ? block.flatsByFloor
      : parseFlatsByFloorInput(block?.flatsByFloorText || '');
    if (custom.length > 0) {
      return custom.reduce((sum, n) => sum + (parseInt(n, 10) || 0), 0);
    }
    return (parseInt(block?.floors, 10) || 0) * (parseInt(block?.flatsPerFloor, 10) || 0);
  };

  const ensureCustomFloorCounts = (block) => {
    const floors = Math.max(1, parseInt(block?.floors, 10) || 1);
    const fallback = Math.max(1, parseInt(block?.flatsPerFloor, 10) || 1);
    const current = Array.isArray(block?.flatsByFloor) ? block.flatsByFloor : [];
    const next = [];
    for (let i = 0; i < floors; i += 1) {
      const parsed = parseInt(current[i], 10);
      next.push(Number.isInteger(parsed) && parsed > 0 ? Math.min(parsed, 200) : fallback);
    }
    return next;
  };

  // Flat form state
  const [flatForm, setFlatForm] = useState({
    flat_number: '',
    area_sqft: '',
    flat_type: '',
    status: 'Vacant',
    parking_slots: '',
  });

  useEffect(() => {
    loadData();
    loadBlocksConfig();
  }, []);

  // Debug effect to log when members/flats are loaded
  useEffect(() => {
    if (members.length > 0 && flats.length > 0) {
      const a304Member = members.find(m => {
        const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
        return mFlat === 'A-304';
      });
      const a304Flat = flats.find(f => {
        const fFlat = (f.flat_number || f.flatNumber || '').trim().toUpperCase();
        return fFlat === 'A-304';
      });

      console.log(' A-304 Data Check:', {
        member: a304Member,
        flat: a304Flat,
        allMembersCount: members.length,
        allFlatsCount: flats.length,
        memberFlatNumbers: members.map(m => (m.flat_number || m.flatNumber || '').trim().toUpperCase()).slice(0, 5),
        flatNumbers: flats.map(f => (f.flat_number || f.flatNumber || '').trim().toUpperCase()).slice(0, 5)
      });
    }
  }, [members, flats]);

  const loadBlocksConfig = async () => {
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings && settings.blocks_config) {
        const normalized = sanitizeBlocksConfig(settings.blocks_config);
        setBlocksConfig(normalized);
        addDebugMessage(` Loaded blocks config: ${JSON.stringify(normalized)}`, 'success');
      } else {
        setBlocksConfig([]);
        addDebugMessage(' No blocks config found', 'warning');
      }
    } catch (error) {
      console.error('Error loading blocks config:', error);
      addDebugMessage(` Error loading blocks config: ${error.message}`, 'error');
      setBlocksConfig([]);
    }
  };

  const handleSaveBlocksConfig = async (nextBlocksConfig = blocksConfig) => {
    const uiBlocks = sanitizeBlocksConfig(nextBlocksConfig);
    setBlocksConfig(uiBlocks);
    const payloadBlocks = uiBlocks.map((block) => ({
      name: block.name,
      floors: block.floors,
      flatsPerFloor: block.flatsPerFloor,
      flatsByFloor: block.customPerFloor ? (block.flatsByFloor || []).slice(0, block.floors) : [],
    }));
    setSaving(true);
    try {
      await settingsService.saveSocietySettings({
        blocks_config: payloadBlocks
      });
      addDebugMessage('Blocks configuration saved successfully!', 'success');
      alert('Blocks configuration saved successfully!');
    } catch (error) {
      console.error('Error saving blocks config:', error);
      const saveError = getErrorMessage(error);
      addDebugMessage(`Error saving blocks config: ${saveError}`, 'error');
      alert(`Failed to save blocks configuration: ${saveError}`);
      setSaving(false);
      return;
    }

    try {
      // Reload flats after save; reload issues should not report as save failure.
      await loadData();
    } catch (reloadError) {
      const reloadMessage = getErrorMessage(reloadError);
      addDebugMessage(`Saved, but refresh failed: ${reloadMessage}`, 'warning');
      alert(`Blocks saved, but refresh failed: ${reloadMessage}`);
    } finally {
      setSaving(false);
    }
  };

  const handleEditBlock = (index) => {
    setEditingBlock(index);
  };

  const handleUpdateBlock = (index, field, value) => {
    const updated = [...blocksConfig];
    const next = { ...updated[index], [field]: value };
    if (field === 'floors') {
      const floors = Math.max(1, parseInt(value, 10) || 1);
      if (next.customPerFloor) {
        next.flatsByFloor = ensureCustomFloorCounts({ ...next, floors });
      }
    }
    if (field === 'customPerFloor') {
      if (value) {
        next.flatsByFloor = ensureCustomFloorCounts(next);
      } else {
        next.flatsByFloor = [];
      }
    }
    updated[index] = next;
    setBlocksConfig(updated);
  };

  const handleCustomFloorCountChange = (blockIndex, floorIndex, value) => {
    const updated = [...blocksConfig];
    const block = { ...updated[blockIndex] };
    const counts = ensureCustomFloorCounts(block);
    counts[floorIndex] = Math.max(1, Math.min(200, parseInt(value, 10) || 1));
    block.flatsByFloor = counts;
    block.customPerFloor = true;
    updated[blockIndex] = block;
    setBlocksConfig(updated);
  };

  const handleSaveBlock = (index) => {
    setEditingBlock(null);
    // Auto-save when editing is done
    handleSaveBlocksConfig();
  };

  const handleAddBlock = () => {
    const newBlock = {
      name: String.fromCharCode(65 + blocksConfig.length),
      floors: 4,
      flatsPerFloor: 5,
      flatsByFloor: [],
      customPerFloor: false,
    };
    setBlocksConfig([...blocksConfig, newBlock]);
    setEditingBlock(blocksConfig.length);
  };

  const handleDeleteBlock = async (index) => {
    if (!confirm('Are you sure you want to delete this block? This will also delete all flats in this block.')) {
      return;
    }
    const updated = blocksConfig.filter((_, i) => i !== index);
    setBlocksConfig(updated);
    await handleSaveBlocksConfig(updated);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // Load flats and members separately to handle errors better
      let flatsList = [];
      let membersList = [];

      try {
        flatsList = await flatsService.getFlats();
        const count = flatsList?.length || 0;
        console.log(' Flats loaded:', count, 'flats');
        addDebugMessage(` Loaded ${count} flats successfully`, 'success');
        // Ensure flatsList is an array
        if (!Array.isArray(flatsList)) {
          console.warn(' Flats response is not an array:', flatsList);
          addDebugMessage(` Flats response is not an array: ${JSON.stringify(flatsList)}`, 'warning');
          flatsList = [];
        }
        // Debug: Check if flats have ID field
        if (flatsList.length > 0) {
          const sampleFlat = flatsList[0];
          console.log(' Sample flat structure:', {
            hasId: 'id' in sampleFlat,
            has_id: '_id' in sampleFlat,
            idValue: sampleFlat.id || sampleFlat._id,
            allKeys: Object.keys(sampleFlat),
            flatNumber: sampleFlat.flat_number
          });
          addDebugMessage(` Sample flat keys: ${Object.keys(sampleFlat).join(', ')}`, 'info');
          if (!sampleFlat.id && !sampleFlat._id) {
            console.error(' WARNING: Flats are missing ID field!');
            addDebugMessage(' WARNING: Flats are missing ID field!', 'error');
          }
        }
      } catch (flatsError) {
        console.error(' Error loading flats:', flatsError);
        const flatsErrorMsg = flatsError.response?.data?.detail || flatsError.message || 'Failed to load flats';
        const errorDetails = {
          status: flatsError.response?.status,
          data: flatsError.response?.data,
          message: flatsErrorMsg,
          url: flatsError.config?.url
        };
        console.error('Flats error details:', errorDetails);
        addDebugMessage(` Error loading flats: ${flatsErrorMsg}`, 'error');
        addDebugMessage(`Details: Status ${errorDetails.status}, URL: ${errorDetails.url}`, 'error');
        // Continue even if flats fail - show error but don't block
        console.warn(`Warning: Could not load flats. ${flatsErrorMsg}`);
        flatsList = []; // Set to empty array on error
      }

      try {
        membersList = await memberOnboardingService.listMembers();
        console.log(' Members loaded:', membersList?.length || 0, 'members');
        // Ensure membersList is an array
        if (!Array.isArray(membersList)) {
          console.warn(' Members response is not an array:', membersList);
          membersList = [];
        }
      } catch (membersError) {
        console.error(' Error loading members:', membersError);
        const membersErrorMsg = membersError.response?.data?.detail || membersError.message || 'Failed to load members';
        console.error('Members error details:', {
          status: membersError.response?.status,
          data: membersError.response?.data,
          message: membersErrorMsg
        });
        // Continue even if members fail - show error but don't block
        console.warn(`Warning: Could not load members. ${membersErrorMsg}`);
        membersList = []; // Set to empty array on error
      }

      setFlats(flatsList || []);
      setMembers(membersList || []);

      // Debug: Log A-304 data after loading
      if (membersList && membersList.length > 0) {
        const a304Member = membersList.find(m => {
          const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
          return mFlat === 'A-304';
        });
        console.log(' After Loading - A-304 Member:', a304Member);
        if (a304Member) {
          addDebugMessage(` Found A-304 member: ${a304Member.name} (${a304Member.status})`, 'success');
        } else {
          addDebugMessage(` A-304 member not found in ${membersList.length} members`, 'warning');
          console.log('All member flat numbers:', membersList.map(m => (m.flat_number || m.flatNumber || 'N/A')));
        }
      }
    } catch (error) {
      console.error(' Unexpected error loading data:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to load data. Please check your connection and try again.';
      console.error('Unexpected error:', errorMsg);
      setFlats([]);
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  // Convert bedrooms to BHK format
  const bedroomsToBHK = (bedrooms) => {
    if (!bedrooms) return '';
    if (bedrooms === 1) return '1 BHK';
    if (bedrooms === 2) return '2 BHK';
    if (bedrooms === 3) return '3 BHK';
    if (bedrooms === 4) return '4 BHK';
    return `${bedrooms} BHK`;
  };

  // Convert BHK to bedrooms number
  const bhkToBedrooms = (bhk) => {
    if (!bhk) return null;
    const match = bhk.match(/^(\d+)\s*BHK/i);
    return match ? parseInt(match[1]) : null;
  };

  // Auto-generate parking slot from flat number
  // Examples: A-101  "101", A-102  "102", A-201  "201", A-302  "302"
  const generateParkingSlot = (flatNumber) => {
    if (!flatNumber) return '';
    // Extract numeric part after dash/hyphen
    // Matches patterns like: A-101, 1-201, A-302, etc.
    const match = flatNumber.match(/[-_](\d+)$/);
    if (match) {
      return match[1]; // Return the numeric part
    }
    // If no dash found, try to extract any trailing numbers
    const numMatch = flatNumber.match(/(\d+)$/);
    return numMatch ? numMatch[1] : '';
  };

  // Auto-fill flat details when flat number changes
  const handleFlatNumberChange = (flatNumber) => {
    setFlatForm(prev => ({ ...prev, flat_number: flatNumber }));

    if (!flatNumber.trim()) {
      // Clear form if flat number is empty
      setFlatForm({
        flat_number: '',
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: '',
      });
      return;
    }

    // Normalize flat number for comparison
    const normalizedFlatNumber = flatNumber.trim().toUpperCase();

    // Find existing flat - handle both flat_number and flatNumber field names
    const existingFlat = flats.find(f => {
      const fFlatNumber = (f.flat_number || f.flatNumber || '').trim().toUpperCase();
      return fFlatNumber === normalizedFlatNumber;
    });

    // Find existing member for this flat - use same logic as table display
    const existingMember = members.find(m => {
      const memberFlatNumber = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
      const isActive = m.status === 'active';
      const hasNoMoveOut = !m.move_out_date || new Date(m.move_out_date) > new Date();

      return memberFlatNumber === normalizedFlatNumber && isActive && hasNoMoveOut;
    });

    if (existingFlat || existingMember) {
      // Get flat data - prefer existing flat, otherwise find flat by member's flat_id
      let flatData = existingFlat;
      if (!flatData && existingMember) {
        flatData = flats.find(f => f.id === existingMember.flat_id || f.flat_number === existingMember.flat_number);
      }

      // Auto-fill form from existing data
      const trimmedFlatNumber = flatNumber.trim();
      const autoParkingSlot = generateParkingSlot(trimmedFlatNumber);

      // Ensure area_sqft is properly loaded - use flatData.area_sqft if it exists (even if 0)
      const loadedArea = flatData && flatData.area_sqft !== undefined && flatData.area_sqft !== null
        ? String(flatData.area_sqft)
        : '';

      console.log(' Loading flat data:', {
        flatNumber: trimmedFlatNumber,
        flatData: flatData,
        area_sqft: flatData?.area_sqft,
        loadedArea: loadedArea
      });
      addDebugMessage(` Loading flat: ${trimmedFlatNumber}, Area: ${loadedArea || 'N/A'}`, 'info');

      setFlatForm(prev => ({
        ...prev,
        flat_number: trimmedFlatNumber,
        area_sqft: loadedArea, // Always use loaded area, even if empty
        flat_type: flatData?.bedrooms ? bedroomsToBHK(flatData.bedrooms) : '',
        status: existingMember
          ? (existingMember.member_type === 'owner' ? 'Owner Occupied' : 'Tenant')
          : (flatData?.occupancy_status === 'OWNER_OCCUPIED' ? 'Owner Occupied' :
            flatData?.occupancy_status === 'TENANT_OCCUPIED' ? 'Tenant' : 'Vacant'),
        parking_slots: (flatData?.parking_slots ? String(flatData.parking_slots) : autoParkingSlot),
      }));
    } else {
      // Flat doesn't exist yet, keep flat number but clear other fields
      const trimmedFlatNumber = flatNumber.trim();
      const autoParkingSlot = generateParkingSlot(trimmedFlatNumber);

      setFlatForm(prev => ({
        ...prev,
        flat_number: trimmedFlatNumber,
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: autoParkingSlot, // Auto-generate parking slot from flat number
      }));
    }
  };

  const handleAddFlat = async (e) => {
    // Prevent form submission if called from a form
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    console.log(' handleAddFlat called', {
      flatForm,
      saving,
      loading,
      flatNumber: flatForm.flat_number,
      areaSqft: flatForm.area_sqft
    });
    addDebugMessage(' Button clicked - handleAddFlat called', 'info');
    addDebugMessage(`Form data: Flat=${flatForm.flat_number}, Area=${flatForm.area_sqft}`, 'info');

    if (!flatForm.flat_number.trim()) {
      addDebugMessage(' Validation: Please enter flat number', 'error');
      alert('Please enter flat number');
      return;
    }
    if (!flatForm.area_sqft || parseFloat(flatForm.area_sqft) <= 0) {
      addDebugMessage(' Validation: Please enter valid flat size', 'error');
      alert('Please enter valid flat size');
      return;
    }

    setSaving(true);
    addDebugMessage(` Starting save operation for flat: ${flatForm.flat_number.trim()}`, 'info');
    try {
      const bedrooms = bhkToBedrooms(flatForm.flat_type);

      // Check if flat already exists
      // Handle both 'id' and '_id' field names (backend model uses alias)
      const existingFlat = flats.find(f => {
        const flatNum = f.flat_number || f.flatNumber;
        return flatNum === flatForm.flat_number.trim();
      });

      console.log(' Searching for flat:', {
        searchNumber: flatForm.flat_number.trim(),
        totalFlats: flats.length,
        flatNumbers: flats.map(f => ({
          number: f.flat_number || f.flatNumber,
          id: f.id || f._id,
          hasId: !!(f.id || f._id)
        })),
        found: existingFlat ? 'YES' : 'NO',
        foundFlat: existingFlat
      });
      addDebugMessage(` Searching for flat: ${flatForm.flat_number.trim()}, Found: ${existingFlat ? 'YES' : 'NO'}`, 'info');

      if (existingFlat) {
        // Get ID - handle both 'id' and '_id' field names
        const flatId = existingFlat.id || existingFlat._id;

        // Update existing flat
        console.log(' Existing flat data:', {
          id: flatId,
          idType: typeof flatId,
          hasId: !!existingFlat.id,
          has_id: !!existingFlat._id,
          flat_number: existingFlat.flat_number || existingFlat.flatNumber,
          area_sqft: existingFlat.area_sqft || existingFlat.areaSqft,
          allKeys: Object.keys(existingFlat)
        });
        addDebugMessage(` Found flat - ID: ${flatId}, Type: ${typeof flatId}`, 'info');

        if (!flatId && flatId !== 0 && flatId !== '0') {
          addDebugMessage(` Error: Flat found but ID is missing. Flat data: ${JSON.stringify(existingFlat)}`, 'error');
          addDebugMessage(`Available keys: ${Object.keys(existingFlat).join(', ')}`, 'error');
          alert('Error: Flat ID is missing. Please refresh the page and try again.');
          return;
        }

        const updateData = {
          area_sqft: parseFloat(flatForm.area_sqft),
          parking_slots: (flatForm.parking_slots || '').trim() || null,
        };

        if (bedrooms) {
          updateData.bedrooms = bedrooms;
        }

        // Use the ID we extracted (handles both 'id' and '_id')
        const flatIdToUpdate = flatId;

        console.log(' Updating flat:', {
          flatId: flatIdToUpdate,
          flatNumber: existingFlat.flat_number || existingFlat.flatNumber,
          updateData: updateData
        });
        addDebugMessage(` Updating flat ID: ${flatIdToUpdate}, Number: ${existingFlat.flat_number || existingFlat.flatNumber}`, 'info');

        // Note: occupancy_status update might need to be done separately via member onboarding
        // For now, we'll update what we can through the flat update endpoint
        await flatsService.updateFlat(flatIdToUpdate, updateData);
        addDebugMessage(` Flat "${existingFlat.flat_number}" updated successfully!`, 'success');
        alert('Flat updated successfully!');
      } else {
        // Create new flat - backend requires owner_name, so use a placeholder
        const flatData = {
          flat_number: flatForm.flat_number.trim(),
          area_sqft: parseFloat(flatForm.area_sqft),
          bedrooms: bedrooms || 2, // Default to 2 if not specified
          parking_slots: (flatForm.parking_slots || '').trim() || null,
          occupants: 1,
          owner_name: 'To be assigned', // Required field, will be updated when member is onboarded
        };

        console.log(' Creating flat with data:', flatData);
        addDebugMessage(` Creating flat: ${flatData.flat_number}`, 'info');
        const createdFlat = await flatsService.createFlat(flatData);
        console.log(' Flat created successfully:', createdFlat);
        addDebugMessage(` Flat "${flatForm.flat_number.trim()}" created successfully!`, 'success');
        alert(`Flat "${flatForm.flat_number.trim()}" added successfully!`);
      }

      // Reload data and reset form
      await loadData();
      setFlatForm({
        flat_number: '',
        area_sqft: '',
        flat_type: '',
        status: 'Vacant',
        parking_slots: '',
      });
    } catch (error) {
      console.error(' Error saving flat:', error);
      const errorDetails = {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url,
        requestData: error.config?.data
      };
      console.error('Error details:', errorDetails);
      addDebugMessage(` Error saving flat: ${error.message}`, 'error');
      if (error.response?.data) {
        addDebugMessage(`Response: ${JSON.stringify(error.response.data)}`, 'error');
      }
      const errorMsg = getErrorMessage(error) || 'Failed to save flat';
      if (Array.isArray(errorMsg)) {
        const validationErrors = errorMsg.map(e => typeof e === 'object' ? e.msg || e.message : e).join('\n');
        addDebugMessage(`Validation Errors: ${validationErrors}`, 'error');
        alert(`Validation Error:\n${validationErrors}`);
      } else {
        addDebugMessage(`Full Error: ${errorMsg}`, 'error');
        alert(`Error: ${errorMsg}\n\nCheck the Debug Panel below for details.`);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Flats & Blocks Setup</h2>
      <p className="settings-tab-description">Physical structure of the society</p>

      <div className="settings-section">
        <h3>Blocks / Wings</h3>
        <div style={{ marginBottom: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className="settings-add-btn"
            onClick={handleAddBlock}
            disabled={saving}
          >
            + Add Block
          </button>
          {blocksConfig.length > 0 && (
            <button
              className="settings-save-btn"
              onClick={() => handleSaveBlocksConfig()}
              disabled={saving}
              style={{ marginLeft: '10px' }}
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          )}
        </div>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Block/Wing</th>
                <th>Floors</th>
                <th>Flats per Floor</th>
                <th>Total Flats</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {blocksConfig.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
                    No blocks configured. Click "+ Add Block" to add one.
                  </td>
                </tr>
              ) : (
                blocksConfig.map((block, index) => {
                  const totalFlats = blockTotalFlats(block);
                  const isEditing = editingBlock === index;
                  return (
                    <tr key={index}>
                      <td>
                        {isEditing ? (
                          <input
                            type="text"
                            value={block.name}
                            onChange={(e) => handleUpdateBlock(index, 'name', e.target.value)}
                            style={{ width: '60px', padding: '4px' }}
                            maxLength="10"
                          />
                        ) : (
                          <strong>{block.name}</strong>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="number"
                            value={block.floors}
                            onChange={(e) => handleUpdateBlock(index, 'floors', parseInt(e.target.value) || 0)}
                            style={{ width: '80px', padding: '4px' }}
                            min="1"
                          />
                        ) : (
                          block.floors
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <button
                                type="button"
                                className="settings-action-btn"
                                style={{
                                  backgroundColor: block.customPerFloor ? '#f3f4f6' : '#007AFF',
                                  color: block.customPerFloor ? '#333' : 'white',
                                  borderColor: '#007AFF',
                                }}
                                onClick={() => handleUpdateBlock(index, 'customPerFloor', false)}
                              >
                                Uniform
                              </button>
                              <button
                                type="button"
                                className="settings-action-btn"
                                style={{
                                  backgroundColor: block.customPerFloor ? '#007AFF' : '#f3f4f6',
                                  color: block.customPerFloor ? 'white' : '#333',
                                  borderColor: '#007AFF',
                                }}
                                onClick={() => handleUpdateBlock(index, 'customPerFloor', true)}
                              >
                                Custom per floor
                              </button>
                            </div>
                            {!block.customPerFloor ? (
                              <input
                                type="number"
                                value={block.flatsPerFloor}
                                onChange={(e) => handleUpdateBlock(index, 'flatsPerFloor', parseInt(e.target.value, 10) || 0)}
                                style={{ width: '120px', padding: '4px' }}
                                min="1"
                              />
                            ) : (
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(84px, 1fr))', gap: '6px' }}>
                                {Array.from({ length: Math.max(1, parseInt(block.floors, 10) || 1) }).map((_, floorIdx) => (
                                  <label key={floorIdx} style={{ display: 'flex', flexDirection: 'column', fontSize: '12px', color: '#555' }}>
                                    Floor {floorIdx + 1}
                                    <input
                                      type="number"
                                      min="1"
                                      value={(block.flatsByFloor || [])[floorIdx] ?? block.flatsPerFloor}
                                      onChange={(e) => handleCustomFloorCountChange(index, floorIdx, e.target.value)}
                                      style={{ width: '100%', padding: '4px' }}
                                    />
                                  </label>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          block.customPerFloor && Array.isArray(block.flatsByFloor) && block.flatsByFloor.length > 0
                            ? `Custom (${block.flatsByFloor.join('/')})`
                            : `Uniform (${block.flatsPerFloor})`
                        )}
                      </td>
                      <td>
                        <strong>{totalFlats}</strong>
                      </td>
                      <td>
                        {isEditing ? (
                          <button
                            className="settings-action-btn"
                            onClick={() => handleSaveBlock(index)}
                            style={{ backgroundColor: '#34C759', color: 'white' }}
                          >
                             Save
                          </button>
                        ) : (
                          <>
                            <button
                              className="settings-action-btn"
                              onClick={() => handleEditBlock(index)}
                            >
                              Edit
                            </button>
                            <button
                              className="settings-action-btn danger"
                              onClick={() => handleDeleteBlock(index)}
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {blocksConfig.length > 0 && (
          <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '6px', fontSize: '14px', color: '#666' }}>
            <strong>Note:</strong> After saving, flats will be automatically synced to match this configuration.
            Existing flats that don't match will be removed, and missing flats will be created.
          </div>
        )}
      </div>

      <div className="settings-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Existing Flats</h3>
          <button
            onClick={loadData}
            disabled={loading}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007AFF',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        {loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            Loading flats and members data...
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '16px', fontSize: '14px', color: '#666' }}>
              {flats.length > 0 && (
                <span style={{ color: '#34C759', marginRight: '16px' }}>
                   {flats.length} flat{flats.length !== 1 ? 's' : ''} loaded
                </span>
              )}
              {members.length > 0 && (
                <span style={{ color: '#34C759' }}>
                   {members.length} member{members.length !== 1 ? 's' : ''} loaded
                </span>
              )}
              {flats.length === 0 && members.length === 0 && (
                <span style={{ color: '#FF9500' }}>
                   No data loaded. Check console for errors or click Refresh.
                </span>
              )}
            </div>

            {flats.length > 0 ? (
              <div className="settings-table-container" style={{ marginBottom: '24px' }}>
                {/* Debug Info */}
                {flats.some(f => (f.flat_number || f.flatNumber || '').trim().toUpperCase() === 'A-304') && (
                  <div style={{
                    padding: '10px',
                    marginBottom: '10px',
                    backgroundColor: '#FFF3CD',
                    border: '1px solid #FFC107',
                    borderRadius: '4px',
                    fontSize: '12px'
                  }}>
                    <strong>A-304 Debug:</strong> Members loaded: {members.length},
                    A-304 Member: {members.find(m => ((m.flat_number || m.flatNumber || '').trim().toUpperCase() === 'A-304'))?.name || 'NOT FOUND'}
                    <br />
                    Check browser console (F12) for detailed logs.
                  </div>
                )}
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Flat Number</th>
                      <th>Area (Sq.ft)</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Owner/Tenant</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flats.map(flat => {
                      const flatId = flat.id || flat._id;
                      const flatNumber = flat.flat_number || flat.flatNumber;
                      const flatArea = flat.area_sqft || flat.areaSqft;

                      // Find active member for this flat - use same logic as Members page
                      // Normalize flat numbers for comparison (trim whitespace, case-insensitive)
                      const normalizedFlatNumber = flatNumber ? flatNumber.trim().toUpperCase() : '';

                      // Find active member for this flat - try multiple matching strategies
                      let flatMember = null;

                      // Only try to find member if we have members loaded
                      if (members && members.length > 0) {
                        flatMember = members.find(m => {
                          // Strategy 1: Match by flat_number (normalized)
                          const memberFlatNumber = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
                          const flatNumberMatch = memberFlatNumber === normalizedFlatNumber;

                          // Strategy 2: Match by flat_id (if available)
                          const memberFlatId = m.flat_id ? String(m.flat_id) : null;
                          const flatIdStr = flatId ? String(flatId) : null;
                          const flatIdMatch = flatIdStr && memberFlatId && memberFlatId === flatIdStr;

                          // Status checks - be more lenient
                          const statusLower = (m.status || '').toLowerCase();
                          const isActive = statusLower === 'active';
                          const hasNoMoveOut = !m.move_out_date ||
                            m.move_out_date === null ||
                            m.move_out_date === '' ||
                            (m.move_out_date && new Date(m.move_out_date) > new Date());

                          // Match if either flat_number OR flat_id matches, and member is active
                          const matches = (flatNumberMatch || flatIdMatch) && isActive && hasNoMoveOut;

                          // Debug for A-304
                          if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                            console.log(' A-304 Member Lookup - Checking member:', {
                              memberName: m.name,
                              memberFlatNumber: memberFlatNumber,
                              normalizedFlatNumber: normalizedFlatNumber,
                              memberFlatId: memberFlatId,
                              flatId: flatIdStr,
                              flatNumberMatch: flatNumberMatch,
                              flatIdMatch: flatIdMatch,
                              status: m.status,
                              statusLower: statusLower,
                              isActive: isActive,
                              move_out_date: m.move_out_date,
                              hasNoMoveOut: hasNoMoveOut,
                              matches: matches
                            });
                          }

                          return matches;
                        });

                        // Debug for A-304 - final result
                        if ((normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') && !flatMember) {
                          console.log(' A-304 NO MEMBER FOUND - All members checked:', {
                            totalMembers: members.length,
                            allMembers: members.map(m => ({
                              name: m.name,
                              flat_number: m.flat_number || m.flatNumber,
                              flat_id: m.flat_id,
                              status: m.status,
                              move_out_date: m.move_out_date
                            })),
                            searchCriteria: {
                              normalizedFlatNumber: normalizedFlatNumber,
                              flatId: flatId
                            }
                          });
                        } else if ((normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') && flatMember) {
                          console.log(' A-304 MEMBER FOUND:', {
                            name: flatMember.name,
                            flat_number: flatMember.flat_number,
                            flat_id: flatMember.flat_id,
                            status: flatMember.status,
                            member_type: flatMember.member_type
                          });
                        }
                      } else {
                        // Debug: No members loaded
                        if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                          console.log(' A-304: Members array is empty or not loaded yet');
                        }
                      }

                      // Debug for A-304 specifically (console only, no state updates during render)
                      if (normalizedFlatNumber === 'A-304') {
                        console.log(' A-304 Debug:', {
                          flatNumber: flatNumber,
                          normalizedFlatNumber: normalizedFlatNumber,
                          membersCount: members.length,
                          matchingMembers: members.filter(m => {
                            const mFlat = (m.flat_number || m.flatNumber || '').trim().toUpperCase();
                            return mFlat === normalizedFlatNumber;
                          }),
                          foundMember: flatMember,
                          allMembersForA304: members.filter(m => {
                            const mFlat = (m.flat_number || m.flatNumber || '').trim();
                            return mFlat.toUpperCase().includes('A-304');
                          })
                        });
                        // Note: Don't call addDebugMessage here - it updates state and causes infinite loop
                        // Use console.log only for debugging during render
                      }

                      return (
                        <tr key={flatId || flatNumber}>
                          <td><strong>{flatNumber}</strong></td>
                          <td>
                            <input
                              type="number"
                              value={flatArea || ''}
                              onChange={async (e) => {
                                const newArea = parseFloat(e.target.value);
                                if (!isNaN(newArea) && newArea > 0 && flatId) {
                                  try {
                                    await flatsService.updateFlat(flatId, { area_sqft: newArea });
                                    addDebugMessage(` Updated area for ${flatNumber} to ${newArea}`, 'success');
                                    await loadData(); // Reload to refresh the list
                                  } catch (error) {
                                    console.error('Error updating area:', error);
                                    addDebugMessage(` Error updating area: ${error.message}`, 'error');
                                    alert('Failed to update area. Please try again.');
                                  }
                                }
                              }}
                              onBlur={async (e) => {
                                // Auto-save on blur if value changed
                                const newArea = parseFloat(e.target.value);
                                if (!isNaN(newArea) && newArea > 0 && flatId && newArea !== flatArea) {
                                  try {
                                    await flatsService.updateFlat(flatId, { area_sqft: newArea });
                                    addDebugMessage(` Auto-saved area for ${flatNumber}`, 'success');
                                    await loadData();
                                  } catch (error) {
                                    console.error('Error auto-saving area:', error);
                                  }
                                }
                              }}
                              style={{
                                width: '100px',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                border: '1px solid #ddd',
                                fontSize: '14px',
                              }}
                              placeholder="Area"
                            />
                          </td>
                          <td>{flat.bedrooms ? `${flat.bedrooms} BR` : 'N/A'}</td>
                          <td>
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: '600',
                              backgroundColor: flatMember
                                ? (((flatMember.member_type || flatMember.memberType || '').toLowerCase() === 'owner') ? '#E3F2FD' : '#E8F5E9')
                                : '#F5F5F5',
                              color: flatMember
                                ? (((flatMember.member_type || flatMember.memberType || '').toLowerCase() === 'owner') ? '#1976D2' : '#2E7D32')
                                : '#666',
                            }}>
                              {(() => {
                                if (!flatMember) {
                                  if (normalizedFlatNumber === 'A-304' || flatNumber === 'A-304') {
                                    console.log(' A-304 Showing Vacant:', { flatId, flatNumber, membersCount: members.length });
                                  }
                                  return 'Vacant';
                                }
                                const memberType = (flatMember.member_type || flatMember.memberType || 'owner').toLowerCase();
                                return memberType === 'owner' ? 'Owner' : 'Tenant';
                              })()}
                            </span>
                          </td>
                          <td>
                            {flatMember ? flatMember.name : (flat.owner_name || 'N/A')}
                            {normalizedFlatNumber === 'A-304' && flatMember && console.log(' A-304 Found:', flatMember.name)}
                          </td>
                          <td>
                            <button
                              className="settings-action-btn"
                              onClick={() => {
                                // Auto-fill form with this flat's data
                                handleFlatNumberChange(flat.flat_number);
                                // Scroll to form
                                document.querySelector('.settings-section:last-child')?.scrollIntoView({ behavior: 'smooth' });
                              }}
                            >
                              Edit
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#666', marginBottom: '24px' }}>
                No flats found. Add your first flat below.
              </div>
            )}
          </>
        )}
      </div>

      <div className="settings-section">
        <h3>Add / Edit Flat Details</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleAddFlat(e);
          }}
          style={{ display: 'contents' }}
        >
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Flat Number *</label>
              <input
                type="text"
                placeholder="A-101"
                value={flatForm.flat_number}
                onChange={(e) => handleFlatNumberChange(e.target.value)}
                list="flat-numbers"
              />
              <datalist id="flat-numbers">
                {flats.map(flat => (
                  <option key={flat.id || flat._id || flat.flat_number} value={flat.flat_number || flat.flatNumber} />
                ))}
              </datalist>
              <small style={{ color: '#666', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                Start typing to see existing flats. Data will auto-fill from member records.
              </small>
            </div>
            <div className="settings-form-group">
              <label>Flat Size (Sq.ft) *</label>
              <input
                type="number"
                placeholder="1200"
                value={flatForm.area_sqft}
                onChange={(e) => setFlatForm(prev => ({ ...prev, area_sqft: e.target.value }))}
              />
            </div>
            <div className="settings-form-group">
              <label>Flat Type</label>
              <select
                value={flatForm.flat_type}
                onChange={(e) => setFlatForm(prev => ({ ...prev, flat_type: e.target.value }))}
              >
                <option value="">Select Type</option>
                <option>1 BHK</option>
                <option>2 BHK</option>
                <option>3 BHK</option>
                <option>4 BHK</option>
                <option>Penthouse</option>
              </select>
            </div>
            <div className="settings-form-group">
              <label>Status</label>
              <select
                value={flatForm.status}
                onChange={(e) => setFlatForm(prev => ({ ...prev, status: e.target.value }))}
              >
                <option>Owner Occupied</option>
                <option>Tenant</option>
                <option>Vacant</option>
              </select>
            </div>
          </div>
          <div className="settings-form-group">
            <label>Parking Slots</label>
            <input
              type="text"
              placeholder="P-01, P-02"
              value={flatForm.parking_slots}
              onChange={(e) => setFlatForm(prev => ({ ...prev, parking_slots: e.target.value }))}
            />
          </div>
          <div style={{ marginTop: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              type="submit"
              className="settings-add-btn"
              disabled={loading || saving}
              style={{
                opacity: (loading || saving) ? 0.6 : 1,
                cursor: (loading || saving) ? 'not-allowed' : 'pointer',
                padding: '12px 24px',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              {saving ? ' Saving...' : `+ ${flats.find(f => f.flat_number === flatForm.flat_number.trim()) ? 'Update' : 'Add'} Flat`}
            </button>
            <button
              type="button"
              onClick={() => {
                alert('Test button works! Now try the Add Flat button.');
                addDebugMessage(' Test button clicked', 'info');
              }}
              style={{
                padding: '12px 24px',
                backgroundColor: '#34C759',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 'bold'
              }}
            >
               Test Click
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const MemberConfigTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    max_members_per_flat: 4,
    messaging_members_per_flat: 3,
    pan_mandatory: true,
    aadhaar_mandatory: true,
    sale_deed_required: true,
    rent_agreement_required: true,
    tenant_expiry_reminder_days: 30,
    approval_workflow: 'auto', // 'auto' or 'admin'
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          max_members_per_flat: settings.max_members_per_flat || 4,
          messaging_members_per_flat: settings.messaging_members_per_flat || 3,
          pan_mandatory: settings.pan_mandatory ?? true,
          aadhaar_mandatory: settings.aadhaar_mandatory ?? true,
          sale_deed_required: settings.sale_deed_required ?? true,
          rent_agreement_required: settings.rent_agreement_required ?? true,
          tenant_expiry_reminder_days: settings.tenant_expiry_reminder_days || 30,
          approval_workflow: settings.member_approval_required ? 'admin' : 'auto',
        });
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const settingsData = {
        max_members_per_flat: parseInt(formData.max_members_per_flat) || 4,
        messaging_members_per_flat: parseInt(formData.messaging_members_per_flat) || 3,
        pan_mandatory: !!formData.pan_mandatory,
        aadhaar_mandatory: !!formData.aadhaar_mandatory,
        sale_deed_required: !!formData.sale_deed_required,
        rent_agreement_required: !!formData.rent_agreement_required,
        tenant_expiry_reminder_days: parseInt(formData.tenant_expiry_reminder_days) || 30,
        member_approval_required: formData.approval_workflow === 'admin',
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Member configuration saved successfully!' });
      await loadSettings();

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Member Configuration</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading member configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Member Configuration</h2>
      <p className="settings-tab-description">Resident governance rules</p>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{message.type === 'success' ? '' : ''}</span>
          <span>{message.text}</span>
        </div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Allowed Family Members per Flat</label>
            <input
              type="number"
              min="1"
              value={formData.max_members_per_flat}
              onChange={(e) => setFormData(prev => ({ ...prev, max_members_per_flat: e.target.value }))}
            />
          </div>
          <div className="settings-form-group">
            <label>Messaging Members per Flat (default)</label>
            <input
              type="number"
              min="1"
              value={formData.messaging_members_per_flat}
              onChange={(e) => setFormData(prev => ({ ...prev, messaging_members_per_flat: e.target.value }))}
            />
          </div>
        </div>

        <div className="settings-section">
          <h3>Document Requirements</h3>
          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.pan_mandatory}
                onChange={(e) => setFormData(prev => ({ ...prev, pan_mandatory: e.target.checked }))}
              />
              <span>PAN mandatory for owners</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.aadhaar_mandatory}
                onChange={(e) => setFormData(prev => ({ ...prev, aadhaar_mandatory: e.target.checked }))}
              />
              <span>Aadhaar mandatory</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.sale_deed_required}
                onChange={(e) => setFormData(prev => ({ ...prev, sale_deed_required: e.target.checked }))}
              />
              <span>Sale deed required for owners</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.rent_agreement_required}
                onChange={(e) => setFormData(prev => ({ ...prev, rent_agreement_required: e.target.checked }))}
              />
              <span>Rent agreement required for tenants</span>
            </label>
          </div>
        </div>

        <div className="settings-form-group">
          <label>Tenant Validity Expiry Reminder (days before)</label>
          <input
            type="number"
            min="1"
            value={formData.tenant_expiry_reminder_days}
            onChange={(e) => setFormData(prev => ({ ...prev, tenant_expiry_reminder_days: e.target.value }))}
          />
        </div>

        <div className="settings-form-group">
          <label>Approval Workflow</label>
          <select
            value={formData.approval_workflow}
            onChange={(e) => setFormData(prev => ({ ...prev, approval_workflow: e.target.value }))}
          >
            <option value="auto">Auto-approve</option>
            <option value="admin">Admin approval required</option>
          </select>
        </div>

        <div className="settings-form-actions">
          <button
            type="submit"
            className="settings-save-btn"
            disabled={saving}
            style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            className="settings-cancel-btn"
            onClick={() => loadSettings()}
            disabled={saving}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

const BillingRulesTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    maintenance_calculation_logic: 'mixed', // 'sqft', 'fixed', 'water_based', 'mixed'
    maintenance_rate_sqft: 0,
    maintenance_rate_flat: 0,
    sinking_fund_rate: 0,
    repair_fund_rate: 0,
    association_fund_rate: 0,
    corpus_fund_rate: 0,
    water_calculation_type: 'person', // 'flat', 'person', 'meter'
    water_rate_per_person: 0,
    water_min_charge: 0,
    expense_distribution_logic: 'equal', // 'equal', 'sqft'
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          maintenance_calculation_logic: settings.maintenance_calculation_logic || 'mixed',
          maintenance_rate_sqft: settings.maintenance_rate_sqft || 0,
          maintenance_rate_flat: settings.maintenance_rate_flat || 0,
          sinking_fund_rate: settings.sinking_fund_rate || 0,
          repair_fund_rate: settings.repair_fund_rate || 0,
          association_fund_rate: settings.association_fund_rate || 0,
          corpus_fund_rate: settings.corpus_fund_rate || 0,
          water_calculation_type: settings.water_calculation_type || 'person',
          water_rate_per_person: settings.water_rate_per_person || 0,
          water_min_charge: settings.water_min_charge || 0,
          expense_distribution_logic: settings.expense_distribution_logic || 'equal',
        });
      }
    } catch (error) {
      console.error('Error loading billing rules:', error);
      setMessage({ type: 'error', text: 'Failed to load billing rules. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const settingsData = {
        maintenance_calculation_logic: formData.maintenance_calculation_logic,
        maintenance_rate_sqft: parseFloat(formData.maintenance_rate_sqft) || 0,
        maintenance_rate_flat: parseFloat(formData.maintenance_rate_flat) || 0,
        sinking_fund_rate: parseFloat(formData.sinking_fund_rate) || 0,
        repair_fund_rate: parseFloat(formData.repair_fund_rate) || 0,
        association_fund_rate: parseFloat(formData.association_fund_rate) || 0,
        corpus_fund_rate: parseFloat(formData.corpus_fund_rate) || 0,
        water_calculation_type: formData.water_calculation_type,
        water_rate_per_person: parseFloat(formData.water_rate_per_person) || 0,
        water_min_charge: parseFloat(formData.water_min_charge) || 0,
        expense_distribution_logic: formData.expense_distribution_logic,
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Billing rules saved successfully!' });
      await loadSettings();

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving billing rules:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save billing rules. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Billing Rules</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading billing rules...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Billing Rules</h2>
      <p className="settings-tab-description">Configure billing and charges</p>

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

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-section">
          <h3>Maintenance Calculation Method</h3>
          <div className="settings-form-group">
            <label>Calculation Logic *</label>
            <select
              value={formData.maintenance_calculation_logic}
              onChange={(e) => setFormData({ ...formData, maintenance_calculation_logic: e.target.value })}
              required
            >
              <option value="sqft">Square Feet Based</option>
              <option value="fixed">Fixed per Flat</option>
              <option value="water_based">Water Based</option>
              <option value="mixed">Mixed (Sqft + Water + Fixed Expenses)</option>
            </select>
            <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
              Mixed method: Maintenance (sqft) + Water (per person) + Fixed Expenses + Funds
            </small>
          </div>
        </div>

        <div className="settings-section">
          <h3>Fixed Charges</h3>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Rate per Sq.ft ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.maintenance_rate_sqft}
                onChange={(e) => setFormData({ ...formData, maintenance_rate_sqft: e.target.value })}
                placeholder="5.00"
              />
            </div>
            <div className="settings-form-group">
              <label>Maintenance per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.maintenance_rate_flat}
                onChange={(e) => setFormData({ ...formData, maintenance_rate_flat: e.target.value })}
                placeholder="500"
              />
            </div>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Sinking Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.sinking_fund_rate}
                onChange={(e) => setFormData({ ...formData, sinking_fund_rate: e.target.value })}
                placeholder="200"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
            <div className="settings-form-group">
              <label>Repair Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.repair_fund_rate}
                onChange={(e) => setFormData({ ...formData, repair_fund_rate: e.target.value })}
                placeholder="300"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Association Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.association_fund_rate}
                onChange={(e) => setFormData({ ...formData, association_fund_rate: e.target.value })}
                placeholder="100"
              />
            </div>
            <div className="settings-form-group">
              <label>Corpus Fund per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.corpus_fund_rate}
                onChange={(e) => setFormData({ ...formData, corpus_fund_rate: e.target.value })}
                placeholder="150"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                Amount per flat (not total)
              </small>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3>Water Billing</h3>
          <div className="settings-form-group">
            <label>Water Calculation Type</label>
            <select
              value={formData.water_calculation_type}
              onChange={(e) => setFormData({ ...formData, water_calculation_type: e.target.value })}
            >
              <option value="flat">Per Flat</option>
              <option value="person">Per Person</option>
              <option value="meter">Per Meter</option>
            </select>
          </div>
          <div className="settings-form-row">
            <div className="settings-form-group">
              <label>Water Rate per Person ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.water_rate_per_person}
                onChange={(e) => setFormData({ ...formData, water_rate_per_person: e.target.value })}
                placeholder="200"
              />
            </div>
            <div className="settings-form-group">
              <label>Minimum Charge per Flat ()</label>
              <input
                type="number"
                step="0.01"
                value={formData.water_min_charge}
                onChange={(e) => setFormData({ ...formData, water_min_charge: e.target.value })}
                placeholder="200"
              />
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3>Shared Expense Distribution</h3>
          <div className="settings-form-group">
            <label>Distribution Method</label>
            <select
              value={formData.expense_distribution_logic}
              onChange={(e) => setFormData({ ...formData, expense_distribution_logic: e.target.value })}
            >
              <option value="equal">Equal to all flats</option>
              <option value="sqft">Proportionate to sq.ft</option>
            </select>
          </div>
        </div>

        <div className="settings-form-actions">
          <button type="submit" className="settings-save-btn" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};

const LateFeeTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Form state
  const [formData, setFormData] = useState({
    bill_due_days: 5, // Due date of month
    late_payment_grace_days: 10,
    late_payment_penalty_type: 'fixed', // 'fixed' or 'percentage'
    late_payment_penalty_value: 5,
    late_fee_frequency: 'one-time', // Not in API, keeping for UI
    interest_on_overdue: false,
    interest_rate: 1.5,
    max_penalty_cap: 1000, // Not in API, keeping for UI
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings) {
        setFormData({
          bill_due_days: settings.bill_due_days || 5,
          late_payment_grace_days: settings.late_payment_grace_days || 10,
          late_payment_penalty_type: settings.late_payment_penalty_type || 'fixed',
          late_payment_penalty_value: settings.late_payment_penalty_value || 5,
          late_fee_frequency: 'one-time', // Not in API
          interest_on_overdue: settings.interest_on_overdue || false,
          interest_rate: settings.interest_rate || 1.5,
          max_penalty_cap: 1000, // Not in API
        });
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      // Validate penalty value if penalty type is set
      if (formData.late_payment_penalty_type && (!formData.late_payment_penalty_value || formData.late_payment_penalty_value <= 0)) {
        setMessage({ type: 'error', text: 'Late Fee Amount/Percentage must be greater than 0' });
        setSaving(false);
        return;
      }

      // Validate interest rate if interest is enabled
      if (formData.interest_on_overdue && (!formData.interest_rate || formData.interest_rate <= 0)) {
        setMessage({ type: 'error', text: 'Interest Rate must be greater than 0 when interest on arrears is enabled' });
        setSaving(false);
        return;
      }

      const settingsData = {
        bill_due_days: parseInt(formData.bill_due_days) || 5,
        late_payment_grace_days: parseInt(formData.late_payment_grace_days) || 0,
        late_payment_penalty_type: formData.late_payment_penalty_type,
        late_payment_penalty_value: parseFloat(formData.late_payment_penalty_value) || undefined,
        interest_on_overdue: formData.interest_on_overdue,
        interest_rate: formData.interest_on_overdue ? parseFloat(formData.interest_rate) : undefined,
      };

      await settingsService.saveSocietySettings(settingsData);
      setMessage({ type: 'success', text: 'Late fee & penalties configuration saved successfully!' });
      await loadSettings();

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      const errorMsg = getErrorMessage(error) || 'Failed to save settings. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-tab-content">
        <h2 className="settings-tab-title">Late Fee & Penalties</h2>
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          Loading late fee configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Late Fee & Penalties</h2>
      <p className="settings-tab-description">Configure late payment charges</p>

      {/* Success/Error Message */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : '#FFEBEE',
          color: message.type === 'success' ? '#2E7D32' : '#C62828',
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : '#EF5350'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{message.type === 'success' ? '' : ''}</span>
          <span>{message.text}</span>
        </div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="settings-form-group">
          <label>Due Date of Every Month</label>
          <input
            type="number"
            min="1"
            max="31"
            value={formData.bill_due_days}
            onChange={(e) => setFormData(prev => ({ ...prev, bill_due_days: e.target.value }))}
          />
          <small>Day of month when bills are due</small>
        </div>

        <div className="settings-form-group">
          <label>Grace Period (days)</label>
          <input
            type="number"
            min="0"
            value={formData.late_payment_grace_days}
            onChange={(e) => setFormData(prev => ({ ...prev, late_payment_grace_days: e.target.value }))}
          />
          <small>Days after due date before late fee applies</small>
        </div>

        <div className="settings-form-group">
          <label>Late Fee Type</label>
          <select
            value={formData.late_payment_penalty_type}
            onChange={(e) => setFormData(prev => ({ ...prev, late_payment_penalty_type: e.target.value }))}
          >
            <option value="fixed">Flat Amount</option>
            <option value="percentage">Percentage of Bill</option>
          </select>
        </div>

        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>Late Fee Amount / Percentage</label>
            <input
              type="number"
              placeholder={formData.late_payment_penalty_type === 'fixed' ? "500" : "5"}
              step={formData.late_payment_penalty_type === 'percentage' ? "0.01" : "1"}
              value={formData.late_payment_penalty_value}
              onChange={(e) => setFormData(prev => ({ ...prev, late_payment_penalty_value: e.target.value }))}
            />
            <small>{formData.late_payment_penalty_type === 'fixed' ? 'Enter amount in ' : 'Enter percentage (e.g., 5 for 5%)'}</small>
          </div>
          <div className="settings-form-group">
            <label>Late Fee Frequency</label>
            <select
              value={formData.late_fee_frequency}
              onChange={(e) => setFormData(prev => ({ ...prev, late_fee_frequency: e.target.value }))}
            >
              <option value="one-time">One-time</option>
              <option value="monthly">Monthly</option>
              <option value="daily">Daily</option>
            </select>
            <small style={{ color: '#666', fontSize: '11px' }}>Note: Frequency setting is for display only</small>
          </div>
        </div>

        <div className="settings-checkbox-group">
          <label className="settings-checkbox">
            <input
              type="checkbox"
              checked={formData.interest_on_overdue}
              onChange={(e) => setFormData(prev => ({ ...prev, interest_on_overdue: e.target.checked }))}
            />
            <span>Apply interest on arrears</span>
          </label>
        </div>

        <div className="settings-form-group">
          <label>Interest Rate on Arrears (% per month)</label>
          <input
            type="number"
            step="0.1"
            placeholder="1.5"
            value={formData.interest_rate}
            onChange={(e) => setFormData(prev => ({ ...prev, interest_rate: e.target.value }))}
            disabled={!formData.interest_on_overdue}
            style={{ opacity: formData.interest_on_overdue ? 1 : 0.6 }}
          />
        </div>

        <div className="settings-form-group">
          <label>Maximum Penalty Cap ()</label>
          <input
            type="number"
            placeholder="5000"
            value={formData.max_penalty_cap}
            onChange={(e) => setFormData(prev => ({ ...prev, max_penalty_cap: e.target.value }))}
          />
          <small>Maximum total penalty that can be charged (Note: This setting is for display only)</small>
        </div>

        <div className="settings-form-actions">
          <button
            type="submit"
            className="settings-save-btn"
            disabled={saving}
            style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            className="settings-cancel-btn"
            onClick={() => loadSettings()}
            disabled={saving}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

const AccountingTab = () => {
  const [financialYears, setFinancialYears] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showAddForm, setShowAddForm] = useState(false);
  const [newYear, setNewYear] = useState({
    year_name: '',
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    loadFinancialYears();
  }, []);

  const loadFinancialYears = async () => {
    setLoading(true);
    try {
      const years = await financialYearService.listFinancialYears();
      setFinancialYears(years);
    } catch (error) {
      console.error('Error loading financial years:', error);
      setMessage({ type: 'error', text: 'Failed to load financial years' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateYear = async (e) => {
    e.preventDefault();
    if (!newYear.year_name || !newYear.start_date || !newYear.end_date) {
      setMessage({ type: 'error', text: 'Please fill all fields' });
      return;
    }

    setSaving(true);
    try {
      await financialYearService.createFinancialYear(newYear);
      setMessage({ type: 'success', text: 'Financial year created successfully!' });
      setShowAddForm(false);
      setNewYear({ year_name: '', start_date: '', end_date: '' });
      loadFinancialYears();
    } catch (error) {
      console.error('Error creating financial year:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: 'Error: ' + errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Accounting Settings</h2>
      <p className="settings-tab-description">Financial year management & controls</p>

      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          backgroundColor: message.type === 'success' ? '#E8F5E9' : (message.type === 'error' ? '#FFEBEE' : '#E3F2FD'),
          color: message.type === 'success' ? '#2E7D32' : (message.type === 'error' ? '#C62828' : '#1565C0'),
          border: `1px solid ${message.type === 'success' ? '#4CAF50' : (message.type === 'error' ? '#EF5350' : '#2196F3')}`,
        }}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Financial Years</h3>
          <button
            className="settings-add-btn"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : '+ Add New Financial Year'}
          </button>
        </div>

        {showAddForm && (
          <form className="settings-form" onSubmit={handleCreateYear} style={{ marginBottom: '25px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Year Name (e.g. FY 2025-26)</label>
                <input
                  type="text"
                  value={newYear.year_name}
                  onChange={(e) => setNewYear({ ...newYear, year_name: e.target.value })}
                  placeholder="FY 2025-26"
                  required
                />
              </div>
              <div className="settings-form-group">
                <label>Start Date</label>
                <input
                  type="date"
                  value={newYear.start_date}
                  onChange={(e) => setNewYear({ ...newYear, start_date: e.target.value })}
                  required
                />
              </div>
              <div className="settings-form-group">
                <label>End Date</label>
                <input
                  type="date"
                  value={newYear.end_date}
                  onChange={(e) => setNewYear({ ...newYear, end_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <button type="submit" className="settings-save-btn" disabled={saving}>
              {saving ? 'Creating...' : 'Create Financial Year'}
            </button>
          </form>
        )}

        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Year Name</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Status</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="5" style={{ textAlign: 'center' }}>Loading...</td></tr>
              ) : financialYears.length === 0 ? (
                <tr><td colSpan="5" style={{ textAlign: 'center' }}>No financial years found. Create one to start accounting.</td></tr>
              ) : (
                financialYears.map(year => (
                  <tr key={year.id}>
                    <td><strong>{year.year_name}</strong></td>
                    <td>{year.start_date}</td>
                    <td>{year.end_date}</td>
                    <td>
                      <span className={`settings-badge status-${year.status.toLowerCase()}`}>
                        {year.status}
                      </span>
                    </td>
                    <td>
                      {year.is_active ? ' Active' : 'Inactive'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="settings-section">
        <h3>Accounting Controls</h3>
        <div className="settings-checkbox-group">
          <label className="settings-checkbox">
            <input type="checkbox" readOnly checked={financialYears.some(y => y.is_active && y.is_closed)} />
            <span>Lock current financial year (prevent modifications)</span>
          </label>
        </div>
      </div>
    </div>
  );
};

const PaymentGatewayTab = () => (
  <div className="settings-tab-content">
    <h2 className="settings-tab-title">Payment Gateway</h2>
    <p className="settings-tab-description">Configure payment collection</p>

    <div className="settings-form">
      <div className="settings-form-group">
        <label>Payment Gateway Provider</label>
        <select>
          <option value="">Select Gateway</option>
          <option value="razorpay">Razorpay</option>
          <option value="payu">PayU</option>
          <option value="stripe">Stripe</option>
          <option value="upi">UPI Direct</option>
        </select>
      </div>

      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>API Key</label>
          <input type="password" placeholder="Enter API key" />
        </div>
        <div className="settings-form-group">
          <label>API Secret</label>
          <input type="password" placeholder="Enter API secret" />
        </div>
      </div>

      <div className="settings-form-group">
        <label>Society Bank Account Mapping</label>
        <select>
          <option>HDFC - Current (Primary)</option>
          <option>ICICI - Savings</option>
        </select>
      </div>

      <div className="settings-checkbox-group">
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Auto-generate payment receipts</span>
        </label>
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Auto-reconcile payments</span>
        </label>
      </div>

      <div className="settings-form-group">
        <label>Convenience Fee (%)</label>
        <input type="number" step="0.01" placeholder="0.00" />
        <small>Additional fee charged to members (if any)</small>
      </div>

      <div className="settings-form-actions">
        <button className="settings-save-btn">Save & Test Connection</button>
      </div>
    </div>
  </div>
);

const NotificationsTab = () => (
  <div className="settings-tab-content">
    <h2 className="settings-tab-title">Notifications & Communication</h2>
    <p className="settings-tab-description">Configure member engagement</p>

    <div className="settings-section">
      <h3>SMS Provider</h3>
      <div className="settings-form">
        <div className="settings-form-group">
          <label>Provider</label>
          <select>
            <option value="">Select Provider</option>
            <option value="twilio">Twilio</option>
            <option value="msg91">MSG91</option>
            <option value="textlocal">TextLocal</option>
          </select>
        </div>
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>API Key</label>
            <input type="password" />
          </div>
          <div className="settings-form-group">
            <label>Sender ID</label>
            <input type="text" />
          </div>
        </div>
      </div>
    </div>

    <div className="settings-section">
      <h3>WhatsApp Integration</h3>
      <div className="settings-form-group">
        <label>WhatsApp Business API</label>
        <input type="text" placeholder="API endpoint" />
      </div>
    </div>

    <div className="settings-section">
      <h3>Email Settings</h3>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>SMTP Server</label>
          <input type="text" placeholder="smtp.gmail.com" />
        </div>
        <div className="settings-form-group">
          <label>Port</label>
          <input type="number" placeholder="587" />
        </div>
      </div>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>Email</label>
          <input type="email" />
        </div>
        <div className="settings-form-group">
          <label>Password</label>
          <input type="password" />
        </div>
      </div>
    </div>

    <div className="settings-section">
      <h3>Notification Schedule</h3>
      <div className="settings-form-row">
        <div className="settings-form-group">
          <label>Bill Reminder (days before due)</label>
          <input type="number" defaultValue="3" />
        </div>
        <div className="settings-form-group">
          <label>Due Alert (days after due)</label>
          <input type="number" defaultValue="1" />
        </div>
      </div>
      <div className="settings-checkbox-group">
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Send complaint status alerts</span>
        </label>
        <label className="settings-checkbox">
          <input type="checkbox" defaultChecked />
          <span>Enable push notifications</span>
        </label>
      </div>
    </div>

    <div className="settings-form-actions">
      <button className="settings-save-btn">Save Changes</button>
    </div>
  </div>
);

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

const ComplaintsTab = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [categories, setCategories] = useState(['Lift', 'Water', 'Security', 'Plumbing', 'Electricity']);
  const [newCategory, setNewCategory] = useState('');

  const [formData, setFormData] = useState({
    sla_low_priority_days: 7,
    sla_medium_priority_days: 3,
    sla_high_priority_hours: 24,
    escalation_days: 5,
    escalate_to: 'Secretary',
    auto_close_resolved: false
  });

  useEffect(() => {
    loadComplaintSettings();
  }, []);

  const loadComplaintSettings = async () => {
    setLoading(true);
    try {
      const response = await settingsService.getSocietySettings();
      const complaintConfig = response.complaint_config || {};

      if (complaintConfig.categories) {
        setCategories(complaintConfig.categories);
      }

      setFormData({
        sla_low_priority_days: complaintConfig.sla_low_priority_days || 7,
        sla_medium_priority_days: complaintConfig.sla_medium_priority_days || 3,
        sla_high_priority_hours: complaintConfig.sla_high_priority_hours || 24,
        escalation_days: complaintConfig.escalation_days || 5,
        escalate_to: complaintConfig.escalate_to || 'Secretary',
        auto_close_resolved: complaintConfig.auto_close_resolved || false
      });
    } catch (error) {
      console.error('Error loading complaint settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCategory = () => {
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setCategories([...categories, newCategory.trim()]);
      setNewCategory('');
    }
  };

  const handleRemoveCategory = (category) => {
    setCategories(categories.filter(c => c !== category));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const complaintConfig = {
        categories: categories,
        sla_low_priority_days: parseInt(formData.sla_low_priority_days) || 7,
        sla_medium_priority_days: parseInt(formData.sla_medium_priority_days) || 3,
        sla_high_priority_hours: parseInt(formData.sla_high_priority_hours) || 24,
        escalation_days: parseInt(formData.escalation_days) || 5,
        escalate_to: formData.escalate_to,
        auto_close_resolved: formData.auto_close_resolved
      };

      await settingsService.saveSocietySettings({ complaint_config: complaintConfig });
      setMessage({ type: 'success', text: 'Complaint settings saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving complaint settings:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Complaints & Helpdesk</h2>
      <p className="settings-tab-description">Configure complaint management</p>

      {message.text && (
        <div className={`settings-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <p>Loading settings...</p>
      ) : (
        <>
          <div className="settings-section">
            <h3>Complaint Categories</h3>
            <div className="settings-form-row" style={{ marginBottom: '10px' }}>
              <div className="settings-form-group" style={{ flex: 1 }}>
                <input
                  type="text"
                  placeholder="Category name (e.g., Lift, Water, Security)"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCategory()}
                />
              </div>
              <button className="settings-add-btn" onClick={handleAddCategory}>+ Add Category</button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
              {categories.map((category, index) => (
                <div key={index} className="settings-badge" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
                  <span>{category}</span>
                  <button
                    onClick={() => handleRemoveCategory(category)}
                    style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer', fontSize: '16px', padding: '0', lineHeight: '1' }}
                  >
                    
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <h3>SLA Timelines</h3>
            <div className="settings-form-row">
              <div className="settings-form-group">
                <label>Low Priority (days)</label>
                <input
                  type="number"
                  value={formData.sla_low_priority_days}
                  onChange={(e) => setFormData({ ...formData, sla_low_priority_days: e.target.value })}
                />
              </div>
              <div className="settings-form-group">
                <label>Medium Priority (days)</label>
                <input
                  type="number"
                  value={formData.sla_medium_priority_days}
                  onChange={(e) => setFormData({ ...formData, sla_medium_priority_days: e.target.value })}
                />
              </div>
              <div className="settings-form-group">
                <label>High Priority (hours)</label>
                <input
                  type="number"
                  value={formData.sla_high_priority_hours}
                  onChange={(e) => setFormData({ ...formData, sla_high_priority_hours: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="settings-section">
            <h3>Escalation Rules</h3>
            <div className="settings-form-group">
              <label>Auto-escalate after (days)</label>
              <input
                type="number"
                value={formData.escalation_days}
                onChange={(e) => setFormData({ ...formData, escalation_days: e.target.value })}
              />
            </div>
            <div className="settings-form-group">
              <label>Escalate to</label>
              <select
                value={formData.escalate_to}
                onChange={(e) => setFormData({ ...formData, escalate_to: e.target.value })}
              >
                <option>Secretary</option>
                <option>Committee</option>
                <option>Admin</option>
              </select>
            </div>
          </div>

          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={formData.auto_close_resolved}
                onChange={(e) => setFormData({ ...formData, auto_close_resolved: e.target.checked })}
              />
              <span>Auto-close resolved complaints after 7 days</span>
            </label>
          </div>

          <div className="settings-form-actions">
            <button
              className="settings-save-btn"
              onClick={handleSave}
              disabled={saving}
              style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};

const AssetsTab = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const [assets, setAssets] = useState([]);
  const [vendors, setVendors] = useState([]);

  const [assetForm, setAssetForm] = useState({
    name: '',
    type: 'Lift',
    installationDate: '',
    warrantyExpiry: ''
  });

  const [vendorForm, setVendorForm] = useState({
    name: '',
    serviceType: 'Security',
    startDate: '',
    endDate: '',
    reminderDays: 30
  });

  const [notifications, setNotifications] = useState({
    sendAMCReminders: true,
    sendExpiryAlerts: true
  });

  useEffect(() => {
    loadAssetConfig();
  }, []);

  const loadAssetConfig = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings && settings.asset_config) {
        const config = settings.asset_config;
        setAssets(config.assets || []);
        setVendors(config.vendors || []);
        setNotifications({
          sendAMCReminders: config.sendAMCReminders ?? true,
          sendExpiryAlerts: config.sendExpiryAlerts ?? true
        });
      }
    } catch (error) {
      console.error('Error loading asset config:', error);
      setMessage({ type: 'error', text: 'Failed to load asset configuration.' });
    } finally {
      setLoading(false);
    }
  };

  const handleAddAsset = () => {
    if (!assetForm.name.trim()) {
      setMessage({ type: 'error', text: 'Asset Name is required' });
      return;
    }
    setAssets([...assets, { ...assetForm, id: Date.now() }]);
    setAssetForm({
      name: '',
      type: 'Lift',
      installationDate: '',
      warrantyExpiry: ''
    });
    setMessage({ type: 'info', text: 'Asset added to list. Click Save Changes to persist.' });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleAddVendor = () => {
    if (!vendorForm.name.trim()) {
      setMessage({ type: 'error', text: 'Vendor Name is required' });
      return;
    }
    setVendors([...vendors, { ...vendorForm, id: Date.now() }]);
    setVendorForm({
      name: '',
      serviceType: 'Security',
      startDate: '',
      endDate: '',
      reminderDays: 30
    });
    setMessage({ type: 'info', text: 'Vendor added to list. Click Save Changes to persist.' });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleRemoveAsset = (id) => {
    setAssets(assets.filter(a => a.id !== id));
  };

  const handleRemoveVendor = (id) => {
    setVendors(vendors.filter(v => v.id !== id));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      const asset_config = {
        assets,
        vendors,
        ...notifications
      };
      await settingsService.saveSocietySettings({ asset_config });
      setMessage({ type: 'success', text: 'Asset & Vendor settings saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving asset config:', error);
      const errorMsg = getErrorMessage(error);
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Assets & Vendor Management</h2>
      <p className="settings-tab-description">Manage society assets and vendors</p>

      {message.text && (
        <div className={`settings-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <p>Loading configuration...</p>
      ) : (
        <>
          <div className="settings-section">
            <h3>Society Assets</h3>

            {/* Asset List */}
            {assets.length > 0 && (
              <div className="settings-table-container" style={{ marginBottom: '20px' }}>
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Installation</th>
                      <th>Warranty</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map(asset => (
                      <tr key={asset.id}>
                        <td>{asset.name}</td>
                        <td>{asset.type}</td>
                        <td>{asset.installationDate || '-'}</td>
                        <td>{asset.warrantyExpiry || '-'}</td>
                        <td>
                          <button onClick={() => handleRemoveAsset(asset.id)} style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer' }}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Asset Name</label>
                  <input
                    type="text"
                    placeholder="Lift 1, Generator, etc"
                    value={assetForm.name}
                    onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Asset Type</label>
                  <select
                    value={assetForm.type}
                    onChange={(e) => setAssetForm({ ...assetForm, type: e.target.value })}
                  >
                    <option>Lift</option>
                    <option>Generator</option>
                    <option>Water Pump</option>
                    <option>CCTV</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Installation Date</label>
                  <input
                    type="date"
                    value={assetForm.installationDate}
                    onChange={(e) => setAssetForm({ ...assetForm, installationDate: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Warranty Expiry</label>
                  <input
                    type="date"
                    value={assetForm.warrantyExpiry}
                    onChange={(e) => setAssetForm({ ...assetForm, warrantyExpiry: e.target.value })}
                  />
                </div>
              </div>
              <button
                type="button"
                className="settings-add-btn"
                onClick={handleAddAsset}
                style={{ width: 'fit-content' }}
              >
                + Add Asset to List
              </button>
            </div>
          </div>

          <div className="settings-section">
            <h3>Vendor Management</h3>

            {/* Vendor List */}
            {vendors.length > 0 && (
              <div className="settings-table-container" style={{ marginBottom: '20px' }}>
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Service</th>
                      <th>Contract End</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vendors.map(vendor => (
                      <tr key={vendor.id}>
                        <td>{vendor.name}</td>
                        <td>{vendor.serviceType}</td>
                        <td>{vendor.endDate || '-'}</td>
                        <td>
                          <button onClick={() => handleRemoveVendor(vendor.id)} style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer' }}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Vendor Name</label>
                  <input
                    type="text"
                    placeholder="Vendor name"
                    value={vendorForm.name}
                    onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Service Type</label>
                  <select
                    value={vendorForm.serviceType}
                    onChange={(e) => setVendorForm({ ...vendorForm, serviceType: e.target.value })}
                  >
                    <option>Security</option>
                    <option>Housekeeping</option>
                    <option>AMC</option>
                    <option>Maintenance</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Contract Start Date</label>
                  <input
                    type="date"
                    value={vendorForm.startDate}
                    onChange={(e) => setVendorForm({ ...vendorForm, startDate: e.target.value })}
                  />
                </div>
                <div className="settings-form-group">
                  <label>Contract End Date</label>
                  <input
                    type="date"
                    value={vendorForm.endDate}
                    onChange={(e) => setVendorForm({ ...vendorForm, endDate: e.target.value })}
                  />
                </div>
              </div>
              <div className="settings-form-group">
                <label>Reminder Before Expiry (days)</label>
                <input
                  type="number"
                  value={vendorForm.reminderDays}
                  onChange={(e) => setVendorForm({ ...vendorForm, reminderDays: parseInt(e.target.value) || 0 })}
                />
              </div>
              <button
                type="button"
                className="settings-add-btn"
                onClick={handleAddVendor}
                style={{ width: 'fit-content' }}
              >
                + Add Vendor to List
              </button>
            </div>
          </div>

          <div className="settings-checkbox-group">
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={notifications.sendAMCReminders}
                onChange={(e) => setNotifications({ ...notifications, sendAMCReminders: e.target.checked })}
              />
              <span>Send AMC renewal reminders</span>
            </label>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={notifications.sendExpiryAlerts}
                onChange={(e) => setNotifications({ ...notifications, sendExpiryAlerts: e.target.checked })}
              />
              <span>Send contract expiry alerts</span>
            </label>
          </div>

          <div className="settings-form-actions" style={{ marginTop: '30px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
            <button
              className="settings-save-btn"
              onClick={handleSave}
              disabled={saving}
              style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};

const LegalTab = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const [legalConfig, setLegalConfig] = useState({
    bye_laws_url: '',
    bye_laws_filename: '',
    agm_date: '',
    audit_due_date: '',
    itr_filing_due_date: '',
    mca_filing_due_date: '',
    send_agm_reminder: true,
    send_audit_reminder: true,
    send_itr_reminder: true,
    statutory_docs: []
  });

  const [byeLawsFile, setByeLawsFile] = useState(null);

  useEffect(() => {
    loadLegalConfig();
  }, []);

  const loadLegalConfig = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      if (settings && settings.legal_config) {
        setLegalConfig(prev => ({
          ...prev,
          ...settings.legal_config
        }));
      }
    } catch (error) {
      console.error('Error loading legal config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDocument = async (url) => {
    try {
      const endpoint = normalizeDocumentEndpoint(url);
      const response = await api.get(endpoint, {
        responseType: 'blob'
      });
      const file = new Blob([response.data], { type: response.headers['content-type'] });
      const fileURL = URL.createObjectURL(file);
      window.open(fileURL, '_blank');
    } catch (error) {
      console.error('Error viewing document:', error);
      alert('Failed to open document. ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleByeLawsChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setByeLawsFile(e.target.files[0]);
    }
  };

  const handleUploadByeLaws = async () => {
    if (!byeLawsFile) {
      setMessage({ type: 'error', text: 'Please select a file first' });
      return;
    }

    setSaving(true);
    setMessage({ type: 'info', text: 'Uploading Bye-laws...' });
    try {
      const result = await uploadSocietyDocumentWithFallback(byeLawsFile, 'bye_laws');
      setLegalConfig(prev => ({
        ...prev,
        bye_laws_url: result.url,
        bye_laws_filename: result.file_name
      }));
      setMessage({ type: 'success', text: 'Bye-laws uploaded successfully!' });
      setByeLawsFile(null);
      // Automatically save the updated config
      await settingsService.saveSocietySettings({
        legal_config: { ...legalConfig, bye_laws_url: result.url, bye_laws_filename: result.file_name }
      });
    } catch (error) {
      console.error('Upload failed:', error);
      setMessage({ type: 'error', text: 'Upload failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveByeLaws = async () => {
    const currentUrl = legalConfig.bye_laws_url;
    const fileName = extractDocumentFileName(currentUrl);
    if (!fileName) {
      setMessage({ type: 'error', text: 'No document found to remove.' });
      return;
    }
    const confirmed = window.confirm(`Remove current bye-laws document (${legalConfig.bye_laws_filename || fileName})?`);
    if (!confirmed) return;

    setSaving(true);
    setMessage({ type: 'info', text: 'Removing Bye-laws document...' });
    try {
      if (typeof settingsService.deleteSocietyDocument === 'function') {
        await settingsService.deleteSocietyDocument(fileName);
      } else {
        await api.delete(`/society/documents/${encodeURIComponent(fileName)}`);
      }
      const updatedConfig = { ...legalConfig, bye_laws_url: '', bye_laws_filename: '' };
      setLegalConfig(updatedConfig);
      await settingsService.saveSocietySettings({
        legal_config: updatedConfig,
      });
      setMessage({ type: 'success', text: 'Bye-laws document removed successfully.' });
    } catch (error) {
      console.error('Remove failed:', error);
      setMessage({ type: 'error', text: 'Remove failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = (e) => {
    const { name, value, type, checked } = e.target;
    setLegalConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      await settingsService.saveSocietySettings({
        legal_config: legalConfig
      });
      setMessage({ type: 'success', text: 'Legal & Compliance settings saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error saving legal config:', error);
      setMessage({ type: 'error', text: 'Save failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="settings-loading">Loading legal settings...</div>;

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Legal & Compliance</h2>
      <p className="settings-tab-description">Legal documents and compliance tracking</p>

      {message.text && (
        <div className={`settings-message ${message.type}`} style={{
          padding: '12px',
          marginBottom: '20px',
          borderRadius: '8px',
          backgroundColor: message.type === 'error' ? '#ffeeee' : message.type === 'success' ? '#eeffee' : '#eefaff',
          color: message.type === 'error' ? '#cc0000' : message.type === 'success' ? '#008800' : '#006688',
          border: `1px solid ${message.type === 'error' ? '#ffcccc' : message.type === 'success' ? '#ccffcc' : '#cceeff'}`
        }}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <h3>Bye-laws Document</h3>
        <div className="settings-form-group">
          <label>Upload New Bye-laws (PDF/Doc)</label>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleByeLawsChange}
              className="settings-input"
              style={{ padding: '8px' }}
            />
            <button
              className="settings-action-btn"
              onClick={handleUploadByeLaws}
              disabled={saving || !byeLawsFile}
            >
              {saving ? 'Uploading...' : 'Upload'}
            </button>
          </div>
          {legalConfig.bye_laws_url && (
            <div style={{ marginTop: '10px', padding: '10px', background: '#f9f9f9', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span> Current: <strong>{legalConfig.bye_laws_filename || 'Bye-laws.pdf'}</strong></span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleViewDocument(legalConfig.bye_laws_url)}
                  className="settings-action-btn"
                  style={{ cursor: 'pointer', textAlign: 'center' }}
                >
                  View Document
                </button>
                <button
                  onClick={handleRemoveByeLaws}
                  className="settings-action-btn"
                  disabled={saving}
                  style={{ cursor: saving ? 'not-allowed' : 'pointer', textAlign: 'center', background: '#e74c3c' }}
                >
                  {saving ? 'Removing...' : 'Remove Document'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="settings-section">
        <h3>Important Dates</h3>
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>AGM Date</label>
            <input
              type="date"
              name="agm_date"
              value={legalConfig.agm_date}
              onChange={handleConfigChange}
              className="settings-input"
            />
          </div>
          <div className="settings-form-group">
            <label>Audit Due Date</label>
            <input
              type="date"
              name="audit_due_date"
              value={legalConfig.audit_due_date}
              onChange={handleConfigChange}
              className="settings-input"
            />
          </div>
        </div>
        <div className="settings-form-row">
          <div className="settings-form-group">
            <label>ITR Filing Due Date</label>
            <input
              type="date"
              name="itr_filing_due_date"
              value={legalConfig.itr_filing_due_date}
              onChange={handleConfigChange}
              className="settings-input"
            />
          </div>
          <div className="settings-form-group">
            <label>MCA Filing Due Date</label>
            <input
              type="date"
              name="mca_filing_due_date"
              value={legalConfig.mca_filing_due_date}
              onChange={handleConfigChange}
              className="settings-input"
            />
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Reminders</h3>
        <div className="settings-checkbox-group">
          <label className="settings-checkbox">
            <input
              type="checkbox"
              name="send_agm_reminder"
              checked={legalConfig.send_agm_reminder}
              onChange={handleConfigChange}
            />
            <span>Send AGM reminder 30 days before</span>
          </label>
          <label className="settings-checkbox">
            <input
              type="checkbox"
              name="send_audit_reminder"
              checked={legalConfig.send_audit_reminder}
              onChange={handleConfigChange}
            />
            <span>Send audit due reminder 15 days before</span>
          </label>
          <label className="settings-checkbox">
            <input
              type="checkbox"
              name="send_itr_reminder"
              checked={legalConfig.send_itr_reminder}
              onChange={handleConfigChange}
            />
            <span>Send ITR filing reminder</span>
          </label>
        </div>
      </div>

      <div className="settings-form-actions">
        <button
          className="settings-save-btn"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Legal Settings'}
        </button>
      </div>
    </div>
  );
};

const DataSecurityTab = () => {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [demoImporting, setDemoImporting] = useState(false);
  const [flatCsvFile, setFlatCsvFile] = useState(null);
  const [memberCsvFile, setMemberCsvFile] = useState(null);
  const [replaceExistingFlats, setReplaceExistingFlats] = useState(false);
  const [updateExistingMembers, setUpdateExistingMembers] = useState(false);

  const fetchBackups = async () => {
    try {
      const response = await api.get('/database/backups');
      setBackups(response.data);
    } catch (error) {
      console.error('Failed to fetch backups:', error);
    }
  };

  useEffect(() => {
    fetchBackups();
  }, []);

  const handleBackupNow = async () => {
    setLoading(true);
    setMessage({ type: 'info', text: 'Creating backup...' });
    try {
      await api.post('/database/backup');
      setMessage({ type: 'success', text: 'Backup created successfully!' });
      fetchBackups();
    } catch (error) {
      setMessage({ type: 'error', text: 'Backup failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (filename) => {
    if (!window.confirm(`Are you sure you want to restore ${filename}? This will overwrite current data and require a server restart.`)) {
      return;
    }

    setLoading(true);
    setMessage({ type: 'info', text: 'Restoring backup...' });
    try {
      const response = await api.post(`/database/restore?filename=${filename}`);
      setMessage({ type: 'success', text: response.data.message });
      alert(response.data.message);
    } catch (error) {
      setMessage({ type: 'error', text: 'Restore failed: ' + (error.response?.data?.detail || error.message) });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBackup = async (filename) => {
    try {
      const response = await api.get(`/database/backups/${encodeURIComponent(filename)}/download`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/octet-stream' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setMessage({ type: 'error', text: 'Download failed: ' + (error.response?.data?.detail || error.message) });
    }
  };

  const handleDownloadTemplate = async (kind) => {
    try {
      const blob = await onboardingImportService.downloadTemplate(kind);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = kind === 'flats' ? 'gharmitra_flats_template.csv' : 'gharmitra_members_template.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setMessage({ type: 'error', text: `Template download failed: ${error.response?.data?.detail || error.message}` });
    }
  };

  const handleImportDemoData = async () => {
    const confirmed = window.confirm(
      'Import demo data into this society? Existing onboarding/accounting demo tables will be replaced.'
    );
    if (!confirmed) return;

    setDemoImporting(true);
    setMessage({ type: 'info', text: 'Importing demo data...' });
    try {
      const result = await onboardingImportService.importDemoData({
        source_society_id: 1,
        replace_target: true,
        update_society_profile: false,
      });
      setMessage({
        type: 'success',
        text: `Demo import completed. Flats=${result.imported?.flats || 0}, Members=${result.imported?.members || 0}.`,
      });
    } catch (error) {
      setMessage({ type: 'error', text: `Demo import failed: ${error.response?.data?.detail || error.message}` });
    } finally {
      setDemoImporting(false);
    }
  };

  const handleImportFlatsCsv = async () => {
    if (!flatCsvFile) {
      setMessage({ type: 'error', text: 'Please choose a flats CSV file.' });
      return;
    }
    setLoading(true);
    setMessage({ type: 'info', text: 'Importing flats CSV...' });
    try {
      const result = await onboardingImportService.importFlats(flatCsvFile, replaceExistingFlats);
      setMessage({
        type: 'success',
        text: result.summary || `Flats import completed: created=${result.created}, updated=${result.updated}, failed=${result.failed}, skipped=${result.skipped}`,
      });
      setFlatCsvFile(null);
    } catch (error) {
      setMessage({ type: 'error', text: `Flats import failed: ${error.response?.data?.detail || error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleImportMembersCsv = async () => {
    if (!memberCsvFile) {
      setMessage({ type: 'error', text: 'Please choose a members CSV file.' });
      return;
    }
    setLoading(true);
    setMessage({ type: 'info', text: 'Importing members CSV...' });
    try {
      const result = await onboardingImportService.importMembers(memberCsvFile, updateExistingMembers);
      setMessage({
        type: 'success',
        text: result.summary || `Members import completed: created=${result.created}, updated=${result.updated}, failed=${result.failed}, skipped=${result.skipped}`,
      });
      setMemberCsvFile(null);
    } catch (error) {
      setMessage({ type: 'error', text: `Members import failed: ${error.response?.data?.detail || error.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Data & Security</h2>
      <p className="settings-tab-description">Database management, demo data import, and onboarding migration tools</p>

      {message.text && (
        <div className={`settings-message ${message.type}`} style={{
          padding: '10px',
          marginBottom: '20px',
          borderRadius: '4px',
          backgroundColor: message.type === 'error' ? '#ffeeee' : message.type === 'success' ? '#eeffee' : '#eefaff',
          color: message.type === 'error' ? '#cc0000' : message.type === 'success' ? '#008800' : '#006688',
          border: `1px solid ${message.type === 'error' ? '#ffcccc' : message.type === 'success' ? '#ccffcc' : '#cceeff'}`
        }}>
          {message.text}
        </div>
      )}

      <div className="settings-section">
        <h3>Manual Backup</h3>
        <p>Trigger a safe copy of the current database. Use this before performing major operations.</p>
        <button
          className="settings-action-btn"
          onClick={handleBackupNow}
          disabled={loading}
          style={{ width: 'auto', padding: '10px 20px' }}
        >
          {loading ? 'Processing...' : 'Backup Now'}
        </button>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Demo Data Seeder</h3>
        <p>One-click import of demo dataset for this society.</p>
        <button
          className="settings-action-btn"
          onClick={handleImportDemoData}
          disabled={demoImporting}
          style={{ width: 'auto', padding: '10px 20px' }}
        >
          {demoImporting ? 'Importing...' : 'Import Demo Data'}
        </button>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Onboarding CSV Templates</h3>
        <p>Download, fill, and import for fast society onboarding.</p>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button className="settings-action-btn" onClick={() => handleDownloadTemplate('flats')}>
            Download Flats Template
          </button>
          <button className="settings-action-btn" onClick={() => handleDownloadTemplate('members')}>
            Download Members Template
          </button>
        </div>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Bulk Import Flats</h3>
        <div className="settings-form-group">
          <label>Flats CSV</label>
          <input type="file" accept=".csv" onChange={(e) => setFlatCsvFile(e.target.files?.[0] || null)} />
        </div>
        <label className="settings-checkbox">
          <input
            type="checkbox"
            checked={replaceExistingFlats}
            onChange={(e) => setReplaceExistingFlats(e.target.checked)}
          />
          <span>Replace existing flats with same flat number</span>
        </label>
        <div style={{ marginTop: '10px' }}>
          <button className="settings-action-btn" onClick={handleImportFlatsCsv} disabled={loading}>
            Import Flats CSV
          </button>
        </div>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Bulk Import Members</h3>
        <div className="settings-form-group">
          <label>Members CSV</label>
          <input type="file" accept=".csv" onChange={(e) => setMemberCsvFile(e.target.files?.[0] || null)} />
        </div>
        <label className="settings-checkbox">
          <input
            type="checkbox"
            checked={updateExistingMembers}
            onChange={(e) => setUpdateExistingMembers(e.target.checked)}
          />
          <span>Update existing members with same phone number</span>
        </label>
        <div style={{ marginTop: '10px' }}>
          <button className="settings-action-btn" onClick={handleImportMembersCsv} disabled={loading}>
            Import Members CSV
          </button>
        </div>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>System Backups</h3>
        <p>List of automated and manual backups (last 5 kept). Restoring will overwrite current data.</p>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>File Name</th>
                <th>Size</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {backups.length > 0 ? (
                backups.map((b, idx) => (
                  <tr key={idx}>
                    <td>{new Date(b.created_at).toLocaleString()}</td>
                    <td style={{ fontSize: '11px', fontFamily: 'monospace', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{b.filename}</td>
                    <td>{b.size_kb} KB</td>
                    <td>
                      <button
                        className="settings-action-btn"
                        onClick={() => handleDownloadBackup(b.filename)}
                        disabled={loading}
                        style={{ fontSize: '12px', padding: '4px 8px', marginRight: '6px' }}
                      >
                        Download
                      </button>
                      <button
                        className="settings-action-btn"
                        onClick={() => handleRestore(b.filename)}
                        disabled={loading}
                        style={{ fontSize: '12px', padding: '4px 8px' }}
                      >
                        Restore
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '20px' }}>No backups found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="settings-section" style={{ marginTop: '30px' }}>
        <h3>Data Integrity Status</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="settings-form-group">
            <label>Journal Mode</label>
            <input type="text" readOnly value="WAL (Resilient)" style={{ backgroundColor: '#f9f9f9' }} />
          </div>
          <div className="settings-form-group">
            <label>Automated Protection</label>
            <input type="text" readOnly value="Enabled (on startup & logout)" style={{ backgroundColor: '#f9f9f9' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

const MultiSocietyTab = () => {
  const navigate = useNavigate();

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">Multi-Society Mode</h2>
      <p className="settings-tab-description">Search societies, manage memberships, and approvals</p>

      <div className="settings-section">
        <h3>Member Actions</h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button className="settings-action-btn" onClick={() => navigate('/onboarding/search')}>
             Search Society & Join
          </button>
          <button className="settings-action-btn" onClick={() => navigate('/onboarding/memberships')}>
             My Memberships
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h3>Admin Actions</h3>
        <p style={{ color: '#666', marginBottom: '12px' }}>
          Approve or reject join requests for your society.
        </p>
        <button className="settings-action-btn" onClick={() => navigate('/onboarding/requests')}>
           Review Join Requests
        </button>
      </div>

      <div className="settings-section">
        <h3>Society Switching</h3>
        <p style={{ color: '#666' }}>
          Society switching UI will be enabled after memberships are approved.
        </p>
      </div>
    </div>
  );
};

export default SettingsScreen;


