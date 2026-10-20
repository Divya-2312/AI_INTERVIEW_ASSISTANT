import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Bot, LogIn, Eye, EyeOff, AlertCircle, CheckCircle2, Clock, Mail, RefreshCw } from 'lucide-react';
import '../styles/auth.css';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const destination = location.state?.from;
  const returnTo = destination
    ? `${destination.pathname || ''}${destination.search || ''}${destination.hash || ''}`
    : '/dashboard';

  const [formData, setFormData] = useState({
    email: location.state?.email || '',
    password: '',
    rememberMe: false,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const [serverErrorCode, setServerErrorCode] = useState('');
  const [unverifiedEmail, setUnverifiedEmail] = useState('');

  // Resend verification state
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState('');

  // Manage 30-second cooldown timer
  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const errs = {};
    const email = formData.email.trim();

    if (!email) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      errs.password = 'Password is required';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    setServerErrorCode('');
    setResendMessage('');

    if (!validate()) return;

    setSubmitting(true);
    const result = await login(formData.email.trim(), formData.password, formData.rememberMe);
    setSubmitting(false);

    if (result.success) {
      navigate(returnTo, { replace: true });
    } else {
      setServerErrorCode(result.code || '');
      setServerError(result.message || 'Invalid email or password');
      if (result.code === 'EMAIL_NOT_VERIFIED') {
        setUnverifiedEmail(result.email || formData.email.trim());
      }
    }
  };

  const handleResendVerification = async () => {
    if (resendCooldown > 0 || resending || !unverifiedEmail) return;

    setResending(true);
    try {
      await apiService.resendVerification(unverifiedEmail);
      setResendMessage('Verification link sent! Please check your inbox.');
      setResendCooldown(30);
    } catch (err) {
      setResendMessage(err.message || 'Unable to resend verification email.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-page container">
      <div className="auth-card-wrapper">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <Bot size={30} />
            </div>
            <h2>Student Login</h2>
            <p className="subtitle">Welcome back! Access your AI Interview Assistant dashboard.</p>
          </div>

          {/* Flash status banners from navigation */}
          {location.state?.emailVerified && (
            <div className="auth-alert auth-alert-success" role="status">
              <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Email verified successfully!</strong>
                <div>You can now log in with your credentials.</div>
              </div>
            </div>
          )}

          {location.state?.passwordReset && (
            <div className="auth-alert auth-alert-success" role="status">
              <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Password updated!</strong>
                <div>Please log in with your new password.</div>
              </div>
            </div>
          )}

          {location.state?.sessionExpired && (
            <div className="auth-alert auth-alert-warning" role="alert">
              <Clock size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>Your session has expired. Please sign in again to continue.</div>
            </div>
          )}

          {/* Server Error Alerts */}
          {serverErrorCode === 'EMAIL_NOT_VERIFIED' ? (
            <div className="auth-alert auth-alert-warning" role="alert">
              <Mail size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ width: '100%' }}>
                <strong>Email not verified</strong>
                <p style={{ margin: '4px 0 8px 0', fontSize: '0.825rem' }}>
                  Please click the link in your verification email before logging in.
                </p>
                {resendMessage ? (
                  <div style={{ fontSize: '0.825rem', color: '#15803d', fontWeight: 600 }}>
                    {resendMessage}
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendCooldown > 0 || resending}
                    className="auth-secondary-btn"
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                  >
                    {resending ? (
                      <>
                        <RefreshCw size={14} className="spin" /> Sending...
                      </>
                    ) : resendCooldown > 0 ? (
                      `Resend in ${resendCooldown}s`
                    ) : (
                      'Resend Verification Link'
                    )}
                  </button>
                )}
              </div>
            </div>
          ) : serverErrorCode === 'ACCOUNT_LOCKED' ? (
            <div className="auth-alert auth-alert-danger" role="alert">
              <Clock size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{serverError}</div>
            </div>
          ) : serverError ? (
            <div className="auth-alert auth-alert-danger" role="alert">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{serverError}</div>
            </div>
          ) : null}

          <form onSubmit={handleSubmit} noValidate>
            <div className="auth-form-group">
              <label className="auth-form-label" htmlFor="login-email">
                Student Email Address <span className="req">*</span>
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  placeholder="e.g. student@university.edu"
                  value={formData.email}
                  onChange={handleChange}
                  className={`auth-input ${errors.email ? 'has-error' : ''}`}
                  disabled={submitting}
                  required
                />
              </div>
              {errors.email && <span className="auth-field-error">{errors.email}</span>}
            </div>

            <div className="auth-form-group">
              <label className="auth-form-label" htmlFor="login-password">
                Password <span className="req">*</span>
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your account password"
                  value={formData.password}
                  onChange={handleChange}
                  className={`auth-input auth-input-has-toggle ${errors.password ? 'has-error' : ''}`}
                  disabled={submitting}
                  required
                />
                <button
                  type="button"
                  className="auth-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && <span className="auth-field-error">{errors.password}</span>}
            </div>

            <div className="auth-meta-row">
              <label className="auth-checkbox-label" htmlFor="remember-me">
                <input
                  id="remember-me"
                  name="rememberMe"
                  type="checkbox"
                  checked={formData.rememberMe}
                  onChange={handleChange}
                />
                <span>Remember me</span>
              </label>
              <Link to="/forgot-password" className="auth-link">
                Forgot password?
              </Link>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={submitting}>
              {submitting ? (
                <>
                  <RefreshCw size={18} className="spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <LogIn size={18} />
                  <span>Login to Dashboard</span>
                </>
              )}
            </button>
          </form>

          <div className="auth-footer">
            Don't have an account?{' '}
            <Link to="/register" state={location.state} className="auth-link">
              Create a Student Account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
