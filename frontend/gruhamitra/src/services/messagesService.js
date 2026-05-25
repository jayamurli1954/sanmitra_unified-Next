import api from './api';

const messagesService = {
    /**
     * List all chat rooms for the current society
     */
    listRooms: async () => {
        const response = await api.get('/messages/rooms');
        return response.data;
    },

    /**
     * Get messages in a specific room
     */
    getMessages: async (roomId, limit = 100) => {
        const response = await api.get(`/messages/rooms/${roomId}/messages?limit=${limit}`);
        return response.data;
    },

    /**
     * Send a message to a room
     */
    sendMessage: async (roomId, text, options = {}) => {
        if (options.file) {
            const formData = new FormData();
            formData.append('text', text || '');
            formData.append('retention_days', String(options.retention_days || 30));
            formData.append('file', options.file);
            const response = await api.post(`/messages/rooms/${roomId}/messages/with-attachment`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return response.data;
        }
        const response = await api.post(`/messages/rooms/${roomId}/messages`, {
            text,
            retention_days: options.retention_days || 30
        });
        return response.data;
    },

    downloadAttachment: async (downloadUrl, fileName) => {
        const response = await api.get(downloadUrl.replace('/api/v1', ''), { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', fileName || 'attachment');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    },

    /**
     * Create a new chat room (Admin only)
     */
    createRoom: async (roomData) => {
        const response = await api.post('/messages/rooms', roomData);
        return response.data;
    }
};

export default messagesService;
