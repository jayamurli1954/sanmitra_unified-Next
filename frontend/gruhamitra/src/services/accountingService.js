/**
 * Accounting Service
 * Handles chart of accounts and accounting operations
 */
import api from './api';

const BASE_URL = '/accounting';

const normalizeAccount = (account) => ({
  ...account,
  id: account.id || account.account_id || account.code || account.account_code,
  code: account.code || account.account_code || String(account.id || account.account_id || ''),
  name: account.name || account.account_name || '',
  type: account.type || account.account_type || 'Asset',
  description: account.description || '',
  current_balance: account.current_balance ?? account.balance ?? 0,
});

const normalizeAccounts = (accounts) => (
  Array.isArray(accounts) ? accounts.map(normalizeAccount) : []
);

export const accountingService = {
  /**
   * Get all account codes
   */
  async getAccounts(type = null) {
    const response = await api.get(type ? `${BASE_URL}/accounts?type=${type}` : `${BASE_URL}/accounts`);
    return normalizeAccounts(response.data);
  },

  /**
   * Get a specific account by code
   */
  async getAccount(code) {
    const response = await api.get(`${BASE_URL}/accounts/${code}`);
    return normalizeAccount(response.data);
  },

  /**
   * Create a new account
   */
  async createAccount(accountData) {
    const response = await api.post(`${BASE_URL}/accounts`, accountData);
    return normalizeAccount(response.data);
  },

  /**
   * Update an account (name, description, etc.) - code cannot be changed
   */
  async updateAccount(code, updateData) {
    const response = await api.patch(`${BASE_URL}/accounts/${encodeURIComponent(code)}`, updateData);
    return normalizeAccount(response.data);
  },

  /**
   * Delete an account
   */
  async deleteAccount(code) {
    throw new Error('Deleting accounts is not supported by the live backend yet.');
  },

  /**
   * Initialize chart of accounts from predefined list
   */
  async initializeChartOfAccounts() {
    const response = await api.post(`${BASE_URL}/initialize-chart-of-accounts`);
    return response.data;
  },

  /**
   * Update opening balance for an account
   */
  async updateOpeningBalance(code, openingBalance) {
    throw new Error('Opening balance updates are not supported by the isolated accounting backend yet.');
  },

  /**
   * Validate balance sheet
   */
  async validateBalanceSheet() {
    const response = await api.get(`${BASE_URL}/reports/trial-balance`, {
      params: { as_of: new Date().toISOString().slice(0, 10) },
    });
    return response.data;
  },

  /**
   * Delete all account codes (admin only)
   */
  async deleteAccounts() {
    throw new Error('Deleting accounts is not supported by the live backend yet.');
  }
};

export default accountingService;

