/**
 * Member Onboarding Service for Web
 */
import api from './api';

const normalizeMembersResponse = (data) => {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.items)) {
    return data.items;
  }

  if (Array.isArray(data?.members)) {
    return data.members;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
};

class MemberOnboardingService {
  /**
   * Create a single member profile (admin only)
   */
  async createMember(memberData) {
    const response = await api.post('/member-onboarding/', memberData);
    return response.data;
  }

  /**
   * Bulk import members from CSV file (admin only)
   */
  async bulkImportMembers(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/member-onboarding/bulk-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Download bulk upload template CSV
   */
  async downloadTemplate() {
    const response = await api.get('/member-onboarding/template', {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * List all members in the society
   */
  async listMembers(statusFilter, flatNumber) {
    const params = {};
    if (statusFilter) params.status_filter = statusFilter;
    if (flatNumber) params.flat_number = flatNumber;

    const response = await api.get('/member-onboarding', { params });
    return normalizeMembersResponse(response.data);
  }

  /**
   * Get current user's member profile
   */
  async getMyProfile() {
    const response = await api.get('/member-onboarding/my-profile');
    return response.data;
  }

  /**
   * Update member details (admin only)
   */
  async updateMember(memberId, memberData) {
    const response = await api.patch(`/member-onboarding/${memberId}`, memberData);
    return response.data;
  }

  /**
   * Get document checklist for a member
   */
  async getChecklist(memberId) {
    const response = await api.get(`/member-onboarding/${memberId}/checklist`);
    return response.data;
  }

  /**
   * Update document checklist
   */
  async updateChecklist(memberId, checklistData) {
    const response = await api.patch(`/member-onboarding/${memberId}/checklist`, checklistData);
    return response.data;
  }
}

export const memberOnboardingService = new MemberOnboardingService();
export default memberOnboardingService;

