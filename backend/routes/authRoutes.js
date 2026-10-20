import express from 'express';
import rateLimit from 'express-rate-limit';
import {
  registerUser,
  verifyEmail,
  resendVerification,
  loginUser,
  refreshToken,
  logoutUser,
  forgotPassword,
  verifyResetCode,
  resetPassword,
  getMe,
} from '../controllers/authController.js';
import { protect } from '../middleware/authMiddleware.js';

const router = express.Router();

/**
 * Strict rate limiting for sensitive authentication endpoints:
 * 15 requests per 15 minutes per IP window.
 */
const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 15,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    code: 'RATE_LIMIT_EXCEEDED',
    message: 'Too many requests from this IP. Please wait 15 minutes before trying again.',
  },
});

// Registration & Email Verification
router.post('/register', authRateLimiter, registerUser);
router.get('/verify-email', verifyEmail);
router.post('/verify-email', verifyEmail);
router.post('/resend-verification', authRateLimiter, resendVerification);

// Login, Refresh, Logout
router.post('/login', authRateLimiter, loginUser);
router.post('/refresh', refreshToken);
router.post('/logout', logoutUser);

// Password Reset Flow (6-digit code + reset token)
router.post('/forgot-password', authRateLimiter, forgotPassword);
router.post('/verify-reset-code', authRateLimiter, verifyResetCode);
router.post('/reset-password', resetPassword);

// Current User Profile
router.get('/me', protect, getMe);

export default router;
