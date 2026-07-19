import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { getErrorMessage } from './settingsHelpers';

const VisitorBrandsTab = () => {
  const [brands, setBrands] = useState([]);
  const [newBrand, setNewBrand] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await settingsService.getSocietySettings();
      setBrands(settings.custom_visitor_brands || []);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load custom brands.' });
    } finally {
      setLoading(false);
    }
  };

  const handleAddBrand = async (e) => {
    e.preventDefault();
    if (!newBrand.trim()) return;
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const updatedBrands = [...brands, { name: newBrand.trim() }];
      await settingsService.saveSocietySettings({ custom_visitor_brands: updatedBrands });
      setBrands(updatedBrands);
      setNewBrand('');
      setMessage({ type: 'success', text: 'Brand added successfully!' });
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBrand = async (nameToDelete) => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const updatedBrands = brands.filter((b) => b.name !== nameToDelete);
      await settingsService.saveSocietySettings({ custom_visitor_brands: updatedBrands });
      setBrands(updatedBrands);
      setMessage({ type: 'success', text: 'Brand removed.' });
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-tab-content">
      <h2 className="settings-tab-title">One-Tap Visitor Brands</h2>
      <p className="settings-tab-description">Configure custom visitor and delivery brands shown to security guards at the gate.</p>

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

      <div className="settings-section">
        <h3>Add New Brand</h3>
        <form onSubmit={handleAddBrand} style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            value={newBrand}
            onChange={(e) => setNewBrand(e.target.value)}
            placeholder="e.g. Amul Milk, Local Laundry, Water Can"
            style={{ flex: 1, padding: '10px 14px', borderRadius: '8px', border: '1px solid #ddd' }}
          />
          <button className="settings-save-btn" type="submit" disabled={loading} style={{ width: 'auto', margin: 0, padding: '10px 24px' }}>
            Add Brand
          </button>
        </form>
      </div>

      <div className="settings-section">
        <h3>Current Custom Brands</h3>
        {brands.length === 0 ? (
          <p style={{ color: '#666' }}>No custom brands configured yet. Pre-listed standard brands (Swiggy, Zomato, Zepto, etc.) are always available.</p>
        ) : (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {brands.map((brand) => (
              <div
                key={brand.name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  background: '#f1f1f7',
                  borderRadius: '20px',
                  border: '1px solid #ddd',
                  fontSize: '14px',
                  fontWeight: '600'
                }}
              >
                <span>{brand.name}</span>
                <button
                  type="button"
                  onClick={() => handleDeleteBrand(brand.name)}
                  disabled={loading}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#c53030',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    padding: '0 2px'
                  }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VisitorBrandsTab;
