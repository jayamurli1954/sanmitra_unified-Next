/**
 * Tests for the App component (src/App.js)
 * Covers: routing, protected routes, theme, provider wrapping
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../App';

jest.mock('../components/ProtectedRoute', () => ({
    __esModule: true,
    default: ({ children }) => (globalThis.sessionStorage.getItem('mm_access_token_v1') ? children : <div data-testid="login-page">Login Page</div>),
}));
jest.mock('../contexts/CurrentUserContext', () => ({
    __esModule: true,
    CurrentUserProvider: ({ children }) => <>{children}</>,
    useCurrentUser: () => ({ user: {}, loading: false, refreshUser: jest.fn(), setCurrentUser: jest.fn(), clearCurrentUser: jest.fn() }),
}));
jest.mock('../contexts/NotificationContext', () => ({
    __esModule: true,
    NotificationProvider: ({ children }) => <>{children}</>,
    useNotification: () => ({ showSuccess: jest.fn(), showError: jest.fn(), showInfo: jest.fn(), showWarning: jest.fn() }),
}));
jest.mock('../contexts/LoadingContext', () => ({
    __esModule: true,
    LoadingProvider: ({ children }) => <>{children}</>,
}));

// Mock all page components to keep tests fast and focused on routing
jest.mock('../pages/Login', () => () => <div data-testid="login-page">Login Page</div>);
jest.mock('../pages/BrandIntro', () => () => <div data-testid="brand-intro-page">Brand Intro</div>);
jest.mock('../pages/Dashboard', () => () => <div data-testid="dashboard-page">Dashboard</div>);
jest.mock('../pages/Donations', () => () => <div data-testid="donations-page">Donations</div>);
jest.mock('../pages/Devotees', () => () => <div data-testid="devotees-page">Devotees</div>);
jest.mock('../pages/Reports', () => () => <div data-testid="reports-page">Reports</div>);
jest.mock('../pages/Sevas', () => () => <div data-testid="sevas-page">Sevas</div>);
jest.mock('../pages/SevaManagement', () => () => <div data-testid="seva-management-page">Seva Management</div>);
jest.mock('../pages/Settings', () => () => <div data-testid="settings-page">Settings</div>);
jest.mock('../pages/Panchang', () => () => <div data-testid="panchang-page">Panchang</div>);
jest.mock('../pages/PanchangSettings', () => () => <div data-testid="panchang-settings-page">Panchang Settings</div>);
jest.mock('../pages/CategoryWiseDonationReport', () => () => <div>Cat Report</div>);
jest.mock('../pages/DetailedDonationReport', () => () => <div>Detailed Donation</div>);
jest.mock('../pages/DetailedSevaReport', () => () => <div>Detailed Seva</div>);
jest.mock('../pages/SevaSchedule', () => () => <div>Seva Schedule</div>);
jest.mock('../pages/SevaRescheduleApproval', () => () => <div>Reschedule Approval</div>);
jest.mock('../pages/accounting/ChartOfAccounts', () => () => <div>COA</div>);
jest.mock('../pages/accounting/QuickExpense', () => () => <div>Quick Expense</div>);
jest.mock('../pages/accounting/JournalEntries', () => () => <div>Journal Entries</div>);
jest.mock('../pages/accounting/UpiPayments', () => () => <div>UPI Payments</div>);
jest.mock('../pages/accounting/AccountingReports', () => () => <div>Accounting Reports</div>);

// Helper to render App with a specific URL
const renderAppAt = (url) => {
    window.history.pushState({}, 'Test', url);
    return render(<App />);
};

beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
});

describe('App - Routing', () => {
    it('renders Login page at /login', async () => {
        renderAppAt('/login');
        expect(await screen.findByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects to /login when accessing /dashboard without token', async () => {
        renderAppAt('/dashboard');
        expect(await screen.findByTestId('login-page')).toBeInTheDocument();
    });

    it('renders Dashboard when authenticated and accessing /dashboard', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/dashboard');
        expect(await screen.findByTestId('dashboard-page')).toBeInTheDocument();
    });

    it('renders Brand Intro when authenticated and accessing /brand-intro', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/brand-intro');
        expect(await screen.findByTestId('brand-intro-page')).toBeInTheDocument();
    });

    it('renders Devotees page when authenticated and accessing /devotees', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/devotees');
        expect(await screen.findByTestId('devotees-page')).toBeInTheDocument();
    });

    it('renders Donations page when authenticated and accessing /donations', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/donations');
        expect(await screen.findByTestId('donations-page')).toBeInTheDocument();
    });

    it('renders Sevas page when authenticated and accessing /sevas', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/sevas');
        expect(await screen.findByTestId('sevas-page')).toBeInTheDocument();
    });

    it('renders SevaManagement page at /sevas/manage', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/sevas/manage');
        expect(await screen.findByTestId('seva-management-page')).toBeInTheDocument();
    });

    it('renders Settings page at /settings', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/settings');
        expect(await screen.findByTestId('settings-page')).toBeInTheDocument();
    });

    it('renders Panchang page at /panchang', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/panchang');
        expect(await screen.findByTestId('panchang-page')).toBeInTheDocument();
    });

    it('redirects to /dashboard from / when authenticated', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'valid-token');
        renderAppAt('/');
        expect(await screen.findByTestId('dashboard-page')).toBeInTheDocument();
    });

    it('redirects to /login from / when not authenticated', async () => {
        renderAppAt('/');
        expect(await screen.findByTestId('login-page')).toBeInTheDocument();
    });
});

describe('App - Theme', () => {
    it('renders without crashing', () => {
        expect(() => renderAppAt('/login')).not.toThrow();
    });
});
