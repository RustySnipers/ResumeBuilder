import axios from 'axios';

// Create generic axios instance
const api = axios.create({
    baseURL: '/api/v1', // Proxy will handle this in Vite
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 300000, // 5 minutes
});

export const authService = {
    login: async (username, password) => {
        // Stub login - not used
        return { access_token: "guest_mode" };
    },
    register: async (userData) => {
        // Stub register
        return {};
    },
};

export const resumeService = {
    upload: async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        // Use title from filename if possible
        formData.append('title', file.name || 'My Resume');
        const res = await api.post('/resumes/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return res.data;
    },
    analyze: async (resumeId, jobDescription, jobUrl) => {
        const res = await api.post('/jobs/analyze', {
            resume_id: resumeId,
            job_description: jobDescription,
            job_url: jobUrl,
        });
        return res.data;
    },
    export: async (resumeId, template, format = 'docx') => {
        const res = await api.post(`/export/${format}`, {
            resume_id: resumeId,
            template: template,
            format: format
        }, {
            responseType: 'blob' // Important for file download
        });
        return res.data; // Blob
    },
    getPreview: async (resumeId, template) => {
        const res = await api.post('/export/preview', {
            resume_id: resumeId,
            template: template,
            format: 'html'
        });
        return res.data; // HTML String
    },
    optimize: async (resumeId, jobDescription) => {
        const res = await api.post('/jobs/optimize', {
            resume_id: resumeId,
            job_description: jobDescription
        });
        return res.data;
    }
};

export default api;
