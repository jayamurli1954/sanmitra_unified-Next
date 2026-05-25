/**
 * Flats Service for Web
 */
import api from './api';

class FlatsService {
  /**
   * Get all flats
   */
  async getFlats() {
    const response = await api.get('/flats/');
    return response.data;
  }

  /**
   * Get a specific flat by ID
   */
  async getFlat(flatId) {
    const response = await api.get(`/flats/${flatId}`);
    return response.data;
  }

  /**
   * Create a new flat
   */
  async createFlat(flatData) {
    const response = await api.post('/flats/', flatData);
    return response.data;
  }

  /**
   * Update an existing flat
   */
  async updateFlat(flatId, flatData) {
    const response = await api.put(`/flats/${flatId}`, flatData);
    return response.data;
  }
}

export const flatsService = new FlatsService();
export default flatsService;

