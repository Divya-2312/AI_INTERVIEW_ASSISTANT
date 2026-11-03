import nodemailer from 'nodemailer';
import dotenv from 'dotenv';

dotenv.config();

let customTransport = null;

// Honesty Guard: Startup warning if SMTP_HOST is Ethereal sandbox
if (typeof process !== 'undefined' && (process.env?.SMTP_HOST || '').toLowerCase().includes('ethereal')) {
  console.warn('\n====================================================================');
  console.warn('⚠️  [EmailService WARNING] SMTP is an Ethereal sandbox - emails will NOT reach real inboxes');
  console.warn('====================================================================\n');
}

/**
 * Injects a custom/mocked nodemailer transporter (used by automated tests).
 */
export const setCustomTransport = (transport) => {
  customTransport = transport;
};

/**
 * Checks if production/custom SMTP credentials are fully configured.
 */
export const isSmtpConfigured = () => {
  if (customTransport) return true;

  const host = process.env.SMTP_HOST;
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;

  if (!host || !user || !pass) return false;
  if (user.includes('your_email') || pass.includes('your_app_specific_password')) return false;

  return true;
};

/**
 * Creates and returns a nodemailer transport instance.
 */
const getTransport = () => {
  if (customTransport) return customTransport;

  const host = process.env.SMTP_HOST || 'smtp.gmail.com';
  const port = parseInt(process.env.SMTP_PORT || '587', 10);
  const secure = process.env.SMTP_SECURE === 'true' || port === 465;
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;

  return nodemailer.createTransport({
    host,
    port,
    secure,
    auth: {
      user,
      pass,
    },
  });
};

/**
 * Internal helper to send an email via configured transport.
 * Fails explicitly with clear logging if SMTP is not configured.
 */
const sendOrLogEmail = async ({ to, subject, text, html }) => {
  const mailFrom = process.env.MAIL_FROM || '"AI Interview Assistant" <no-reply@ai-interview-assistant.com>';

  // Honesty Guard: Never send or report sent for an Ethereal sandbox host
  const host = (process.env.SMTP_HOST || '').toLowerCase();
  if (host.includes('ethereal')) {
    console.warn('[EmailService] SMTP is an Ethereal sandbox - emails will NOT reach real inboxes');
    return {
      success: false,
      emailSent: false,
      code: 'ETHEREAL_SANDBOX',
      error: 'SMTP is an Ethereal sandbox - emails will NOT reach real inboxes. The email service is a test sandbox.',
      message: 'The email service is a test sandbox and emails will not reach real inboxes.',
    };
  }

  if (!isSmtpConfigured()) {
    console.error(
      `[EmailService] Cannot send email to ${to}: SMTP is not configured on this server. ` +
      `Configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASS in backend/.env to send real emails.`
    );
    return {
      success: false,
      code: 'SMTP_NOT_CONFIGURED',
      error: 'SMTP server is not configured on this system. Verification email could not be dispatched.',
    };
  }

  try {
    const transporter = getTransport();
    const info = await transporter.sendMail({
      from: mailFrom,
      to,
      subject,
      text,
      html,
    });
    console.log(`[EmailService] Email dispatched successfully to ${to} (MessageID: ${info.messageId || 'mock-id'})`);
    const previewUrl = nodemailer.getTestMessageUrl(info);
    if (previewUrl) {
      console.log(`[EmailService] Preview URL (Ethereal): ${previewUrl}`);
    }
    return { success: true, messageId: info.messageId || 'mock-id', previewUrl };
  } catch (error) {
    console.error(`[EmailService] Failed to send email to ${to}:`, error.message);
    return { success: false, code: 'EMAIL_SEND_FAILED', error: error.message || 'Email delivery failed' };
  }
};

/**
 * Mask an email address for safe logging (e.g., di***n@gmail.com)
 */
const maskEmail = (email) => {
  if (!email || typeof email !== 'string') return '';
  const [local, domain] = email.split('@');
  if (!domain) return email;
  if (local.length <= 2) return `${local[0]}***@${domain}`;
  return `${local.slice(0, 2)}***${local.slice(-1)}@${domain}`;
};

/**
 * Send 6-digit registration email verification code.
 */
