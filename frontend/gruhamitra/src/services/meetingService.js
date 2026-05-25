/**
 * Meeting Management Service (Web)
 * Handles meeting creation, attendance, minutes, and resolutions
 */
import api from './api';

export const meetingService = {
    // ===== List Meetings =====
    async getMeetings(params = {}) {
        const response = await api.get('/meetings', { params });
        return response.data;
    },

    // ===== Get Single Meeting =====
    async getMeeting(meetingId) {
        const response = await api.get(`/meetings/${meetingId}`);
        return response.data;
    },

    // ===== Get Complete Meeting Details =====
    async getMeetingDetails(meetingId) {
        const response = await api.get(`/meetings/${meetingId}/details`);
        return response.data;
    },

    // ===== Create Meeting =====
    async createMeeting(data) {
        const response = await api.post('/meetings', data);
        return response.data;
    },

    // ===== Update Meeting =====
    async updateMeeting(meetingId, data) {
        const response = await api.patch(`/meetings/${meetingId}`, data);
        return response.data;
    },

    // ===== Delete Meeting =====
    async deleteMeeting(meetingId) {
        await api.delete(`/meetings/${meetingId}`);
    },

    // ===== Mark Attendance =====
    async markAttendance(meetingId, data) {
        const response = await api.post(`/meetings/${meetingId}/attendance`, data);
        return response.data;
    },

    // ===== Record Minutes =====
    async recordMinutes(meetingId, data) {
        const response = await api.post(`/meetings/${meetingId}/minutes`, data);
        return response.data;
    },

    // ===== Create Resolution =====
    async createResolution(meetingId, data) {
        const response = await api.post(`/meetings/${meetingId}/resolutions`, data);
        return response.data;
    },

    // ===== Send Meeting Notice =====
    async sendNotice(meetingId, data) {
        const response = await api.post(`/meetings/${meetingId}/send-notice`, data);
        return response.data;
    },

    // ===== Get Members (for attendance and resolutions) =====
    async getMembers() {
        try {
            const response = await api.get('/member-onboarding');
            return response.data.map(member => ({
                id: member.id,
                name: member.name,
                flat_number: member.flat_number,
                member_type: member.member_type,
                status: member.status,
                email: member.email,
                phone_number: member.phone_number,
            }));
        } catch (error) {
            console.error('Error loading members:', error);
            return [];
        }
    },


};

export default meetingService;
