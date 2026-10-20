import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Bot, UserPlus, Eye, EyeOff, AlertCircle, Check, X, Mail, RefreshCw, ArrowLeft } from 'lucide-react';
import '../styles/auth.css';

export const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    degree: 'B.Tech Computer Science',
    university: 'Anna University / Tech Campus',
    targetRole: 'Software Development Engineer (SDE)',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');

  // Post-registration "Check your email" screen state
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState('');

  // 30-second cooldown timer
  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Real-time password rules evaluation
  const password = formData.password;
  const hasMinLength = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^a-zA-Z0-9]/.test(password);

  const calculateStrength = () => {
    if (!password) return { label: '', class: '', score: 0 };
    let score = 0;
    if (hasMinLength) score += 1;
    if (hasLetter) score += 1;
    if (hasNumber) score += 1;
    if (hasSpecial && password.length >= 10) score += 1;

    if (score <= 1) return { label: 'Weak', class: 'weak', score };
    if (score === 2) return { label: 'Fair', class: 'fair', score };
    if (score === 3) return { label: 'Good', class: 'good', score };
    return { label: 'Strong', class: 'strong', score };
  };

  const strength = calculateStrength();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const errs = {};
    if (!formData.name.trim()) {
      errs.name = 'Full name is required';
    }

    const email = formData.email.trim();
    if (!email) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please provide a valid email format';
    }

    if (!formData.password) {
      errs.password = 'Password is required';
    } else if (!hasMinLength || !hasLetter || !hasNumber) {
      errs.password = 'Password must meet all security requirements';
    }

    if (formData.confirmPassword !== formData.password) {
      errs.confirmPassword = 'Passwords do not match';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    setResendMessage('');

    if (!validate()) return;

    setSubmitting(true);
    const result = await register(
      formData.name.trim(),
      formData.email.trim(),
      formData.password,
      formData.degree,
      formData.university,
      formData.targetRole
    );
    setSubmitting(false);

    if (result.success) {
      setRegisteredEmail(formData.email.trim());
      setResendCooldown(30);
    } else {
      setServerError(result.message || 'Registration failed. Please check your information.');
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || resending || !registeredEmail) return;

    setResending(true);
    try {
      await apiService.resendVerification(registeredEmail);
      setResendMessage('A new verification email has been sent!');
      setResendCooldown(30);
    } catch (err) {
      setResendMessage(err.message || 'Failed to resend verification email.');
    } finally {
      setResending(false);
    }
  };

  // SCREEN 2: "Check your email" after successful registration
  if (registeredEmail) {
    return (
      <div className="auth-page container">
        <div className="auth-card-wrapper">
          <div className="auth-card">
            <div className="auth-email-check-screen">
              <div className="auth-email-icon-wrapper">
                <Mail size={36} />
              </div>
              <h2>Check Your Email</h2>
              <p className="subtitle">
                We sent a secure verification link to activate your AI Interview Assistant account:
              </p>
              <div className="auth-email-badge">{registeredEmail}</div>
              <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.6, margin: '1rem 0' }}>
                Please check your inbox (and spam folder) and click the link to verify your account.
                The link is valid for <strong>24 hours</strong>.
              </p>

              {resendMessage && (
                <div className="auth-alert auth-alert-success" style={{ marginTop: '1rem', textAlign: 'left' }}>
                  {resendMessage}
                </div>
              )}

              <div className="auth-resend-row">
                <span>Didn't receive the email?</span>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || resending}
                  className="auth-secondary-btn"
                >
                  {resending ? (
                    <>
                      <RefreshCw size={14} className="spin" /> Sending...
                    </>
                  ) : resendCooldown > 0 ? (
                    `Resend in ${resendCooldown}s`
                  ) : (
                    'Resend Email'
                  )}
                </button>
              </div>

              <div style={{ marginTop: '2rem' }}>
                <Link to="/login" state={{ email: registeredEmail }} className="auth-link">
                  Continue to Login &rarr;
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // SCREEN 1: Registration Form
  return (
    <div className="auth-page container">
      <div className="auth-card-wrapper wide">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <Bot size={30} />
            </div>
            <h2>Student Account Registration</h2>
            <p className="subtitle">Create your account to practice technical & HR mock interviews.</p>
          </div>

          {serverError && (
            <div className="auth-alert auth-alert-danger" role="alert">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{serverError}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="auth-form-group">
              <label className="auth-form-label" htmlFor="reg-name">
                Full Name <span className="req">*</span>
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="reg-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  placeholder="e.g. Alex Morgan"
                  value={formData.name}
                  onChange={handleChange}
                  className={`auth-input ${errors.name ? 'has-error' : ''}`}
                  disabled={submitting}
                  required
                />
              </div>
              {errors.name && <span className="auth-field-error">{errors.name}</span>}
            </div>

            <div className="auth-form-group">
              <label className="auth-form-label" htmlFor="reg-email">
                Student Email Address <span className="req">*</span>
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="reg-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="e.g. alex.morgan@student.edu"
                  value={formData.email}
                  onChange={handleChange}
                  className={`auth-input ${errors.email ? 'has-error' : ''}`}
                  disabled={submitting}
                  required
                />
              </div>
              {errors.email && <span className="auth-field-error">{errors.email}</span>}
            </div>

            <div className="auth-grid-2">
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reg-password">
                  Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reg-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Min 8 characters"
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
              </div>

              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reg-confirm-password">
                  Confirm Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reg-confirm-password"
                    name="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter password"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className={`auth-input auth-input-has-toggle ${errors.confirmPassword ? 'has-error' : ''}`}
                    disabled={submitting}
                    required
                  />
                  <button
                    type="button"
                    className="auth-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Password Strength & Requirements Checklist */}
            {password && (
              <div className="auth-strength-container">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                  <span style={{ color: '#64748b', fontWeight: 500 }}>Password Strength:</span>
                  <span style={{ fontWeight: 700 }} className={`auth-strength-label ${strength.class}`}>
                    {strength.label}
                  </span>
                </div>
                <div className="auth-strength-bar-bg">
                  <div className={`auth-strength-bar ${strength.class}`} />
                </div>
                <div className="auth-rules-checklist">
                  <div className={`auth-rule-item ${hasMinLength ? 'valid' : ''}`}>
                    {hasMinLength ? <Check size={12} /> : <X size={12} />}
                    <span>At least 8 characters</span>
                  </div>
                  <div className={`auth-rule-item ${hasLetter ? 'valid' : ''}`}>
                    {hasLetter ? <Check size={12} /> : <X size={12} />}
                    <span>At least one letter</span>
                  </div>
                  <div className={`auth-rule-item ${hasNumber ? 'valid' : ''}`}>
                    {hasNumber ? <Check size={12} /> : <X size={12} />}
                    <span>At least one number</span>
                  </div>
                  <div className={`auth-rule-item ${formData.confirmPassword && formData.confirmPassword === password ? 'valid' : ''}`}>
                    {formData.confirmPassword && formData.confirmPassword === password ? <Check size={12} /> : <X size={12} />}
                    <span>Passwords match</span>
                  </div>
                </div>
              </div>
            )}

            {errors.password && <span className="auth-field-error" style={{ marginBottom: '0.5rem' }}>{errors.password}</span>}
            {errors.confirmPassword && <span className="auth-field-error" style={{ marginBottom: '0.5rem' }}>{errors.confirmPassword}</span>}

            <div className="auth-grid-2">
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reg-degree">
                  Academic Degree
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reg-degree"
                    name="degree"
                    type="text"
                    value={formData.degree}
                    onChange={handleChange}
                    className="auth-input"
                    disabled={submitting}
                  />
                </div>
              </div>

              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reg-role">
                  Target Career Role
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reg-role"
                    name="targetRole"
                    type="text"
                    value={formData.targetRole}
                    onChange={handleChange}
                    className="auth-input"
                    disabled={submitting}
                  />
                </div>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={submitting}>
              {submitting ? (
                <>
                  <RefreshCw size={18} className="spin" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <UserPlus size={18} />
                  <span>Create Student Account</span>
                </>
              )}
            </button>
          </form>

          <div className="auth-footer">
            Already have an account?{' '}
            <Link to="/login" className="auth-link">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
