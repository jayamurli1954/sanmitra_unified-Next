import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../services/authService';
import visitorsService from '../services/visitorsService';
import flatsService from '../services/flatsService';
import staffService from '../services/staffService';
import settingsService from '../services/settingsService';
import { QRCodeSVG } from 'qrcode.react';

const STATIC_VISITOR_TYPES = [
  { value: 'guest', label: 'Guest' },
  { value: 'delivery', label: 'Delivery' },
  { value: 'cab', label: 'Cab' },
  { value: 'vendor', label: 'Vendor' },
  { value: 'service_staff', label: 'Service Staff' },
  { value: 'domestic_help', label: 'Domestic Help' },
  { value: 'other', label: 'Other' },
];

const VEHICLE_TYPES = [
  { value: 'none', label: 'None / Walking' },
  { value: 'bike', label: 'Two Wheeler (Scooter/Bike)' },
  { value: 'car', label: 'Car' },
  { value: 'auto', label: 'Auto Rickshaw' },
  { value: 'van', label: 'Van / Commercial' },
  { value: 'other', label: 'Other' },
];

const STATUS_COLORS = {
  pending: '#E8842A',
  approved: '#007AFF',
  rejected: '#C53030',
  inside: '#2F855A',
  exited: '#718096',
  cancelled: '#718096',
};

const isSecurityUser = (user) => {
  const normalized = String(user?.role || '').trim().toLowerCase();
  return ['security', 'security_guard', 'guard', 'gate', 'watchman'].includes(normalized);
};

const formatDateTime = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value);
  }
};

