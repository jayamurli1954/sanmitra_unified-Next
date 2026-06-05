import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';

const AssetDetailScreen = () => {
    const { asset_id } = useParams();
    const navigate = useNavigate();
    const [asset, setAsset] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [scrapping, setScrapping] = useState(false);
    const [scrapReason, setScrapReason] = useState('');
    const [postingAccounting, setPostingAccounting] = useState(false);

    const fetchAsset = useCallback(async () => {
        try {
            setLoading(true);
            const response = await api.get(`/assets/${asset_id}`);
            setAsset(response.data);
            setError(null);
        } catch (err) {
            console.error('Error fetching asset:', err);
            setError('Asset not found');
        } finally {
            setLoading(false);
        }
    }, [asset_id]);

    useEffect(() => {
        fetchAsset();
    }, [fetchAsset]);

    const handleScrap = async () => {
        if (!scrapReason.trim()) {
            alert('Please provide a reason for scrapping.');
            return;
        }
        try {
            await api.post(`/assets/${asset_id}/scrap?scrapping_reason=${encodeURIComponent(scrapReason)}`, {});
            setScrapping(false);
            fetchAsset();
        } catch (err) {
            console.error('Error scrapping asset:', err);
            alert('Failed to scrap asset.');
        }
    };

    const handlePostAccounting = async () => {
        try {
            setPostingAccounting(true);
            const response = await api.post(`/assets/${asset_id}/post-accounting`, {});
            setAsset(response.data);
            alert('Asset posted to accounting. Run Trial Balance again to see it.');
        } catch (err) {
            console.error('Error posting asset to accounting:', err);
            alert(err.response?.data?.detail || 'Failed to post asset to accounting.');
        } finally {
            setPostingAccounting(false);
        }
    };

    const formatCurrency = (amount) => new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(Number(amount || 0));

    const formatDate = (value) => {
        if (!value) return 'Not set';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString();
    };

    const calculateWDV = () => {
        if (!asset) return 0;
        const cost = Number(asset.original_cost || 0);
        const residual = Number(asset.residual_value || 0);
        if (asset.depreciation_method === 'straight_line') {
            const rate = Number(asset.depreciation_rate || 0) / 100;
            const acqDate = new Date(asset.purchase_date || asset.handover_date || asset.created_at);
            const today = new Date();
            const yearsPassed = Math.max(0, (today - acqDate) / (1000 * 60 * 60 * 24 * 365));
            return Math.max(residual, cost - (cost * rate * yearsPassed));
        }
        return cost;
    };

    const canPostAccounting = asset
        && asset.acquisition_type === 'builder_handover'
        && Number(asset.original_cost || 0) > 0
        && asset.accounting_posting_status !== 'posted'
        && !asset.journal_entry_id;

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="dashboard-header">
                    <div className="dashboard-header-left">
                        <h1 className="dashboard-header-title">Asset Register</h1>
                        <span className="dashboard-header-subtitle">Asset details</span>
                    </div>
                    <div className="dashboard-header-right">
                        <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
                    </div>
                </div>
                <div className="dashboard-content">
                    <div className="settings-section">Loading asset...</div>
                </div>
            </div>
        );
    }

    if (!asset) {
        return (
            <div className="dashboard-container">
                <div className="dashboard-header">
                    <div className="dashboard-header-left">
                        <h1 className="dashboard-header-title">Asset Register</h1>
                        <span className="dashboard-header-subtitle">Asset details</span>
                    </div>
                    <div className="dashboard-header-right">
                        <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
                    </div>
                </div>
                <div className="dashboard-content">
                    <div className="settings-tab-content" style={{ maxWidth: '900px' }}>
                        <div style={{ background: '#fff1f1', border: '1px solid #f2b8b5', color: '#C0392B', borderRadius: '8px', padding: '16px' }}>
                            {error || 'Asset not found'}
                        </div>
                        <button className="settings-cancel-btn" onClick={() => navigate('/assets')} style={{ marginTop: '18px' }}>
                            Back to Register
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container asset-detail-page">
            <style>{`
                .asset-detail-page .detail-wrap { max-width: 1120px; width: 100%; }
                .asset-detail-page .asset-hero {
                    display: flex;
                    justify-content: space-between;
                    gap: 18px;
                    align-items: flex-start;
                    margin-bottom: 24px;
                }
                .asset-detail-page .detail-grid {
                    display: grid;
                    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
                    gap: 24px;
                }
                .asset-detail-page .detail-card {
                    background: #fff;
                    border: 1px solid #f0e3d3;
                    border-radius: 8px;
                    box-shadow: 0 6px 20px rgba(92, 52, 18, 0.06);
                    overflow: hidden;
                    margin-bottom: 22px;
                }
                .asset-detail-page .detail-card h3 {
                    margin: 0;
                    padding: 18px 24px;
                    background: linear-gradient(90deg, #FFF3E0, #FFFFFF);
                    border-bottom: 1px solid #f0e3d3;
                    color: #5A2E0A;
                    font-size: 18px;
                }
                .asset-detail-page .detail-body { padding: 22px 24px; }
                .asset-detail-page .detail-row {
                    display: flex;
                    justify-content: space-between;
                    gap: 18px;
                    padding: 12px 0;
                    border-bottom: 1px solid #f5eadc;
                }
                .asset-detail-page .detail-row:last-child { border-bottom: 0; }
                .asset-detail-page .detail-label { color: #8E6A3A; font-size: 14px; }
                .asset-detail-page .detail-value { color: #3A1F05; font-weight: 700; text-align: right; }
                .asset-detail-page .metric {
                    padding: 18px;
                    border-radius: 8px;
                    background: #FFF7EC;
                    border: 1px solid #f0d7b5;
                    margin-bottom: 14px;
                }
                .asset-detail-page .metric-label { color: #8E6A3A; font-size: 12px; font-weight: 800; text-transform: uppercase; }
                .asset-detail-page .metric-value { color: #5A2E0A; font-size: 26px; font-weight: 900; margin-top: 6px; }
                .asset-detail-page .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
                .asset-detail-page .modal-card { background: white; padding: 28px; border-radius: 8px; width: 520px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
                .asset-detail-page textarea { width: 100%; border: 1px solid #d9d9d9; border-radius: 8px; padding: 12px; font-size: 15px; box-sizing: border-box; }
                @media (max-width: 900px) { .asset-detail-page .detail-grid { grid-template-columns: 1fr; } }
            `}</style>

            <div className="dashboard-header">
                <div className="dashboard-header-left">
                    <h1 className="dashboard-header-title">Asset Register</h1>
                    <span className="dashboard-header-subtitle">Asset details and valuation</span>
                </div>
                <div className="dashboard-header-right">
                    <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
                </div>
            </div>

            <div className="dashboard-content">
                <div className="settings-tab-content detail-wrap">
                    <div className="asset-hero">
                        <div>
                            <h2 className="settings-tab-title">{asset.name}</h2>
                            <p className="settings-tab-description" style={{ marginBottom: 0 }}>
                                Asset Code: <strong>{asset.asset_code}</strong>
                            </p>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                            <button className="settings-cancel-btn" onClick={() => navigate('/assets')}>Back to Register</button>
                            {canPostAccounting && (
                                <button className="settings-save-btn" onClick={handlePostAccounting} disabled={postingAccounting}>
                                    {postingAccounting ? 'Posting...' : 'Post to Accounting'}
                                </button>
                            )}
                            {!asset.is_scrapped && (
                                <button className="settings-save-btn" style={{ background: '#C0392B' }} onClick={() => setScrapping(true)}>
                                    Mark as Scrapped
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="detail-grid">
                        <div>
                            <div className="detail-card">
                                <h3>Identity & Source</h3>
                                <div className="detail-body">
                                    <div className="detail-row"><span className="detail-label">Category</span><span className="detail-value" style={{ textTransform: 'capitalize' }}>{asset.category}</span></div>
                                    <div className="detail-row"><span className="detail-label">Location</span><span className="detail-value">{asset.location || 'Not specified'}</span></div>
                                    <div className="detail-row"><span className="detail-label">Quantity</span><span className="detail-value">{asset.quantity || 1}</span></div>
                                    <div className="detail-row"><span className="detail-label">Acquisition</span><span className="detail-value">{asset.acquisition_type === 'builder_handover' ? 'Builder Handover' : 'Society Purchase'}</span></div>
                                    <div className="detail-row"><span className="detail-label">Date</span><span className="detail-value">{formatDate(asset.purchase_date || asset.handover_date)}</span></div>
                                    <div className="detail-row"><span className="detail-label">Status</span><span className="detail-value">{asset.status}</span></div>
                                </div>
                            </div>

                            <div className="detail-card">
                                <h3>Maintenance & Insurance</h3>
                                <div className="detail-body">
                                    <div className="detail-row"><span className="detail-label">AMC Vendor</span><span className="detail-value">{asset.amc_vendor || 'None'}</span></div>
                                    <div className="detail-row"><span className="detail-label">AMC Expiry</span><span className="detail-value">{formatDate(asset.amc_expiry)}</span></div>
                                    <div className="detail-row"><span className="detail-label">Insurance Policy</span><span className="detail-value">{asset.insurance_policy_no || 'None'}</span></div>
                                    <div className="detail-row"><span className="detail-label">Insurance Expiry</span><span className="detail-value">{formatDate(asset.insurance_expiry)}</span></div>
                                </div>
                            </div>
                        </div>

                        <div>
                            <div className="detail-card">
                                <h3>Financial Valuation</h3>
                                <div className="detail-body">
                                    <div className="metric">
                                        <div className="metric-label">Original Cost</div>
                                        <div className="metric-value">{formatCurrency(asset.original_cost)}</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-label">Estimated Current Value</div>
                                        <div className="metric-value">{formatCurrency(calculateWDV())}</div>
                                    </div>
                                    <div className="detail-row"><span className="detail-label">Depreciation</span><span className="detail-value">{asset.depreciation_rate}% ({asset.depreciation_method === 'straight_line' ? 'SLM' : 'WDV'})</span></div>
                                    <div className="detail-row"><span className="detail-label">Useful Life</span><span className="detail-value">{asset.useful_life_years || 0} years</span></div>
                                    <div className="detail-row"><span className="detail-label">Residual Value</span><span className="detail-value">{formatCurrency(asset.residual_value)}</span></div>
                                    <div className="detail-row"><span className="detail-label">Account Head</span><span className="detail-value">{asset.account_code || '16003'}</span></div>
                                    <div className="detail-row"><span className="detail-label">Accounting Status</span><span className="detail-value">{asset.accounting_posting_status === 'posted' ? `Posted${asset.journal_entry_id ? ` (#${asset.journal_entry_id})` : ''}` : 'Not posted'}</span></div>
                                </div>
                            </div>

                            <div className="detail-card">
                                <h3>Notes & History</h3>
                                <div className="detail-body">
                                    <p style={{ whiteSpace: 'pre-wrap', color: '#5A2E0A', fontSize: '15px', lineHeight: 1.6, margin: 0 }}>
                                        {asset.notes || 'No additional notes provided.'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {scrapping && (
                <div className="modal-overlay">
                    <div className="modal-card">
                        <h3 style={{ color: '#C0392B', marginTop: 0 }}>Confirm Asset Scrapping</h3>
                        <p style={{ color: '#8E6A3A' }}>This marks the asset inactive for audit purposes.</p>
                        <label style={{ display: 'block', color: '#5A2E0A', fontWeight: 700, marginBottom: '8px' }}>Reason for Scrapping*</label>
                        <textarea rows="4" placeholder="e.g. Beyond economic repair, replaced..." value={scrapReason} onChange={(e) => setScrapReason(e.target.value)} />
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '22px' }}>
                            <button className="settings-cancel-btn" onClick={() => setScrapping(false)}>Cancel</button>
                            <button className="settings-save-btn" style={{ background: '#C0392B' }} onClick={handleScrap}>Perform Scrapping</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AssetDetailScreen;
