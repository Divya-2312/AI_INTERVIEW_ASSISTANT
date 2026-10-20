import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Bot, KeyRound, Mail, ArrowLeft, ArrowRight, Eye, EyeOff, Check, X, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import '../styles/auth.css';

export const ForgotPassword = () => {
  const navigate = useNavigate();

  // Multi-step flow: 1 = Email, 2 = 6-digit Code, 3 = New Password, 4 = Success
  const [step, setStep] = useState(1);

  // Form State
  const [email, setEmail] = useState('');
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // UX Feedback State
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState('');

  // Refs for 6-digit input boxes
  const digitRefs = [
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
  ];

  // Cooldown countdown timer
  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Autofocus first digit box on entering Step 2
  useEffect(() => {
    if (step === 2 && digitRefs[0].current) {
      digitRefs[0].current.focus();
    }
  }, [step]);

  // Real-time password rules
  const hasMinLength = newPassword.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(newPassword);
  const hasNumber = /[0-9]/.test(newPassword);
  const hasSpecial = /[^a-zA-Z0-9]/.test(newPassword);

  const calculateStrength = () => {
    if (!newPassword) return { label: '', class: '', score: 0 };
    let score = 0;
    if (hasMinLength) score += 1;
    if (hasLetter) score += 1;
    if (hasNumber) score += 1;
    if (hasSpecial && newPassword.length >= 10) score += 1;

    if (score <= 1) return { label: 'Weak', class: 'weak' };
    if (score === 2) return { label: 'Fair', class: 'fair' };
    if (score === 3) return { label: 'Good', class: 'good' };
    return { label: 'Strong', class: 'strong' };
  };

  const strength = calculateStrength();

  // -------------------------------------------------------------
  // STEP 1: Request 6-digit Code
  // -------------------------------------------------------------
  const handleRequestCode = async (e) => {
    e.preventDefault();
    setServerError('');
    setResendMessage('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setServerError('Please enter a valid email address.');
      return;
    }

    setSubmitting(true);
    try {
      await apiService.requestPasswordReset(cleanEmail);
      setSubmitting(false);
      setStep(2);
      setResendCooldown(30);
    } catch (err) {
      setSubmitting(false);
      setServerError(err.message || 'Unable to request verification code.');
    }
  };

  // -------------------------------------------------------------
  // STEP 2: Handle 6-Digit Code Input & Verification
  // -------------------------------------------------------------
  const handleDigitChange = (index, value) => {
    // Only accept numeric characters
    const numericChar = value.replace(/[^0-9]/g, '');

    const newDigits = [...digits];
    newDigits[index] = numericChar ? numericChar.slice(-1) : '';
    setDigits(newDigits);

    // Auto-advance to next box if digit entered
    if (numericChar && index < 5 && digitRefs[index + 1].current) {
      digitRefs[index + 1].current.focus();
    }
  };

  const handleDigitKeyDown = (index, e) => {
    // Backspace: clear current or move to previous box
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0 && digitRefs[index - 1].current) {
        digitRefs[index - 1].current.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      digitRefs[index - 1].current.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      digitRefs[index + 1].current.focus();
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

    // Focus last filled box or next empty box
    const focusIndex = Math.min(pasted.length, 5);
    if (digitRefs[focusIndex].current) {
      digitRefs[focusIndex].current.focus();
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setServerError('');
    setResendMessage('');

    const fullCode = digits.join('');
    if (fullCode.length !== 6) {
      setServerError('Please enter all 6 digits of your verification code.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiService.verifyResetCode(email.trim(), fullCode);
      setSubmitting(false);
      if (res.success && res.resetToken) {
        setResetToken(res.resetToken);
        setStep(3);
      } else {
        setServerError(res.message || 'Invalid verification code.');
      }
    } catch (err) {
      setSubmitting(false);
      setServerError(err.message || 'Invalid or expired code.');
    }
  };

  const handleResendCode = async () => {
    if (resendCooldown > 0 || submitting) return;

    setServerError('');
    setResendMessage('');
    try {
      await apiService.requestPasswordReset(email.trim());
      setResendMessage('A new 6-digit code has been dispatched to your email.');
      setResendCooldown(30);
      setDigits(['', '', '', '', '', '']);
      if (digitRefs[0].current) digitRefs[0].current.focus();
    } catch (err) {
      setServerError(err.message || 'Unable to resend code right now.');
    }
  };

  // -------------------------------------------------------------
  // STEP 3: Submit New Password
  // -------------------------------------------------------------
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!hasMinLength || !hasLetter || !hasNumber) {
      setServerError('Password must be at least 8 characters and contain at least one letter and one number.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setServerError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiService.resetPassword(email.trim(), resetToken, newPassword, confirmPassword);
      setSubmitting(false);
      if (res.success) {
        setStep(4);
      } else {
        setServerError(res.message || 'Unable to reset password.');
      }
    } catch (err) {
      setSubmitting(false);
      setServerError(err.message || 'Password reset link has expired. Please start over.');
    }
  };

  return (
    <div className="auth-page container">
      <div className="auth-card-wrapper">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <KeyRound size={28} />
            </div>
            <h2>
              {step === 1 && 'Forgot Password'}
              {step === 2 && 'Enter Verification Code'}
              {step === 3 && 'Set New Password'}
              {step === 4 && 'Password Reset'}
            </h2>
            <p className="subtitle">
              {step === 1 && 'Enter your email address to receive a 6-digit verification code.'}
              {step === 2 && `We sent a 6-digit code to ${email}. Valid for 10 minutes.`}
              {step === 3 && 'Choose a strong new password for your student account.'}
              {step === 4 && 'Your password has been successfully updated.'}
            </p>
          </div>

          {serverError && (
            <div className="auth-alert auth-alert-danger" role="alert">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{serverError}</div>
            </div>
          )}

          {resendMessage && (
            <div className="auth-alert auth-alert-success" role="status">
              <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{resendMessage}</div>
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 1: Email Form                                        */}
          {/* ========================================================= */}
          {step === 1 && (
            <form onSubmit={handleRequestCode} noValidate>
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="forgot-email">
                  Student Email Address <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="forgot-email"
                    type="email"
                    autoComplete="email"
                    autoFocus
                    placeholder="student@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="auth-input"
                    disabled={submitting}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="auth-submit-btn" disabled={submitting}>
                {submitting ? (
                  <>
                    <RefreshCw size={18} className="spin" />
                    <span>Sending Code...</span>
                  </>
                ) : (
                  <>
                    <Mail size={18} />
                    <span>Send Verification Code</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 2: 6-Digit Code Boxes                                */}
          {/* ========================================================= */}
          {step === 2 && (
            <form onSubmit={handleVerifyCode} noValidate>
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
                    disabled={submitting}
                    aria-label={`Digit ${idx + 1} of verification code`}
                  />
                ))}
              </div>

              <button type="submit" className="auth-submit-btn" disabled={submitting || digits.join('').length !== 6}>
                {submitting ? (
                  <>
                    <RefreshCw size={18} className="spin" />
                    <span>Verifying Code...</span>
                  </>
                ) : (
                  <>
                    <span>Verify Code</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>

              <div className="auth-resend-row" style={{ marginTop: '1.25rem' }}>
                <span>Didn't receive the code?</span>
                <button
                  type="button"
                  onClick={handleResendCode}
                  disabled={resendCooldown > 0 || submitting}
                  className="auth-secondary-btn"
                >
                  {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                </button>
              </div>

              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setServerError('');
                  }}
                  className="auth-link"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.85rem' }}
                >
                  Change email address
                </button>
              </div>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 3: Set New Password                                   */}
          {/* ========================================================= */}
          {step === 3 && (
            <form onSubmit={handleResetPassword} noValidate>
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reset-new-password">
                  New Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reset-new-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Min 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="auth-input auth-input-has-toggle"
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
                <label className="auth-form-label" htmlFor="reset-confirm-password">
                  Confirm New Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reset-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="auth-input auth-input-has-toggle"
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

              {/* Password strength meter */}
              {newPassword && (
                <div className="auth-strength-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>Strength:</span>
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
                      <span>At least 8 chars</span>
                    </div>
                    <div className={`auth-rule-item ${hasLetter ? 'valid' : ''}`}>
                      {hasLetter ? <Check size={12} /> : <X size={12} />}
                      <span>At least 1 letter</span>
                    </div>
                    <div className={`auth-rule-item ${hasNumber ? 'valid' : ''}`}>
                      {hasNumber ? <Check size={12} /> : <X size={12} />}
                      <span>At least 1 number</span>
                    </div>
                    <div className={`auth-rule-item ${confirmPassword && confirmPassword === newPassword ? 'valid' : ''}`}>
                      {confirmPassword && confirmPassword === newPassword ? <Check size={12} /> : <X size={12} />}
                      <span>Passwords match</span>
                    </div>
                  </div>
                </div>
              )}

              <button type="submit" className="auth-submit-btn" disabled={submitting}>
                {submitting ? (
                  <>
                    <RefreshCw size={18} className="spin" />
                    <span>Resetting Password...</span>
                  </>
                ) : (
                  <>
                    <KeyRound size={18} />
                    <span>Save New Password</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 4: Success Screen                                     */}
          {/* ========================================================= */}
          {step === 4 && (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '64px',
                  height: '64px',
                  background: '#f0fdf4',
                  borderRadius: '50%',
                  color: '#16a34a',
                  marginBottom: '1rem',
                }}
              >
                <CheckCircle2 size={36} />
              </div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>Password Reset Successful!</h3>
              <p className="subtitle" style={{ marginBottom: '1.75rem' }}>
                Your account password has been updated. You can now log in with your new credentials.
              </p>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => navigate('/login', { state: { passwordReset: true } })}
              >
                <span>Continue to Login</span>
                <ArrowRight size={18} />
              </button>
            </div>
          )}

          {step !== 4 && (
            <div className="auth-footer">
              <Link to="/login" className="auth-link" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <ArrowLeft size={14} /> Back to Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