const VisitorsScreen = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('visitors'); // 'visitors' or 'staff'
  const [user, setUser] = useState(null);
  const [visitors, setVisitors] = useState([]);
  const [flats, setFlats] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [attendanceLogs, setAttendanceLogs] = useState([]);
  const [societySettings, setSocietySettings] = useState(null);
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [message, setMessage] = useState({ type: '', text: '' });
  
  // Passcode verification state
  const [passcode, setPasscode] = useState('');
  const [verifiedGuest, setVerifiedGuest] = useState(null);

  // Expected visitor pass modal/view state (for residents)
  const [createdPass, setCreatedPass] = useState(null);

  // Camera QR scanner state
  const [scanning, setScanning] = useState(false);
  const [scannerSupported, setScannerSupported] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const [formData, setFormData] = useState({
    visitor_name: '',
    phone_number: '',
    visitor_type: 'guest',
    flat_number: '',
    vehicle_type: 'none',
    vehicle_number: '',
    vendor_name: '',
    purpose: '',
    validity_hours: 24,
  });

  const isGuard = useMemo(() => isSecurityUser(user), [user]);

  // Combine static types and admin-configured brands
  const brandsList = useMemo(() => {
    const custom = societySettings?.custom_visitor_brands || [];
    return [
      { value: 'Swiggy', label: 'Swiggy' },
      { value: 'Zomato', label: 'Zomato' },
      { value: 'Zepto', label: 'Zepto' },
      { value: 'Amazon', label: 'Amazon' },
      { value: 'Flipkart', label: 'Flipkart' },
      { value: 'Blinkit', label: 'Blinkit' },
      { value: 'Apollo Pharmacy', label: 'Apollo Pharmacy' },
      { value: 'Urban Company', label: 'Urban Company' },
      ...custom.map((b) => ({ value: b.name, label: b.name })),
    ];
  }, [societySettings]);

  // Check BarcodeDetector support on mount
  useEffect(() => {
    if (typeof window !== 'undefined' && 'BarcodeDetector' in window) {
      setScannerSupported(true);
    }
  }, []);

  // Handle URL query parameter approval/rejection triggers (from service worker)
  useEffect(() => {
    const action = searchParams.get('action');
    const visitorId = searchParams.get('id');
    if (action && visitorId) {
      setSearchParams({}, { replace: true });
      const executeQueryAction = async () => {
        setSubmitting(true);
        setMessage({ type: '', text: '' });
        try {
          if (action === 'approve') {
            await visitorsService.approveVisitor(visitorId);
            setMessage({ type: 'success', text: 'Visitor approved successfully.' });
          } else if (action === 'reject') {
            await visitorsService.rejectVisitor(visitorId);
            setMessage({ type: 'success', text: 'Visitor rejected successfully.' });
          }
          await loadData();
        } catch (error) {
          setMessage({ type: 'error', text: error.response?.data?.detail || `Failed to ${action} visitor.` });
        } finally {
          setSubmitting(false);
        }
      };
      executeQueryAction();
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const startScanning = async () => {
    setMessage({ type: '', text: '' });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', true);
        videoRef.current.play();
        setScanning(true);
      }
    } catch (error) {
      console.error('Camera access failed:', error);
      setMessage({ type: 'error', text: 'Failed to access camera. Please enter passcode manually.' });
    }
  };

  const stopScanning = useCallback(() => {
    setScanning(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Run barcode detection loop when scanning is active
  useEffect(() => {
    let active = true;
    const detect = async () => {
      if (!scanning || !videoRef.current || !active) return;
      try {
        const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
        const barcodes = await detector.detect(videoRef.current);
        if (barcodes.length > 0 && active) {
          const code = barcodes[0].rawValue;
          stopScanning();
          active = false;
          await handleVerifyQR(code);
          return;
        }
      } catch (err) {
        console.warn('Detector error:', err);
      }
      if (scanning && active) {
        requestAnimationFrame(detect);
      }
    };

    if (scanning) {
      requestAnimationFrame(detect);
    }

    return () => {
      active = false;
    };
  }, [scanning, stopScanning]);

  const handleVerifyQR = async (codeValue) => {
    if (!codeValue) return;
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    setVerifiedGuest(null);
    try {
      const guest = await visitorsService.verifyPass(codeValue.trim());
      setVerifiedGuest(guest);
      setMessage({ type: 'success', text: `Pass verified: ${guest.visitor_name} for Flat ${guest.flat_number}.` });
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Invalid passcode or QR code.' });
    } finally {
      setSubmitting(false);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      
      // Load flats
      const allFlats = await flatsService.getFlats();
      setFlats(allFlats || []);

      // Load society settings
      try {
        const settings = await settingsService.getSocietySettings();
        setSocietySettings(settings);
      } catch (err) {
        console.warn('Could not load society settings', err);
      }

      setFormData((prev) => ({
        ...prev,
        flat_number: prev.flat_number || currentUser?.flat_number || currentUser?.unit_number || (allFlats[0]?.flat_number || ''),
      }));

      if (activeTab === 'visitors') {
        const rows = await visitorsService.listVisitors();
        setVisitors(rows);
      } else {
        const staff = await staffService.listStaff();
        setStaffList(staff.filter((s) => s.status === 'active'));
        const logs = await staffService.listAttendance();
        setAttendanceLogs(logs);
      }
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not load data.' });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
      navigate('/login');
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to logout.' });
    }
  };

  const handleShareWhatsApp = () => {
    if (!createdPass) return;
    const publicPassUrl = `${window.location.origin}/gruhamitra/public/pass/${createdPass.id}`;
    const messageText = `*GruhaMitra Guest Pass*

Dear ${createdPass.visitor_name},
You are invited to Flat ${createdPass.flat_number}.
Please show this QR Pass or Passcode at the gate for quick entry:

🔑 *Passcode:* ${createdPass.passcode}
📱 *QR Code Link:* ${publicPassUrl}`;

    const whatsappUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(messageText)}`;
    window.open(whatsappUrl, '_blank');
  };

  const handleCreateVisitor = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    setCreatedPass(null);

    // If visitor type is delivery/cab/vendor, auto-populate purpose/vendor if not provided
    const submissionData = { ...formData };
    if (['delivery', 'cab', 'vendor'].includes(formData.visitor_type) && !formData.vendor_name) {
      submissionData.vendor_name = formData.visitor_type;
    }

    try {
      const result = await visitorsService.createVisitor(submissionData);
      
      setFormData({
        visitor_name: '',
        phone_number: '',
        visitor_type: 'guest',
        flat_number: flats[0]?.flat_number || '',
        vehicle_type: 'none',
        vehicle_number: '',
        vendor_name: '',
        purpose: '',
        validity_hours: 24,
      });

      if (!isGuard) {
        // Residents get a shareable QR pass
        setCreatedPass(result);
        setMessage({ type: 'success', text: 'Expected visitor pass generated successfully!' });
      } else {
        setMessage({ type: 'success', text: 'Visitor entry created successfully.' });
      }
      
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message || 'Could not create entry.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyPasscode = async (event) => {
    event.preventDefault();
    if (!passcode.trim()) return;
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    setVerifiedGuest(null);

    try {
      const guest = await visitorsService.verifyPass(passcode.trim());
      setVerifiedGuest(guest);
      setPasscode('');
      setMessage({ type: 'success', text: `Pass verified: ${guest.visitor_name} for Flat ${guest.flat_number}.` });
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Invalid passcode or QR code.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleStaffCheckIn = async (staffId) => {
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      await staffService.checkInStaff(staffId);
      setMessage({ type: 'success', text: 'Staff checked in.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Check-in failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleStaffCheckOut = async (logId) => {
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      await staffService.checkOutStaff(logId);
      setMessage({ type: 'success', text: 'Staff checked out.' });
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Check-out failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  const runAction = async (action, visitorId) => {
    setSubmitting(true);
    setMessage({ type: '', text: '' });
    try {
      if (action === 'approve') await visitorsService.approveVisitor(visitorId);
      if (action === 'reject') await visitorsService.rejectVisitor(visitorId);
      if (action === 'check_in') await visitorsService.checkInVisitor(visitorId);
      if (action === 'check_out') await visitorsService.checkOutVisitor(visitorId);
      await loadData();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Action failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  // Memoized visitor stats
  const visitorStats = useMemo(() => {
    return {
      pending: visitors.filter((row) => row.status === 'pending').length,
      inside: visitors.filter((row) => row.status === 'inside').length,
      approved: visitors.filter((row) => row.status === 'approved').length,
      today: visitors.filter((row) => {
        if (!row.created_at) return false;
        return new Date(row.created_at).toDateString() === new Date().toDateString();
      }).length,
    };
  }, [visitors]);

  const filteredVisitors = visitors.filter((row) => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['pending', 'approved', 'inside'].includes(row.status);
    return row.status === filter;
  });

  const getActiveAttendanceLog = (staffId) => {
    return attendanceLogs.find((log) => log.staff_id === staffId && log.status === 'inside');
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <img src="/gruhamitra/GruhaMitra_Logo.png" alt="GruhaMitra Logo" className="dashboard-logo" />
          <div className="dashboard-header-text">
            <div className="dashboard-society-name">{user?.society_name || 'GruhaMitra'}</div>
            <div className="dashboard-tagline">Gate Security and Staff Attendance</div>
          </div>
        </div>
        <div className="dashboard-header-right">
          {isGuard ? (
            <button onClick={handleLogout} className="dashboard-logout-button" style={{ backgroundColor: '#c53030' }}>
              Logout
            </button>
          ) : (
            <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
              Back to Dashboard
            </button>
          )}
        </div>
      </div>

      {/* Main Content Container */}
      <div className="dashboard-content">
        {/* Status/Success Message Alerts */}
        {message.text && (
          <div className={`message ${message.type}`} style={{
            marginBottom: '20px',
            padding: '12px 14px',
            borderRadius: '8px',
            backgroundColor: message.type === 'error' ? '#fee' : '#efe',
            color: message.type === 'error' ? '#c00' : '#0c0',
            border: `1px solid ${message.type === 'error' ? '#f44' : '#4f4'}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>{message.text}</span>
            <button onClick={() => setMessage({ type: '', text: '' })} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
          </div>
        )}

        {/* Tab Controls (Only shown for guards/managers) */}
        {isGuard && (
          <div style={{ display: 'flex', borderBottom: '2px solid #E5E5EA', marginBottom: '24px', gap: '8px' }}>
            <button
              onClick={() => setActiveTab('visitors')}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                fontWeight: 'bold',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'visitors' ? '3px solid #007AFF' : '3px solid transparent',
                color: activeTab === 'visitors' ? '#007AFF' : '#8E8E93',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Visitors Register
            </button>
            <button
              onClick={() => setActiveTab('staff')}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                fontWeight: 'bold',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'staff' ? '3px solid #007AFF' : '3px solid transparent',
                color: activeTab === 'staff' ? '#007AFF' : '#8E8E93',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Staff Attendance
            </button>
          </div>
        )}

        {activeTab === 'visitors' ? (
          <>
            {/* Quick Metrics */}
            <div className="dashboard-metrics-grid" style={{ marginBottom: '24px' }}>
              <div className="dashboard-metric-card">
                <div className="dashboard-metric-label">Waiting Approval</div>
                <div className="dashboard-metric-value" style={{ color: '#E8842A' }}>{visitorStats.pending}</div>
              </div>
              <div className="dashboard-metric-card">
                <div className="dashboard-metric-label">Visitors Inside</div>
                <div className="dashboard-metric-value" style={{ color: '#2F855A' }}>{visitorStats.inside}</div>
              </div>
              <div className="dashboard-metric-card">
                <div className="dashboard-metric-label">Approved Today</div>
                <div className="dashboard-metric-value">{visitorStats.approved}</div>
              </div>
              <div className="dashboard-metric-card">
                <div className="dashboard-metric-label">Total Entries Today</div>
                <div className="dashboard-metric-value">{visitorStats.today}</div>
              </div>
            </div>

            {/* Quick Passcode Verification (For Guards) */}
            {isGuard && (
              <div className="settings-section" style={{ marginBottom: '24px', padding: '16px' }}>
                <h3 className="settings-section-title" style={{ fontSize: '16px', marginBottom: '12px' }}>Verify Guest Pass (Passcode / QR)</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <form onSubmit={handleVerifyPasscode} style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <input
                      value={passcode}
                      onChange={(e) => setPasscode(e.target.value)}
                      placeholder="Enter 6-digit passcode or scan visitor code"
                      maxLength={36}
                      style={{ flex: 1, minWidth: '200px', padding: '10px 14px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '15px' }}
                    />
                    <button className="settings-save-btn" type="submit" disabled={submitting} style={{ width: 'auto', padding: '10px 20px', margin: 0 }}>
                      Verify Pass
                    </button>
                    {scannerSupported && !scanning && (
                      <button
                        className="settings-action-btn"
                        type="button"
                        onClick={startScanning}
                        style={{ width: 'auto', padding: '10px 20px', margin: 0, backgroundColor: '#007AFF', color: 'white' }}
                      >
                        📷 Scan QR
                      </button>
                    )}
                  </form>

                  {/* Camera QR Scanner Interface */}
                  {scanning && (
                    <div style={{
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      background: '#000',
                      padding: '16px',
                      borderRadius: '12px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        position: 'absolute',
                        top: '12px',
                        left: '12px',
                        color: 'white',
                        fontSize: '12px',
                        zIndex: 10,
                        backgroundColor: 'rgba(0,0,0,0.6)',
                        padding: '4px 8px',
                        borderRadius: '4px'
                      }}>
                        Align QR Code within the camera view
                      </div>
                      <video
                        ref={videoRef}
                        style={{
                          width: '100%',
                          maxWidth: '350px',
                          height: '250px',
                          objectFit: 'cover',
                          borderRadius: '8px'
                        }}
                      />
                      <button
                        className="settings-action-btn"
                        type="button"
                        onClick={stopScanning}
                        style={{
                          marginTop: '12px',
                          width: 'auto',
                          padding: '8px 24px',
                          backgroundColor: '#c53030',
                          color: 'white',
                          marginRight: 0
                        }}
                      >
                        Cancel Scan
                      </button>
                    </div>
                  )}
                </div>

                {/* Verified Guest Details */}
                {verifiedGuest && (
                  <div style={{ marginTop: '16px', padding: '16px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <div>
                        <h4 style={{ margin: '0 0 4px 0', color: '#0369a1' }}>Verified Guest: {verifiedGuest.visitor_name}</h4>
                        <p style={{ margin: 0, fontSize: '14px', color: '#0284c7' }}>
                          Visiting Flat: <strong>{verifiedGuest.flat_number}</strong> | Type: <strong>{verifiedGuest.visitor_type}</strong>
                        </p>
                        {verifiedGuest.phone_number && <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#555' }}>Phone: {verifiedGuest.phone_number}</p>}
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        {['pending', 'approved'].includes(verifiedGuest.status) && (
                          <button
                            className="settings-save-btn"
                            onClick={async () => {
                              await runAction('check_in', verifiedGuest.id);
                              setVerifiedGuest(null);
                            }}
                            style={{ padding: '6px 12px', fontSize: '13px', margin: 0, width: 'auto' }}
                          >
                            Check In Now
                          </button>
                        )}
                        <button
                          className="settings-action-btn"
                          onClick={() => setVerifiedGuest(null)}
                          style={{ padding: '6px 12px', fontSize: '13px', margin: 0, width: 'auto' }}
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Resident shareable Pass Card */}
            {createdPass && (
              <div className="settings-section" style={{ marginBottom: '24px', padding: '24px', textAlign: 'center', background: '#F2F2F7', borderRadius: '12px' }}>
                <h3 style={{ color: '#007AFF', margin: '0 0 12px 0' }}>Invite Pass Generated</h3>
                <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', display: 'inline-block', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '18px' }}>{createdPass.visitor_name}</h4>
                  <p style={{ color: '#666', margin: '0 0 16px 0', fontSize: '14px' }}>Expected Guest for Flat {createdPass.flat_number}</p>
                  
                  {/* QR SVG */}
                  <div style={{ background: '#f9f9f9', padding: '16px', borderRadius: '8px', display: 'inline-block', marginBottom: '16px' }}>
                    <QRCodeSVG value={createdPass.id} size={150} />
                  </div>
                  
                  <div style={{ fontSize: '20px', fontWeight: 'bold', letterSpacing: '2px', color: '#007AFF' }}>
                    Passcode: {createdPass.passcode}
                  </div>
                  <p style={{ fontSize: '11px', color: '#8E8E93', margin: '8px 0 0 0' }}>Show this code or QR pass at the security gate for quick entry</p>
                </div>
                <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <button
                    className="settings-save-btn"
                    type="button"
                    style={{
                      width: 'auto',
                      padding: '8px 24px',
                      margin: 0,
                      backgroundColor: '#25D366',
                      color: 'white',
                      fontWeight: 'bold',
                      borderRadius: '8px',
                      border: 'none',
                      cursor: 'pointer'
                    }}
                    onClick={handleShareWhatsApp}
                  >
                    Share on WhatsApp
                  </button>
                  <button className="settings-action-btn" type="button" style={{ width: 'auto', padding: '8px 24px', margin: 0 }} onClick={() => setCreatedPass(null)}>Done</button>
                </div>
              </div>
            )}

            {/* Two-Column Grid: Form & List */}
            <div className="dashboard-main-grid" style={{ alignItems: 'start' }}>
              
              {/* Entry Form */}
              <div className="settings-section">
                <h2 className="settings-section-title">{isGuard ? 'Log Visitor Entry' : 'Add Expected Guest'}</h2>
                <form onSubmit={handleCreateVisitor} className="settings-form">
                  <div className="settings-form-row">
                    <div className="settings-form-group">
                      <label>Visitor Name *</label>
                      <input
                        value={formData.visitor_name}
                        onChange={(e) => setFormData({ ...formData, visitor_name: e.target.value })}
                        required
                        placeholder="Visitor's name"
                      />
                    </div>
                    <div className="settings-form-group">
                      <label>Phone Number</label>
                      <input
                        value={formData.phone_number}
                        onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                        placeholder="Mobile number"
                        type="tel"
                      />
                    </div>
                  </div>

                  <div className="settings-form-row">
                    <div className="settings-form-group">
                      <label>Visitor Type</label>
                      <select
                        value={formData.visitor_type}
                        onChange={(e) => setFormData({ ...formData, visitor_type: e.target.value })}
                      >
                        {STATIC_VISITOR_TYPES.map((item) => (
                          <option key={item.value} value={item.value}>{item.label}</option>
                        ))}
                      </select>
                    </div>

                    <div className="settings-form-group">
                      <label>Flat Number *</label>
                      {isGuard ? (
                        <select
                          value={formData.flat_number}
                          onChange={(e) => setFormData({ ...formData, flat_number: e.target.value })}
                          required
                        >
                          <option value="">-- Select Flat --</option>
                          {flats.map((f) => (
                            <option key={f.id} value={f.flat_number}>Flat {f.flat_number}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          value={formData.flat_number}
                          readOnly
                          style={{ backgroundColor: '#F2F2F7', cursor: 'not-allowed' }}
                        />
                      )}
                    </div>
                  </div>

                  {!isGuard && (
                    <div className="settings-form-row">
                      <div className="settings-form-group">
                        <label>Pass Validity Limit *</label>
                        <select
                          value={formData.validity_hours}
                          onChange={(e) => setFormData({ ...formData, validity_hours: parseInt(e.target.value) })}
                        >
                          <option value={4}>4 Hours</option>
                          <option value={8}>8 Hours</option>
                          <option value={12}>12 Hours</option>
                          <option value={24}>24 Hours</option>
                        </select>
                      </div>
                      <div className="settings-form-group" style={{ opacity: 0, pointerEvents: 'none' }}>
                        <label>&nbsp;</label>
                        <input disabled />
                      </div>
                    </div>
                  )}

                  {/* Render Brand picker if type is delivery/cab/vendor */}
                  {['delivery', 'cab', 'vendor'].includes(formData.visitor_type) && (
                    <div className="settings-form-group" style={{ marginBottom: '16px' }}>
                      <label>One-Tap Visitor Brand *</label>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                        {brandsList.map((brand) => (
                          <button
                            key={brand.value}
                            type="button"
                            onClick={() => setFormData({ ...formData, vendor_name: brand.value, visitor_name: brand.value })}
                            style={{
                              padding: '8px 14px',
                              borderRadius: '20px',
                              border: '1px solid #ddd',
                              background: formData.vendor_name === brand.value ? '#007AFF' : '#fff',
                              color: formData.vendor_name === brand.value ? '#fff' : '#333',
                              fontSize: '13px',
                              cursor: 'pointer',
                              fontWeight: '600'
                            }}
                          >
                            {brand.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="settings-form-row">
                    <div className="settings-form-group">
                      <label>Vehicle Type</label>
                      <select
                        value={formData.vehicle_type}
                        onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                      >
                        {VEHICLE_TYPES.map((item) => (
                          <option key={item.value} value={item.value}>{item.label}</option>
                        ))}
                      </select>
                    </div>

                    <div className="settings-form-group">
                      <label>Vehicle Number {formData.vehicle_type !== 'none' && '*'}</label>
                      <input
                        value={formData.vehicle_number}
                        onChange={(e) => setFormData({ ...formData, vehicle_number: e.target.value })}
                        disabled={formData.vehicle_type === 'none'}
                        required={formData.vehicle_type !== 'none'}
                        placeholder={formData.vehicle_type === 'none' ? 'N/A - Walking' : 'e.g. KA-03-HA-1234'}
                        style={{ backgroundColor: formData.vehicle_type === 'none' ? '#f5f5f5' : '#fff' }}
                      />
                    </div>
                  </div>

                  <div className="settings-form-group">
                    <label>Purpose / Description</label>
                    <textarea
                      rows={2}
                      value={formData.purpose}
                      onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                      placeholder="e.g. Guest visit, plumbing repairs, courier delivery"
                    />
                  </div>

                  <button className="settings-save-btn" type="submit" disabled={submitting}>
                    {submitting ? 'Saving...' : (isGuard ? 'Create Gate Entry' : 'Add expected visitor')}
                  </button>
                </form>
              </div>

              {/* Visitor List */}
              <div className="settings-section">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                  <h2 className="settings-section-title" style={{ margin: 0 }}>Register Log</h2>
                  <button className="settings-action-btn" style={{ width: 'auto', padding: '6px 14px' }} type="button" onClick={loadData}>Refresh</button>
                </div>
                
                {/* Filters */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  {['all', 'active', 'pending', 'approved', 'inside', 'exited', 'rejected'].map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setFilter(item)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '20px',
                        border: '1px solid #ddd',
                        backgroundColor: filter === item ? '#007AFF' : '#fff',
                        color: filter === item ? '#fff' : '#444',
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}
                    >
                      {item}
                    </button>
                  ))}
                </div>

                {filteredVisitors.length === 0 ? (
                  <div style={{ padding: '32px 16px', background: '#f9f9f9', borderRadius: '8px', textAlign: 'center', color: '#8E8E93' }}>
                    No visitor entries match this filter.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {filteredVisitors.map((entry) => (
                      <div key={entry.id} className="dashboard-metric-card" style={{ alignItems: 'stretch', flexDirection: 'column', padding: '16px', border: '1px solid #E5E5EA' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                          <div>
                            <strong style={{ fontSize: '15px' }}>{entry.visitor_name}</strong>
                            <div style={{ color: '#666', fontSize: '13px', marginTop: '4px' }}>
                              <span style={{ textTransform: 'capitalize' }}>{entry.visitor_type?.replace(/_/g, ' ')}</span> for Flat <strong>{entry.flat_number}</strong>
                            </div>
                          </div>
                          <span style={{
                            alignSelf: 'flex-start',
                            color: 'white',
                            backgroundColor: STATUS_COLORS[entry.status] || '#718096',
                            borderRadius: '999px',
                            padding: '4px 10px',
                            textTransform: 'capitalize',
                            fontSize: '11px',
                            fontWeight: 'bold',
                          }}>
                            {entry.status}
                          </span>
                        </div>
                        <div style={{ marginTop: '10px', color: '#555', fontSize: '13px', lineHeight: '1.4' }}>
                          {entry.vendor_name && <div>Brand: {entry.vendor_name}</div>}
                          {entry.phone_number && <div>Mobile: {entry.phone_number}</div>}
                          {entry.vehicle_type !== 'none' && <div>Vehicle: <span style={{ textTransform: 'uppercase' }}>{entry.vehicle_type} ({entry.vehicle_number})</span></div>}
                          {entry.purpose && <div>Purpose: {entry.purpose}</div>}
                          {entry.passcode && entry.status === 'pending' && <div style={{ color: '#007AFF', fontWeight: 'bold' }}>Passcode: {entry.passcode}</div>}
                          <div style={{ color: '#8e8e93', marginTop: '4px', fontSize: '11px' }}>Logged: {formatDateTime(entry.created_at)}</div>
                          {entry.checked_in_at && <div>Entry: {formatDateTime(entry.checked_in_at)}</div>}
                          {entry.checked_out_at && <div>Exit: {formatDateTime(entry.checked_out_at)}</div>}
                        </div>

                        {/* Guard / Resident Actions */}
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                          {/* Residents Approve/Reject Expected Guest requests */}
                          {!isGuard && entry.status === 'pending' && (
                            <>
                              <button className="settings-save-btn" type="button" disabled={submitting} onClick={() => runAction('approve', entry.id)} style={{ padding: '6px 12px', fontSize: '12px', width: 'auto', margin: 0 }}>Approve</button>
                              <button className="settings-action-btn" type="button" disabled={submitting} onClick={() => runAction('reject', entry.id)} style={{ padding: '6px 12px', fontSize: '12px', width: 'auto', margin: 0 }}>Reject</button>
                            </>
                          )}
                          {/* Guards Check-In / Out */}
                          {isGuard && ['pending', 'approved'].includes(entry.status) && (
                            <button className="settings-save-btn" type="button" disabled={submitting} onClick={() => runAction('check_in', entry.id)} style={{ padding: '6px 12px', fontSize: '12px', width: 'auto', margin: 0 }}>Check In</button>
                          )}
                          {isGuard && entry.status === 'inside' && (
                            <button className="settings-action-btn" type="button" disabled={submitting} onClick={() => runAction('check_out', entry.id)} style={{ padding: '6px 12px', fontSize: '12px', width: 'auto', margin: 0 }}>Check Out</button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          /* Staff Attendance Tab */
          <div className="dashboard-main-grid" style={{ alignItems: 'start' }}>
            
            {/* Active Staff List for Checking In/Out */}
            <div className="settings-section">
              <h2 className="settings-section-title">Staff Check In / Check Out</h2>
              {staffList.length === 0 ? (
                <div style={{ padding: '24px', background: '#f9f9f9', borderRadius: '8px', textAlign: 'center', color: '#666' }}>
                  No active staff members pre-registered. Register them in Admin Settings first.
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '12px' }}>
                  {staffList.map((staff) => {
                    const activeLog = getActiveAttendanceLog(staff.id);
                    const isInside = !!activeLog;

                    return (
                      <div key={staff.id} className="dashboard-metric-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', border: '1px solid #E5E5EA' }}>
                        <div>
                          <strong style={{ fontSize: '15px' }}>{staff.name}</strong>
                          <div style={{ color: '#666', fontSize: '13px', marginTop: '4px' }}>
                            Role: <strong>{staff.role}</strong>
                            {staff.flat_number && <span> | Flat: {staff.flat_number}</span>}
                          </div>
                          {staff.phone_number && <div style={{ color: '#888', fontSize: '12px' }}>Phone: {staff.phone_number}</div>}
                          {staff.vehicle_type !== 'none' && <div style={{ color: '#888', fontSize: '12px' }}>Vehicle: {staff.vehicle_type} ({staff.vehicle_number})</div>}
                        </div>
                        <div>
                          {isInside ? (
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ color: '#2F855A', fontWeight: 'bold', fontSize: '12px', marginBottom: '6px' }}>Inside premises</div>
                              <button
                                className="settings-action-btn"
                                onClick={() => handleStaffCheckOut(activeLog.id)}
                                disabled={submitting}
                                style={{ padding: '8px 16px', fontSize: '13px', margin: 0, width: 'auto', backgroundColor: '#c53030', color: 'white' }}
                              >
                                Check Out
                              </button>
                            </div>
                          ) : (
                            <button
                              className="settings-save-btn"
                              onClick={() => handleStaffCheckIn(staff.id)}
                              disabled={submitting}
                              style={{ padding: '8px 16px', fontSize: '13px', margin: 0, width: 'auto' }}
                            >
                              Check In
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Today's Attendance Logs */}
            <div className="settings-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <h2 className="settings-section-title" style={{ margin: 0 }}>Today's Staff Log</h2>
                <button className="settings-action-btn" style={{ width: 'auto', padding: '6px 14px' }} onClick={loadData}>Refresh</button>
              </div>

              {attendanceLogs.length === 0 ? (
                <div style={{ padding: '24px', background: '#f9f9f9', borderRadius: '8px', textAlign: 'center', color: '#666' }}>
                  No staff entries or exits logged today.
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '12px' }}>
                  {attendanceLogs.map((log) => (
                    <div key={log.id} style={{ padding: '12px 16px', background: '#f9f9f9', borderRadius: '8px', borderLeft: log.status === 'inside' ? '4px solid #2F855A' : '4px solid #718096' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '14px' }}>
                        <span>{log.name}</span>
                        <span style={{ color: log.status === 'inside' ? '#2F855A' : '#718096' }}>{log.status === 'inside' ? 'Inside' : 'Left'}</span>
                      </div>
                      <div style={{ color: '#666', fontSize: '12px', marginTop: '4px' }}>
                        {log.role} {log.flat_number && `for Flat ${log.flat_number}`}
                      </div>
                      <div style={{ fontSize: '11px', color: '#888', marginTop: '4px' }}>
                        In: {formatDateTime(log.checked_in_at)} {log.checked_out_at && ` | Out: ${formatDateTime(log.checked_out_at)}`}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VisitorsScreen;
