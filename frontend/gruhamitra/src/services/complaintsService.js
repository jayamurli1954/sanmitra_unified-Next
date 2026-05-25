
import api from './api';

export const complaintsService = {
    getComplaints: async (status = null) => {
        let url = '/complaints/';
        if (status) {
            url += `?status=${status}`;
        }
        const response = await api.get(url);
        return response.data;
    },

    createComplaint: async (complaintData) => {
        const response = await api.post('/complaints/', complaintData);
        return response.data;
    },

    updateComplaint: async (id, updateData) => {
        const response = await api.patch(`/complaints/${id}`, updateData);
        return response.data;
    }
};
