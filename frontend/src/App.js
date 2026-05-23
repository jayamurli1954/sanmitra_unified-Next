import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { NotificationProvider } from './contexts/NotificationContext';
import { LoadingProvider } from './contexts/LoadingContext';
import { CurrentUserProvider } from './contexts/CurrentUserContext';
import ProtectedRoute from './components/ProtectedRoute';
import { clearAuthSession, getAccessToken } from './utils/authStorage';

const Login = lazy(() => import('./pages/Login'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const TempleRegistration = lazy(() => import('./pages/TempleRegistration'));
const TenantInactive = lazy(() => import('./pages/TenantInactive'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const BrandIntro = lazy(() => import('./pages/BrandIntro'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Donations = lazy(() => import('./pages/Donations'));
const Devotees = lazy(() => import('./pages/Devotees'));
const Reports = lazy(() => import('./pages/Reports'));
const Panchang = lazy(() => import('./pages/Panchang'));
const PanchangSettings = lazy(() => import('./pages/PanchangSettings'));
const Sevas = lazy(() => import('./pages/Sevas'));
const SevaManagement = lazy(() => import('./pages/SevaManagement'));
const Settings = lazy(() => import('./pages/Settings'));
const ImplementationChecks = lazy(() => import('./pages/ImplementationChecks'));
const SetupWizard = lazy(() => import('./pages/SetupWizard'));
const Profile = lazy(() => import('./pages/Profile'));
const TempleDirectory = lazy(() => import('./pages/TempleDirectory'));
const CategoryWiseDonationReport = lazy(() => import('./pages/CategoryWiseDonationReport'));
const DetailedDonationReport = lazy(() => import('./pages/DetailedDonationReport'));
const DetailedSevaReport = lazy(() => import('./pages/DetailedSevaReport'));
const SevaSchedule = lazy(() => import('./pages/SevaSchedule'));
const SevaRescheduleApproval = lazy(() => import('./pages/SevaRescheduleApproval'));
const Inventory = lazy(() => import('./pages/Inventory'));
const Assets = lazy(() => import('./pages/Assets'));
const HR = lazy(() => import('./pages/HR'));
const Hundi = lazy(() => import('./pages/Hundi'));
const ChartOfAccounts = lazy(() => import('./pages/accounting/ChartOfAccounts'));
const QuickExpense = lazy(() => import('./pages/accounting/QuickExpense'));
const JournalEntries = lazy(() => import('./pages/accounting/JournalEntries'));
const UpiPayments = lazy(() => import('./pages/accounting/UpiPayments'));
const BankReconciliation = lazy(() => import('./pages/accounting/BankReconciliation'));
const FinancialClosing = lazy(() => import('./pages/accounting/FinancialClosing'));
const AccountingReports = lazy(() => import('./pages/accounting/AccountingReports'));
const PublicPayments = lazy(() => import('./pages/accounting/PublicPayments'));
const SevaReminders = lazy(() => import('./pages/SevaReminders'));
const QuickTicket = lazy(() => import('./pages/QuickTicket'));
const ReleaseNotes = lazy(() => import('./pages/ReleaseNotes'));
const PublicSevaPayment = lazy(() => import('./pages/PublicSevaPayment'));

const IDLE_TIMEOUT_MS = 5 * 60 * 1000;
const IDLE_CHECK_INTERVAL_MS = 15000;

const theme = createTheme({
  typography: {
    fontFamily: [
      'Noto Sans',
      'Noto Sans Kannada',
      'Noto Sans Devanagari',
      'Noto Sans Tamil',
      'Noto Sans Telugu',
      'Noto Sans Malayalam',
      'Noto Sans Bengali',
      '-apple-system',
      'BlinkMacSystemFont',
      'Segoe UI',
      'Roboto',
      'Helvetica Neue',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  palette: {
    primary: {
      main: '#FF9933',
    },
    secondary: {
      main: '#138808',
    },
  },
});

function App() {
  useEffect(() => {
    let lastActivityAt = Date.now();

    const recordActivity = () => {
      lastActivityAt = Date.now();
    };

    const performIdleLogout = () => {
      if (!getAccessToken()) {
        return;
      }

      clearAuthSession();
      window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { clear: true, reason: 'idle-timeout' } }));

      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    };

    const checkIdle = () => {
      if (!getAccessToken()) {
        lastActivityAt = Date.now();
        return;
      }

      if (Date.now() - lastActivityAt >= IDLE_TIMEOUT_MS) {
        performIdleLogout();
      }
    };

    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click', 'focus'];
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, recordActivity, { passive: true });
    });

    const onVisibilityChange = () => {
      if (!document.hidden) {
        recordActivity();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);

    const intervalId = window.setInterval(checkIdle, IDLE_CHECK_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, recordActivity);
      });
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NotificationProvider>
        <LoadingProvider>
          <CurrentUserProvider>
            <Router>
              <Suspense fallback={<div style={{ padding: 16 }}>Loading...</div>}>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  <Route path="/register-temple" element={<TempleRegistration />} />
                  <Route path="/tenant-inactive" element={<TenantInactive />} />
                  <Route path="/reset-password" element={<ResetPassword />} />
                  <Route
                    path="/brand-intro"
                    element={(
                      <ProtectedRoute>
                        <BrandIntro />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/dashboard"
                    element={(
                      <ProtectedRoute>
                        <Dashboard />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/donations"
                    element={(
                      <ProtectedRoute>
                        <Donations />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/devotees"
                    element={(
                      <ProtectedRoute>
                        <Devotees />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/reports"
                    element={(
                      <ProtectedRoute>
                        <Reports />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/reports/donations/category-wise"
                    element={(
                      <ProtectedRoute>
                        <CategoryWiseDonationReport />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/reports/donations/detailed"
                    element={(
                      <ProtectedRoute>
                        <DetailedDonationReport />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/reports/sevas/detailed"
                    element={(
                      <ProtectedRoute>
                        <DetailedSevaReport />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/reports/sevas/schedule"
                    element={(
                      <ProtectedRoute>
                        <SevaSchedule />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/sevas/reschedule-approval"
                    element={(
                      <ProtectedRoute>
                        <SevaRescheduleApproval />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/panchang"
                    element={(
                      <ProtectedRoute>
                        <Panchang />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/panchang/settings"
                    element={(
                      <ProtectedRoute>
                        <PanchangSettings />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/sevas"
                    element={(
                      <ProtectedRoute>
                        <Sevas />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/sevas/manage"
                    element={(
                      <ProtectedRoute>
                        <SevaManagement />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/hundi"
                    element={(
                      <ProtectedRoute>
                        <Hundi />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/inventory"
                    element={(
                      <ProtectedRoute>
                        <Inventory />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/assets"
                    element={(
                      <ProtectedRoute>
                        <Assets />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/hr"
                    element={(
                      <ProtectedRoute>
                        <HR />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/setup-wizard"
                    element={(
                      <ProtectedRoute>
                        <SetupWizard />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/settings"
                    element={(
                      <ProtectedRoute>
                        <Settings />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/settings/release-notes"
                    element={(
                      <ProtectedRoute>
                        <ReleaseNotes />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/implementation-checks"
                    element={(
                      <ProtectedRoute>
                        <ImplementationChecks />
                      </ProtectedRoute>
                    )}
                  />

                  <Route
                    path="/profile"
                    element={(
                      <ProtectedRoute>
                        <Profile />
                      </ProtectedRoute>
                    )}
                  />

                  <Route
                    path="/platform/operations"
                    element={(
                      <ProtectedRoute>
                        <TempleDirectory />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/platform/temples"
                    element={<Navigate to="/platform/operations" replace />}
                  />

                  <Route
                    path="/accounting/chart-of-accounts"
                    element={(
                      <ProtectedRoute>
                        <ChartOfAccounts />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/quick-expense"
                    element={(
                      <ProtectedRoute>
                        <QuickExpense />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/journal-entries"
                    element={(
                      <ProtectedRoute>
                        <JournalEntries />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/upi-payments"
                    element={(
                      <ProtectedRoute>
                        <UpiPayments />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/bank-reconciliation"
                    element={(
                      <ProtectedRoute>
                        <BankReconciliation />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/financial-closing"
                    element={(
                      <ProtectedRoute>
                        <FinancialClosing />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/reports"
                    element={(
                      <ProtectedRoute>
                        <AccountingReports />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/public-payments"
                    element={(
                      <ProtectedRoute>
                        <PublicPayments />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/accounting/seva-reminders"
                    element={(
                      <ProtectedRoute>
                        <SevaReminders />
                      </ProtectedRoute>
                    )}
                  />
                  <Route
                    path="/sevas/quick-ticket"
                    element={(
                      <ProtectedRoute>
                        <QuickTicket />
                      </ProtectedRoute>
                    )}
                  />
                  <Route path="/pay" element={<PublicSevaPayment />} />
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </Suspense>
            </Router>
          </CurrentUserProvider>
        </LoadingProvider>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;

