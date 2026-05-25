import api from './api';

class OnboardingImportService {
  async downloadTemplate(kind) {
    const response = await api.get(`/onboarding-imports/templates/${kind}.csv`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async importDemoData(payload = {}) {
    const response = await api.post('/onboarding-imports/demo/import', payload);
    return response.data;
  }

  async importFlats(file, replaceExisting = false) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(
      `/onboarding-imports/import/flats?replace_existing=${replaceExisting ? 'true' : 'false'}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  }

  async importMembers(file, updateExisting = false) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(
      `/onboarding-imports/import/members?update_existing=${updateExisting ? 'true' : 'false'}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  }
}

export const onboardingImportService = new OnboardingImportService();
export default onboardingImportService;
