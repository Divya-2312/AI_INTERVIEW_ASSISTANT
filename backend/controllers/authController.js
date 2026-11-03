import { createHash, randomBytes, randomInt } from 'node:crypto';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';
import { emailService } from '../services/emailService.js';

const JWT_ACCESS_EXPIRY = '15m';
const REFRESH_TOKEN_DAYS = 7;
const REMEMBER_ME_DAYS = 30;
const RESET_CODE_TTL_MS = 10 * 60 * 1000; // 10 minutes
export const VERIFY_CODE_TTL_MS = 60 * 1000; // 1 minute (60 seconds)
const VERIFY_EMAIL_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const LOCKOUT_TIME_MS = 15 * 60 * 1000; // 15 minutes
const MAX_LOGIN_ATTEMPTS = 5;
const MAX_RESET_CODE_ATTEMPTS = 5;
const COOLDOWN_SECONDS = 30;

/**
 * SHA-256 hash helper
 */
const sha256 = (str) => createHash('sha256').update(String(str)).digest('hex');

/**
 * Generates short-lived access token (15 mins)
 */
const generateAccessToken = (userId) => {
  return jwt.sign(
    { id: userId },
    process.env.JWT_SECRET || 'ai_interview_assistant_jwt_secret_key_2026_super_secure',
    { expiresIn: JWT_ACCESS_EXPIRY }
  );
};

/**
 * Generates a random refresh token string
 */
const generateRefreshTokenString = () => randomBytes(40).toString('hex');

/**
 * Helper to set the httpOnly refresh cookie
 */
const setRefreshTokenCookie = (res, rawRefreshToken, rememberMe = false) => {
  const isProd = process.env.NODE_ENV === 'production';
  const days = rememberMe ? REMEMBER_ME_DAYS : REFRESH_TOKEN_DAYS;
  const maxAge = days * 24 * 60 * 60 * 1000;

  res.cookie('refreshToken', rawRefreshToken, {
    httpOnly: true,
    sameSite: isProd ? 'none' : 'lax',
    secure: isProd,
    path: '/api/auth',
    maxAge,
  });
};

/**
 * Helper to clear the refresh token cookie
 */
const clearRefreshTokenCookie = (res) => {
  const isProd = process.env.NODE_ENV === 'production';
  res.clearCookie('refreshToken', {
    httpOnly: true,
    sameSite: isProd ? 'none' : 'lax',
    secure: isProd,
    path: '/api/auth',
  });
};

/**
 * Password validation rule: min 8 characters, at least one letter and one number
 */
const isValidPassword = (password) => {
  if (typeof password !== 'string' || password.length < 8) return false;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  return hasLetter && hasNumber;
};

