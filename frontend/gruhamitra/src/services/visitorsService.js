import api from './api';

const visitorsService = {
  async listVisitors(params = {}) {
    const response = await api.get('/visitors', { params });
    return response.data || [];
  },

  async createVisitor(data) {
    const response = await api.post('/visitors', data);
    return response.data;
  },

  async approveVisitor(visitorId) {
    const response = await api.post(`/visitors/${visitorId}/approve`);
    return response.data;
  },

  async rejectVisitor(visitorId, reason = '') {
    const response = await api.post(`/visitors/${visitorId}/reject`, { reason });
    return response.data;
  },

  async checkInVisitor(visitorId) {
    const response = await api.post(`/visitors/${visitorId}/check-in`);
    return response.data;
  },

  async checkOutVisitor(visitorId) {
    const response = await api.post(`/visitors/${visitorId}/check-out`);
    return response.data;
  },
};

export default visitorsService;
