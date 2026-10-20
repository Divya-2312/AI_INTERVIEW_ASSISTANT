import dotenv from 'dotenv';
import { sendTestEmail, isSmtpConfigured } from '../services/emailService.js';

dotenv.config();

const targetEmail = process.argv[2] || process.env.SMTP_USER || 'student.test@example.com';

console.log('--- AI Interview Assistant SMTP Test Utility ---');
console.log(`Checking SMTP Configuration: ${isSmtpConfigured() ? 'CONFIGURED' : 'NOT CONFIGURED (DEV FALLBACK)'}`);
console.log(`Target Recipient: ${targetEmail}`);

async function run() {
  try {
    const result = await sendTestEmail(targetEmail);
    if (result.success) {
      console.log('\n[SUCCESS] Test email dispatched successfully.');
      if (result.devMode) {
        console.log('[NOTE] App is running in DEV MODE. To send live emails, set valid SMTP_HOST, SMTP_USER, and SMTP_PASS in your .env file.');
      } else {
        console.log(`[NOTE] Message ID: ${result.messageId}`);
      }
    } else {
      console.error('\n[FAILED] Failed to dispatch test email:', result.error);
    }
  } catch (error) {
    console.error('\n[ERROR] Unexpected error running email test:', error.message);
  }
}

run();
