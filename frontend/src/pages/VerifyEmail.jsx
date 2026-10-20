import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Bot, CheckCircle2, AlertCircle, RefreshCw, Mail, ArrowRight } from 'lucide-react';
import '../styles/auth.css';

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token') || '';
  const emailParam = searchParams.get('email') || '';

  const [status, setStatus] = useState('verifying'); // 'verifying' | 'success' | 'error' | 'invalid_params'
  const [errorMessage, setErrorMessage] = useState('');

  // Resend state
  const [emailInput, setEmailInput] = useState(emailParam);
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState('');

  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  useEffect(() => {
    let isMounted = true;

    if (!token || !emailParam) {
      setStatus('invalid_params');
      return;
    }

    const performVerification = async () => {
      try {
        const res = await apiService.verifyEmail(token, emailParam);
        if (isMounted) {
          if (res.success) {
            setStatus('success');
          } else {
            setStatus('error');
            setErrorMessage(res.message || 'Verification link could not be verified.');
          }
        }
      } catch (err) {
        if (isMounted) {
          setStatus('error');
          setErrorMessage(err.message || 'Verification link is invalid or has expired.');
        }
      }
    };

    performVerification();

    return () => {
      isMounted = false;
    };
  }, [token, emailParam]);

  const handleResend = async (e) => {
    e.preventDefault();
    const targetEmail = emailInput.trim();
    if (!targetEmail || resendCooldown > 0 || resending) return;

    setResending(true);
    setResendMessage('');
    try {
      await apiService.resendVerification(targetEmail);
      setResendMessage('A new verification email has been sent! Check your inbox.');
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
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div className="auth-header">
            <div className="auth-logo">
              <Bot size={30} />
            </div>
            <h2>Email Verification</h2>
          </div>

          {/* STATE 1: Verifying */}
          {status === 'verifying' && (
            <div style={{ padding: '2rem 1rem' }}>
              <RefreshCw size={40} className="spin" style={{ color: 'var(--primary, #4f46e5)', margin: '0 auto 1.5rem' }} />
              <h3>Verifying your email...</h3>
              <p className="subtitle" style={{ marginTop: '0.5rem' }}>
                Please wait while we confirm your credentials.
              </p>
            </div>
          )}

          {/* STATE 2: Success */}
          {status === 'success' && (
            <div style={{ padding: '1rem 0' }}>
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
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>Email Verified Successfully!</h3>
              <p className="subtitle" style={{ marginBottom: '1.75rem' }}>
                Your AI Interview Assistant account is now active. You can log in and start practicing interviews.
              </p>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => navigate('/login', { state: { emailVerified: true, email: emailParam } })}
              >
                <span>Continue to Login</span>
                <ArrowRight size={18} />
              </button>
            </div>
          )}

          {/* STATE 3: Error or Invalid */}
          {(status === 'error' || status === 'invalid_params') && (
            <div style={{ padding: '0.5rem 0' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '64px',
                  height: '64px',
                  background: '#fef2f2',
                  borderRadius: '50%',
                  color: '#dc2626',
                  marginBottom: '1rem',
                }}
              >
                <AlertCircle size={36} />
              </div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>
                {status === 'invalid_params' ? 'Invalid Verification Link' : 'Verification Failed'}
              </h3>
              <p className="subtitle" style={{ marginBottom: '1.5rem' }}>
                {errorMessage || 'The verification link is invalid, incomplete, or has expired after 24 hours.'}
              </p>

              {resendMessage && (
                <div className="auth-alert auth-alert-success" style={{ textAlign: 'left' }}>
                  {resendMessage}
                </div>
              )}

              <form onSubmit={handleResend} style={{ marginTop: '1rem', textAlign: 'left' }}>
                <div className="auth-form-group">
                  <label className="auth-form-label" htmlFor="resend-email">
                    Enter your email to receive a new link:
                  </label>
                  <div className="auth-input-wrapper">
                    <input
                      id="resend-email"
                      type="email"
                      placeholder="student@example.com"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      className="auth-input"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={resendCooldown > 0 || resending || !emailInput.trim()}
                  className="auth-submit-btn"
                >
                  {resending ? (
                    <>
                      <RefreshCw size={16} className="spin" /> Sending Link...
                    </>
                  ) : resendCooldown > 0 ? (
                    `Resend Link in ${resendCooldown}s`
                  ) : (
                    <>
                      <Mail size={16} /> Send New Verification Link
                    </>
                  )}
                </button>
              </form>
            </div>
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
