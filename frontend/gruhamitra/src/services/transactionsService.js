/**
 * Transactions Service
 * Handles simple transaction entries (Quick Entry)
 */
import api from './api';

const BASE_URL = '/transactions';

export const transactionsService = {
    /**
     * Get all transactions
     */
    async getTransactions(params = {}) {
        const normalizedParams = { ...params };
        if (normalizedParams.type === 'income') {
            normalizedParams.voucher_type = 'receipt';
            delete normalizedParams.type;
        } else if (normalizedParams.type === 'expense') {
            normalizedParams.voucher_type = 'payment';
            delete normalizedParams.type;
        }
        if (normalizedParams.limit && !normalizedParams.page_size) {
            normalizedParams.page_size = normalizedParams.limit;
            delete normalizedParams.limit;
        }

        const response = await api.get(BASE_URL, { params: normalizedParams });
        return Array.isArray(response.data?.transactions) ? response.data.transactions : response.data;
    },

    /**
     * Get a single transaction by ID
     */
    async getTransaction(id) {
        const response = await api.get(`${BASE_URL}/${id}`);
        return response.data;
    },

    /**
     * Create a new transaction
     */
    async createTransaction(transactionData) {
        const response = await api.post(BASE_URL, transactionData);
        return response.data;
    },

    /**
     * Update a transaction
     */
    async updateTransaction(id, transactionData) {
        const response = await api.put(`${BASE_URL}/${id}`, transactionData);
        return response.data;
    },

    /**
     * Delete a transaction
     */
    async deleteTransaction(id) {
        await api.delete(`${BASE_URL}/${id}`);
    },

    /**
     * Reverse a transaction (group reversal via journal_entry if linked)
     */
    async reverseTransaction(id, reason = null) {
        let url = `${BASE_URL}/${id}/reverse`;
        if (reason) {
            url += `?reason=${encodeURIComponent(reason)}`;
        }
        const response = await api.post(url);
        return response.data;
    },

    /**
     * Create a specialized Receipt Voucher
     */
    async createReceipt(receiptData) {
        const response = await api.post(`${BASE_URL}/receipt`, receiptData);
        return response.data;
    },

    /**
     * Create a specialized Payment Voucher
     */
    async createPayment(paymentData) {
        const response = await api.post(`${BASE_URL}/payment`, paymentData);
        return response.data;
    },

    /**
     * Download Voucher PDF
     */
    async downloadVoucherPdf(journalEntryId) {
        const response = await api.get(`${BASE_URL}/vouchers/${journalEntryId}/pdf`, {
            responseType: 'blob'
        });
        return response.data;
    }
};

export default transactionsService;
