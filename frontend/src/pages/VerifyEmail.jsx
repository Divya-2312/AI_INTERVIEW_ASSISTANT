import React, { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Bot, CheckCircle2, AlertCircle, RefreshCw, Mail, ArrowRight, Check, Clock } from 'lucide-react';
import '../styles/auth.css';

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token') || '';
  const emailParam = searchParams.get('email') || '';

  const [status, setStatus] = useState(token && emailParam ? 'verifying' : 'enter_code'); // 'verifying' | 'enter_code' | 'success' | 'error' | 'invalid_params'
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // 6-digit code state
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [verifyingCode, setVerifyingCode] = useState(false);
  const [codeError, setCodeError] = useState('');
  const [codeCountdown, setCodeCountdown] = useState(60);
  const [codeExpired, setCodeExpired] = useState(false);

  const digitRefs = [
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
  ];

  // Resend state
  const [emailInput, setEmailInput] = useState(emailParam);
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendStatus, setResendStatus] = useState(''); // 'success' | 'error' | ''
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

  // 60-second code expiration countdown timer
  useEffect(() => {
    let timer;
    if (status === 'enter_code' && codeCountdown > 0) {
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
  }, [status, codeCountdown]);

  const formatCountdown = (secs) => {
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${mins}:${remSecs < 10 ? '0' : ''}${remSecs}`;
  };

  useEffect(() => {
    let isMounted = true;

    if (!token || !emailParam) {
      // No token to verify automatically; allow user to enter code
      return;
    }

    const performVerification = async () => {
      try {
        const res = await apiService.verifyEmail(token, emailParam);
        if (isMounted) {
          if (res.success) {
            setStatus('success');
            setSuccessMessage(res.message || 'Email verified successfully! You can now log in to your account.');
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

  const handleVerifyCodeSubmit = async (e) => {
    if (e) e.preventDefault();
    const code = digits.join('').trim();
    const targetEmail = emailInput.trim();
    if (code.length !== 6 || !targetEmail || verifyingCode || codeExpired) return;

    setVerifyingCode(true);
    setCodeError('');
    try {
      const res = await apiService.verifyEmailCode(targetEmail, code);
      if (res.success) {
        setStatus('success');
        setSuccessMessage(res.message || 'Email verified successfully! You can now log in to your account.');
      } else {
        setCodeError(res.message || 'Invalid or expired verification code.');
      }
    } catch (err) {
      setCodeError(err.message || 'Verification code is invalid or has expired.');
    } finally {
      setVerifyingCode(false);
    }
  };

  const handleResend = async (e) => {
    if (e) e.preventDefault();
    const targetEmail = emailInput.trim();
    if (!targetEmail || resendCooldown > 0 || resending) return;

    setResending(true);
    setResendMessage('');
    setResendStatus('');
    try {
      const res = await apiService.resendVerification(targetEmail);
      if (res.success && res.emailSent) {
        setResendStatus('success');
        setResendMessage(res.message || 'A new 6-digit verification code has been sent! Check your inbox.');
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
      setResendMessage(err.message || 'Unable to resend verification code.');
      if (err.status === 429) {
        setResendCooldown(err.retryAfter || 30);
      }
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

          {/* STATE 1: Verifying via link */}
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
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>
                {successMessage || 'Email Verified Successfully!'}
              </h3>
              <p className="subtitle" style={{ marginBottom: '1.75rem' }}>
                Your AI Interview Assistant account is active. You can log in and start practicing interviews.
              </p>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => navigate('/login', { state: { emailVerified: true, email: emailInput || emailParam } })}
              >
                <span>Continue to Login</span>
                <ArrowRight size={18} />
              </button>
            </div>
          )}

          {/* STATE 3: Enter 6-digit Code or Error */}
          {(status === 'enter_code' || status === 'error' || status === 'invalid_params') && (
            <div style={{ padding: '0.5rem 0' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '56px',
                  height: '56px',
                  background: status === 'enter_code' ? '#eff6ff' : '#fef2f2',
                  borderRadius: '50%',
                  color: status === 'enter_code' ? '#3b82f6' : '#dc2626',
                  marginBottom: '1rem',
                }}
              >
                {status === 'enter_code' ? <Mail size={30} /> : <AlertCircle size={30} />}
              </div>

              <h3 style={{ color: '#0f172a', marginBottom: '0.25rem' }}>
                {status === 'enter_code' ? 'Enter 6-Digit Code' : 'Verification Needed'}
              </h3>
              <p className="subtitle" style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.5rem' }}>
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
                  id="verify-code-countdown"
                >
                  <Clock size={15} />
                  <span>Expires in {formatCountdown(codeCountdown)}</span>
                </div>
              ) : (
                <div className="auth-alert auth-alert-danger" style={{ textAlign: 'left', marginTop: '0.5rem', marginBottom: '1rem' }} id="verify-code-expired-notice">
                  <AlertCircle size={16} style={{ flexShrink: 0 }} /> <span>Code expired - request a new code</span>
                </div>
              )}
              <p className="subtitle" style={{ marginBottom: '1rem', fontSize: '0.875rem' }}>
                {errorMessage || 'Enter the 6-digit verification code sent to your email address:'}
              </p>

              <form onSubmit={handleVerifyCodeSubmit} style={{ marginTop: '0.5rem', textAlign: 'left' }}>
                <div className="auth-form-group">
                  <label className="auth-form-label" htmlFor="verify-email-input">
                    Student Email Address
                  </label>
                  <div className="auth-input-wrapper">
                    <input
                      id="verify-email-input"
                      type="email"
                      placeholder="student@example.com"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      className="auth-input"
                      required
                    />
                  </div>
                </div>

                <div className="auth-form-group" style={{ marginTop: '1rem' }}>
                  <label className="auth-form-label">
                    6-Digit Verification Code
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
                  disabled={verifyingCode || digits.join('').length !== 6 || !emailInput.trim() || codeExpired}
                  className="auth-submit-btn"
                  style={{ marginTop: '1rem' }}
                >
                  {verifyingCode ? (
                    <>
                      <RefreshCw size={16} className="spin" /> Verifying Code...
                    </>
                  ) : (
                    <>
                      <Check size={18} /> Verify Code & Activate
                    </>
                  )}
                </button>
              </form>

              {resendMessage && (
                <div
                  className={`auth-alert ${resendStatus === 'error' ? 'auth-alert-danger' : 'auth-alert-success'}`}
                  style={{ textAlign: 'left', marginTop: '1rem' }}
                >
                  {resendStatus === 'error' ? (
                    <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  ) : (
                    <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
                  )}
                  <span>{resendMessage}</span>
                </div>
              )}

              <div className="auth-resend-row" style={{ marginTop: '1.25rem' }}>
                <span>Didn't receive the code?</span>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || resending || !emailInput.trim()}
                  className="auth-secondary-btn"
                >
                  {resending ? 'Sending...' : resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                </button>
              </div>
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
