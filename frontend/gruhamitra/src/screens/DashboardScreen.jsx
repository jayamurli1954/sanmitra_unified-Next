/**
 * GruhaMitra Dashboard Screen
 * Warm, trust-based design with brand colors
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FaBell,
  FaWallet,
  FaFileInvoice,
  FaHourglassHalf,
  FaTools,
  FaCalculator,
  FaUsers,
  FaSearch,
  FaClipboardList,
  FaCheckSquare,
  FaChartBar,
  FaComments,
  FaCalendarAlt,
  FaBuilding,
  FaCog,
  FaGavel,
} from 'react-icons/fa';
import { authService } from '../services/authService';
import api from '../services/api';
import messagesService from '../services/messagesService';

const DEFAULT_STATS = {
  society_balance: 0,
  monthly_billing: 0,
  dues_pending: 0,
  complaints_open: 0,
};
const DASHBOARD_CACHE_KEY = 'gm_dashboard_summary_cache_v1';
const MESSAGE_LAST_SEEN_KEY = 'gm_messages_last_seen_at';

const readDashboardCache = () => {
  try {
    const raw = sessionStorage.getItem(DASHBOARD_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return {
      stats: parsed.stats || DEFAULT_STATS,
      collectionTrend: Array.isArray(parsed.collectionTrend) ? parsed.collectionTrend : [],
      recentActivity: Array.isArray(parsed.recentActivity) ? parsed.recentActivity : [],
    };
  } catch (error) {
    return null;
  }
};

const persistDashboardCache = (payload) => {
  try {
    sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(payload));
  } catch (error) {
    // Ignore storage errors
  }
};

const DashboardScreen = () => {
  const navigate = useNavigate();
  const cachedDashboardRef = useRef(readDashboardCache());
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState(() => cachedDashboardRef.current?.stats || DEFAULT_STATS);
  const [loading, setLoading] = useState(true);
  const [recentActivity, setRecentActivity] = useState(() => cachedDashboardRef.current?.recentActivity || []);
  const [collectionTrend, setCollectionTrend] = useState(() => cachedDashboardRef.current?.collectionTrend || []);
  const [societyInfo, setSocietyInfo] = useState(null);
  const [societyLogoSrc, setSocietyLogoSrc] = useState('/GruhaMitra_Logo.png');
  const [newMessageNotice, setNewMessageNotice] = useState(null);
  const objectUrlRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      try {
        const currentUser = await authService.getCurrentUser();
        if (!currentUser) {
          navigate('/login');
          return;
        }

        if (!isMounted) return;
        setUser(currentUser);
        setLoading(false);

        // Run dashboard requests in background so the shell opens immediately.
        void loadDashboardSummary();
        void loadSocietyInfo(currentUser);
        void loadMessageNotice();
      } catch (error) {
        console.error('Error loading dashboard:', error);
        if (isMounted) {
          setLoading(false);
        }
        if (error.response?.status === 401) {
          navigate('/login');
        }
      }
    };

    bootstrap();

    return () => {
      isMounted = false;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
    };
  }, [navigate]);

  const clearExistingLogoObjectUrl = () => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  };

  const resolveSocietyLogo = async (rawLogoUrl) => {
    if (!rawLogoUrl) {
      clearExistingLogoObjectUrl();
      setSocietyLogoSrc('/GruhaMitra_Logo.png');
      return;
    }

    const normalized = String(rawLogoUrl).replace(/\\/g, '/');

    // External/public URL: can be used directly.
    if (/^https?:\/\//i.test(normalized)) {
      clearExistingLogoObjectUrl();
      setSocietyLogoSrc(normalized);
      return;
    }

    try {
      let endpoint = null;
      if (normalized.includes('/society/documents/')) {
        endpoint = normalized.slice(normalized.indexOf('/society/documents/'));
      } else {
        const fileName = normalized.split('/').pop();
        if (fileName) {
          endpoint = `/society/documents/${encodeURIComponent(fileName)}`;
        }
      }

      if (!endpoint) {
        clearExistingLogoObjectUrl();
        setSocietyLogoSrc('/GruhaMitra_Logo.png');
        return;
      }

      const response = await api.get(endpoint, {
        responseType: 'blob',
      });
      clearExistingLogoObjectUrl();
      const blobUrl = URL.createObjectURL(response.data);
      objectUrlRef.current = blobUrl;
      setSocietyLogoSrc(blobUrl);
    } catch (error) {
      console.warn('Could not load society logo from backend path:', error);
      clearExistingLogoObjectUrl();
      setSocietyLogoSrc('/GruhaMitra_Logo.png');
    }
  };

  const loadSocietyInfo = async (currentUser) => {
    try {
      if (currentUser && currentUser.society_id) {
        const response = await api.get(`/society/${currentUser.society_id}`);
        setSocietyInfo(response.data);
        void resolveSocietyLogo(response?.data?.logo_url);
        if (response?.data?.name) {
          const mergedUser = { ...currentUser, society_name: response.data.name };
          setUser((prev) => ({ ...(prev || {}), society_name: response.data.name }));
          if (authService.updateStoredUser) {
            void authService.updateStoredUser(mergedUser);
          }
        }
      }
    } catch (error) {
      console.error('Error loading society info:', error);
    }
  };

  const handleViewDocument = async (url) => {
    try {
      const response = await api.get(url, {
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

  const loadDashboardSummary = async () => {
    try {
      const response = await api.get('/dashboard/summary');
      const adminStats = response.data?.admin_stats || {};

      const statsData = {
        society_balance: adminStats.society_balance || 0,
        monthly_billing: adminStats.monthly_billing || 0,
        dues_pending: adminStats.dues_pending || 0,
        complaints_open: adminStats.complaints_open || 0,
      };
      const trend = adminStats.collection_trend || [];
      const activities = response.data?.recent_activities || [];
      const mappedActivities = activities.map(act => ({
        id: act.id,
        text: act.title,
        icon: act.icon || 'i',
        description: act.description
      }));

      setStats(statsData);
      setCollectionTrend(trend);
      setRecentActivity(mappedActivities);
      persistDashboardCache({
        stats: statsData,
        collectionTrend: trend,
        recentActivity: mappedActivities,
      });
    } catch (error) {
      console.error('Error loading dashboard stats:', error);
      if (error.response?.status === 401) {
        navigate('/login');
      }
    }
  };

  const loadMessageNotice = async () => {
    try {
      const rooms = await messagesService.listRooms();
      const roomList = Array.isArray(rooms) ? rooms : [];
      const latestRoom = roomList
        .filter((room) => room.last_message_at)
        .sort((a, b) => new Date(b.last_message_at).getTime() - new Date(a.last_message_at).getTime())[0];

      if (!latestRoom) {
        setNewMessageNotice(null);
        return;
      }

      const lastSeen = localStorage.getItem(MESSAGE_LAST_SEEN_KEY);
      const latestTime = new Date(latestRoom.last_message_at).getTime();
      const lastSeenTime = lastSeen ? new Date(lastSeen).getTime() : 0;

      if (latestTime > lastSeenTime) {
        setNewMessageNotice({
          roomName: latestRoom.name || 'Message Board',
          lastMessageAt: latestRoom.last_message_at,
        });
      } else {
        setNewMessageNotice(null);
      }
    } catch (error) {
      console.warn('Could not check message board activity:', error);
    }
  };


  const formatCurrency = (amount) => {
    if (!amount) return ' 0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatSocietyBalance = (amount) => {
    // Society Balance: Remove negative sign (debit balance, not negative)
    if (!amount) return ' 0';
    const absAmount = Math.abs(amount);
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(absAmount);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-watermark" aria-hidden="true">SANMITRA TECH</div>
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <img
            src="/GruhaMitra_Logo.png"
            alt="GruhaMitra System"
            className="dashboard-logo"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          />
        </div>
        <div className="dashboard-header-center">
          <div className="dashboard-center-brand">
            <img
              src={societyLogoSrc}
              alt="Society Logo"
              className="dashboard-society-logo"
              onError={() => setSocietyLogoSrc('/gruhamitra/icons/icon-192.png')}
            />
            <div className="dashboard-society-name-wrap">
              <div className="dashboard-society-name">
                {societyInfo?.name || user?.society_name || 'GruhaMitra Demo Society'}
              </div>
              <div className="dashboard-tagline">
                Your Society, Digitally Simplified
              </div>
            </div>
          </div>
        </div>
        <div className="dashboard-header-right">
          <span className="dashboard-header-icon dashboard-header-icon--notification" title="Notifications"><FaBell /></span>
          <div
            className="dashboard-user-info"
            onClick={() => navigate('/profile')}
            style={{ cursor: 'pointer' }}
          >
            <div className="dashboard-user-name">{user?.name || user?.email}</div>
            <div className="dashboard-user-role">{user?.role || 'Admin'}</div>
          </div>
          <button onClick={async () => {
            await authService.logout();
            window.location.href = '/gruhamitra/login';
          }} className="dashboard-logout-button">
             Logout
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {newMessageNotice && (
          <button
            type="button"
            onClick={() => navigate('/message')}
            style={{
              width: '100%',
              border: '1px solid #F4A640',
              background: '#FFF7EC',
              color: '#5A2E0A',
              borderRadius: '8px',
              padding: '12px 16px',
              marginBottom: '16px',
              textAlign: 'left',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <span>New message in {newMessageNotice.roomName}</span>
            <span style={{ color: '#E8842A' }}>Open Message Board</span>
          </button>
        )}

        {/* Metric Cards */}
        <div className="dashboard-metrics-grid">
          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon dashboard-metric-icon--balance"><FaWallet /></span>
            <div className="dashboard-metric-label">Society Balance</div>
            <div className="dashboard-metric-value">
              {formatSocietyBalance(stats?.society_balance || 0)}
            </div>
          </div>

          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon dashboard-metric-icon--billing"><FaFileInvoice /></span>
            <div className="dashboard-metric-label">This Month Billing</div>
            <div className="dashboard-metric-value">
              {formatCurrency(stats?.monthly_billing || 0)}
            </div>
          </div>

          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon dashboard-metric-icon--dues"><FaHourglassHalf /></span>
            <div className="dashboard-metric-label">Dues Pending</div>
            <div className="dashboard-metric-value" style={{ color: 'var(--gm-warning)' }}>
              {formatCurrency(stats?.dues_pending || 0)}
            </div>
          </div>

          <div className="dashboard-metric-card">
            <span className="dashboard-metric-icon dashboard-metric-icon--complaints"><FaTools /></span>
            <div className="dashboard-metric-label">Complaints Open</div>
            <div className="dashboard-metric-value" style={{ color: 'var(--gm-danger)' }}>
              {stats?.complaints_open || 0}
            </div>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="dashboard-main-grid">
          {/* Quick Actions */}
          <div className="dashboard-quick-actions">
            <h2 className="dashboard-section-title">Quick Actions</h2>
            <div className="dashboard-actions-grid">
              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/accounting')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--accounting"><FaCalculator /></span>
                <p className="dashboard-quick-tile-label">Accounting</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/maintenance')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--bills"><FaFileInvoice /></span>
                <p className="dashboard-quick-tile-label">Generate Bills</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/members')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--members"><FaUsers /></span>
                <p className="dashboard-quick-tile-label">Members</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/onboarding/search')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--find"><FaSearch /></span>
                <p className="dashboard-quick-tile-label">Find Society</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/onboarding/memberships')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--memberships"><FaClipboardList /></span>
                <p className="dashboard-quick-tile-label">My Memberships</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/onboarding/requests')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--requests"><FaCheckSquare /></span>
                <p className="dashboard-quick-tile-label">Join Requests</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/complaints')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--complaints"><FaTools /></span>
                <p className="dashboard-quick-tile-label">Complaints</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/reports')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--reports"><FaChartBar /></span>
                <p className="dashboard-quick-tile-label">Reports</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/message')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--message"><FaComments /></span>
                <p className="dashboard-quick-tile-label">Message</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/meeting')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--meeting"><FaCalendarAlt /></span>
                <p className="dashboard-quick-tile-label">Meeting</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/assets')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--assets"><FaBuilding /></span>
                <p className="dashboard-quick-tile-label">Society Assets</p>
              </button>

              <button
                className="dashboard-quick-tile"
                onClick={() => navigate('/settings')}
              >
                <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--settings"><FaCog /></span>
                <p className="dashboard-quick-tile-label">Settings</p>
              </button>

              {societyInfo?.legal_config?.bye_laws_url && (
                <button
                  className="dashboard-quick-tile"
                  style={{ border: '2px solid var(--gm-orange)' }}
                  onClick={() => handleViewDocument(societyInfo.legal_config.bye_laws_url)}
                >
                  <span className="dashboard-quick-tile-icon dashboard-quick-tile-icon--byelaws"><FaGavel /></span>
                  <p className="dashboard-quick-tile-label">Bye-laws</p>
                </button>
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="dashboard-recent-activity">
            <h2 className="dashboard-section-title">Recent Activity</h2>
            <ul className="dashboard-activity-list">
              {recentActivity.map((activity) => (
                <li key={activity.id} className="dashboard-activity-item">
                  <span className="dashboard-activity-icon">{activity.icon}</span>
                  <div className="dashboard-activity-info">
                    <span className="dashboard-activity-text">{activity.text}</span>
                    {activity.description && (
                      <span className="dashboard-activity-desc">{activity.description}</span>
                    )}
                  </div>
                </li>
              ))}
              {recentActivity.length === 0 && (
                <li className="dashboard-activity-item">
                  <span>No recent activity</span>
                </li>
              )}
            </ul>
          </div>
        </div>

        {/* Monthly Collection Trend */}
        <div className="dashboard-chart-section">
          <h2 className="dashboard-section-title">Monthly Collection Trend</h2>
          <CollectionTrendChart data={collectionTrend} />
        </div>

        <div className="dashboard-brand-footer">
          GruhaMitra is part of the SanMitra Digital Ecosystem   2026 SanMitra Tech Solutions
        </div>
      </div>
    </div>
  );
};

const CollectionTrendChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="dashboard-chart-placeholder">
        No data available for trend
      </div>
    );
  }

  // Find max amount for scaling
  const maxAmount = Math.max(...data.map(d => d.amount), 1000); // at least 1000 for scale

  // Chart dimensions
  const height = 180;
  const width = 800; // Simplified scaling
  const barWidth = 60;
  const gap = 40;

  return (
    <div className="trend-chart-container">
      <div className="trend-chart-y-axis">
        <span className="y-label">{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(maxAmount)}</span>
        <span className="y-label">{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(maxAmount / 2)}</span>
        <span className="y-label"> 0</span>
      </div>
      <div className="trend-chart-main">
        <div className="trend-chart-bars">
          {data.map((item, index) => {
            const barHeight = (item.amount / maxAmount) * height;
            return (
              <div key={index} className="trend-bar-wrapper">
                <div
                  className="trend-bar"
                  style={{
                    height: `${barHeight}px`,
                    animationDelay: `${index * 0.1}s`
                  }}
                  title={`${item.month}: ${item.amount.toLocaleString()}`}
                >
                  <span className="trend-bar-value">
                    {item.amount > 0 ? (item.amount > 1000 ? `${(item.amount / 1000).toFixed(1)}k` : item.amount) : ''}
                  </span>
                </div>
                <span className="trend-bar-month">{item.month}</span>
              </div>
            );
          })}
        </div>
        <div className="trend-chart-grid">
          <div className="grid-line" style={{ bottom: '0%' }}></div>
          <div className="grid-line" style={{ bottom: '50%' }}></div>
          <div className="grid-line" style={{ bottom: '100%' }}></div>
        </div>
      </div>
    </div>
  );
};

export default DashboardScreen;

