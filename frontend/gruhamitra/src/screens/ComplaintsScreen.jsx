
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { complaintsService } from '../services/complaintsService';
import { authService } from '../services/authService';

const ComplaintsScreen = () => {
    const navigate = useNavigate();
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    const [showModal, setShowModal] = useState(false);
    const [selectedComplaint, setSelectedComplaint] = useState(null);
    const [user, setUser] = useState(null);

    // Form state
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        type: 'other',
        priority: 'medium',
        scope: 'individual'
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
            const data = await complaintsService.getComplaints();
            setComplaints(data);
        } catch (error) {
            console.error('Error loading complaints:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateComplaint = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await complaintsService.createComplaint(formData);
            setShowModal(false);
            setFormData({ title: '', description: '', type: 'other', priority: 'medium', scope: 'individual' });
            loadData();
        } catch (error) {
            console.error('Error creating complaint:', error);
            alert('Failed to submit complaint. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    const handleUpdateStatus = async (id, newStatus) => {
        try {
            await complaintsService.updateComplaint(id, { status: newStatus });
            loadData();
            if (selectedComplaint && selectedComplaint.id === id) {
                setSelectedComplaint(prev => ({ ...prev, status: newStatus }));
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    };

    const filteredComplaints = complaints.filter(c => {
        if (filter === 'all') return true;
        if (filter === 'open') return c.status === 'open' || c.status === 'in_progress';
        if (filter === 'resolved') return c.status === 'resolved' || c.status === 'closed';
        return c.status === filter;
    });

    const getStatusColor = (status) => {
        switch (status) {
            case 'open': return '#E8842A'; // GM Warning
            case 'in_progress': return '#3498db'; // Blue
            case 'resolved': return '#2ecc71'; // Green
            case 'closed': return '#95a5a6'; // Gray
            default: return '#333';
        }
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return '#e74c3c';
            case 'medium': return '#f39c12';
            case 'low': return '#27ae60';
            default: return '#95a5a6';
        }
    };

    if (loading && complaints.length === 0) {
        return <div className="loading-container"><div className="loading-text">Loading Complaints...</div></div>;
    }

    return (
        <div className="dashboard-container">
            {/* Header */}
            <div className="dashboard-header">
                <div className="dashboard-header-left" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>
                    <img src="/gruhamitra/GruhaMitra_Logo.png" alt="GruhaMitra Logo" className="dashboard-logo" />
                    <div className="dashboard-header-text">
                        <div className="dashboard-society-name">{user?.society_name || 'GruhaMitra'}</div>
                        <div className="dashboard-tagline">Complaint Management</div>
                    </div>
                </div>
                <div className="dashboard-header-right">
                    <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">Back to Dashboard</button>
                </div>
            </div>

            <div className="dashboard-content">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 className="dashboard-section-title" style={{ margin: 0 }}> Active Complaints</h2>
                    <button
                        onClick={() => setShowModal(true)}
                        style={{
                            backgroundColor: '#E8842A',
                            color: 'white',
                            border: 'none',
                            padding: '10px 20px',
                            borderRadius: '8px',
                            fontWeight: 'bold',
                            cursor: 'pointer'
                        }}
                    >
                        + New Complaint
                    </button>
                </div>

                {/* Filters */}
                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                    {['all', 'open', 'resolved'].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '20px',
                                border: '1px solid #ddd',
                                backgroundColor: filter === f ? '#007AFF' : 'white',
                                color: filter === f ? 'white' : '#666',
                                cursor: 'pointer',
                                textTransform: 'capitalize'
                            }}
                        >
                            {f}
                        </button>
                    ))}
                </div>

                {/* Complaints Grid */}
                {filteredComplaints.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '50px', background: 'white', borderRadius: '12px' }}>
                        <div style={{ fontSize: '48px', marginBottom: '10px' }}></div>
                        <p style={{ color: '#666' }}>No complaints found for the selected filter.</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                        {filteredComplaints.map(complaint => (
                            <div
                                key={complaint.id}
                                className="dashboard-metric-card"
                                style={{
                                    flexDirection: 'column',
                                    alignItems: 'flex-start',
                                    cursor: 'pointer',
                                    position: 'relative',
                                    padding: '20px'
                                }}
                                onClick={() => setSelectedComplaint(complaint)}
                            >
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    width: '100%',
                                    marginBottom: '10px'
                                }}>
                                    <span style={{
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        textTransform: 'uppercase',
                                        backgroundColor: getStatusColor(complaint.status),
                                        color: 'white',
                                        padding: '2px 8px',
                                        borderRadius: '4px'
                                    }}>
                                        {complaint.status.replace('_', ' ')}
                                    </span>
                                    <span style={{
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: getPriorityColor(complaint.priority)
                                    }}>
                                        {complaint.priority.toUpperCase()} PRIORITY
                                    </span>
                                </div>
                                <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>{complaint.title}</h3>
                                <p style={{
                                    fontSize: '14px',
                                    color: '#666',
                                    margin: '0 0 15px 0',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden'
                                }}>
                                    {complaint.description}
                                </p>
                                <div style={{
                                    fontSize: '12px',
                                    color: '#888',
                                    marginTop: 'auto',
                                    borderTop: '1px solid #eee',
                                    paddingTop: '10px',
                                    width: '100%',
                                    display: 'flex',
                                    justifyContent: 'space-between'
                                }}>
                                    <div>
                                        By: {complaint.user_name} ({complaint.flat_number}) <br />
                                        {new Date(complaint.created_at).toLocaleDateString()}
                                    </div>
                                    <div style={{
                                        alignSelf: 'flex-end',
                                        backgroundColor: complaint.scope === 'common_area' ? '#EEF2FF' : '#F3F4F6',
                                        color: complaint.scope === 'common_area' ? '#4F46E5' : '#4B5563',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        fontWeight: 'bold',
                                        fontSize: '10px'
                                    }}>
                                        {complaint.scope === 'common_area' ? ' COMMON' : ' FLAT'}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* NEW COMPLAINT MODAL */}
            {showModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}>
                    <div style={{
                        backgroundColor: 'white', padding: '30px',
                        borderRadius: '16px', width: '90%', maxWidth: '500px',
                        boxShadow: '0 10px 25px rgba(0,0,0,0.2)'
                    }}>
                        <h2 style={{ marginTop: 0 }}>Log New Complaint</h2>
                        <form onSubmit={handleCreateComplaint}>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Title</label>
                                <input
                                    type="text"
                                    required
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    value={formData.title}
                                    onChange={e => setFormData({ ...formData, title: e.target.value })}
                                />
                            </div>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Category</label>
                                <select
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    value={formData.type}
                                    onChange={e => setFormData({ ...formData, type: e.target.value })}
                                >
                                    <option value="plumbing">Plumbing</option>
                                    <option value="electrical">Electrical</option>
                                    <option value="security">Security</option>
                                    <option value="cleaning">Cleaning</option>
                                    <option value="parking">Parking</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Complaint Scope</label>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    {[
                                        { value: 'individual', label: 'Individual Flat', icon: '' },
                                        { value: 'common_area', label: 'Common Area', icon: '' }
                                    ].map(s => (
                                        <label key={s.value} style={{
                                            flex: 1, textAlign: 'center', padding: '10px', border: '1px solid #ddd',
                                            borderRadius: '8px', cursor: 'pointer',
                                            backgroundColor: formData.scope === s.value ? '#EEF2FF' : 'white',
                                            borderColor: formData.scope === s.value ? '#4F46E5' : '#ddd',
                                            color: formData.scope === s.value ? '#4F46E5' : '#333',
                                            fontWeight: formData.scope === s.value ? 'bold' : 'normal',
                                            transition: 'all 0.2s'
                                        }}>
                                            <input
                                                type="radio" name="scope" value={s.value}
                                                checked={formData.scope === s.value}
                                                onChange={() => setFormData({ ...formData, scope: s.value })}
                                                style={{ display: 'none' }}
                                            />
                                            <div style={{ fontSize: '18px', marginBottom: '4px' }}>{s.icon}</div>
                                            <div style={{ fontSize: '11px' }}>{s.label}</div>
                                        </label>
                                    ))}
                                </div>
                                <p style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
                                    {formData.scope === 'common_area'
                                        ? ' Common area complaints are visible to all residents.'
                                        : ' Individual flat complaints are private to you and admins.'}
                                </p>
                            </div>
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Priority</label>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    {['low', 'medium', 'high'].map(p => (
                                        <label key={p} style={{
                                            flex: 1, textAlign: 'center', padding: '10px', border: '1px solid #ddd',
                                            borderRadius: '8px', cursor: 'pointer',
                                            backgroundColor: formData.priority === p ? '#eee' : 'white',
                                            fontWeight: formData.priority === p ? 'bold' : 'normal'
                                        }}>
                                            <input
                                                type="radio" name="priority" value={p}
                                                checked={formData.priority === p}
                                                onChange={() => setFormData({ ...formData, priority: p })}
                                                style={{ display: 'none' }}
                                            />
                                            {p.toUpperCase()}
                                        </label>
                                    ))}
                                </div>
                            </div>
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Description</label>
                                <textarea
                                    required
                                    rows="4"
                                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button type="button" onClick={() => setShowModal(false)} style={{ flex: 1, padding: '12px', border: 'none', borderRadius: '8px' }}>Cancel</button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    style={{
                                        flex: 2, padding: '12px', border: 'none', borderRadius: '8px',
                                        backgroundColor: '#007AFF', color: 'white', fontWeight: 'bold'
                                    }}
                                >
                                    {submitting ? 'Submitting...' : 'Submit Complaint'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* COMPLAINT DETAIL MODAL */}
            {selectedComplaint && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}>
                    <div style={{
                        backgroundColor: 'white', padding: '30px',
                        borderRadius: '16px', width: '90%', maxWidth: '600px',
                        maxHeight: '80vh', overflowY: 'auto'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                            <div>
                                <h2 style={{ margin: 0 }}>{selectedComplaint.title}</h2>
                                <span style={{ color: '#888', fontSize: '14px' }}>Ticket #{selectedComplaint.id}</span>
                            </div>
                            <button onClick={() => setSelectedComplaint(null)} style={{ border: 'none', background: 'none', fontSize: '24px', cursor: 'pointer' }}></button>
                        </div>

                        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                            <span style={{
                                fontSize: '12px', fontWeight: 'bold',
                                backgroundColor: getStatusColor(selectedComplaint.status),
                                color: 'white', padding: '4px 12px', borderRadius: '20px'
                            }}>
                                {selectedComplaint.status.replace('_', ' ').toUpperCase()}
                            </span>
                            <span style={{
                                fontSize: '12px', fontWeight: 'bold',
                                border: `1px solid ${getPriorityColor(selectedComplaint.priority)}`,
                                color: getPriorityColor(selectedComplaint.priority),
                                padding: '4px 12px', borderRadius: '20px'
                            }}>
                                {selectedComplaint.priority.toUpperCase()} PRIORITY
                            </span>
                            <span style={{
                                fontSize: '12px', fontWeight: 'bold',
                                backgroundColor: selectedComplaint.scope === 'common_area' ? '#EEF2FF' : '#F3F4F6',
                                color: selectedComplaint.scope === 'common_area' ? '#4F46E5' : '#4B5563',
                                padding: '4px 12px', borderRadius: '20px'
                            }}>
                                {selectedComplaint.scope === 'common_area' ? ' COMMON AREA' : ' INDIVIDUAL FLAT'}
                            </span>
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <h4 style={{ margin: '0 0 5px 0' }}>Description</h4>
                            <p style={{ margin: 0, lineHeight: '1.6', color: '#444' }}>{selectedComplaint.description}</p>
                        </div>

                        <div style={{
                            padding: '15px', backgroundColor: '#f9f9f9',
                            borderRadius: '12px', marginBottom: '20px'
                        }}>
                            <div style={{ fontSize: '14px', marginBottom: '5px' }}>
                                <strong>Opened By:</strong> {selectedComplaint.user_name} (Flat {selectedComplaint.flat_number})
                            </div>
                            <div style={{ fontSize: '14px' }}>
                                <strong>Date:</strong> {new Date(selectedComplaint.created_at).toLocaleString()}
                            </div>
                        </div>

                        {/* Admin Controls */}
                        {['admin', 'super_admin', 'secretary'].includes(String(user?.role || '').toLowerCase()) && (
                            <div style={{ borderTop: '1px solid #eee', paddingTop: '20px' }}>
                                <h4 style={{ margin: '0 0 15px 0' }}>Admin Actions</h4>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    {selectedComplaint.status === 'open' && (
                                        <button
                                            onClick={() => handleUpdateStatus(selectedComplaint.id, 'in_progress')}
                                            style={{ flex: 1, padding: '10px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '8px' }}
                                        >
                                            Start Work
                                        </button>
                                    )}
                                    {(selectedComplaint.status === 'open' || selectedComplaint.status === 'in_progress') && (
                                        <button
                                            onClick={() => handleUpdateStatus(selectedComplaint.id, 'resolved')}
                                            style={{ flex: 1, padding: '10px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '8px' }}
                                        >
                                            Mark Resolved
                                        </button>
                                    )}
                                    {selectedComplaint.status === 'resolved' && (
                                        <button
                                            onClick={() => handleUpdateStatus(selectedComplaint.id, 'closed')}
                                            style={{ flex: 1, padding: '10px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '8px' }}
                                        >
                                            Close Ticket
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ComplaintsScreen;

