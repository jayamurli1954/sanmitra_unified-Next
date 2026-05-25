import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const AssetRegisterScreen = () => {
    const navigate = useNavigate();
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchAssets = useCallback(async () => {
        try {
            setLoading(true);
            const response = await api.get('/assets/');
            setAssets(response.data);
            setError(null);
        } catch (err) {
            console.error('Error fetching assets:', err);
            setError('Failed to load asset register. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAssets();
    }, [fetchAssets]);

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(amount);
    };

    const getStatusColor = (status) => {
        switch (status?.toLowerCase()) {
            case 'active': return '#28a745';
            case 'under maintenance': return '#ffc107';
            case 'scrapped': return '#dc3545';
            default: return '#6c757d';
        }
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="dashboard-header">
                    <div className="dashboard-header-left">
                        <h1 className="dashboard-header-title">Asset Register</h1>
                        <span className="dashboard-header-subtitle">Society property records</span>
                    </div>
                    <div className="dashboard-header-right">
                        <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>
                            Back to Dashboard
                        </button>
                    </div>
                </div>
                <div className="dashboard-content">
                    <div className="settings-section">
                        <div className="loading-text">Loading assets...</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <div className="dashboard-header-left">
                    <h1 className="dashboard-header-title">Asset Register</h1>
                    <span className="dashboard-header-subtitle">Society property records</span>
                </div>
                <div className="dashboard-header-right">
                    <button className="dashboard-logout-button" onClick={() => navigate('/dashboard')}>
                        Back to Dashboard
                    </button>
                </div>
            </div>

            <div className="dashboard-content">
                <div className="settings-tab-content" style={{ maxWidth: '1120px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', marginBottom: '24px' }}>
                        <div>
                            <h2 className="settings-tab-title">Asset Register</h2>
                            <p className="settings-tab-description" style={{ marginBottom: 0 }}>
                                Complete record of society assets and common property.
                            </p>
                        </div>
                        <button
                            className="settings-save-btn"
                            onClick={() => navigate('/assets/add')}
                        >
                            + Add New Asset
                        </button>
                    </div>

                    {error && (
                        <div style={{ background: '#fff1f1', border: '1px solid #f2b8b5', color: 'var(--gm-danger)', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px' }}>
                            {error}
                        </div>
                    )}

                    <div className="settings-section">
                        <h3>Society Assets</h3>
                        <div className="settings-table-container">
                            <table className="settings-table">
                                <thead>
                                    <tr>
                                        <th>Code</th>
                                        <th>Asset Name</th>
                                        <th>Category</th>
                                        <th>Location</th>
                                        <th>Original Cost</th>
                                        <th>Acquisition</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {assets.length === 0 ? (
                                        <tr>
                                            <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                                                No assets recorded yet. Start by adding a society asset.
                                            </td>
                                        </tr>
                                    ) : (
                                        assets.map((asset) => (
                                            <tr key={asset.id} onClick={() => navigate(`/assets/${asset.id}`)} style={{ cursor: 'pointer' }}>
                                                <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{asset.asset_code}</td>
                                                <td style={{ fontWeight: '600' }}>{asset.name}</td>
                                                <td style={{ textTransform: 'capitalize' }}>{asset.category}</td>
                                                <td>{asset.location}</td>
                                                <td>{formatCurrency(asset.original_cost)}</td>
                                                <td style={{ fontSize: '12px' }}>
                                                    {asset.acquisition_type === 'builder_handover' ? 'Builder Handover' : 'Society Purchase'}
                                                </td>
                                                <td>
                                                    <span
                                                        style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            minHeight: '26px',
                                                            padding: '4px 10px',
                                                            borderRadius: '999px',
                                                            fontSize: '12px',
                                                            fontWeight: 700,
                                                            backgroundColor: getStatusColor(asset.status) + '20',
                                                            color: getStatusColor(asset.status),
                                                            border: `1px solid ${getStatusColor(asset.status)}40`,
                                                        }}
                                                    >
                                                        {asset.status}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        className="settings-action-btn"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            navigate(`/assets/${asset.id}`);
                                                        }}
                                                    >
                                                        View
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="settings-section" style={{ background: 'linear-gradient(90deg, #FFF3E0, #FFFFFF)' }}>
                        <h3>Audit Tip</h3>
                        <p style={{ fontSize: '14px', color: 'var(--gm-text-dark)', lineHeight: 1.6 }}>
                            Builder handover assets should reconcile against the <strong>Corpus Fund</strong>.
                            Purchased assets should have a matching payment voucher for audit trail.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AssetRegisterScreen;

