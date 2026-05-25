import api from './api';

const moveGovernanceService = {
    _extractBlobError: async (error) => {
        try {
            const blobData = error?.response?.data;
            if (blobData instanceof Blob) {
                const text = await blobData.text();
                if (text) {
                    try {
                        const json = JSON.parse(text);
                        return json?.detail || json?.message || text;
                    } catch {
                        return text;
                    }
                }
            }
            return error?.response?.data?.detail || error?.response?.data?.message || error?.message || 'Request failed';
        } catch {
            return error?.message || 'Request failed';
        }
    },

    _downloadPdfBlob: (blob, filename) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    },

    /**
     * Transfer flat dues to a personal arrears ledger
     * @param {Object} data { member_id, flat_id, amount, notes }
     */
    transferToArrears: async (data) => {
        const response = await api.post('/move-governance/transfer-to-arrears', data);
        return response.data;
    },

    /**
     * Transfer flat dues to another flat directly
     * @param {Object} data { source_flat_id, destination_flat_id, amount, notes }
     */
    transferFlatToFlatArrears: async (data) => {
        const response = await api.post('/move-governance/transfer-flat-to-flat', data);
        return response.data;
    },

    /**
     * List all personal arrears
     */
    listPersonalArrears: async () => {
        const response = await api.get('/move-governance/personal-arrears');
        return response.data;
    },

    /**
     * Download No Dues Certificate (NDC)
     * @param {number} flatId 
     */
    downloadNDC: async (flatId, flatNumber) => {
        try {
            const response = await api.get(`/move-governance/generate-ndc/${flatId}`, {
                responseType: 'blob'
            });
            const contentType = (response?.headers?.['content-type'] || '').toLowerCase();
            if (!contentType.includes('application/pdf')) {
                const text = await response.data.text();
                throw new Error(text || 'Invalid PDF response');
            }
            moveGovernanceService._downloadPdfBlob(response.data, `NDC_${flatNumber || flatId}.pdf`);
        } catch (error) {
            const message = await moveGovernanceService._extractBlobError(error);
            throw new Error(message || 'Failed to download NDC');
        }
    },

    /**
     * Download Police Verification Form for a member
     * @param {number} memberId 
     * @param {string} memberName 
     */
    downloadPoliceVerification: async (memberId, memberName) => {
        try {
            const response = await api.get(`/move-governance/police-verification-form/${memberId}`, {
                responseType: 'blob'
            });
            const contentType = (response?.headers?.['content-type'] || '').toLowerCase();
            if (!contentType.includes('application/pdf')) {
                const text = await response.data.text();
                throw new Error(text || 'Invalid PDF response');
            }
            moveGovernanceService._downloadPdfBlob(response.data, `Police_Verification_${memberName}.pdf`);
        } catch (error) {
            const message = await moveGovernanceService._extractBlobError(error);
            throw new Error(message || 'Failed to download Police Verification Form');
        }
    },

    /**
     * Download tenant/owner ID form for a member
     * @param {string} memberId
     * @param {string} memberName
     */
    downloadTenantIdForm: async (memberId, memberName) => {
        try {
            const response = await api.get(`/move-governance/tenant-id-form/${memberId}`, {
                responseType: 'blob'
            });
            const contentType = (response?.headers?.['content-type'] || '').toLowerCase();
            if (!contentType.includes('application/pdf')) {
                const text = await response.data.text();
                throw new Error(text || 'Invalid PDF response');
            }
            moveGovernanceService._downloadPdfBlob(response.data, `Tenant_ID_${memberName}.pdf`);
        } catch (error) {
            const message = await moveGovernanceService._extractBlobError(error);
            throw new Error(message || 'Failed to download Tenant ID Form');
        }
    },

    /**
     * Calculate final bill for move-out
     * @param {number} flatId 
     */
    calculateFinalBill: async (flatId) => {
        const response = await api.get(`/move-governance/calculate-final-bill/${flatId}`);
        return response.data;
    },

    /**
     * Raise an instant damage/misuse claim
     * @param {Object} data { flat_id, amount, description, instant_post }
     */
    raiseDamageClaim: async (data) => {
        const response = await api.post('/move-governance/damage-claim', data);
        return response.data;
    }
};

export default moveGovernanceService;
