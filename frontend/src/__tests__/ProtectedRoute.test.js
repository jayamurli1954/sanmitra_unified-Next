/**
 * Tests for ProtectedRoute component (src/components/ProtectedRoute.js)
 * Covers: redirect when unauthenticated, setup-wizard redirect behaviour, exempt profile access,
 * and backend-driven platform super admin bypass for forced setup.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';

jest.mock('../utils/apiBaseUrl', () => ({
  fetchWithApiFallback: jest.fn(),
}));

const ProtectedPage = ({ label = 'Protected Content' }) => <div>{label}</div>;
const LoginPage = () => <div>Login Page</div>;
const SetupWizardPage = () => <div>First-Time Setup Wizard</div>;

const buildResponse = (payload, ok = true) => ({
  ok,
  json: async () => payload,
});

const mockAuthRequests = ({ setup, currentUser }) => {
  fetchWithApiFallback.mockImplementation((url) => {
    if (url === '/api/v1/setup-wizard/status') {
      return Promise.resolve(buildResponse(setup));
    }
    if (url === '/api/v1/users/me') {
      return Promise.resolve(buildResponse(currentUser));
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
};

const renderWithRoute = (initialEntry = '/dashboard', protectedPath = '/dashboard') => {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/setup-wizard" element={<SetupWizardPage />} />
        <Route
          path={protectedPath}
          element={
            <ProtectedRoute>
              <ProtectedPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
};

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  fetchWithApiFallback.mockReset();
  mockAuthRequests({
    setup: {
      force_setup: false,
      can_manage_setup: true,
    },
    currentUser: {
      id: 1,
      email: 'user@example.com',
      role: 'temple_manager',
      system_role: 'temple_manager',
      is_superuser: false,
    },
  });
});

describe('ProtectedRoute', () => {
  it('redirects to /login when no token in sessionStorage', () => {
    renderWithRoute('/dashboard');
    expect(screen.getByText(/Login Page/i)).toBeInTheDocument();
    expect(screen.queryByText(/Protected Content/i)).not.toBeInTheDocument();
  });

  it('renders children when token exists in sessionStorage', async () => {
    sessionStorage.setItem('mm_access_token_v1', 'valid-jwt-token');
    renderWithRoute('/dashboard');
    await waitFor(() => expect(screen.getByText(/Protected Content/i)).toBeInTheDocument());
    expect(screen.queryByText(/Login Page/i)).not.toBeInTheDocument();
  });

  it('redirects to /login when token is empty string', () => {
    sessionStorage.setItem('mm_access_token_v1', '');
    renderWithRoute('/dashboard');
    expect(screen.getByText(/Login Page/i)).toBeInTheDocument();
  });

  it('redirects non-exempt routes to the setup wizard when forced setup is required', async () => {
    sessionStorage.setItem('mm_access_token_v1', 'valid-jwt-token');
    mockAuthRequests({
      setup: {
        force_setup: true,
        can_manage_setup: true,
      },
      currentUser: {
        id: 2,
        email: 'manager@example.com',
        role: 'temple_manager',
        system_role: 'temple_manager',
        is_superuser: false,
      },
    });

    renderWithRoute('/dashboard');

    await waitFor(() => expect(screen.getByText(/First-Time Setup Wizard/i)).toBeInTheDocument());
  });

  it('keeps the profile route accessible even when forced setup is required', async () => {
    sessionStorage.setItem('mm_access_token_v1', 'valid-jwt-token');
    mockAuthRequests({
      setup: {
        force_setup: true,
        can_manage_setup: true,
      },
      currentUser: {
        id: 3,
        email: 'manager@example.com',
        role: 'temple_manager',
        system_role: 'temple_manager',
        is_superuser: false,
      },
    });

    renderWithRoute('/profile', '/profile');

    await waitFor(() => expect(screen.getByText(/Protected Content/i)).toBeInTheDocument());
    expect(screen.queryByText(/First-Time Setup Wizard/i)).not.toBeInTheDocument();
  });

  it('keeps super admins out of the setup redirect even when local storage is stale', async () => {
    sessionStorage.setItem('mm_access_token_v1', 'valid-jwt-token');
    sessionStorage.setItem('mm_current_user_v1', JSON.stringify({ role: 'temple_manager', is_superuser: false }));
    mockAuthRequests({
      setup: {
        force_setup: true,
        can_manage_setup: true,
      },
      currentUser: {
        id: 4,
        email: 'superadmin@example.com',
        role: 'super_admin',
        system_role: 'super_admin',
        is_superuser: true,
      },
    });

    renderWithRoute('/sevas', '/sevas');

    await waitFor(() => expect(screen.getByText(/Protected Content/i)).toBeInTheDocument());
    expect(screen.queryByText(/First-Time Setup Wizard/i)).not.toBeInTheDocument();
  });
});
