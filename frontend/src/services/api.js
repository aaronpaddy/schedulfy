import axios from 'axios';

// API base URL comes from the build-time environment.
// Set REACT_APP_API_URL to the deployed backend origin (no trailing slash).
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5003';

// Create axios instance
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable sending cookies with requests
});

// API service objects
export const healthAPI = {
  checkHealth: () => {
    return api.get('/health');
  },
  checkBackendStatus: () => {
    return api.get('/courses').catch(() => {
      throw new Error('Backend not responding');
    });
  },
};

export const courseAPI = {
  getCourses: () => {
    return api.get('/courses');
  },

  importCourses: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/courses/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  scrapeCourses: (url, enhanced = false) => {
    return api.post('/courses/scrape', { url, enhanced });
  },

  exportCourses: () => {
    return api.get('/courses/export', {
      responseType: 'blob'
    });
  },

  clearCourses: () => {
    return api.delete('/courses/clear');
  },
};

export const scheduleAPI = {
  generateSchedule: (data) => {
    return api.post('/schedule/generate', data);
  },

  createSchedule: (data) => {
    return api.post('/schedule', data);
  },

  getSchedule: (scheduleId) => {
    return api.get(`/schedule/${scheduleId}`);
  },

  updateSchedule: (scheduleId, courseIds, forceUpdate = false) => {
    return api.put(`/schedule/${scheduleId}`, { 
      course_ids: courseIds,
      force_update: forceUpdate
    });
  },

  getWeeklySchedule: (scheduleId) => {
    return api.get(`/schedule/${scheduleId}/weekly`);
  },

  exportSchedule: (scheduleId) => {
    return api.get(`/schedule/${scheduleId}/export`, {
      responseType: 'blob'
    });
  },

  deleteSchedule: (scheduleId) => {
    return api.delete(`/schedule/${scheduleId}`);
  },

  getUserSchedules: () => {
    // Backend uses session-based auth, so no userId needed
    return api.get('/schedules');
  },
};

export const userAPI = {
  createUser: (userData) => {
    return api.post('/users', userData);
  },

  getUser: (userId) => {
    return api.get(`/users/${userId}`);
  },

  updateUser: (userId, userData) => {
    return api.put(`/users/${userId}`, userData);
  },

  getUserSchedules: (userId) => {
    // Backend uses session-based auth, so no userId needed
    return api.get(`/schedules`);
  },
  
  getUserPreferences: (userId) => {
    return api.get(`/users/${userId}/preferences`);
  },
  
  updateUserPreferences: (userId, preferences) => {
    return api.put(`/users/${userId}/preferences`, { preferences });
  },
};

export const requirementsAPI = {
  getRequirements: (major) => {
    return api.get(`/requirements/${major}`);
  },
};

export const authAPI = {
  signup: (userData) => {
    return api.post('/auth/signup', userData);
  },

  login: (credentials) => {
    return api.post('/auth/login', credentials);
  },

  logout: () => {
    return api.post('/auth/logout');
  },

  getCurrentUser: () => {
    return api.get('/auth/me');
  },

  checkAuth: () => {
    return api.get('/auth/check');
  },
};

// AI-powered API endpoints
export const aiAPI = {
  getRecommendations: (data) => {
    return api.post('/ai/recommendations', data);
  },

  chat: (message, includeHistory = true) => {
    return api.post('/ai/chat', { message, include_history: includeHistory });
  },

  predictWorkload: (courseIds) => {
    return api.post('/ai/workload-prediction', { course_ids: courseIds });
  },

  analyzeSchedule: (scheduleId) => {
    return api.get(`/ai/analyze-schedule/${scheduleId}`);
  },
};

export default api; 