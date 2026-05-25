/**
 * Journal Service
 * Handles journal vouchers and journal entries
 */
import api from './api';

const BASE_URL = '/journal';

export const journalService = {
  /**
   * Get all journal entries
   */
  async getJournalEntries(fromDate = null, toDate = null) {
    let url = BASE_URL;
    const params = [];
    if (fromDate) params.push(`from_date=${fromDate}`);
    if (toDate) params.push(`to_date=${toDate}`);
    if (params.length > 0) url += `?${params.join('&')}`;

    const response = await api.get(url);
    return response.data;
  },

  /**
   * Get a specific journal entry by ID
   */
  async getJournalEntry(entryId) {
    const response = await api.get(`${BASE_URL}/${entryId}`);
    return response.data;
  },

  /**
   * Create a new journal entry
   */
  async createJournalEntry(entryData) {
    const response = await api.post(BASE_URL, entryData);
    return response.data;
  },

  /**
   * Update a journal entry
   */
  async updateJournalEntry(entryId, entryData) {
    const response = await api.put(`${BASE_URL}/${entryId}`, entryData);
    return response.data;
  },

  /**
   * Delete a journal entry
   */
  async deleteJournalEntry(entryId) {
    await api.delete(`${BASE_URL}/${entryId}`);
  },

  /**
   * Reverse a journal entry (creates a contra-entry)
   */
  async reverseJournalEntry(entryId) {
    const response = await api.post(`${BASE_URL}/${entryId}/reverse`);
    return response.data;
  }
};

export default journalService;

