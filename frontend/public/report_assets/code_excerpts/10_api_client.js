// frontend/src/services/api.js:43-75
const fetchAPI = async (endpoint, options = {}, isRetry = false) => {
  const token = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include', // Sends httpOnly refreshToken cookie
  });

  // Handle silent token refresh on 401 TOKEN_EXPIRED
  if (response.status === 401 && !isRetry) {
    const data = await response.json().catch(() => ({}));
    if (data.code === 'TOKEN_EXPIRED') {
      const refreshed = await performSilentRefresh();
      if (refreshed) {
        return fetchAPI(endpoint, options, true);
      }
    }
  }
  return response.json();
};
