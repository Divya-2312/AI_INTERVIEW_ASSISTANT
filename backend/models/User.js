import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'Please provide a name'],
      trim: true,
    },
    email: {
      type: String,
      required: [true, 'Please provide an email address'],
      unique: true,
      lowercase: true,
      trim: true,
      match: [
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        'Please provide a valid email address',
      ],
    },
    password: {
      type: String,
      required: [true, 'Please provide a password'],
      minlength: [6, 'Password must be at least 6 characters'],
    },
    passwordResetTokenHash: {
      type: String,
      default: undefined,
      select: false,
    },
    passwordResetExpiresAt: {
      type: Date,
      default: undefined,
      select: false,
    },
    // Email verification fields (undefined for existing users, false for new registrations)
    emailVerified: {
      type: Boolean,
      default: undefined,
    },
    emailVerificationTokenHash: {
      type: String,
      default: undefined,
      select: false,
    },
    emailVerificationExpiresAt: {
      type: Date,
      default: undefined,
      select: false,
    },
    lastEmailVerificationSentAt: {
      type: Date,
      default: undefined,
      select: false,
    },
    // JWT Refresh token rotation
    refreshTokenHash: {
      type: String,
      default: undefined,
      select: false,
    },
    // Account lockout protection
    failedLoginAttempts: {
      type: Number,
      default: 0,
    },
    lockUntil: {
      type: Date,
      default: undefined,
    },
    // 6-digit forgot password verification code
    passwordResetCodeHash: {
      type: String,
      default: undefined,
      select: false,
    },
    passwordResetCodeExpiresAt: {
      type: Date,
      default: undefined,
      select: false,
    },
    passwordResetCodeAttempts: {
      type: Number,
      default: 0,
      select: false,
    },
    lastPasswordResetCodeSentAt: {
      type: Date,
      default: undefined,
      select: false,
    },
    degree: {
      type: String,
      default: 'B.Tech Computer Science',
    },
    university: {
      type: String,
      default: 'Anna University / Tech Campus',
    },
    targetRole: {
      type: String,
      default: 'Software Development Engineer (SDE)',
    },
  },
  {
    timestamps: true,
  }
);

// Hash password before saving
userSchema.pre('save', async function (next) {
  if (!this.isModified('password')) {
    return next();
  }
  const salt = await bcrypt.genSalt(10);
  this.password = await bcrypt.hash(this.password, salt);
  next();
});

// Match user password
userSchema.methods.matchPassword = async function (enteredPassword) {
  return await bcrypt.compare(enteredPassword, this.password);
};

export const User = mongoose.model('User', userSchema);