// @desc    Register a new student with email verification
// @route   POST /api/auth/register
// @access  Public
export const registerUser = async (req, res, next) => {
  try {
    const { name, email, password, degree, university, targetRole } = req.body;

    const trimmedName = typeof name === 'string' ? name.trim() : '';
    const normalizedEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';

    if (!trimmedName || !normalizedEmail || !password) {
      return res.status(400).json({
        success: false,
        message: 'Please provide full name, email address, and password.',
      });
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      return res.status(400).json({
        success: false,
        message: 'Please provide a valid email address format.',
      });
    }

    if (!isValidPassword(password)) {
      return res.status(400).json({
        success: false,
        message: 'Password must be at least 8 characters long and contain at least one letter and one number.',
      });
    }

    const existingUser = await User.findOne({ email: normalizedEmail });
    if (existingUser) {
      return res.status(409).json({
        success: false,
        code: 'EMAIL_ALREADY_EXISTS',
        message: 'An account with this email address already exists. Please log in or reset your password.',
      });
    }

    // Generate random 32-byte verification token and 6-digit code
    const verificationToken = randomBytes(32).toString('hex');
    const verificationCode = String(randomInt(100000, 1000000));
    const verificationTokenHash = sha256(verificationToken);
    const verificationCodeHash = sha256(verificationCode);

    const user = await User.create({
      name: trimmedName,
      email: normalizedEmail,
      password,
      degree: degree || 'B.Tech Computer Science',
      university: university || 'Anna University',
      targetRole: targetRole || 'Software Development Engineer (SDE)',
      emailVerified: false,
      emailVerificationTokenHash: verificationTokenHash,
      emailVerificationCodeHash: verificationCodeHash,
      emailVerificationCodeExpiresAt: new Date(Date.now() + VERIFY_CODE_TTL_MS), // 1 minute
      emailVerificationCodeAttempts: 0,
      emailVerificationExpiresAt: new Date(Date.now() + VERIFY_EMAIL_TTL_MS),
      lastEmailVerificationSentAt: new Date(),
    });

    // Send 6-digit verification code email and report honest outcome
    let emailResult;
    try {
      emailResult = await emailService.sendVerificationCodeEmail(user.email, user.name, verificationCode);
    } catch (mailError) {
      console.error(`[Auth] Verification code email error for ${user.email}:`, mailError.message);
      emailResult = { success: false, code: 'EMAIL_SEND_FAILED', error: mailError.message };
    }
    const emailSent = !!(emailResult && emailResult.success);

    let registerMessage = 'Registration successful! A 6-digit verification code has been sent to your email address.';
    if (!emailSent) {
      if (emailResult?.code === 'ETHEREAL_SANDBOX') {
        registerMessage =
          'Your account was created, but the email service is a test sandbox (Ethereal) and emails will not reach real inboxes.';
      } else {
        const reason = emailResult?.code === 'SMTP_NOT_CONFIGURED'
          ? 'SMTP is not configured on the server'
          : (emailResult?.error || 'email delivery failed');
        console.error(`[Auth] Verification code email NOT delivered to ${user.email} (${reason}).`);
        registerMessage =
          'Your account was created, but we could not send the verification email. Please use the Resend button to try again.';
      }
    }

    return res.status(201).json({
      success: true,
      requiresVerification: true,
      emailSent,
      expiresAt: user.emailVerificationCodeExpiresAt.toISOString(),
      expiresInSeconds: Math.floor(VERIFY_CODE_TTL_MS / 1000),
      message: registerMessage,
      email: user.email,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        emailVerified: false,
        degree: user.degree,
        university: user.university,
        targetRole: user.targetRole,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Verify email address via 6-digit code
// @route   POST /api/auth/verify-email-code
// @access  Public (Rate-limited)
export const verifyEmailCode = async (req, res, next) => {
  try {
    const { email, code } = req.body;
    const rawEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    const rawCode = typeof code === 'string' || typeof code === 'number' ? String(code).trim() : '';

    if (!rawEmail || !rawCode) {
      return res.status(400).json({
        success: false,
        code: 'INVALID_PARAMETERS',
        message: 'Please provide both email address and 6-digit verification code.',
      });
    }

    const user = await User.findOne({ email: rawEmail }).select(
      '+emailVerificationCodeHash +emailVerificationCodeExpiresAt +emailVerificationCodeAttempts'
    );

    if (!user) {
      return res.status(400).json({
        success: false,
        code: 'USER_NOT_FOUND',
        message: 'Invalid verification request or user does not exist.',
      });
    }

    if (user.emailVerified === true) {
      return res.status(200).json({
        success: true,
        alreadyVerified: true,
        message: 'Your email address is already verified. You can log in now.',
      });
    }

    // 1. Check if locked out due to >= 5 failed attempts
    if ((user.emailVerificationCodeAttempts || 0) >= 5) {
      return res.status(400).json({
        success: false,
        code: 'TOO_MANY_ATTEMPTS',
        message: 'Too many incorrect attempts. This code has been invalidated. Please request a new verification code.',
      });
    }

    // 2. Check expiration FIRST (now > expiresAt)
    const now = Date.now();
    if (!user.emailVerificationCodeExpiresAt || now > user.emailVerificationCodeExpiresAt.getTime() || !user.emailVerificationCodeHash) {
      // Clear stored code so it can never be accepted later; do NOT count as a wrong attempt
      user.emailVerificationCodeHash = undefined;
      user.emailVerificationCodeExpiresAt = undefined;
      await user.save();
      return res.status(400).json({
        success: false,
        code: 'CODE_EXPIRED',
        message: 'This code has expired (codes are valid for 1 minute). Please request a new one.',
      });
    }

    const incomingHash = sha256(rawCode);
    if (incomingHash !== user.emailVerificationCodeHash) {
      user.emailVerificationCodeAttempts = (user.emailVerificationCodeAttempts || 0) + 1;
      if (user.emailVerificationCodeAttempts >= 5) {
        user.emailVerificationCodeHash = undefined;
        user.emailVerificationCodeExpiresAt = undefined;
        await user.save();
        return res.status(400).json({
          success: false,
          code: 'TOO_MANY_ATTEMPTS',
          message: 'Too many incorrect attempts. This code has been invalidated. Please request a new verification code.',
        });
      }
      await user.save();
      const remaining = 5 - user.emailVerificationCodeAttempts;
      return res.status(400).json({
        success: false,
        code: 'INVALID_CODE',
        message: `Invalid verification code. You have ${remaining} attempt(s) remaining.`,
      });
    }

    // Success! Clear code fields and mark emailVerified = true
    user.emailVerified = true;
    user.emailVerificationCodeHash = undefined;
    user.emailVerificationCodeExpiresAt = undefined;
    user.emailVerificationCodeAttempts = 0;
    user.emailVerificationTokenHash = undefined;
    user.emailVerificationExpiresAt = undefined;
    await user.save();

    return res.status(200).json({
      success: true,
      message: 'Email verified successfully! You can now log in.',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Verify email address via token or legacy link
// @route   GET or POST /api/auth/verify-email
// @access  Public
export const verifyEmail = async (req, res, next) => {
  try {
    const tokenOrCode = req.query.token || req.body.token || req.body.code || req.query.code;
    const rawEmail = req.query.email || req.body.email;

    if (!tokenOrCode || !rawEmail) {
      return res.status(400).json({
        success: false,
        code: 'INVALID_PARAMETERS',
        message: 'Verification code or token and email are required.',
      });
    }

    const normalizedEmail = String(rawEmail).trim().toLowerCase();
    const user = await User.findOne({ email: normalizedEmail }).select(
      '+emailVerificationTokenHash +emailVerificationCodeHash +emailVerificationExpiresAt +emailVerificationCodeExpiresAt'
    );

    if (!user) {
      return res.status(400).json({
        success: false,
        code: 'USER_NOT_FOUND',
        message: 'Invalid verification link or user does not exist.',
      });
    }

    if (user.emailVerified === true) {
      return res.status(200).json({
        success: true,
        alreadyVerified: true,
        message: 'Your email address is already verified. You can log in now.',
      });
    }

    const incomingHash = sha256(String(tokenOrCode).trim());

    const isTokenMatch = user.emailVerificationTokenHash && user.emailVerificationTokenHash === incomingHash;
    const isCodeMatch = user.emailVerificationCodeHash && user.emailVerificationCodeHash === incomingHash;

    const tokenExpired = user.emailVerificationExpiresAt && user.emailVerificationExpiresAt.getTime() < Date.now();
    const codeExpired = user.emailVerificationCodeExpiresAt && user.emailVerificationCodeExpiresAt.getTime() < Date.now();

    if (!isTokenMatch && !isCodeMatch) {
      return res.status(400).json({
        success: false,
        code: 'TOKEN_EXPIRED',
        message: 'The email verification code or link has expired or is invalid. Please request a new verification code.',
      });
    }

    if ((isTokenMatch && tokenExpired) || (isCodeMatch && codeExpired)) {
      return res.status(400).json({
        success: false,
        code: 'TOKEN_EXPIRED',
        message: 'The email verification code or link has expired or is invalid. Please request a new verification code.',
      });
    }

    // Mark email as verified and clear token/code fields
    user.emailVerified = true;
    user.emailVerificationTokenHash = undefined;
    user.emailVerificationCodeHash = undefined;
    user.emailVerificationExpiresAt = undefined;
    user.emailVerificationCodeExpiresAt = undefined;
    user.emailVerificationCodeAttempts = 0;
    await user.save();

    return res.status(200).json({
      success: true,
      message: 'Email verified successfully! You can now log in to your account.',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Resend email verification code
// @route   POST /api/auth/resend-verification
// @access  Public (Rate-limited)
export const resendVerification = async (req, res, next) => {
  try {
    const rawEmail = req.body.email;
    const normalizedEmail = typeof rawEmail === 'string' ? rawEmail.trim().toLowerCase() : '';

    if (!normalizedEmail) {
      return res.status(400).json({
        success: false,
        code: 'INVALID_PARAMETERS',
        message: 'Please provide an email address.',
      });
    }

    const user = await User.findOne({ email: normalizedEmail }).select(
      '+emailVerificationCodeHash +emailVerificationCodeExpiresAt +emailVerificationCodeAttempts +lastEmailVerificationSentAt'
    );

    if (!user) {
      return res.status(404).json({
        success: false,
        code: 'USER_NOT_FOUND',
        message: 'No account found with this email address.',
      });
    }

    if (user.emailVerified === true) {
      return res.status(400).json({
        success: false,
        code: 'ALREADY_VERIFIED',
        message: 'Your email address is already verified. You can log in directly.',
      });
    }

    // Cooldown check (30 seconds)
    if (user.lastEmailVerificationSentAt) {
      const elapsedSeconds = (Date.now() - user.lastEmailVerificationSentAt.getTime()) / 1000;
      if (elapsedSeconds < COOLDOWN_SECONDS) {
        const secondsLeft = Math.ceil(COOLDOWN_SECONDS - elapsedSeconds);
        return res.status(429).json({
          success: false,
          code: 'COOLDOWN_ACTIVE',
          message: `Please wait ${secondsLeft} second(s) before requesting a new verification code.`,
          retryAfter: secondsLeft,
        });
      }
    }

    // Check if SMTP is configured before attempting delivery
    if (!emailService.isSmtpConfigured()) {
      // In DEV, also log the code to console so developer can test
      if (process.env.NODE_ENV !== 'production') {
        const devCode = String(randomInt(100000, 1000000));
        user.emailVerificationCodeHash = sha256(devCode);
        user.emailVerificationCodeExpiresAt = new Date(Date.now() + 10 * 60 * 1000);
        user.emailVerificationCodeAttempts = 0;
        user.lastEmailVerificationSentAt = new Date();
        await user.save();
        await emailService.sendVerificationCodeEmail(user.email, user.name, devCode);
      }
      return res.status(503).json({
        success: false,
        code: 'SMTP_NOT_CONFIGURED',
        message: 'Email service is not configured on this server. Please contact an administrator.',
      });
    }

    // Generate new 6-digit code and reset attempts (fresh 1 minute validity)
    const verificationCode = String(randomInt(100000, 1000000));
    const verificationToken = randomBytes(32).toString('hex');
    user.emailVerificationCodeHash = sha256(verificationCode);
    user.emailVerificationCodeExpiresAt = new Date(Date.now() + VERIFY_CODE_TTL_MS); // 1 minute
    user.emailVerificationCodeAttempts = 0;
    user.emailVerificationTokenHash = sha256(verificationToken);
    user.emailVerificationExpiresAt = new Date(Date.now() + VERIFY_EMAIL_TTL_MS);
    user.lastEmailVerificationSentAt = new Date();
    await user.save();

    let resendResult;
    try {
      resendResult = await emailService.sendVerificationCodeEmail(user.email, user.name, verificationCode);
    } catch (mailError) {
      console.error(`[Auth] Resend verification code email error for ${user.email}:`, mailError.message);
      resendResult = { success: false, code: 'EMAIL_SEND_FAILED', error: mailError.message };
    }

    if (!resendResult || !resendResult.success) {
      console.error(
        `[Auth] Resend verification email NOT delivered to ${user.email} ` +
        `(${resendResult?.error || 'delivery error'}).`
      );
      return res.status(502).json({
        success: false,
        emailSent: false,
        code: resendResult?.code || 'EMAIL_SEND_FAILED',
        message: resendResult?.code === 'ETHEREAL_SANDBOX'
          ? 'The email service is a test sandbox and emails will not reach real inboxes.'
          : 'could not send, try again later',
      });
    }

    return res.status(200).json({
      success: true,
      emailSent: true,
      expiresAt: user.emailVerificationCodeExpiresAt.toISOString(),
      expiresInSeconds: Math.floor(VERIFY_CODE_TTL_MS / 1000),
      message: 'A new 6-digit verification code has been sent to your email address.',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Authenticate user & get tokens
// @route   POST /api/auth/login
// @access  Public (Rate-limited)
export const loginUser = async (req, res, next) => {
  try {
    const { email, password, rememberMe } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        success: false,
        message: 'Please provide email and password',
      });
    }

    const normalizedEmail = String(email).trim().toLowerCase();
    const user = await User.findOne({ email: normalizedEmail }).select('+password +refreshTokenHash');

    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password',
      });
    }

    // 1. Check account lockout
    if (user.lockUntil && user.lockUntil.getTime() > Date.now()) {
      const remainingMinutes = Math.ceil((user.lockUntil.getTime() - Date.now()) / (60 * 1000));
      return res.status(423).json({
        success: false,
        code: 'ACCOUNT_LOCKED',
        message: `Account is temporarily locked due to too many failed attempts. Please try again in ${remainingMinutes} minute(s).`,
      });
    }

    // 2. Check password match
    const isMatch = await user.matchPassword(password);
    if (!isMatch) {
      user.failedLoginAttempts = (user.failedLoginAttempts || 0) + 1;
      if (user.failedLoginAttempts >= MAX_LOGIN_ATTEMPTS) {
        user.lockUntil = new Date(Date.now() + LOCKOUT_TIME_MS);
        await user.save();
        return res.status(423).json({
          success: false,
          code: 'ACCOUNT_LOCKED',
          message: 'Account locked for 15 minutes due to 5 consecutive failed login attempts.',
        });
      }
      await user.save();
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password',
      });
    }

    // 3. Password matched - reset lockout counters
    user.failedLoginAttempts = 0;
    user.lockUntil = undefined;

    // 4. Email verification check
    // STRICT RULE: Existing users with emailVerified=undefined/null MUST be permitted.
    // ONLY block if emailVerified === false.
    if (user.emailVerified === false) {
      await user.save();
      return res.status(403).json({
        success: false,
        code: 'EMAIL_NOT_VERIFIED',
        message: 'Your email address is not verified. Please check your inbox for the 6-digit verification code.',
        email: user.email,
      });
    }

    // 5. Issue short-lived access token + rotating refresh token
    const accessToken = generateAccessToken(user._id);
    const rawRefreshToken = generateRefreshTokenString();
    user.refreshTokenHash = sha256(rawRefreshToken);
    user.rememberMe = !!rememberMe;
    await user.save();

    setRefreshTokenCookie(res, rawRefreshToken, !!rememberMe);

    return res.json({
      success: true,
      message: 'Login successful',
      token: accessToken,       // Backward compatibility
      accessToken: accessToken, // Standardized
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        degree: user.degree,
        university: user.university,
        targetRole: user.targetRole,
        emailVerified: user.emailVerified !== false,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Refresh session with rotated refresh token
// @route   POST /api/auth/refresh
// @access  Public (Uses httpOnly cookie)
export const refreshToken = async (req, res, next) => {
  try {
    const rawRefreshToken = req.cookies?.refreshToken || req.body?.refreshToken;

    if (!rawRefreshToken) {
      return res.status(401).json({
        success: false,
        code: 'NO_REFRESH_TOKEN',
        message: 'No refresh token provided',
      });
    }

    const incomingHash = sha256(rawRefreshToken);
    const user = await User.findOne({ refreshTokenHash: incomingHash }).select('+refreshTokenHash');

    if (!user) {
      // Refresh token reuse or revoked! Invalidate session cookie immediately.
      clearRefreshTokenCookie(res);
      return res.status(401).json({
        success: false,
        code: 'INVALID_REFRESH_TOKEN',
        message: 'Session has expired or token was revoked. Please log in again.',
      });
    }

    // Rotate refresh token
    const newRawRefreshToken = generateRefreshTokenString();
    user.refreshTokenHash = sha256(newRawRefreshToken);
    await user.save();

    setRefreshTokenCookie(res, newRawRefreshToken, !!user.rememberMe);
    const newAccessToken = generateAccessToken(user._id);

    return res.json({
      success: true,
      token: newAccessToken,
      accessToken: newAccessToken,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        degree: user.degree,
        university: user.university,
        targetRole: user.targetRole,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Log out user & clear refresh session
// @route   POST /api/auth/logout
// @access  Public
export const logoutUser = async (req, res, next) => {
  try {
    const rawRefreshToken = req.cookies?.refreshToken;
    if (rawRefreshToken) {
      const incomingHash = sha256(rawRefreshToken);
      await User.updateOne({ refreshTokenHash: incomingHash }, { $unset: { refreshTokenHash: 1, rememberMe: 1 } });
    }

    clearRefreshTokenCookie(res);

    return res.json({
      success: true,
      message: 'Logged out successfully',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Permanently delete own user account and cascaded records from server
// @route   DELETE /api/auth/delete-account
// @access  Private (Authenticated)
export const deleteAccount = async (req, res, next) => {
  try {
    const userId = req.user?._id;
    if (!userId) {
      return res.status(401).json({
        success: false,
        code: 'UNAUTHORIZED',
        message: 'You must be logged in to delete your account.',
      });
    }

    // Cascade delete user's owned records from MongoDB
    const [delResults, delAnswers, delInterviews] = await Promise.all([
      Result.deleteMany({ userId }),
      Answer.deleteMany({ userId }),
      Interview.deleteMany({ userId }),
    ]);

    // Permanently remove user from MongoDB
    const deletedUser = await User.findByIdAndDelete(userId);

    if (!deletedUser) {
      return res.status(404).json({
        success: false,
        code: 'USER_NOT_FOUND',
        message: 'Account not found or already deleted.',
      });
    }

    // Clear refresh session cookie
    clearRefreshTokenCookie(res);

    console.log(
      `[Auth] User ${deletedUser.email} (ID: ${userId}) permanently deleted their account. ` +
      `Purged ${delInterviews.deletedCount} interviews, ${delAnswers.deletedCount} answers, ${delResults.deletedCount} results.`
    );

    return res.status(200).json({
      success: true,
      message: 'Your account and all associated data have been permanently deleted from the server.',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Request a 6-digit password reset verification code
// @route   POST /api/auth/forgot-password
// @access  Public (Rate-limited)
export const forgotPassword = async (req, res, next) => {
  try {
    const rawEmail = typeof req.body.email === 'string' ? req.body.email.trim().toLowerCase() : '';

    const genericResponse = {
      success: true,
      message: 'If an account with that email exists, a 6-digit verification code has been sent.',
    };

    if (!rawEmail) {
      return res.json(genericResponse);
    }

    const user = await User.findOne({ email: rawEmail }).select(
      '+passwordResetCodeHash +passwordResetCodeExpiresAt +passwordResetCodeAttempts +lastPasswordResetCodeSentAt'
    );

    if (user) {
      // Cooldown check
      if (user.lastPasswordResetCodeSentAt) {
        const elapsedSeconds = (Date.now() - user.lastPasswordResetCodeSentAt.getTime()) / 1000;
        if (elapsedSeconds < COOLDOWN_SECONDS) {
          return res.json(genericResponse);
        }
      }

      // Generate 6-digit numeric code
      const code = String(randomInt(100000, 1000000));
      user.passwordResetCodeHash = sha256(code);
      user.passwordResetCodeExpiresAt = new Date(Date.now() + RESET_CODE_TTL_MS);
      user.passwordResetCodeAttempts = 0;
      user.lastPasswordResetCodeSentAt = new Date();
      await user.save();

      // Dispatch email
      await emailService.sendPasswordResetCodeEmail(user.email, user.name, code);
    }

    return res.json(genericResponse);
  } catch (error) {
    next(error);
  }
};

// @desc    Verify 6-digit code and get a short-lived reset token
// @route   POST /api/auth/verify-reset-code
// @access  Public (Rate-limited)
export const verifyResetCode = async (req, res, next) => {
  try {
    const { email, code } = req.body;

    const normalizedEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    const cleanCode = typeof code === 'string' ? code.trim() : '';

    if (!normalizedEmail || !cleanCode) {
      return res.status(400).json({
        success: false,
        code: 'MISSING_FIELDS',
        message: 'Please provide both email address and 6-digit verification code.',
      });
    }

    const user = await User.findOne({ email: normalizedEmail }).select(
      '+passwordResetCodeHash +passwordResetCodeExpiresAt +passwordResetCodeAttempts'
    );

    if (!user || !user.passwordResetCodeHash) {
      return res.status(400).json({
        success: false,
        code: 'INVALID_CODE',
        message: 'Invalid or expired verification code. Please request a new one.',
      });
    }

    // Check code expiry
    if (!user.passwordResetCodeExpiresAt || user.passwordResetCodeExpiresAt.getTime() < Date.now()) {
      return res.status(400).json({
        success: false,
        code: 'CODE_EXPIRED',
        message: 'Verification code has expired. Please request a new code.',
      });
    }

    // Check attempt limits
    if (user.passwordResetCodeAttempts >= MAX_RESET_CODE_ATTEMPTS) {
      user.passwordResetCodeHash = undefined;
      user.passwordResetCodeExpiresAt = undefined;
      await user.save();
      return res.status(400).json({
        success: false,
        code: 'TOO_MANY_ATTEMPTS',
        message: 'Too many incorrect attempts. This code has been invalidated. Please request a new code.',
      });
    }

    const incomingHash = sha256(cleanCode);
    if (incomingHash !== user.passwordResetCodeHash) {
      user.passwordResetCodeAttempts = (user.passwordResetCodeAttempts || 0) + 1;
      await user.save();
      const remaining = MAX_RESET_CODE_ATTEMPTS - user.passwordResetCodeAttempts;
      return res.status(400).json({
        success: false,
        code: 'INVALID_CODE',
        message: `Incorrect verification code. ${remaining} attempt(s) remaining.`,
      });
    }

    // Code matches! Clear the code and generate a single-use reset token valid for 10 minutes
    const resetToken = randomBytes(32).toString('hex');
    user.passwordResetTokenHash = sha256(resetToken);
    user.passwordResetExpiresAt = new Date(Date.now() + RESET_CODE_TTL_MS);
    user.passwordResetCodeHash = undefined;
    user.passwordResetCodeExpiresAt = undefined;
    user.passwordResetCodeAttempts = 0;
    await user.save();

    return res.json({
      success: true,
      message: 'Code verified successfully.',
      resetToken,
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Reset password using reset token
// @route   POST /api/auth/reset-password
// @access  Public
export const resetPassword = async (req, res, next) => {
  try {
    const rawToken = req.body.resetToken || req.body.token;
    const newPassword = req.body.newPassword || req.body.password;
    const confirmPassword = req.body.confirmPassword;

    if (!rawToken || !newPassword || !confirmPassword) {
      return res.status(400).json({
        success: false,
        message: 'Please provide the reset token, new password, and password confirmation.',
      });
    }

    if (!isValidPassword(newPassword)) {
      return res.status(400).json({
        success: false,
        message: 'Password must be at least 8 characters long and contain at least one letter and one number.',
      });
    }

    if (newPassword !== confirmPassword) {
      return res.status(400).json({
        success: false,
        message: 'Passwords do not match.',
      });
    }

    const tokenHash = sha256(rawToken.trim());
    const user = await User.findOne({
      passwordResetTokenHash: tokenHash,
      passwordResetExpiresAt: { $gt: new Date() },
    }).select('+passwordResetTokenHash +passwordResetExpiresAt');

    if (!user) {
      return res.status(400).json({
        success: false,
        code: 'INVALID_TOKEN',
        message: 'Password reset link or token is invalid or has expired. Please request a new one.',
      });
    }

    // Set new password (pre-save hook will hash with bcrypt)
    user.password = newPassword;
    user.passwordResetTokenHash = undefined;
    user.passwordResetExpiresAt = undefined;
    user.passwordResetCodeHash = undefined;
    user.passwordResetCodeExpiresAt = undefined;
    user.passwordResetCodeAttempts = 0;
    // CRITICAL: Invalidate any active refresh sessions so old devices are logged out
    user.refreshTokenHash = undefined;
    user.failedLoginAttempts = 0;
    user.lockUntil = undefined;
    await user.save();

    // Send confirmation notification email
    await emailService.sendPasswordChangedNotification(user.email, user.name);

    return res.json({
      success: true,
      message: 'Password has been reset successfully. Please log in with your new password.',
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get current authenticated user profile
// @route   GET /api/auth/me
// @access  Private
export const getMe = async (req, res, next) => {
  try {
    const user = await User.findById(req.user._id).select('-password');
    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'User account not found',
      });
    }

    return res.json({
      success: true,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        degree: user.degree,
        university: user.university,
        targetRole: user.targetRole,
        emailVerified: user.emailVerified !== false,
        createdAt: user.createdAt,
      },
    });
  } catch (error) {
    next(error);
  }
};
