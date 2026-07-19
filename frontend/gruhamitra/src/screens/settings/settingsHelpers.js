import settingsService from '../../services/settingsService';
import api from '../../services/api';

// Helper function to safely extract error message from API errors
const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (Array.isArray(detail)) {
      // Pydantic validation errors - extract messages
      return detail.map(err => {
        if (typeof err === 'string') return err;
        if (typeof err === 'object' && err.msg) return err.msg;
        if (typeof err === 'object' && err.message) return err.message;
        return JSON.stringify(err);
      }).join(', ');
    } else if (typeof detail === 'string') {
      return detail;
    } else if (typeof detail === 'object') {
      return detail.msg || detail.message || 'Validation error occurred';
    }
  }
  if (error.message) {
    return error.message;
  }
  return 'An error occurred. Please try again.';
};

const uploadSocietyLogoWithFallback = async (file) => {
  if (typeof settingsService.uploadSocietyLogo === 'function') {
    return settingsService.uploadSocietyLogo(file);
  }

  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/society/upload-logo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

const uploadSocietyDocumentWithFallback = async (file, documentType = 'other') => {
  if (typeof settingsService.uploadSocietyDocument === 'function') {
    return settingsService.uploadSocietyDocument(file, documentType);
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);
  const response = await api.post('/society/upload-document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

const extractDocumentFileName = (url) => {
  if (!url || typeof url !== 'string') return '';
  const marker = '/society/documents/';
  const idx = url.indexOf(marker);
  const raw = idx >= 0 ? url.slice(idx + marker.length) : url.split('/').pop();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch (error) {
    return raw;
  }
};

const normalizeDocumentEndpoint = (url) => {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (raw.startsWith('/api/v1/')) return raw.replace('/api/v1', '');
  if (raw.startsWith('/v1/')) return raw.replace('/v1', '');
  return raw;
};

export {
  getErrorMessage,
  uploadSocietyLogoWithFallback,
  uploadSocietyDocumentWithFallback,
  extractDocumentFileName,
  normalizeDocumentEndpoint,
};
