import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Bot, UserPlus, Eye, EyeOff, AlertCircle, Check, X, Mail, RefreshCw, ArrowLeft, ArrowRight, CheckCircle2, Clock } from 'lucide-react';
import '../styles/auth.css';

export const Register = () => {
  const { register, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, loading, navigate]);

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

  // Post-registration "Enter Verification Code" / "Delivery Pending" screen state
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [emailSentState, setEmailSentState] = useState(false);
  const [codeCountdown, setCodeCountdown] = useState(60);
  const [codeExpired, setCodeExpired] = useState(false);
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [verifyingCode, setVerifyingCode] = useState(false);
  const [codeError, setCodeError] = useState('');
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendStatus, setResendStatus] = useState(''); // 'success' | 'error' | ''
  const [resendMessage, setResendMessage] = useState('');

  const digitRefs = [
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
  ];

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

  // 60-second code expiration countdown timer
  useEffect(() => {
    let timer;
    if (emailSentState && codeCountdown > 0) {
      timer = setInterval(() => {
        setCodeCountdown((prev) => {
          if (prev <= 1) {
            setCodeExpired(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [emailSentState, codeCountdown]);

  const formatCountdown = (secs) => {
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${mins}:${remSecs < 10 ? '0' : ''}${remSecs}`;
  };

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
    setResendStatus('');

    if (!validate()) return;

    setSubmitting(true);
    try {
      const result = await apiService.register(
        formData.name.trim(),
        formData.email.trim(),
        formData.password,
        formData.degree,
        formData.university,
        formData.targetRole
      );
      if (result.success) {
        setRegisteredEmail(formData.email.trim());
        const mailAccepted = result.emailSent === true;
        setEmailSentState(mailAccepted);
        const ttl = result.expiresInSeconds || 60;
        setCodeCountdown(ttl);
        setCodeExpired(false);
        setResendCooldown(30);
      } else {
        setServerError(result.message || 'Registration failed. Please check your information.');
      }
    } catch (err) {
      setServerError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDigitChange = (index, value) => {
    const numericChar = value.replace(/[^0-9]/g, '');
    const newDigits = [...digits];
    newDigits[index] = numericChar ? numericChar.slice(-1) : '';
    setDigits(newDigits);
    setCodeError('');

    if (numericChar && index < 5 && digitRefs[index + 1]?.current) {
      digitRefs[index + 1].current.focus();
    }
  };

  const handleDigitKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0 && digitRefs[index - 1]?.current) {
      digitRefs[index - 1].current.focus();
    }
  };

  const handleDigitPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6);
    if (!pasted) return;

    const newDigits = [...digits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pasted[i] || '';
    }
    setDigits(newDigits);
    setCodeError('');

    const nextIndex = Math.min(pasted.length, 5);
    if (digitRefs[nextIndex]?.current) {
      digitRefs[nextIndex].current.focus();
    }
  };

  const handleVerifyCode = async (e) => {
    if (e) e.preventDefault();
    const code = digits.join('').trim();
    if (code.length !== 6 || !registeredEmail || verifyingCode || codeExpired) return;

    setVerifyingCode(true);
    setCodeError('');
    try {
      const res = await apiService.verifyEmailCode(registeredEmail, code);
      if (res.success) {
        navigate('/login', {
          state: { emailVerified: true, email: registeredEmail },
          replace: true,
        });
      } else {
        setCodeError(res.message || 'Invalid or expired verification code.');
      }
    } catch (err) {
      setCodeError(err.message || 'Invalid or expired verification code.');
    } finally {
      setVerifyingCode(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || resending || !registeredEmail) return;

    setResending(true);
    setResendMessage('');
    setResendStatus('');
    try {
      const res = await apiService.resendVerification(registeredEmail);
      if (res.success && res.emailSent) {
        setEmailSentState(true);
        setResendStatus('success');
        setResendMessage(res.message || 'A new 6-digit verification code has been sent!');
        const ttl = res.expiresInSeconds || 60;
        setCodeCountdown(ttl);
        setCodeExpired(false);
        setCodeError('');
        setDigits(['', '', '', '', '', '']);
        setResendCooldown(30);
      } else {
        setResendStatus('error');
        setResendMessage(res.message || 'Could not send verification email. Please try again later.');
      }
    } catch (err) {
      setResendStatus('error');
      setResendMessage(err.message || 'Could not send verification email. Please try again later.');
      if (err.status === 429) {
        const remaining = err.retryAfter || 30;
        setResendCooldown(remaining);
      }
    } finally {
      setResending(false);
    }
  };

  // SCREEN 2: Post-registration screen (Honest 6-digit code or Delivery Pending)
  if (registeredEmail) {
    return (
      <div className="auth-page container">
        <div className="auth-card-wrapper">
          <div className="auth-card">
            <div className="auth-email-check-screen">
              <div className="auth-email-icon-wrapper">
                {emailSentState ? <Mail size={36} /> : <AlertCircle size={36} color="#d97706" />}
              </div>

              <h2>{emailSentState ? 'Enter Verification Code' : 'Email Delivery Pending'}</h2>

              {emailSentState ? (
                <>
                  <p className="subtitle">
                    We sent a 6-digit code to <strong>{registeredEmail}</strong>
                  </p>
                  <p className="subtitle" style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem', marginBottom: '0.5rem' }}>
                    The code is valid for 1 minute
                  </p>
                  {!codeExpired ? (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.4rem',
                        margin: '0.25rem auto 1rem',
                        padding: '0.35rem 0.85rem',
                        borderRadius: '9999px',
                        background: codeCountdown <= 15 ? '#fef2f2' : '#f0f9ff',
                        border: codeCountdown <= 15 ? '1px solid #fecaca' : '1px solid #bae6fd',
                        color: codeCountdown <= 15 ? '#b91c1c' : '#0369a1',
                        fontWeight: 700,
                        fontSize: '0.85rem',
                      }}
                      id="code-countdown-badge"
                    >
                      <Clock size={15} />
                      <span>Expires in {formatCountdown(codeCountdown)}</span>
                    </div>
                  ) : (
                    <div className="auth-alert auth-alert-danger" style={{ textAlign: 'left', marginTop: '0.5rem', marginBottom: '1rem' }} id="code-expired-notice">
                      <AlertCircle size={16} style={{ flexShrink: 0 }} /> <span>Code expired - request a new code</span>
                    </div>
                  )}

                  <form onSubmit={handleVerifyCode} style={{ marginTop: '1rem', textAlign: 'left' }}>
                    <div className="auth-form-group">
                      <label className="auth-form-label" style={{ textAlign: 'center', display: 'block' }}>
                        Enter 6-Digit Code
                      </label>
                      <div className="auth-digit-inputs" onPaste={handleDigitPaste}>
                        {digits.map((digit, idx) => (
                          <input
                            key={idx}
                            ref={digitRefs[idx]}
                            type="text"
                            inputMode="numeric"
                            pattern="[0-9]*"
                            maxLength={1}
                            value={digit}
                            onChange={(e) => handleDigitChange(idx, e.target.value)}
                            onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                            className={`auth-digit-box ${digit ? 'filled' : ''}`}
                            disabled={verifyingCode}
                            aria-label={`Digit ${idx + 1}`}
                            autoFocus={idx === 0}
                          />
                        ))}
                      </div>
                    </div>

                    {codeError && (
                      <div className="auth-alert auth-alert-danger" style={{ textAlign: 'left', marginTop: '1rem' }}>
                        <AlertCircle size={16} style={{ flexShrink: 0 }} /> <span>{codeError}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={verifyingCode || digits.join('').length !== 6 || codeExpired}
                      className="auth-submit-btn"
                      style={{ marginTop: '1rem' }}
                      id="verify-code-btn"
                    >
                      {verifyingCode ? (
                        <>
                          <RefreshCw size={16} className="spin" /> Verifying Code...
                        </>
                      ) : (
                        <>
                          <Check size={18} /> Verify &amp; Activate Account
                        </>
                      )}
                    </button>
                  </form>
                </>
              ) : (
                <>
                  <div className="auth-alert auth-alert-warning" style={{ marginTop: '1rem', textAlign: 'left' }}>
                    <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <strong>Your account was created but the email could not be sent.</strong>
                      <div style={{ marginTop: '4px', fontSize: '0.85rem' }}>
                        Please use the Resend button below to try dispatching your 6-digit verification code.
                      </div>
                    </div>
                  </div>
                  <div className="auth-email-badge" style={{ marginTop: '1rem' }}>{registeredEmail}</div>
                </>
              )}

              {resendMessage && (
                <div
                  className={`auth-alert ${resendStatus === 'error' ? 'auth-alert-danger' : 'auth-alert-success'}`}
                  style={{ marginTop: '1rem', textAlign: 'left' }}
                >
                  {resendStatus === 'error' ? (
                    <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  ) : (
                    <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
                  )}
                  <span>{resendMessage}</span>
                </div>
              )}

              <div className="auth-resend-row" style={{ marginTop: '1.5rem', justifyContent: 'center' }}>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || resending}
                  className="auth-secondary-btn"
                  id="resend-verification-btn"
                >
                  {resending ? (
                    <>
                      <RefreshCw size={14} className="spin" /> Sending...
                    </>
                  ) : resendCooldown > 0 ? (
                    `Resend in ${resendCooldown}s`
                  ) : (
                    'Resend Verification Code'
                  )}
                </button>
              </div>

              <div style={{ marginTop: '1.75rem' }}>
                <Link to="/login" state={{ email: registeredEmail }} className="auth-link">
                  Back to Login &rarr;
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
