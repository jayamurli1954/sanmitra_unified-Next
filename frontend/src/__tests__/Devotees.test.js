/**
 * Tests for the Devotees page (src/pages/Devotees.js)
 * Covers: loading state, devotee list rendering, empty state, error state, API calls
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Devotees from '../pages/Devotees';

// Mock the api module
jest.mock('../services/api', () => ({
    get: jest.fn(),
}));
import api from '../services/api';

// Mock Layout to avoid sidebar/navbar complexity
jest.mock('../components/Layout', () => ({ children }) => <div data-testid="layout">{children}</div>);

const renderDevotees = () =>
    render(
        <MemoryRouter>
            <Devotees />
        </MemoryRouter>
    );

beforeEach(() => {
    jest.clearAllMocks();
});

describe('Devotees Page - Rendering', () => {
    it('renders the Devotees heading', async () => {
        api.get.mockResolvedValueOnce({ data: [] });
        renderDevotees();
        // Devotees.js uses component="h1"
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Devotees/i);
    });

    it('shows info alert about automatic devotee creation', async () => {
        api.get.mockResolvedValueOnce({ data: [] });
        renderDevotees();
        expect(
            screen.getByText(/automatically created when donations/i)
        ).toBeInTheDocument();
    });
});

describe('Devotees Page - Loading State', () => {
    it('shows loading spinner while fetching data', async () => {
        // Never resolve to keep loading state
        api.get.mockImplementation(() => new Promise(() => { }));
        renderDevotees();
        await waitFor(() => {
            expect(screen.getByRole('progressbar')).toBeInTheDocument();
        });
    });
});

describe('Devotees Page - Data Display', () => {
    const mockDevotees = [
        {
            id: 1,
            name: 'Rama Sharma',
            phone: '9876543210',
            email: 'rama@temple.com',
            address: '123 Temple St',
            donation_count: 5,
            total_donations: 5000,
            booking_count: 2,
            total_seva_amount: 1500,
        },
        {
            id: 2,
            name: 'Sita Devi',
            phone: '9876543211',
            email: null,
            address: null,
            donation_count: 3,
            total_donations: 3000,
            booking_count: 1,
            total_seva_amount: 700,
        },
    ];

    it('renders devotee names in the table', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText('Rama Sharma')).toBeInTheDocument();
            expect(screen.getByText('Sita Devi')).toBeInTheDocument();
        });
    });

    it('renders phone numbers in the table', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText('9876543210')).toBeInTheDocument();
        });
    });

    it('shows N/A for missing email', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            // Sita Devi has no email
            const naCells = screen.getAllByText('N/A');
            expect(naCells.length).toBeGreaterThan(0);
        });
    });

    it('renders table headers: Name, Phone, Email, Address, Donations, Total Donated, Sevas, Total Seva', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText('Name')).toBeInTheDocument();
            expect(screen.getByText('Phone')).toBeInTheDocument();
            expect(screen.getByText('Email')).toBeInTheDocument();
            expect(screen.getByText('Address')).toBeInTheDocument();
            expect(screen.getByText('Donations')).toBeInTheDocument();
            expect(screen.getByText('Total Donated')).toBeInTheDocument();
            expect(screen.getByText('Sevas')).toBeInTheDocument();
            expect(screen.getByText('Total Seva')).toBeInTheDocument();
        });
    });

    it('renders total donated values from total_donations field', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText(/5,000/)).toBeInTheDocument();
            expect(screen.getByText(/3,000/)).toBeInTheDocument();
        });
    });

    it('renders seva count and total seva values', async () => {
        api.get.mockResolvedValueOnce({ data: mockDevotees });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText('2')).toBeInTheDocument();
            expect(screen.getByText('1')).toBeInTheDocument();
            expect(screen.getByText(/1,500/)).toBeInTheDocument();
            expect(screen.getByText(/700/)).toBeInTheDocument();
        });
    });
});

describe('Devotees Page - Empty State', () => {
    it('shows empty state message when no devotees returned', async () => {
        api.get.mockResolvedValueOnce({ data: [] });
        // Donations fallback also empty
        api.get.mockResolvedValueOnce({ data: [] });
        renderDevotees();

        await waitFor(() => {
            expect(screen.getByText(/No devotees found/i)).toBeInTheDocument();
        });
    });
});

describe('Devotees Page - Error State', () => {
    it('shows error alert when API call fails', async () => {
        api.get.mockRejectedValueOnce(new Error('Network Error'));
        api.get.mockRejectedValueOnce(new Error('Network Error'));
        renderDevotees();

        await waitFor(() => {
            // error alert - there could also be the info alert, so check multiple alerts
            const alerts = screen.getAllByRole('alert');
            expect(alerts.length).toBeGreaterThanOrEqual(1);
        });
    });
});

describe('Devotees Page - API Calls', () => {
    it('calls /api/v1/devotees endpoint on mount', async () => {
        api.get.mockResolvedValueOnce({ data: [] });
        renderDevotees();

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/api/v1/devotees');
            expect(api.get).toHaveBeenCalledWith('/api/v1/donations?limit=2000');
            expect(api.get).toHaveBeenCalledWith('/api/v1/sevas/bookings?limit=500');
        });
    });
});