export const sendVerificationCodeEmail = async (email, name, code) => {
  // DEV only: If NODE_ENV is not production and SMTP is not configured,
  // print the code to the backend console for local developer testing.
  if (process.env.NODE_ENV !== 'production' && !isSmtpConfigured()) {
    console.log(`[DEV] verification code for ${maskEmail(email)}: ${code}`);
  }

  const subject = 'Your AI Interview Assistant Verification Code';

  const text = `Hello ${name || 'Student'},\n\n` +
    `Welcome to AI Interview Assistant! Please verify your email address to activate your account.\n\n` +
    `Your 6-digit verification code is:\n\n` +
    `[ ${code} ]\n\n` +
    `This code is valid for 1 minute.\n` +
    `Enter this code on the verification screen to activate your account.\n\n` +
    `If you did not create an account on AI Interview Assistant, please ignore this email.\n\n` +
    `Best regards,\nThe AI Interview Assistant Team`;

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
          .container { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
          .header { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%); padding: 32px 24px; text-align: center; }
          .logo { font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
          .logo span { color: #38bdf8; }
          .body { padding: 32px 24px; text-align: center; }
          h2 { margin-top: 0; color: #0f172a; font-size: 20px; }
          p { line-height: 1.6; color: #475569; font-size: 15px; margin: 12px 0; text-align: left; }
          .code-box { background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 24px 20px; margin: 24px auto; display: inline-block; }
          .code-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 8px; }
          .code { font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: 800; letter-spacing: 12px; color: #4f46e5; }
          .expiry { font-size: 13px; color: #ef4444; font-weight: 600; margin-top: 8px; }
          .note { font-size: 13px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 28px; text-align: left; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div class="logo">AI Interview<span>Assistant</span></div>
          </div>
          <div class="body">
            <h2>Welcome to AI Interview Assistant, ${name || 'Candidate'}!</h2>
            <p>Thank you for registering. Enter the 6-digit verification code below to verify your email address and activate your account:</p>
            <div class="code-box">
              <div class="code-label">Verification Code</div>
              <div class="code">${code}</div>
              <div class="expiry">Valid for 1 minute</div>
            </div>
            <p class="note">If you did not create an AI Interview Assistant account, you can safely ignore this email.</p>
          </div>
        </div>
      </body>
    </html>
  `;

  return await sendOrLogEmail({
    to: email,
    subject,
    text,
    html,
  });
};

/**
 * Send email verification link and 6-digit verification code after registration (legacy link support).
 */
export const sendVerificationEmail = async (email, name, verificationToken, verificationCode = null) => {
  const clientUrl = process.env.CLIENT_URL || 'http://localhost:3000';
  const verificationLink = `${clientUrl}/verify-email?token=${encodeURIComponent(verificationToken)}&email=${encodeURIComponent(email)}`;

  const subject = 'Verify your AI Interview Assistant Email Address';

  const text = `Hello ${name || 'Student'},\n\n` +
    `Welcome to AI Interview Assistant! Please verify your email address to activate your account.\n\n` +
    (verificationCode ? `Your 6-digit verification code is:\n\n[ ${verificationCode} ]\n\n` : '') +
    `Alternatively, you can click the link below to verify:\n\n` +
    `${verificationLink}\n\n` +
    `This verification code and link will expire in 24 hours.\n\n` +
    `If you did not create an account on AI Interview Assistant, please ignore this message.\n\n` +
    `Best regards,\nThe AI Interview Assistant Team`;

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
          .container { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
          .header { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%); padding: 32px 24px; text-align: center; }
          .logo { font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
          .logo span { color: #38bdf8; }
          .body { padding: 32px 24px; }
          h2 { margin-top: 0; color: #0f172a; font-size: 20px; }
          p { line-height: 1.6; color: #475569; font-size: 15px; margin: 12px 0; }
          .button-wrapper { text-align: center; margin: 24px 0 16px; }
          .btn { background-color: #4f46e5; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 600; text-decoration: none; display: inline-block; font-size: 16px; }
          .btn:hover { background-color: #4338ca; }
          .code-box { background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 20px; margin: 20px auto; text-align: center; max-width: 320px; }
          .code-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 6px; }
          .code { font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 800; letter-spacing: 10px; color: #4f46e5; }
          .code-sub { font-size: 12px; color: #64748b; margin-top: 6px; }
          .note { font-size: 13px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 28px; }
          .fallback-url { word-break: break-all; font-family: monospace; font-size: 12px; color: #64748b; background: #f8fafc; padding: 10px; border-radius: 6px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div class="logo">AI Interview<span>Assistant</span></div>
          </div>
          <div class="body">
            <h2>Welcome to AI Interview Assistant, ${name || 'Candidate'}!</h2>
            <p>Thank you for registering. Please confirm your email address to unlock interview practice sessions, AI evaluations, and performance analytics.</p>
            <div class="button-wrapper">
              <a href="${verificationLink}" class="btn" target="_blank">Verify Email Address</a>
            </div>
            <p style="font-size: 13px; color: #64748b; text-align: center;">This link will expire in <strong>24 hours</strong>.</p>
            <p class="note">If the button above does not work, copy and paste this link into your browser:</p>
            <div class="fallback-url">${verificationLink}</div>
            <p class="note">If you didn't create an AI Interview Assistant account, you can safely ignore this email.</p>
          </div>
        </div>
      </body>
    </html>
  `;

  return await sendOrLogEmail({
    to: email,
    subject,
    text,
    html,
  });
};

/**
 * Send 6-digit password reset verification code.
 */
export const sendPasswordResetCodeEmail = async (email, name, code) => {
  const subject = 'Your AI Interview Assistant Password Reset Code';

  const text = `Hello ${name || 'Student'},\n\n` +
    `We received a request to reset your AI Interview Assistant account password.\n\n` +
    `Your 6-digit verification code is:\n\n` +
    `[ ${code} ]\n\n` +
    `This code will expire in 10 minutes.\n\n` +
    `If you did not request a password reset, please ignore this email or review your account security.\n\n` +
    `Best regards,\nThe AI Interview Assistant Team`;

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
          .container { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
          .header { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%); padding: 32px 24px; text-align: center; }
          .logo { font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
          .logo span { color: #38bdf8; }
          .body { padding: 32px 24px; text-align: center; }
          h2 { margin-top: 0; color: #0f172a; font-size: 20px; }
          p { line-height: 1.6; color: #475569; font-size: 15px; margin: 12px 0; text-align: left; }
          .code-box { background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 20px; margin: 24px auto; display: inline-block; }
          .code { font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 800; letter-spacing: 10px; color: #4f46e5; }
          .expiry { font-size: 13px; color: #ef4444; font-weight: 600; margin-top: 8px; }
          .note { font-size: 13px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 28px; text-align: left; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div class="logo">AI Interview<span>Assistant</span></div>
          </div>
          <div class="body">
            <h2>Password Reset Verification Code</h2>
            <p>Hello ${name || 'Candidate'},</p>
            <p>You requested a password reset for your AI Interview Assistant account. Enter the 6-digit code below to set a new password:</p>
            <div class="code-box">
              <div class="code">${code}</div>
              <div class="expiry">Expires in 10 minutes</div>
            </div>
            <p class="note">If you did not request this password reset, please ignore this email. Your password will remain unchanged.</p>
          </div>
        </div>
      </body>
    </html>
  `;

  return await sendOrLogEmail({
    to: email,
    subject,
    text,
    html,
    devBannerTitle: 'Password Reset 6-Digit Code',
    devDetails: `Verification Code: [ ${code} ] (Expires in 10 minutes)`,
  });
};

/**
 * Send notification when password has been successfully reset.
 */
export const sendPasswordChangedNotification = async (email, name) => {
  const subject = 'Your AI Interview Assistant Password Was Changed';

  const text = `Hello ${name || 'Student'},\n\n` +
    `This is a security confirmation that your password for AI Interview Assistant was changed recently.\n\n` +
    `If you made this change, no further action is required.\n\n` +
    `If you did NOT change your password, please contact support immediately or reset your password.\n\n` +
    `Best regards,\nThe AI Interview Assistant Team`;

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
          .container { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
          .header { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%); padding: 32px 24px; text-align: center; }
          .logo { font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
          .logo span { color: #38bdf8; }
          .body { padding: 32px 24px; }
          h2 { margin-top: 0; color: #0f172a; font-size: 20px; }
          p { line-height: 1.6; color: #475569; font-size: 15px; margin: 12px 0; }
          .alert-box { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 14px 16px; border-radius: 6px; margin: 20px 0; font-size: 14px; color: #15803d; }
          .note { font-size: 13px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 28px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div class="logo">AI Interview<span>Assistant</span></div>
          </div>
          <div class="body">
            <h2>Security Alert: Password Updated</h2>
            <div class="alert-box">Your AI Interview Assistant account password was successfully updated.</div>
            <p>Hello ${name || 'Candidate'},</p>
            <p>If you authorized this change, you can safely disregard this confirmation.</p>
            <p class="note">If you did not perform this action, please reset your password immediately or contact our support team to secure your account.</p>
          </div>
        </div>
      </body>
    </html>
  `;

  return await sendOrLogEmail({
    to: email,
    subject,
    text,
    html,
    devBannerTitle: 'Password Changed Notification',
    devDetails: `Security notification dispatched for ${email}`,
  });
};

/**
 * Diagnostic test email sender for `npm run test-email`.
 */
export const sendTestEmail = async (toEmail) => {
  const subject = 'AI Interview Assistant SMTP Test Email';
  const text = `This is a verification test email from AI Interview Assistant.\nIf you received this, your SMTP configuration is operating properly!`;
  const html = `<h3>AI Interview Assistant SMTP Test</h3><p>Your SMTP credentials are configured correctly and active!</p>`;

  return await sendOrLogEmail({
    to: toEmail,
    subject,
    text,
    html,
    devBannerTitle: 'SMTP Configuration Test Email',
    devDetails: `Test email target: ${toEmail}`,
  });
};

export const emailService = {
  setCustomTransport,
  isSmtpConfigured,
  sendVerificationCodeEmail,
  sendVerificationEmail,
  sendPasswordResetCodeEmail,
  sendPasswordChangedNotification,
  sendTestEmail,
};

export default emailService;
