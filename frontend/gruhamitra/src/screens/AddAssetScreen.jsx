import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const AddAssetScreen = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [assetAccounts, setAssetAccounts] = useState([]);

    const [formData, setFormData] = useState({
        name: '',
        category: 'lift',
        account_code: '16003',
        quantity: 1,
        location: '',
        status: 'Active',
        acquisition_type: 'builder_handover',
        handover_date: new Date().toISOString().split('T')[0],
        purchase_date: '',
        original_cost: '',
        depreciation_method: 'straight_line',
        depreciation_rate: '10',
        useful_life_years: '10',
        residual_value: '1',
        amc_vendor: '',
        amc_expiry: '',
        insurance_policy_no: '',
        insurance_expiry: '',
        vendor_name: '',
        invoice_no: '',
        notes: ''
    });

    useEffect(() => {
        const fetchAccounts = async () => {
            try {
                const response = await api.get('/accounting/accounts?type=asset');
                // Filter for specific asset categories if possible, or just show all assets
                setAssetAccounts(response.data.filter(a => a.code.startsWith('15')) || []);
            } catch (err) {
                console.error('Error fetching asset accounts:', err);
            }
        };
        fetchAccounts();
    }, []);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const payload = {
                ...formData,
                original_cost: parseFloat(formData.original_cost) || 0,
                depreciation_rate: parseFloat(formData.depreciation_rate),
                useful_life_years: parseInt(formData.useful_life_years),
                residual_value: parseFloat(formData.residual_value),
                quantity: parseInt(formData.quantity)
            };

            // Clean up dates based on acquisition type
            if (formData.acquisition_type === 'builder_handover') {
                payload.purchase_date = null;
                payload.vendor_name = null;
                payload.invoice_no = null;
            } else {
                payload.handover_date = null;
            }

            await api.post('/assets/', payload);
            navigate('/assets');
        } catch (err) {
            console.error('Error creating asset:', err);
            setError(err.response?.data?.detail || 'Failed to create asset. Please check all fields.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="dashboard-container asset-add-page">
            <style>{`
                .asset-add-page .asset-form-wrap {
                    max-width: 1120px;
                    width: 100%;
                }
                .asset-add-page .asset-form-head {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 16px;
                    margin-bottom: 24px;
                }
                .asset-add-page .card {
                    background: #fff;
                    border: 1px solid #f0e3d3;
                    border-radius: 8px;
                    box-shadow: 0 6px 20px rgba(92, 52, 18, 0.06);
                    overflow: hidden;
                    margin-bottom: 22px;
                }
                .asset-add-page .card-header {
                    padding: 18px 24px;
                    background: linear-gradient(90deg, #FFF3E0, #FFFFFF);
                    border-bottom: 1px solid #f0e3d3;
                }
                .asset-add-page .card-title {
                    margin: 0;
                    color: #5A2E0A;
                    font-size: 18px;
                    font-weight: 800;
                }
                .asset-add-page .card-body {
                    padding: 24px;
                }
                .asset-add-page .form-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                    gap: 18px 22px;
                }
                .asset-add-page .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 7px;
                }
                .asset-add-page .form-label {
                    color: #5A2E0A;
                    font-size: 14px;
                    font-weight: 700;
                }
                .asset-add-page .form-input,
                .asset-add-page input,
                .asset-add-page select,
                .asset-add-page textarea {
                    width: 100%;
                    min-height: 44px;
                    padding: 10px 12px;
                    border: 1px solid #d9d9d9;
                    border-radius: 8px;
                    background: #fff;
                    color: #3A1F05;
                    font-size: 15px;
                    outline: none;
                    box-sizing: border-box;
                }
                .asset-add-page textarea {
                    min-height: 92px;
                    resize: vertical;
                }
                .asset-add-page .form-input:focus,
                .asset-add-page input:focus,
                .asset-add-page select:focus,
                .asset-add-page textarea:focus {
                    border-color: #E8842A;
                    box-shadow: 0 0 0 3px rgba(232, 132, 42, 0.14);
                }
                .asset-add-page .form-help {
                    color: #8E6A3A;
                    font-size: 12px;
                    line-height: 1.4;
                }
                .asset-add-page .source-choice {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 14px;
                }
                .asset-add-page .source-choice label {
                    min-height: 44px;
                    padding: 10px 14px;
                    border: 1px solid #f0c48b;
                    border-radius: 8px;
                    background: #fffaf2;
                    color: #4A2A0A;
                    font-weight: 700;
                }
                .asset-add-page .asset-actions {
                    display: flex;
                    gap: 14px;
                    justify-content: flex-end;
                    margin-bottom: 40px;
                    padding-top: 4px;
                }
                .asset-add-page .alert-danger {
                    background: #fff1f1;
                    border: 1px solid #f2b8b5;
                    color: #C0392B;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 20px;
                }
            `}</style>

            <div className="dashboard-header">
                <div className="dashboard-header-left">
                    <h1 className="dashboard-header-title">Asset Register</h1>
                    <span className="dashboard-header-subtitle">Common property and equipment</span>
                </div>
                <div className="dashboard-header-right">
                    <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>
                        Back to Dashboard
                    </button>
                </div>
            </div>

            <div className="dashboard-content">
                <div className="settings-tab-content asset-form-wrap">
                    <div className="asset-form-head">
                        <div>
                            <h2 className="settings-tab-title">Add Society Asset</h2>
                            <p className="settings-tab-description" style={{ marginBottom: 0 }}>
                                Register a new common property asset and connect it to accounting.
                            </p>
                        </div>
                        <button className="settings-cancel-btn" onClick={() => navigate('/assets')}>
                            Cancel
                        </button>
                    </div>

                    {error && <div className="alert-danger">{error}</div>}

                    <form onSubmit={handleSubmit}>
                {/* Section 1: Asset Identity */}
                <div className="card" style={{ marginBottom: '20px' }}>
                    <div className="card-header">
                        <h4 className="card-title"> Section 1  Asset Identity</h4>
                    </div>
                    <div className="card-body">
                        <div className="form-grid">
                            <div className="form-group">
                                <label className="form-label">Asset Name*</label>
                                <input
                                    type="text"
                                    name="name"
                                    className="form-input"
                                    placeholder="e.g. Lift - Tower A"
                                    value={formData.name}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Category*</label>
                                <select name="category" className="form-input" value={formData.category} onChange={handleChange}>
                                    <option value="lift">Lift</option>
                                    <option value="electrical">Electrical</option>
                                    <option value="plumbing">Plumbing</option>
                                    <option value="furniture">Furniture</option>
                                    <option value="equipment">Equipment</option>
                                    <option value="infrastructure">Infrastructure</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Quantity</label>
                                <input
                                    type="number"
                                    name="quantity"
                                    className="form-input"
                                    value={formData.quantity}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Location</label>
                                <input
                                    type="text"
                                    name="location"
                                    className="form-input"
                                    placeholder="e.g. Basement, Tower B"
                                    value={formData.location}
                                    onChange={handleChange}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Section 2: Asset Source */}
                <div className="card" style={{ marginBottom: '20px' }}>
                    <div className="card-header">
                        <h4 className="card-title"> Section 2  Asset Source</h4>
                    </div>
                    <div className="card-body">
                        <div className="form-group">
                            <label className="form-label" style={{ display: 'block', marginBottom: '10px' }}>How was this asset acquired?*</label>
                            <div className="source-choice">
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                    <input
                                        type="radio"
                                        name="acquisition_type"
                                        value="builder_handover"
                                        checked={formData.acquisition_type === 'builder_handover'}
                                        onChange={handleChange}
                                    />
                                    From Builder at Society Formation
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                    <input
                                        type="radio"
                                        name="acquisition_type"
                                        value="society_purchase"
                                        checked={formData.acquisition_type === 'society_purchase'}
                                        onChange={handleChange}
                                    />
                                    Purchased by Society
                                </label>
                            </div>
                        </div>

                        <div className="form-grid" style={{ marginTop: '20px' }}>
                            {formData.acquisition_type === 'builder_handover' ? (
                                <>
                                    <div className="form-group">
                                        <label className="form-label">Handover Date*</label>
                                        <input
                                            type="date"
                                            name="handover_date"
                                            className="form-input"
                                            value={formData.handover_date}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Value at Handover*</label>
                                        <input
                                            type="number"
                                            name="original_cost"
                                            className="form-input"
                                            placeholder=""
                                            value={formData.original_cost}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Credit Account (Offset)</label>
                                        <input
                                            type="text"
                                            className="form-input"
                                            value="Corpus Fund (31002)"
                                            disabled
                                            style={{ backgroundColor: '#f0f0f0' }}
                                        />
                                        <small className="form-help">Builder assets post a credit to the Corpus Fund automatically.</small>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="form-group">
                                        <label className="form-label">Purchase Date*</label>
                                        <input
                                            type="date"
                                            name="purchase_date"
                                            className="form-input"
                                            value={formData.purchase_date}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Purchase Cost*</label>
                                        <input
                                            type="number"
                                            name="original_cost"
                                            className="form-input"
                                            placeholder=""
                                            value={formData.original_cost}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Vendor Name</label>
                                        <input
                                            type="text"
                                            name="vendor_name"
                                            className="form-input"
                                            value={formData.vendor_name}
                                            onChange={handleChange}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Invoice No.</label>
                                        <input
                                            type="text"
                                            name="invoice_no"
                                            className="form-input"
                                            value={formData.invoice_no}
                                            onChange={handleChange}
                                        />
                                    </div>
                                </>
                            )}

                            <div className="form-group">
                                <label className="form-label">Asset Account Code*</label>
                                <select name="account_code" className="form-input" value={formData.account_code} onChange={handleChange} required>
                                    {assetAccounts.map(acc => (
                                        <option key={acc.code} value={acc.code}>{acc.code} - {acc.name}</option>
                                    ))}
                                    {assetAccounts.length === 0 && <option value="16003">16003 - Common Area Equipment</option>}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Section 3: Financials */}
                <div className="card" style={{ marginBottom: '20px' }}>
                    <div className="card-header">
                        <h4 className="card-title"> Section 3  Financials (Depreciation)</h4>
                    </div>
                    <div className="card-body">
                        <div className="form-grid">
                            <div className="form-group">
                                <label className="form-label">Depreciation Method*</label>
                                <select name="depreciation_method" className="form-input" value={formData.depreciation_method} onChange={handleChange}>
                                    <option value="straight_line">Straight Line Method</option>
                                    <option value="written_down_value">Written Down Value (WDV)</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Depreciation Rate (%)*</label>
                                <input
                                    type="number"
                                    name="depreciation_rate"
                                    className="form-input"
                                    value={formData.depreciation_rate}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Useful Life (Years)</label>
                                <input
                                    type="number"
                                    name="useful_life_years"
                                    className="form-input"
                                    value={formData.useful_life_years}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Residual Value ()</label>
                                <input
                                    type="number"
                                    name="residual_value"
                                    className="form-input"
                                    value={formData.residual_value}
                                    onChange={handleChange}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Section 4: Maintenance & Insurance */}
                <div className="card" style={{ marginBottom: '20px' }}>
                    <div className="card-header">
                        <h4 className="card-title"> Section 4  Maintenance & Insurance</h4>
                    </div>
                    <div className="card-body">
                        <div className="form-grid">
                            <div className="form-group">
                                <label className="form-label">AMC Vendor</label>
                                <input
                                    type="text"
                                    name="amc_vendor"
                                    className="form-input"
                                    value={formData.amc_vendor}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">AMC End Date</label>
                                <input
                                    type="date"
                                    name="amc_expiry"
                                    className="form-input"
                                    value={formData.amc_expiry}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Insurance Policy No.</label>
                                <input
                                    type="text"
                                    name="insurance_policy_no"
                                    className="form-input"
                                    value={formData.insurance_policy_no}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Insurance Expiry</label>
                                <input
                                    type="date"
                                    name="insurance_expiry"
                                    className="form-input"
                                    value={formData.insurance_expiry}
                                    onChange={handleChange}
                                />
                            </div>
                        </div>

                        <div className="form-group" style={{ marginTop: '15px' }}>
                            <label className="form-label">Additional Notes</label>
                            <textarea
                                name="notes"
                                className="form-input"
                                rows="3"
                                value={formData.notes}
                                onChange={handleChange}
                            ></textarea>
                        </div>
                    </div>
                </div>

                <div className="asset-actions">
                    <button type="button" className="settings-cancel-btn" onClick={() => navigate('/assets')}>
                        Cancel
                    </button>
                    <button type="submit" className="settings-save-btn" disabled={loading}>
                        {loading ? 'Processing...' : ' Save & Create Asset'}
                    </button>
                </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AddAssetScreen;

