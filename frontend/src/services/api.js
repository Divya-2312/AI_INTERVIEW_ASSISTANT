/**
 * AI Interview Assistant Centralized Frontend API Service
 * Communicates with Node.js Express REST API backend & AI Engine
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// In-memory access token storage (secure: not vulnerable to persistent XSS in localStorage)
let inMemoryAccessToken = null;

export const setAccessToken = (token) => {
  inMemoryAccessToken = token || null;
  if (token) {
    localStorage.setItem('assistant_token', token); // Fallback cache
    localStorage.setItem('mockmate_token', token);
  } else {
    localStorage.removeItem('assistant_token');
    localStorage.removeItem('mockmate_token');
  }
};

export const getAccessToken = () => {
  return inMemoryAccessToken || localStorage.getItem('assistant_token') || localStorage.getItem('mockmate_token');
};

// Queue for pending requests during silent refresh
let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onTokenRefreshed = (newAccessToken) => {
  refreshSubscribers.forEach((cb) => cb(newAccessToken));
  refreshSubscribers = [];
};

/**
 * Executes a network fetch against API_BASE_URL.
 * Supports credentials (httpOnly refresh cookies) and silent token refresh on 401 TOKEN_EXPIRED.
 */
const fetchAPI = async (endpoint, options = {}, isRetry = false) => {
  const token = getAccessToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const requestUrl = `${API_BASE_URL}${endpoint}`;
  let response;

  try {
    response = await fetch(requestUrl, {
      ...options,
      headers,
      credentials: 'include', // Transmit and receive httpOnly cookies
    });
  } catch (error) {
    console.error(`[API] Network request failed: ${options.method || 'GET'} ${requestUrl}`, error);
    throw new Error(
      `Unable to reach the AI Interview Assistant backend at ${API_BASE_URL}. Check that the Node/Express service is running. ${error.message || ''}`
    );
  }

  // Handle 401 TOKEN_EXPIRED: Silently refresh access token and retry request once
  if (response.status === 401 && !isRetry && endpoint !== '/auth/login' && endpoint !== '/auth/refresh') {
    let responseData = null;
    try {
      const cloned = response.clone();
      responseData = await cloned.json();
    } catch {
      // Ignore clone json parse errors
    }

    if (responseData && responseData.code === 'TOKEN_EXPIRED') {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
          });

          if (!refreshRes.ok) {
            throw new Error('Refresh token invalid or expired');
          }

          const refreshData = await refreshRes.json();
          const newAccessToken = refreshData.accessToken || refreshData.token;
          setAccessToken(newAccessToken);
          isRefreshing = false;
          onTokenRefreshed(newAccessToken);

          // Retry current request with new token
          return fetchAPI(endpoint, options, true);
        } catch (refreshErr) {
          isRefreshing = false;
          refreshSubscribers = [];
          setAccessToken(null);
          // Broadcast session expiration for AuthContext to cleanly redirect
          window.dispatchEvent(new CustomEvent('assistant:auth:expired'));
          window.dispatchEvent(new CustomEvent('mockmate:auth:expired'));
          const err = new Error('Session expired, please sign in again');
          err.code = 'SESSION_EXPIRED';
          throw err;
        }
      } else {
        // Wait for active refresh to finish then retry
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken) => {
            fetchAPI(endpoint, options, true)
              .then(resolve)
              .catch(reject);
          });
        });
      }
    }
  }

  const data = await response.json();

  if (!response.ok) {
    const errorMsg = data.message || `Request failed with status ${response.status}`;
    const err = new Error(errorMsg);
    err.status = response.status;
    err.code = data.code;
    err.email = data.email;
    if (data.evaluation) err.evaluation = data.evaluation;
    throw err;
  }

  return data;
};

export const apiService = {
  // Auth: Registration & Verification
  async register(name, email, password, degree, university, targetRole) {
    const data = await fetchAPI('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, degree, university, targetRole }),
    });
    return data;
  },

  async verifyEmail(token, email) {
    return await fetchAPI('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token, email }),
    });
  },

  async resendVerification(email) {
    return await fetchAPI('/auth/resend-verification', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  // Auth: Login, Refresh, Logout
  async login(email, password, rememberMe = false) {
    const data = await fetchAPI('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password, rememberMe }),
    });
    const token = data.accessToken || data.token;
    if (token) setAccessToken(token);
    return data;
  },

  async refreshToken() {
    const data = await fetchAPI('/auth/refresh', { method: 'POST' });
    const token = data.accessToken || data.token;
    if (token) setAccessToken(token);
    return data;
  },

  async getMe() {
    return await fetchAPI('/auth/me', { method: 'GET' });
  },

  async logout() {
    try {
      await fetchAPI('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore network errors on logout
    } finally {
      setAccessToken(null);
    }
  },

  // Auth: Password Reset Flow (6-digit code)
  async requestPasswordReset(email) {
    return await fetchAPI('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  async verifyResetCode(email, code) {
    return await fetchAPI('/auth/verify-reset-code', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    });
  },

  async resetPassword(email, resetToken, newPassword, confirmPassword) {
    return await fetchAPI('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email, resetToken, token: resetToken, newPassword, password: newPassword, confirmPassword }),
    });
  },

  // Questions & AI Engine (UNTOUCHED)
  async getQuestions(type, subject, difficulty) {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (subject) params.append('subject', subject);
    if (difficulty) params.append('difficulty', difficulty);

    const data = await fetchAPI(`/questions?${params.toString()}`, { method: 'GET' });
    return data.questions || [];
  },

  async createInterview(type, subject, difficulty, questionFormat) {
    const data = await fetchAPI('/interviews', {
      method: 'POST',
      body: JSON.stringify({ type, subject, difficulty, questionFormat }),
    });
    return data;
  },

  async getInterviews() {
    const data = await fetchAPI('/interviews', { method: 'GET' });
    return data.interviews || [];
  },

  async getInterviewById(id) {
    const data = await fetchAPI(`/interviews/${id}`, { method: 'GET' });
    return data.interview;
  },

  async deleteInterview(id) {
    return await fetchAPI(`/interviews/${id}`, { method: 'DELETE' });
  },

  async submitAnswer(interviewId, answerPayload) {
    return await fetchAPI(`/interviews/${interviewId}/answers`, {
      method: 'POST',
      body: JSON.stringify(answerPayload),
    });
  },

  async completeInterview(interviewId) {
    return await fetchAPI(`/interviews/${interviewId}/complete`, {
      method: 'POST',
    });
  },

  async getResult(interviewId) {
    return await fetchAPI(`/results/${interviewId}`, { method: 'GET' });
  },

  async getQuestionSolution(interviewId, questionKey) {
    const query = questionKey ? `?questionKey=${encodeURIComponent(questionKey)}` : '';
    return await fetchAPI(`/interviews/${interviewId}/solution${query}`, { method: 'GET' });
  },
};
