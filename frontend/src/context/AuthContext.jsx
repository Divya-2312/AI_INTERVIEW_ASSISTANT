import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService, setAccessToken } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize session on startup from httpOnly refresh cookie
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      try {
        // Primary flow: restore session silently via rotated httpOnly refresh cookie
        const res = await apiService.refreshToken();
        if (isMounted && res.success && res.user) {
          setUser(res.user);
          setLoading(false);
          return;
        }
      } catch (refreshErr) {
        // Fallback flow: check cached token if existing user has 30-day token
        const cachedToken = localStorage.getItem('assistant_token') || localStorage.getItem('mockmate_token');
        if (cachedToken) {
          try {
            const meRes = await apiService.getMe();
            if (isMounted && meRes.success && meRes.user) {
              setUser(meRes.user);
              setLoading(false);
              return;
            }
          } catch {
            // Clean up invalid cached token
            apiService.logout();
          }
        }
      }

      if (isMounted) {
        setUser(null);
        setLoading(false);
      }
    };

    restoreSession();

    // Listen for silent refresh expiration event emitted by apiService
    const handleSessionExpired = () => {
      setUser(null);
    };

    window.addEventListener('assistant:auth:expired', handleSessionExpired);
    window.addEventListener('mockmate:auth:expired', handleSessionExpired);

    return () => {
      isMounted = false;
      window.removeEventListener('assistant:auth:expired', handleSessionExpired);
      window.removeEventListener('mockmate:auth:expired', handleSessionExpired);
    };
  }, []);

  const login = async (email, password, rememberMe = false) => {
    try {
      const res = await apiService.login(email, password, rememberMe);
      if (res.success && res.user) {
        setUser(res.user);
        return { success: true, user: res.user };
      }
      return { success: false, message: res.message || 'Login failed' };
    } catch (err) {
      return {
        success: false,
        code: err.code,
        message: err.message || 'Invalid email or password',
        email: err.email,
      };
    }
  };

  const register = async (name, email, password, degree, university, targetRole) => {
    try {
      const res = await apiService.register(name, email, password, degree, university, targetRole);
      return {
        success: true,
        requiresVerification: res.requiresVerification !== false,
        email: res.email,
        message: res.message,
      };
    } catch (err) {
      return {
        success: false,
        code: err.code,
        message: err.message || 'Registration failed. Please check your details.',
      };
    }
  };

  const logout = async () => {
    try {
      await apiService.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        register,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
