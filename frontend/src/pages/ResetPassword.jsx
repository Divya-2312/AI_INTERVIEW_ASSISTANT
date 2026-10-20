import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Bot, KeyRound, Eye, EyeOff, AlertCircle, RefreshCw, Check, X } from 'lucide-react';
import { apiService } from '../services/api';
import '../styles/auth.css';

export const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const hasMinLength = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!token) {
      setError('This reset link is invalid or incomplete. Please request a new link.');
      return;
    }
    if (!hasMinLength || !hasLetter || !hasNumber) {
      setError('Password must be at least 8 characters and contain at least one letter and one number.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await apiService.resetPassword('', token, password, confirmPassword);
      navigate('/login', { replace: true, state: { passwordReset: true } });
    } catch (requestError) {
      setError(requestError.message || 'Unable to reset the password. Request a new link.');
    } finally {
      setSubmitting(false);
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
            <h2>Reset Password</h2>
            <p className="subtitle">Choose a new password for your account.</p>
          </div>

          {error && (
            <div className="auth-alert auth-alert-danger" role="alert">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{error}</div>
            </div>
          )}

          {!token ? (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>
                This reset link is invalid or incomplete.
              </p>
              <Link to="/forgot-password" className="auth-submit-btn" style={{ textDecoration: 'none' }}>
                Request Verification Code
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="reset-new-pw">
                  New Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reset-new-pw"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
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
                <label className="auth-form-label" htmlFor="reset-confirm-pw">
                  Confirm New Password <span className="req">*</span>
                </label>
                <div className="auth-input-wrapper">
                  <input
                    id="reset-confirm-pw"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Re-enter password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
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

              {password && (
                <div className="auth-strength-container">
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
                    <div className={`auth-rule-item ${confirmPassword && confirmPassword === password ? 'valid' : ''}`}>
                      {confirmPassword && confirmPassword === password ? <Check size={12} /> : <X size={12} />}
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
                    <span>Reset Password</span>
                  </>
                )}
              </button>
            </form>
          )}

          <div className="auth-footer">
            <Link to="/login" className="auth-link">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
