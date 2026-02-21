const API_BASE = '/api';

const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem('token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
    };

    const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
    const data = await response.json();

    if (!response.ok) {
        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/login';
        }
        throw new Error(data.error || 'Request failed');
    }
    return data;
};

export const api = {
    // Auth
    login: (credentials) => fetchWithAuth('/login', {
        method: 'POST',
        body: JSON.stringify(credentials)
    }),
    register: (userData) => fetchWithAuth('/register', {
        method: 'POST',
        body: JSON.stringify(userData)
    }),

    // Patient
    createLog: (log) => fetchWithAuth('/patient/daily-log', {
        method: 'POST',
        body: JSON.stringify(log)
    }),
    getLogs: () => fetchWithAuth('/patient/my-logs'),
    getGuidance: () => fetchWithAuth('/patient/guidance'),

    // RAG
    askRAG: (question) => fetchWithAuth('/rag/ask', {
        method: 'POST',
        body: JSON.stringify({ question })
    }),
    uploadDischarge: (formData) => {
        const token = localStorage.getItem('token');
        return fetch(`${API_BASE}/rag/upload-discharge`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        }).then(r => r.json());
    },

    // Doctor
    getPatients: () => fetchWithAuth('/doctor/patients'),
    getPatientDetails: (id) => fetchWithAuth(`/doctor/patient/${id}`),
    getAlerts: (status = 'unread') => fetchWithAuth(`/doctor/alerts?status=${status}`),
    markAlertRead: (alertId) => fetchWithAuth(`/doctor/alerts/${alertId}/read`, { method: 'POST' }),

    // Community
    createCommunityPost: (post) => fetchWithAuth('/community/posts', {
        method: 'POST',
        body: JSON.stringify(post)
    }),
    getCommunityPosts: (category) => fetchWithAuth(`/community/posts${category ? `?category=${category}` : ''}`),
    getCommunityPostById: (postId) => fetchWithAuth(`/community/posts/${postId}`),
    addCommunityComment: (postId, comment) => fetchWithAuth(`/community/posts/${postId}/comments`, {
        method: 'POST',
        body: JSON.stringify(comment)
    }),
    likeCommunityPost: (postId) => fetchWithAuth(`/community/posts/${postId}/like`, {
        method: 'POST'
    }),
};
