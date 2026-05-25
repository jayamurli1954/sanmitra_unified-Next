/**
 * Resource Service for Web
 */
import api from './api';

class ResourceService {
  /**
   * Upload a resource file
   */
  async uploadResourceFile(file, category, description = null) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    if (description) {
      formData.append('description', description);
    }

    const response = await api.post('/resources/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Get resource files by category
   */
  async getResourceFiles(category = null) {
    const params = category ? { category } : {};
    const response = await api.get('/resources/files', { params });
    return response.data;
  }

  /**
   * Delete a resource file
   */
  async deleteResourceFile(fileId) {
    const response = await api.delete(`/resources/files/${fileId}`);
    return response.data;
  }

  /**
   * Download a resource file
   */
  getFileDownloadUrl(fileId) {
    return `${api.defaults.baseURL}/resources/files/${fileId}/download`;
  }
}

export const resourceService = new ResourceService();
export default resourceService;
