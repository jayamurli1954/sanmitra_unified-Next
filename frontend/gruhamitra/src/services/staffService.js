import api from './api';

const staffService = {
  async listStaff() {
    const response = await api.get('/staff');
    return response.data || [];
  },

  async createStaff(data) {
    const response = await api.post('/staff', data);
    return response.data;
  },

  async updateStaff(staffId, data) {
    const response = await api.put(`/staff/${staffId}`, data);
    return response.data;
  },

  async deleteStaff(staffId) {
    const response = await api.delete(`/staff/${staffId}`);
    return response.data;
  },

  async listAttendance(date = null) {
    const params = date ? { date } : {};
    const response = await api.get('/staff/attendance', { params });
    return response.data || [];
  },

  async checkInStaff(staffId) {
    const response = await api.post(`/staff/attendance/${staffId}/check-in`);
    return response.data;
  },

  async checkOutStaff(logId) {
    const response = await api.post(`/staff/attendance/${logId}/check-out`);
    return response.data;
  },
};

export default staffService;
