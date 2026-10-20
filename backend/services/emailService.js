import nodemailer from 'nodemailer';

/**
 * Checks if production/custom SMTP credentials are fully configured.
 */
export const isSmtpConfigured = () => {
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
 * Internal helper to send or log an email.
 */
const sendOrLogEmail = async ({ to, subject, text, html, devBannerTitle, devDetails }) => {
  const mailFrom = process.env.MAIL_FROM || '"AI Interview Assistant" <no-reply@ai-interview-assistant.com>';

  if (!isSmtpConfigured()) {
    // DEV MODE: Print high-visibility banner to console so tests and local dev work seamlessly
    console.log('\n================================================================================');
    console.log(`[DEV MODE - email not sent] ${devBannerTitle || 'AI Interview Assistant Email Dispatch'}`);
    console.log(`To:      ${to}`);
    console.log(`Subject: ${subject}`);
    if (devDetails) {
      console.log(`Details: ${devDetails}`);
    }
    console.log('Plain text snippet:');
    console.log(text.trim());
    console.log('================================================================================\n');

    return { success: true, devMode: true };
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
    console.log(`[EmailService] Email dispatched successfully to ${to} (MessageID: ${info.messageId})`);
    return { success: true, messageId: info.messageId };
  } catch (error) {
    console.error(`[EmailService] Failed to send email to ${to}:`, error.message);
    // Never leak stack trace or internal SMTP secrets to caller
    return { success: false, error: 'Email delivery failed' };
  }
};

/**
 * Send email verification link after registration.
 */
export const sendVerificationEmail = async (email, name, verificationToken) => {
  const clientUrl = process.env.CLIENT_URL || 'http://localhost:3000';
  const verificationLink = `${clientUrl}/verify-email?token=${encodeURIComponent(verificationToken)}&email=${encodeURIComponent(email)}`;

  const subject = 'Verify your AI Interview Assistant Email Address';

  const text = `Hello ${name || 'Student'},\n\n` +
    `Welcome to AI Interview Assistant! Please verify your email address to activate your account by clicking the link below:\n\n` +
    `${verificationLink}\n\n` +
    `This verification link will expire in 24 hours.\n\n` +
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
          .button-wrapper { text-align: center; margin: 30px 0; }
          .btn { background-color: #4f46e5; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 600; text-decoration: none; display: inline-block; font-size: 16px; }
          .btn:hover { background-color: #4338ca; }
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
            <p style="font-size: 13px; color: #64748b;">This verification link will expire in <strong>24 hours</strong>.</p>
            <p class="note">If the button doesn't work, copy and paste this link into your browser:</p>
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
    devBannerTitle: 'Email Verification Link',
    devDetails: `Verification Link -> ${verificationLink}`,
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
  isSmtpConfigured,
  sendVerificationEmail,
  sendPasswordResetCodeEmail,
  sendPasswordChangedNotification,
  sendTestEmail,
};

export default emailService;
