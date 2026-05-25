/**
 * Web Version of GruhaMitra App
 * Adapted from React Native App.tsx for web/desktop
 */
import React, { useEffect, useState, useCallback, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import './styles.css';
import PWAInstallBanner from './PWAInstallBanner';

// Auth Service (web-compatible)
import { authService } from './services/authService';

// Route-level lazy loading to reduce initial bundle size on first load.
import LoginScreen from './screens/LoginScreen';
import RegisterScreen from './screens/RegisterScreen';
import ForgotPasswordScreen from './screens/ForgotPasswordScreen';
import ResetPasswordScreen from './screens/ResetPasswordScreen';
const SocietyOnboardingScreen = lazy(() => import('./screens/SocietyOnboardingScreen'));
const ResidentSignupScreen = lazy(() => import('./screens/ResidentSignupScreen'));
const CompleteRegistrationScreen = lazy(() => import('./screens/CompleteRegistrationScreen'));
const SplashScreen = lazy(() => import('./screens/SplashScreen'));
const DashboardScreen = lazy(() => import('./screens/DashboardScreen'));
const AccountingScreen = lazy(() => import('./screens/AccountingScreen'));
const ProfileScreen = lazy(() => import('./screens/ProfileScreen'));
const SettingsScreen = lazy(() => import('./screens/SettingsScreen'));
const MembersScreen = lazy(() => import('./screens/MembersScreen'));
const MaintenanceScreen = lazy(() => import('./screens/MaintenanceScreen'));
const MessagesScreen = lazy(() => import('./screens/MessagesScreen'));
const MeetingsScreen = lazy(() => import('./screens/MeetingsScreen'));
const ReportsScreen = lazy(() => import('./screens/ReportsScreen'));
const ComplaintsScreen = lazy(() => import('./screens/ComplaintsScreen'));
const AssetRegisterScreen = lazy(() => import('./screens/AssetRegisterScreen'));
const AddAssetScreen = lazy(() => import('./screens/AddAssetScreen'));
const AssetDetailScreen = lazy(() => import('./screens/AssetDetailScreen'));
const SocietySearchScreen = lazy(() => import('./screens/SocietySearchScreen'));
const MyMembershipsScreen = lazy(() => import('./screens/MyMembershipsScreen'));
const JoinRequestsScreen = lazy(() => import('./screens/JoinRequestsScreen'));

const getInitialUserFromStorage = () => {
  if (typeof window === 'undefined') return null;
  try {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    const parsed = JSON.parse(userStr);
    return parsed && (parsed.email || parsed.id || parsed.username) ? parsed : null;
  } catch (error) {
    return null;
  }
};

const MobileNav = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path || (path === '/' && location.pathname === '/dashboard');

  return (
    <div className="mobile-bottom-nav">
      <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`}>
        <span className="nav-icon"></span>
        <span>Home</span>
      </Link>
      <Link to="/accounting" className={`nav-item ${isActive('/accounting') ? 'active' : ''}`}>
        <span className="nav-icon"></span>
        <span>Account</span>
      </Link>
      <Link to="/reports" className={`nav-item ${isActive('/reports') ? 'active' : ''}`}>
        <span className="nav-icon"></span>
        <span>Reports</span>
      </Link>
      <Link to="/members" className={`nav-item ${isActive('/members') ? 'active' : ''}`}>
        <span className="nav-icon"></span>
        <span>Members</span>
      </Link>
      <Link to="/settings" className={`nav-item ${isActive('/settings') ? 'active' : ''}`}>
        <span className="nav-icon"></span>
        <span>Setup</span>
      </Link>
    </div>
  );
};

const App = () => {
  const [user, setUser] = useState(() => getInitialUserFromStorage());

  const checkAuthStatus = useCallback(async () => {
    try {
      // Check authentication status
      const isAuthenticated = await authService.isAuthenticated();

      if (isAuthenticated) {
        try {
          // Get user - this will use storage first (fast), only calls API if needed
          const currentUser = await authService.getCurrentUser();
          if (currentUser) {
            setUser(currentUser);
          } else {
            // User not found, but token exists - don't logout immediately
            setUser(null);
          }
        } catch (error) {
          console.error('Failed to get current user:', error);
          setUser(null);
        }
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    // Do not block initial auth state check on listener registration.
    authService.initAuthListener().catch((err) => {
      console.warn('Auth listener initialization failed:', err);
    });
    checkAuthStatus();
  }, [checkAuthStatus]);

  const handleAuthSuccess = useCallback((authenticatedUser = null) => {
    if (authenticatedUser) {
      setUser(authenticatedUser);
    }
    checkAuthStatus();
  }, [checkAuthStatus]);

  return (
    <Router basename="/gruhamitra">
      <PWAInstallBanner />
      {user && <MobileNav />}
      <Suspense
        fallback={
          <div className="loading-container">
            <div>
              <div className="loading-text">Loading GruhaMitra...</div>
            </div>
          </div>
        }
      >
        <Routes>
          {user ? (
            <>
              <Route path="/splash" element={<SplashScreen />} />
              <Route path="/" element={<DashboardScreen />} />
              <Route path="/dashboard" element={<DashboardScreen />} />
              <Route path="/maintenance" element={<MaintenanceScreen />} />
              <Route path="/accounting" element={<AccountingScreen />} />
              <Route path="/members" element={<MembersScreen />} />
              <Route path="/complaints" element={<ComplaintsScreen />} />
              <Route path="/reports" element={<ReportsScreen />} />
              <Route path="/message" element={<MessagesScreen />} />
              <Route path="/meeting" element={<MeetingsScreen />} />
              <Route path="/assets" element={<AssetRegisterScreen />} />
              <Route path="/assets/add" element={<AddAssetScreen />} />
              <Route path="/assets/:asset_id" element={<AssetDetailScreen />} />
              <Route path="/onboarding/search" element={<SocietySearchScreen />} />
              <Route path="/onboarding/memberships" element={<MyMembershipsScreen />} />
              <Route path="/onboarding/requests" element={<JoinRequestsScreen />} />
              <Route path="/settings" element={<SettingsScreen />} />
              <Route path="/profile" element={<ProfileScreen />} />
              <Route path="/forgot-password" element={<ForgotPasswordScreen />} />
              <Route path="/reset-password" element={<ResetPasswordScreen />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </>
          ) : (
            <>
              <Route path="/login" element={<LoginScreen onLoginSuccess={handleAuthSuccess} />} />
              <Route path="/forgot-password" element={<ForgotPasswordScreen />} />
              <Route path="/reset-password" element={<ResetPasswordScreen />} />
              <Route path="/register" element={<RegisterScreen onRegisterSuccess={handleAuthSuccess} />} />
              <Route path="/onboard-society" element={<SocietyOnboardingScreen onRegisterSuccess={handleAuthSuccess} />} />
              <Route path="/resident-signup" element={<ResidentSignupScreen />} />
              <Route path="/complete-registration" element={<CompleteRegistrationScreen />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </>
          )}
        </Routes>
      </Suspense>

      {/* Global Footer */}
      {!user && <div className="global-footer" style={{
        textAlign: 'center',
        padding: '12px',
        fontSize: '11px',
        color: '#8E8E93',
        backgroundColor: '#f8f9fa',
        borderTop: '1px solid #E5E5EA',
        marginTop: 'auto'
      }}>
        <div> {new Date().getFullYear()} GruhaMitra. All rights reserved.</div>
        <div style={{ marginTop: '2px' }}>v1.2.0 (Stable)</div>
      </div>}
    </Router>
  );
};

export default App;

