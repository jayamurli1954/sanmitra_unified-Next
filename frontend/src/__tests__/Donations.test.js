import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

jest.setTimeout(10000);
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Donations from '../pages/Donations';

jest.mock('../services/api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
import api from '../services/api';

jest.mock('../components/Layout', () => ({ children }) => <div data-testid="layout">{children}</div>);

const paymentAccountsResponse = {
  data: {
    cash_accounts: [
      { account_id: 1, account_code: 'CASH-001', account_name: 'Main Cash' },
    ],
    bank_accounts: [
      { account_id: 10, account_code: 'BANK-001', account_name: 'Main Bank', bank_account_id: 100 },
    ],
  },
};

const devoteeSearchResponses = {
  '9876543210': {
    data: [
      { name_prefix: 'Sri', name: 'Rama Sharma', email: 'rama@example.com' },
    ],
  },
  '0000000000': {
    data: [],
  },
};

const renderDonations = () =>
  render(
    <MemoryRouter>
      <Donations />
    </MemoryRouter>
  );

const selectMuiOption = async (label, optionText) => {
  fireEvent.mouseDown(screen.getByLabelText(label));
  await waitFor(() => expect(screen.getByText(optionText)).toBeInTheDocument());
  fireEvent.click(screen.getByText(optionText));
};

const searchByMobile = async (phone) => {
  await userEvent.type(screen.getByLabelText(/Phone/i), phone);
  fireEvent.click(screen.getByRole('button', { name: /Search/i }));
};

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockImplementation((url) => {
    if (url === '/api/v1/donations/payment-accounts') {
      return Promise.resolve(paymentAccountsResponse);
    }
    if (url === '/api/v1/donations') {
      return Promise.resolve({ data: [] });
    }
    const phone = url.match(/\/api\/v1\/devotees\/search\/by-mobile\/(\d{10})$/)?.[1];
    if (phone && devoteeSearchResponses[phone]) {
      return Promise.resolve(devoteeSearchResponses[phone]);
    }
    return Promise.resolve({ data: [] });
  });
  api.post.mockResolvedValue({ data: { id: 1 } });
});

describe('Donations Page', () => {
  it('renders the main sections', async () => {
    renderDonations();

    expect(screen.getByText(/^Donations$/i)).toBeInTheDocument();
    expect(screen.getByText(/Record Donations/i)).toBeInTheDocument();
    expect(screen.getByText(/Recent Donations/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save All Donations/i })).toBeInTheDocument();
  });

  it('adds donation rows up to the maximum of five', async () => {
    renderDonations();

    const addButton = screen.getByRole('button', { name: /Add Entry/i });
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Entry 5')).toBeInTheDocument();
      expect(addButton).toBeDisabled();
    });
  });

  it('loads payment accounts and recent donations on mount', async () => {
    renderDonations();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/api/v1/donations/payment-accounts');
      expect(api.get).toHaveBeenCalledWith('/api/v1/donations');
    });
  });

  it('blocks submission until the mobile number has been searched', async () => {
    renderDonations();

    await userEvent.type(screen.getByLabelText(/Phone/i), '9876543210');
    await userEvent.type(screen.getByLabelText(/Amount/i), '1000');
    await selectMuiOption(/Category/i, 'General Donation');
    await selectMuiOption(/Cash Account Code/i, 'CASH-001 - Main Cash');

    fireEvent.click(screen.getByRole('button', { name: /Save All Donations/i }));

    await waitFor(() => {
      expect(screen.getByText(/Search mobile number first/i)).toBeInTheDocument();
      expect(api.post).not.toHaveBeenCalled();
    });
  });

  it('submits a monetary donation after a successful mobile search', async () => {
    renderDonations();

    await searchByMobile('9876543210');

    await waitFor(() => {
      expect(screen.getByDisplayValue('Rama Sharma')).toBeInTheDocument();
      expect(screen.getByDisplayValue('rama@example.com')).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText(/Amount/i), '1000');
    await selectMuiOption(/Category/i, 'General Donation');
    await selectMuiOption(/Cash Account Code/i, 'CASH-001 - Main Cash');

    fireEvent.click(screen.getByRole('button', { name: /Save All Donations/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/donations',
        expect.objectContaining({
          devotee_name: 'Rama Sharma',
          devotee_phone: '9876543210',
          amount: 1000,
          category: 'General Donation',
          payment_mode: 'Cash',
          payment_account_id: 1,
        })
      );
      expect(screen.getByText(/Successfully recorded 1 donation/i)).toBeInTheDocument();
    });
  });

  it('allows manual devotee entry after a mobile search returns no results', async () => {
    renderDonations();

    await searchByMobile('0000000000');

    await waitFor(() => {
      expect(screen.getByText(/No devotee found for this mobile number/i)).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText(/Devotee Name/i), 'Walk-in Devotee');
    await userEvent.type(screen.getByLabelText(/Amount/i), '500');
    await selectMuiOption(/Category/i, 'General Donation');
    await selectMuiOption(/Cash Account Code/i, 'CASH-001 - Main Cash');

    fireEvent.click(screen.getByRole('button', { name: /Save All Donations/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/donations',
        expect.objectContaining({
          devotee_name: 'Walk-in Devotee',
          devotee_phone: '0000000000',
          amount: 500,
        })
      );
    });
  });

  it('shows the backend error after a valid searched submission fails', async () => {
    api.post.mockRejectedValueOnce({
      response: { data: { detail: 'Donation save failed' } },
    });

    renderDonations();

    await searchByMobile('9876543210');
    await waitFor(() => expect(screen.getByDisplayValue('Rama Sharma')).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/Amount/i), '750');
    await selectMuiOption(/Category/i, 'General Donation');
    await selectMuiOption(/Cash Account Code/i, 'CASH-001 - Main Cash');

    fireEvent.click(screen.getByRole('button', { name: /Save All Donations/i }));

    await waitFor(() => {
      expect(screen.getByText(/Donation save failed/i)).toBeInTheDocument();
    });
  });
});
