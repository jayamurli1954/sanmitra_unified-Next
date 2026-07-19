import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import api from '../../services/api';
import { extractDocumentFileName, normalizeDocumentEndpoint, uploadSocietyDocumentWithFallback } from './settingsHelpers';

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

export default LegalTab;
