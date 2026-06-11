/**
 * Tests for the Login page component (src/pages/Login.js)
 * Covers: rendering, form input, successful login, error states, loading state
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Login from '../pages/Login';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';

// Mock useNavigate
const mockedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useNavigate: () => mockedNavigate,
}));

jest.mock('../utils/apiBaseUrl', () => ({
    fetchWithApiFallback: jest.fn(),
}));

const renderLogin = () =>
    render(
        <MemoryRouter>
            <Login />
        </MemoryRouter>
    );

beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
});

describe('Login Page - Rendering', () => {
    it('renders the MandirMitra heading', () => {
        renderLogin();
        expect(screen.getByText(/MandirMitra/i)).toBeInTheDocument();
    });

    it('renders email and password fields', () => {
        renderLogin();
        expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/^Password/i)).toBeInTheDocument();
    });

    it('renders the Sign In button', () => {
        renderLogin();
        expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    it('does not show error alert on initial render', () => {
        renderLogin();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
});

describe('Login Page - User Interaction', () => {
    it('updates email field on input', async () => {
        renderLogin();
        const emailInput = screen.getByLabelText(/Email Address/i);
        await userEvent.type(emailInput, 'test@temple.com');
        expect(emailInput.value).toBe('test@temple.com');
    });

    it('updates password field on input', async () => {
        renderLogin();
        const passwordInput = screen.getByLabelText(/^Password/i);
        await userEvent.type(passwordInput, 'secret123');
        expect(passwordInput.value).toBe('secret123');
    });

    it('password field type is password (hidden text)', () => {
        renderLogin();
        expect(screen.getByLabelText(/^Password/i)).toHaveAttribute('type', 'password');
    });
});

describe('Login Page - Successful Login', () => {
    it('stores token in sessionStorage and navigates to /brand-intro on success', async () => {
        fetchWithApiFallback
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ access_token: 'mock-token-123' }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    id: 1,
                    email: 'admin@temple.com',
                    role: 'admin',
                    system_role: 'admin',
                    is_superuser: false,
                    module_permissions: {},
                    action_permissions: {},
                }),
            });

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'admin@temple.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'admin123');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(sessionStorage.getItem('mm_access_token_v1')).toBe('mock-token-123');
            expect(sessionStorage.getItem('showBrandIntroAfterLogin')).toBe('1');
            expect(mockedNavigate).toHaveBeenCalledWith('/brand-intro');
        });
    });

    it('calls the correct login endpoint with form data', async () => {
        fetchWithApiFallback
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ access_token: 'tok' }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ email: 'admin@temple.com', role: 'admin', system_role: 'admin', is_superuser: false }),
            });

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'admin@temple.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'pass');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(fetchWithApiFallback).toHaveBeenNthCalledWith(
                1,
                expect.stringContaining('/api/v1/login'),
                expect.objectContaining({ method: 'POST' }),
                expect.any(Object)
            );
        });
    });
});

describe('Login Page - Error States', () => {
    it('shows error alert when login fails with backend message', async () => {
        fetchWithApiFallback.mockResolvedValueOnce({
            ok: false,
            json: async () => ({ detail: 'Incorrect username or password' }),
        });

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'wrong@temple.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'badpass');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toBeInTheDocument();
            expect(screen.getByText(/Incorrect username or password/i)).toBeInTheDocument();
        });
    });

    it('shows error alert when fetch throws (network error)', async () => {
        fetchWithApiFallback.mockRejectedValueOnce(new Error('Network Error'));

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'admin@temple.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'pass123');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toBeInTheDocument();
        });
    });

    it('does not navigate on failed login', async () => {
        fetchWithApiFallback.mockResolvedValueOnce({
            ok: false,
            json: async () => ({ detail: 'Forbidden' }),
        });

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'a@b.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'bad');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(mockedNavigate).not.toHaveBeenCalled();
        });
    });
});

describe('Login Page - Loading State', () => {
    it('disables the Sign In button while loading', async () => {
        // Never resolve so we can check intermediate loading state
        fetchWithApiFallback.mockImplementationOnce(() => new Promise(() => { }));

        renderLogin();
        await userEvent.type(screen.getByLabelText(/Email Address/i), 'a@temple.com');
        await userEvent.type(screen.getByLabelText(/^Password/i), 'pass');
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        // After click, loading starts - the submit button becomes disabled while fetch pending
        await waitFor(() => {
            const submitBtn = document.querySelector('button[type="submit"]');
            expect(submitBtn).toBeDisabled();
        });
    });
});
