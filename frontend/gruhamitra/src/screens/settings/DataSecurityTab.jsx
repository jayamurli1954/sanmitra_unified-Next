import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import onboardingImportService from '../../services/onboardingImportService';

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

export default DataSecurityTab;
