/**
 * Membership v2 Onboarding Service (web)
 */
import api from './api';

class MembershipV2Service {
  async searchSocieties({ q, city, pin_code } = {}) {
    const params = {};
    if (q) params.q = q;
    if (city) params.city = city;
    if (pin_code) params.pin_code = pin_code;
    const response = await api.get('/v2/societies/search', { params });
    return response.data;
  }

  async createJoinRequest(societyId, payload) {
    const response = await api.post(`/v2/societies/${societyId}/join-requests`, payload);
    return response.data;
  }

  async listJoinRequests(societyId, status = 'pending') {
    const response = await api.get(`/v2/societies/${societyId}/join-requests`, {
      params: { status_filter: status },
    });
    return response.data;
  }

  async approveJoinRequest(membershipId, payload) {
    const response = await api.post(`/v2/join-requests/${membershipId}/approve`, payload);
    return response.data;
  }

  async rejectJoinRequest(membershipId, payload) {
    const response = await api.post(`/v2/join-requests/${membershipId}/reject`, payload);
    return response.data;
  }

  async listMyMemberships() {
    const response = await api.get('/v2/me/memberships');
    return response.data;
  }

  async listSocietyUnits(societyId) {
    const response = await api.get(`/v2/societies/${societyId}/units`);
    return response.data;
  }

  async createPublicJoinRequest(societyId, payload) {
    const response = await api.post(`/v2/public/societies/${societyId}/join-requests`, payload);
    return response.data;
  }

  async completeResidentRegistration(payload) {
    const response = await api.post('/v2/public/residents/complete-registration', payload);
    return response.data;
  }

  async getSocietyById(societyId) {
    const response = await api.get(`/society/${societyId}`);
    return response.data;
  }
}

export const membershipV2Service = new MembershipV2Service();
export default membershipV2Service;
