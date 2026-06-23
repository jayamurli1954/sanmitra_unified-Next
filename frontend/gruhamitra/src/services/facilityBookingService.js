import api from './api';

class FacilityBookingService {
  async listFacilities(includeInactive = false) {
    const response = await api.get('/facilities', { params: { include_inactive: includeInactive } });
    return response.data || [];
  }

  async createFacility(data) {
    const response = await api.post('/facilities', data);
    return response.data;
  }

  async updateFacility(facilityId, data) {
    const response = await api.patch(`/facilities/${facilityId}`, data);
    return response.data;
  }

  async listBookings(params = {}) {
    const response = await api.get('/facility-bookings', { params });
    return response.data || [];
  }

  async createBooking(data) {
    const response = await api.post('/facility-bookings', data);
    return response.data;
  }

  async approveBooking(bookingId) {
    const response = await api.post(`/facility-bookings/${bookingId}/approve`);
    return response.data;
  }

  async cancelBooking(bookingId, reason = '') {
    const response = await api.post(`/facility-bookings/${bookingId}/cancel`, { reason });
    return response.data;
  }
}

export const facilityBookingService = new FacilityBookingService();
export default facilityBookingService;
