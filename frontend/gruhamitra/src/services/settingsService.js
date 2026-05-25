/**
 * Settings Service for Web
 */
import api from './api';

class SettingsService {
  /**
   * Get society settings
   */
  async getSocietySettings() {
    const response = await api.get('/settings/society');
    return response.data;
  }

  /**
   * Create or update society settings
   */
  async saveSocietySettings(settingsData) {
    const response = await api.patch('/settings/society', settingsData);
    return response.data;
  }

  /**
   * Upload society logo
   */
  async uploadSocietyLogo(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/society/upload-logo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Upload society document (e.g. bye-laws)
   */
  async uploadSocietyDocument(file, documentType = 'other') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const response = await api.post('/society/upload-document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Delete society document by backend stored file name
   */
  async deleteSocietyDocument(fileName) {
    const response = await api.delete(`/society/documents/${encodeURIComponent(fileName)}`);
    return response.data;
  }
}

export const settingsService = new SettingsService();
export default settingsService;
