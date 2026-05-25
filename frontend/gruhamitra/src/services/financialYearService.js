
import api from './api';

class FinancialYearService {
    /**
     * List all financial years
     */
    async listFinancialYears(includeClosed = true) {
        const response = await api.get(`/financial-years/?include_closed=${includeClosed}`);
        return response.data;
    }

    /**
     * Get active financial year
     */
    async getActiveFinancialYear() {
        const response = await api.get('/financial-years/active');
        return response.data;
    }

    /**
     * Create a new financial year
     */
    async createFinancialYear(yearData) {
        const response = await api.post('/financial-years/', yearData);
        return response.data;
    }

    /**
     * Provisionally close a financial year
     */
    async provisionalClose(yearId, closingData) {
        const response = await api.post(`/financial-years/${yearId}/provisional-close`, closingData);
        return response.data;
    }

    /**
     * Finally close a financial year
     */
    async finalClose(yearId, closingData) {
        const response = await api.post(`/financial-years/${yearId}/final-close`, closingData);
        return response.data;
    }
}

export const financialYearService = new FinancialYearService();
export default financialYearService;
