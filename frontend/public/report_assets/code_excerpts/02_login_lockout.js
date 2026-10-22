// backend/controllers/authController.js:145-177
export const loginUser = async (req, res, next) => {
  try {
    const { email, password, rememberMe } = req.body;
    const normalizedEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';

    const user = await User.findOne({ email: normalizedEmail }).select('+password');
    if (!user) {
      return res.status(401).json({ success: false, code: 'INVALID_CREDENTIALS', message: 'Invalid email or password.' });
    }

    // Check account lockout
    if (user.lockUntil && user.lockUntil > Date.now()) {
      const minutesRemaining = Math.ceil((user.lockUntil - Date.now()) / (60 * 1000));
      return res.status(423).json({
        success: false,
        code: 'ACCOUNT_LOCKED',
        message: `Account is locked due to 5 consecutive failed login attempts. Try again in ${minutesRemaining} minute(s).`,
      });
    }

    const isMatch = await user.matchPassword(password);
    if (!isMatch) {
      user.failedLoginAttempts = (user.failedLoginAttempts || 0) + 1;
      if (user.failedLoginAttempts >= MAX_LOGIN_ATTEMPTS) {
        user.lockUntil = new Date(Date.now() + LOCKOUT_TIME_MS);
      }
      await user.save();
      return res.status(401).json({ success: false, code: 'INVALID_CREDENTIALS', message: 'Invalid email or password.' });
    }

    // Reset attempts on successful login
    user.failedLoginAttempts = 0;
    user.lockUntil = undefined;
    await user.save();
    // (Proceeds to issue accessToken and set refresh cookie)
