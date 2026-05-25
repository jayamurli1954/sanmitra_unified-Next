import api from './api';

const attachmentService = {
    /**
     * Upload an attachment for a journal entry
     * @param {number} journalEntryId 
     * @param {File} file 
     */
    uploadAttachment: async (journalEntryId, file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post(`/attachments/upload/${journalEntryId}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    /**
     * List all attachments for a journal entry
     * @param {number} journalEntryId 
     */
    listAttachments: async (journalEntryId) => {
        const response = await api.get(`/attachments/journal/${journalEntryId}`);
        return response.data;
    },

    /**
     * Delete an attachment
     * @param {number} attachmentId 
     */
    deleteAttachment: async (attachmentId) => {
        const response = await api.delete(`/attachments/${attachmentId}`);
        return response.data;
    },

    /**
     * Get attachment download URL
     * Note: This returns the API endpoint URL which requires auth header
     * In a real app, you might use a signed URL or a direct download link with a token
     * Here we'll use the API path and handle it in the UI
     */
    getAttachmentUrl: (attachmentId) => {
        return `${api.defaults.baseURL}/attachments/${attachmentId}`;
    },

    /**
     * Securely download or view the attachment
     * @param {number} attachmentId 
     * @param {string} fileName 
     */
    downloadAttachment: async (attachmentId, fileName) => {
        const response = await api.get(`/attachments/${attachmentId}`, {
            responseType: 'blob',
        });

        // Create a blob URL and trigger download
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', fileName);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }
};

export default attachmentService;
