import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

/**
 * Post a video to selected platforms
 * @param {FormData} formData - Contains: video (file), title, description, platforms (JSON string)
 */
export async function postVideo(formData, { signal } = {}) {
  const response = await api.post('/post-video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000, // 10 minutes — video uploads can be slow
    signal,
  });
  return response.data;
}

/**
 * Get current settings (tokens masked)
 */
export async function getSettings() {
  const response = await api.get('/settings');
  return response.data;
}

/**
 * Save platform credentials
 */
export async function saveSettings(data) {
  const response = await api.post('/settings', data);
  return response.data;
}

export async function generatePlatformCaptions(payload) {
  const response = await api.post('/ai/platform-captions', payload, {
    timeout: 60 * 1000,
  });
  return response.data;
}

/**
 * Exchange YouTube OAuth code for refresh token
 */
export async function exchangeYouTubeAuth(code) {
  const response = await api.post('/settings/youtube-auth', { code });
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}

/**
 * Schedule a video post for a future time
 * @param {FormData} formData - Contains: video, title, description, platforms, scheduledAt
 */
export async function scheduleVideo(formData) {
  const response = await api.post('/schedule', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000,
  });
  return response.data;
}

/**
 * Get all scheduled posts
 */
export async function getSchedules() {
  const response = await api.get('/schedules');
  return response.data;
}

export async function getHistory() {
  const response = await api.get('/history');
  return response.data;
}

export async function deleteHistoryItem(id) {
  const response = await api.delete(`/history/${id}`);
  return response.data;
}

/**
 * Cancel/delete a scheduled post
 */
export async function cancelSchedule(id) {
  const response = await api.delete(`/schedules/${id}`);
  return response.data;
}

export default api;
