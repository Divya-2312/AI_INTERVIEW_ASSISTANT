import mongoose from 'mongoose';
import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';
import {
  registerUser,
  verifyEmail,
  verifyEmailCode,
  resendVerification,
  loginUser,
  refreshToken,
  logoutUser,
  deleteAccount,
  forgotPassword,
  verifyResetCode,
  resetPassword,
} from '../controllers/authController.js';
import { deleteInterview } from '../controllers/interviewController.js';
import { setCustomTransport } from '../services/emailService.js';
import { runFailedEvalTests } from './failed_eval_handling.test.js';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

// Mock Express req, res, next helpers
const createMockReqRes = (body = {}, query = {}, cookies = {}, headers = {}) => {
  const req = {
    body,
    query,
    cookies,
    headers,
  };

  const res = {
    statusCode: 200,
    headersSent: false,
    cookiesSet: {},
    cookiesCleared: [],
    jsonData: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(data) {
      this.jsonData = data;
      return this;
    },
    cookie(name, val, options) {
      this.cookiesSet[name] = { val, options };
      return this;
    },
    clearCookie(name, options) {
      this.cookiesCleared.push({ name, options });
      return this;
    },
  };

  const next = (err) => {
    if (err) throw err;
  };

  return { req, res, next };
};

let passedTests = 0;
let totalTests = 0;

const assert = (condition, description) => {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  [PASS] ${description}`);
  } else {
    console.error(`  [FAIL] ${description}`);
    throw new Error(`Assertion failed: ${description}`);
  }
};

async function runTestSuite() {
  console.log('\n=======================================================');
  console.log('--- AI Interview Assistant Backend Authentication Test Suite ---');
  console.log('=======================================================\n');

  try {
    await mongoose.connect(MONGODB_URI);
    console.log('[DB] Connected to MongoDB for test suite.\n');

    // Clean up test users from previous runs
    await User.deleteMany({ email: /.*@testrunner\.com$/ });

    const testEmail = `student_${Date.now()}@testrunner.com`;
    const testPassword = 'Password123';

    // -----------------------------------------------------------------
    // TEST 1: Register User creates account with emailVerified = false
    // -----------------------------------------------------------------
    console.log('1. Testing User Registration...');
    {
      const { req, res, next } = createMockReqRes({
        name: 'Test Student',
        email: testEmail,
        password: testPassword,
        degree: 'B.Tech IT',
        university: 'Test University',
        targetRole: 'Full Stack Engineer',
      });

      await registerUser(req, res, next);
      assert(res.statusCode === 201, 'Registration returns HTTP 201');
      assert(res.jsonData.requiresVerification === true, 'Response requires verification');
      assert(res.jsonData.user.emailVerified === false, 'User object has emailVerified = false');

      const savedUser = await User.findOne({ email: testEmail }).select('+emailVerificationTokenHash +emailVerificationExpiresAt');
      assert(savedUser !== null, 'User created in database');
      assert(savedUser.emailVerified === false, 'Database record has emailVerified = false');
      assert(!!savedUser.emailVerificationTokenHash, 'Verification token hash stored in database');
    }

    // -----------------------------------------------------------------
    // TEST 2: Login before verification is blocked with EMAIL_NOT_VERIFIED (403)
    // -----------------------------------------------------------------
    console.log('\n2. Testing Unverified Login Attempt...');
    {
      const { req, res, next } = createMockReqRes({
        email: testEmail,
        password: testPassword,
      });

      await loginUser(req, res, next);
      assert(res.statusCode === 403, 'Unverified login returns HTTP 403');
      assert(res.jsonData.code === 'EMAIL_NOT_VERIFIED', 'Returns code EMAIL_NOT_VERIFIED');
    }

    // -----------------------------------------------------------------
    // TEST 3: Email Verification link sets emailVerified = true
    // -----------------------------------------------------------------
    console.log('\n3. Testing Email Verification...');
    {
      const user = await User.findOne({ email: testEmail });
      // We know how token is hashed with sha256; test with invalid token first
      const { req: badReq, res: badRes, next: badNext } = createMockReqRes({}, { token: 'invalid_token_123', email: testEmail });
      await verifyEmail(badReq, badRes, badNext);
      assert(badRes.statusCode === 400, 'Invalid verification token returns HTTP 400');

      // Directly verify user for next tests
      user.emailVerified = true;
      user.emailVerificationTokenHash = undefined;
      await user.save();

      const verifiedUser = await User.findOne({ email: testEmail });
      assert(verifiedUser.emailVerified === true, 'User is now emailVerified = true');
    }

    // -----------------------------------------------------------------
    // TEST 4: Verified user can login & receives JWT + refresh token cookie
    // -----------------------------------------------------------------
    console.log('\n4. Testing Verified Login & JWT Access/Refresh tokens...');
    let activeRefreshToken = '';
    {
      const { req, res, next } = createMockReqRes({
        email: testEmail,
        password: testPassword,
      });

      await loginUser(req, res, next);
      assert(res.statusCode === 200, 'Login returns HTTP 200');
      assert(!!res.jsonData.accessToken, 'Access token is returned');
      assert(!!res.cookiesSet.refreshToken, 'HttpOnly refreshToken cookie is set');
      assert(res.cookiesSet.refreshToken.options.httpOnly === true, 'Refresh cookie has httpOnly: true');

      activeRefreshToken = res.cookiesSet.refreshToken.val;
    }

    // -----------------------------------------------------------------
    // TEST 5: Wrong password returns generic error (never reveals user existence)
    // -----------------------------------------------------------------
    console.log('\n5. Testing Wrong Password Generic Response...');
    {
      const { req, res, next } = createMockReqRes({
        email: testEmail,
        password: 'WrongPassword999',
      });

      await loginUser(req, res, next);
      assert(res.statusCode === 401, 'Wrong password returns HTTP 401');
      assert(res.jsonData.message === 'Invalid email or password', 'Returns generic "Invalid email or password"');
    }

    // -----------------------------------------------------------------
    // TEST 6: Account lockout after 5 consecutive failed attempts
    // -----------------------------------------------------------------
    console.log('\n6. Testing 5-attempt Account Lockout...');
    {
      // Already had 1 failed attempt in test 5; execute 4 more
      for (let i = 0; i < 4; i++) {
        const { req, res, next } = createMockReqRes({
          email: testEmail,
          password: 'WrongPassword999',
        });
        await loginUser(req, res, next);
      }

      // 5th attempt triggered lockout; next attempt must return 423 ACCOUNT_LOCKED
      const { req: lockReq, res: lockRes, next: lockNext } = createMockReqRes({
        email: testEmail,
        password: testPassword, // even with correct password!
      });
      await loginUser(lockReq, lockRes, lockNext);
      assert(lockRes.statusCode === 423, 'Locked account returns HTTP 423');
      assert(lockRes.jsonData.code === 'ACCOUNT_LOCKED', 'Returns code ACCOUNT_LOCKED');

      // Clear lock for remaining tests
      await User.updateOne({ email: testEmail }, { $set: { failedLoginAttempts: 0 }, $unset: { lockUntil: 1 } });
    }

    // -----------------------------------------------------------------
    // TEST 7: Refresh token rotation issues new access token + new refresh token
    // -----------------------------------------------------------------
    console.log('\n7. Testing Refresh Token Rotation & Invalidation...');
    let rotatedRefreshToken = '';
    {
      const { req, res, next } = createMockReqRes({}, {}, { refreshToken: activeRefreshToken });
      await refreshToken(req, res, next);
      assert(res.statusCode === 200, 'Refresh returns HTTP 200');
      assert(!!res.jsonData.accessToken, 'New access token issued');
      assert(!!res.cookiesSet.refreshToken, 'New rotated refresh token cookie set');
      assert(res.cookiesSet.refreshToken.val !== activeRefreshToken, 'Old refresh token rotated out');

      rotatedRefreshToken = res.cookiesSet.refreshToken.val;

      // Reusing the old refresh token must be rejected!
      const { req: reuseReq, res: reuseRes, next: reuseNext } = createMockReqRes({}, {}, { refreshToken: activeRefreshToken });
      await refreshToken(reuseReq, reuseRes, reuseNext);
      assert(reuseRes.statusCode === 401, 'Reused old refresh token rejected with HTTP 401');
    }

    // -----------------------------------------------------------------
    // TEST 8: Logout clears refresh cookie & database hash
    // -----------------------------------------------------------------
    console.log('\n8. Testing Logout...');
    {
      const { req, res, next } = createMockReqRes({}, {}, { refreshToken: rotatedRefreshToken });
      await logoutUser(req, res, next);
      assert(res.statusCode === 200, 'Logout returns HTTP 200');
      assert(res.cookiesCleared.some(c => c.name === 'refreshToken'), 'Refresh token cookie cleared');

      // Refreshing after logout must fail
      const { req: afterReq, res: afterRes, next: afterNext } = createMockReqRes({}, {}, { refreshToken: rotatedRefreshToken });
      await refreshToken(afterReq, afterRes, afterNext);
      assert(afterRes.statusCode === 401, 'Refresh after logout rejected');
    }

    // -----------------------------------------------------------------
    // TEST 9: Forgot password gives generic response for unknown & known email
    // -----------------------------------------------------------------
    console.log('\n9. Testing Forgot Password Generic Response...');
    {
      const { req: unkReq, res: unkRes, next: unkNext } = createMockReqRes({ email: 'nonexistent@nowhere.local' });
      await forgotPassword(unkReq, unkRes, unkNext);
      assert(unkRes.statusCode === 200, 'Unknown email returns HTTP 200 generic message');
      assert(unkRes.jsonData.success === true, 'Success flag true for privacy');

      const { req: knownReq, res: knownRes, next: knownNext } = createMockReqRes({ email: testEmail });
      await forgotPassword(knownReq, knownRes, knownNext);
      assert(knownRes.statusCode === 200, 'Known email returns HTTP 200 generic message');
      assert(knownRes.jsonData.message === unkRes.jsonData.message, 'Generic message identical for known & unknown email');
    }

    // -----------------------------------------------------------------
    // TEST 10: 6-digit Code verification, wrong attempt counter & limit
    // -----------------------------------------------------------------
    console.log('\n10. Testing 6-digit Code Verification & Attempt Limits...');
    let resetToken = '';
    {
      // Test invalid code
      const { req: badReq, res: badRes, next: badNext } = createMockReqRes({ email: testEmail, code: '000000' });
      await verifyResetCode(badReq, badRes, badNext);
      assert(badRes.statusCode === 400, 'Wrong 6-digit code returns HTTP 400');
      assert(badRes.jsonData.code === 'INVALID_CODE', 'Returns code INVALID_CODE');

      // Set known code for testing
      const testCode = '654321';
      const crypto = await import('node:crypto');
      const hash = crypto.createHash('sha256').update(testCode).digest('hex');
      await User.updateOne(
        { email: testEmail },
        {
          $set: {
            passwordResetCodeHash: hash,
            passwordResetCodeExpiresAt: new Date(Date.now() + 10 * 60 * 1000),
            passwordResetCodeAttempts: 0,
          },
        }
      );

      // Verify with correct code
      const { req: goodReq, res: goodRes, next: goodNext } = createMockReqRes({ email: testEmail, code: testCode });
      await verifyResetCode(goodReq, goodRes, goodNext);
      assert(goodRes.statusCode === 200, 'Correct 6-digit code returns HTTP 200');
      assert(!!goodRes.jsonData.resetToken, 'Single-use reset token returned');

      resetToken = goodRes.jsonData.resetToken;
    }

    // -----------------------------------------------------------------
    // TEST 11: Reset password updates password & invalidates refresh tokens
    // -----------------------------------------------------------------
    console.log('\n11. Testing Password Reset & Session Invalidation...');
    const newPassword = 'NewSecretPassword123';
    {
      const { req, res, next } = createMockReqRes({
        email: testEmail,
        resetToken,
        newPassword,
        confirmPassword: newPassword,
      });

      await resetPassword(req, res, next);
      assert(res.statusCode === 200, 'Reset password returns HTTP 200');

      // Login with old password must fail
      const { req: oldReq, res: oldRes, next: oldNext } = createMockReqRes({
        email: testEmail,
        password: testPassword,
      });
      await loginUser(oldReq, oldRes, oldNext);
      assert(oldRes.statusCode === 401, 'Old password fails');

      // Login with new password must succeed
      const { req: newReq, res: newRes, next: newNext } = createMockReqRes({
        email: testEmail,
        password: newPassword,
      });
      await loginUser(newReq, newRes, newNext);
      assert(newRes.statusCode === 200, 'New password succeeds');
    }

    // -----------------------------------------------------------------
    // TEST 12: Existing users without emailVerified field can log in normally (No migration needed)
    // -----------------------------------------------------------------
    console.log('\n12. Testing Existing User Backward Compatibility (no emailVerified field)...');
    {
      const legacyEmail = `legacy_student_${Date.now()}@testrunner.com`;
      const salt = await bcrypt.genSalt(10);
      const hashedPassword = await bcrypt.hash('LegacyPassword123', salt);

      // Insert directly into MongoDB collection without emailVerified field
      await mongoose.connection.collection('users').insertOne({
        name: 'Legacy Student',
        email: legacyEmail,
        password: hashedPassword,
        degree: 'B.Tech CS',
        university: 'Legacy Campus',
        targetRole: 'SDE',
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      // Confirm field is strictly undefined in DB
      const legacyDoc = await mongoose.connection.collection('users').findOne({ email: legacyEmail });
      assert(legacyDoc.emailVerified === undefined, 'Legacy user has NO emailVerified field in DB');

      // Attempt login
      const { req, res, next } = createMockReqRes({
        email: legacyEmail,
        password: 'LegacyPassword123',
      });
      await loginUser(req, res, next);
      assert(res.statusCode === 200, 'Legacy user logs in successfully without migration');
      assert(!!res.jsonData.accessToken, 'Legacy user receives access token');
    }

    // 13. Testing Interview History Deletion and Cascade Cleanup...
    console.log('\n13. Testing Interview History Deletion and Cascade Cleanup...');
    {
      const userDoc = await User.findOne({ email: testEmail });
      const testInterview = await Interview.create({
        userId: userDoc._id,
        type: 'technical',
        subject: 'java',
        difficulty: 'medium',
        status: 'completed',
        score: 85,
      });

      await Answer.create({
        interviewId: testInterview._id,
        userId: userDoc._id,
        questionId: 'test-q-1',
        questionText: 'Explain polymorphism in Java',
        answerText: 'Polymorphism allows objects to be treated as instances of their parent class.',
      });
      await Result.create({
        interviewId: testInterview._id,
        userId: userDoc._id,
        overallScore: 85,
      });

      // Test unauthorized deletion attempt by another user
      const otherUser = await User.create({
        name: 'Other Student',
        email: `other_${Date.now()}@testrunner.com`,
        password: 'Password123',
      });
      const unauthReqRes = createMockReqRes();
      unauthReqRes.req.params = { id: testInterview._id.toString() };
      unauthReqRes.req.user = otherUser;
      await deleteInterview(unauthReqRes.req, unauthReqRes.res, unauthReqRes.next);
      assert(unauthReqRes.res.statusCode === 403, 'Deleting another user interview returns HTTP 403');

      // Test successful deletion by owner
      const authReqRes = createMockReqRes();
      authReqRes.req.params = { id: testInterview._id.toString() };
      authReqRes.req.user = userDoc;
      await deleteInterview(authReqRes.req, authReqRes.res, authReqRes.next);
      assert(authReqRes.res.statusCode === 200, 'Deleting owned interview returns HTTP 200');

      // Verify cascade deletion in database
      const deletedInt = await Interview.findById(testInterview._id);
      assert(deletedInt === null, 'Interview removed from database');
      const answersLeft = await Answer.countDocuments({ interviewId: testInterview._id });
      assert(answersLeft === 0, 'Associated answers cascade deleted');
      const resultsLeft = await Result.countDocuments({ interviewId: testInterview._id });
      assert(resultsLeft === 0, 'Associated result cascade deleted');

      // Test deleting non-existent interview
      const notFoundReqRes = createMockReqRes();
      notFoundReqRes.req.params = { id: new mongoose.Types.ObjectId().toString() };
      notFoundReqRes.req.user = userDoc;
      await deleteInterview(notFoundReqRes.req, notFoundReqRes.res, notFoundReqRes.next);
      assert(notFoundReqRes.res.statusCode === 404, 'Deleting non-existent interview returns HTTP 404');
    }

    // -----------------------------------------------------------------
    // TEST 14: Mocked Mail Transport: 6-Digit Code Flow, Attempt Limits, Lockout, Expiry, Resend Cooldown, Failing Transport, Old Links
    // -----------------------------------------------------------------
    console.log('\n14. Testing Mocked Mail Transport: 6-Digit Code Flow, Attempt Limits, Lockout, Expiry, Resend Cooldown, Failing Transport, Old Links...');
    {
      const originalHost = process.env.SMTP_HOST;
      process.env.SMTP_HOST = 'smtp.mockserver.com';

      const sentMails = [];
      const mockTransport = {
        sendMail: async (mailOptions) => {
          sentMails.push(mailOptions);
          return { messageId: 'mock-msg-' + Date.now() };
        },
      };

      setCustomTransport(mockTransport);

      const mockEmail = `mocked_${Date.now()}@testrunner.com`;
      const mockPass = 'Password123';

      // 14.1 Register sends a 6-digit code via email (honest sent)
      const { req: regReq, res: regRes, next: regNext } = createMockReqRes({
        name: 'Mock Test Candidate',
        email: mockEmail,
        password: mockPass,
      });

      await registerUser(regReq, regRes, regNext);
      assert(regRes.statusCode === 201, 'Mocked registration returns HTTP 201');
      assert(regRes.jsonData.emailSent === true, 'Registration reports emailSent = true with active transport');
      assert(sentMails.length === 1, 'Register called the email transport sendMail');
      assert(sentMails[0].to === mockEmail, 'Email sent to correct user address');

      // Extract 6-digit code from email text
      const codeMatch = sentMails[0].text.match(/\[\s*([0-9]{6})\s*\]/);
      assert(!!codeMatch && !!codeMatch[1], 'Email body contains 6-digit verification code');
      const correctCode = codeMatch[1];

      // Never leak code in API response
      assert(!regRes.jsonData.code, 'Verification code is not in response root');
      assert(!JSON.stringify(regRes.jsonData).includes(correctCode), 'Raw 6-digit code is NEVER leaked in registration response JSON');

      // 14.2 Unverified login is blocked with 403 EMAIL_NOT_VERIFIED
      const { req: logReq, res: logRes, next: logNext } = createMockReqRes({
        email: mockEmail,
        password: mockPass,
      });
      await loginUser(logReq, logRes, logNext);
      assert(logRes.statusCode === 403, 'Unverified account login blocked with HTTP 403');
      assert(logRes.jsonData.code === 'EMAIL_NOT_VERIFIED', 'Unverified account returns EMAIL_NOT_VERIFIED code');

      // 14.3 Register with failing transport reports emailSent = false honestly, no code leaked, user retained
      const failingTransport = {
        sendMail: async () => {
          throw new Error('SMTP connection timed out: 587');
        },
      };
      setCustomTransport(failingTransport);

      const failEmail = `fail_${Date.now()}@testrunner.com`;
      const { req: failReq, res: failRes, next: failNext } = createMockReqRes({
        name: 'Failing Mail Candidate',
        email: failEmail,
        password: mockPass,
      });

      await registerUser(failReq, failRes, failNext);
      assert(failRes.statusCode === 201, 'Failing transport registration returns HTTP 201');
      assert(failRes.jsonData.emailSent === false, 'Sender error reports emailSent = false (honest outcome)');
      assert(failRes.jsonData.message.includes('could not send the verification email'), 'Honest message returned when email fails');
      assert(!failRes.jsonData.code, 'No code in failing transport response');
      const failUserInDb = await User.findOne({ email: failEmail });
      assert(failUserInDb !== null, 'Account kept in database even when email transport fails');

      // 14.4 Unconfigured SMTP reports emailSent = false and honest message
      const savedHost = process.env.SMTP_HOST;
      delete process.env.SMTP_HOST;
      setCustomTransport(null);

      const unconfEmail = `unconf_${Date.now()}@testrunner.com`;
      const { req: unconfReq, res: unconfRes, next: unconfNext } = createMockReqRes({
        name: 'Unconfigured SMTP Candidate',
        email: unconfEmail,
        password: mockPass,
      });

      await registerUser(unconfReq, unconfRes, unconfNext);
      process.env.SMTP_HOST = savedHost;

      assert(unconfRes.statusCode === 201, 'Unconfigured SMTP registration returns HTTP 201');
      assert(unconfRes.jsonData.emailSent === false, 'Unconfigured SMTP reports emailSent = false');
      assert(unconfRes.jsonData.message.includes('could not send the verification email'), 'Message honestly states verification email could not be sent');

      // Restore working mock transport
      setCustomTransport(mockTransport);

      // 14.5 Wrong code increments attempts and locks/invalidates after 5 attempts
      for (let i = 1; i <= 4; i++) {
        const { req: wrgReq, res: wrgRes, next: wrgNext } = createMockReqRes({
          email: mockEmail,
          code: '000000',
        });
        await verifyEmailCode(wrgReq, wrgRes, wrgNext);
        assert(wrgRes.statusCode === 400, `Wrong code attempt ${i} returns HTTP 400`);
        assert(wrgRes.jsonData.code === 'INVALID_CODE', `Wrong code attempt ${i} returns INVALID_CODE`);
        const remainingExpected = 5 - i;
        assert(wrgRes.jsonData.message.includes(`${remainingExpected} attempt`), `Message states ${remainingExpected} attempt(s) remaining`);
      }

      // 5th wrong attempt triggers lockout and invalidates code
      const { req: wrg5Req, res: wrg5Res, next: wrg5Next } = createMockReqRes({
        email: mockEmail,
        code: '000000',
      });
      await verifyEmailCode(wrg5Req, wrg5Res, wrg5Next);
      assert(wrg5Res.statusCode === 400, '5th wrong attempt returns HTTP 400');
      assert(wrg5Res.jsonData.code === 'TOO_MANY_ATTEMPTS', '5th wrong attempt returns TOO_MANY_ATTEMPTS');

      // 6th attempt with previously valid code must fail because code was invalidated
      const { req: lockReq, res: lockRes, next: lockNext } = createMockReqRes({
        email: mockEmail,
        code: correctCode,
      });
      await verifyEmailCode(lockReq, lockRes, lockNext);
      assert(lockRes.statusCode === 400, 'Invalidated code rejected on subsequent attempt');
      assert(lockRes.jsonData.code === 'TOO_MANY_ATTEMPTS', 'Locked code returns TOO_MANY_ATTEMPTS');

      // 14.6 Resend cooldown returns 429 with seconds left
      const { req: cdReq, res: cdRes, next: cdNext } = createMockReqRes({
        email: mockEmail,
      });
      await resendVerification(cdReq, cdRes, cdNext);
      assert(cdRes.statusCode === 429, 'Immediate resend hit cooldown returns HTTP 429');
      assert(cdRes.jsonData.code === 'COOLDOWN_ACTIVE', 'Cooldown returns code COOLDOWN_ACTIVE');
      assert(typeof cdRes.jsonData.retryAfter === 'number' && cdRes.jsonData.retryAfter > 0, 'Returns retryAfter seconds');

      // 14.7 Resend with failing transport returns 502 "could not send, try again later"
      // Simulate cooldown elapsed
      await User.updateOne(
        { email: mockEmail },
        { $set: { lastEmailVerificationSentAt: new Date(Date.now() - 35 * 1000) } }
      );
      setCustomTransport(failingTransport);

      const { req: rfReq, res: rfRes, next: rfNext } = createMockReqRes({
        email: mockEmail,
      });
      await resendVerification(rfReq, rfRes, rfNext);
      assert(rfRes.statusCode === 502, 'Failing transport resend returns HTTP 502');
      assert(rfRes.jsonData.message.includes('could not send, try again later'), 'Honest 502 message "could not send, try again later"');

      // 14.8 Resend succeeds with working transport and issues new code
      setCustomTransport(mockTransport);
      await User.updateOne(
        { email: mockEmail },
        { $set: { lastEmailVerificationSentAt: new Date(Date.now() - 35 * 1000) } }
      );
      const preResendCount = sentMails.length;

      const { req: rsReq, res: rsRes, next: rsNext } = createMockReqRes({
        email: mockEmail,
      });
      await resendVerification(rsReq, rsRes, rsNext);
      assert(rsRes.statusCode === 200, 'Successful resend returns HTTP 200');
      assert(rsRes.jsonData.emailSent === true, 'Resend reports emailSent = true');
      assert(sentMails.length === preResendCount + 1, 'Resend dispatched a new email');

      const newCodeMatch = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/);
      assert(!!newCodeMatch && !!newCodeMatch[1], 'New email contains new 6-digit code');
      const newCode = newCodeMatch[1];

      // 14.9 Expired code is rejected with 400 CODE_EXPIRED
      await User.updateOne(
        { email: mockEmail },
        { $set: { emailVerificationCodeExpiresAt: new Date(Date.now() - 1000) } }
      );

      const { req: expReq, res: expRes, next: expNext } = createMockReqRes({
        email: mockEmail,
        code: newCode,
      });
      await verifyEmailCode(expReq, expRes, expNext);
      assert(expRes.statusCode === 400, 'Expired verification code returns HTTP 400');
      assert(expRes.jsonData.code === 'CODE_EXPIRED', 'Returns code CODE_EXPIRED');

      // 14.10 After code expires and is cleared, resend generates fresh code that verifies successfully
      await User.updateOne(
        { email: mockEmail },
        { $set: { lastEmailVerificationSentAt: new Date(Date.now() - 35 * 1000) } }
      );
      const { req: rs2Req, res: rs2Res, next: rs2Next } = createMockReqRes({ email: mockEmail });
      await resendVerification(rs2Req, rs2Res, rs2Next);
      assert(rs2Res.statusCode === 200, 'Fresh resend after expiration returns HTTP 200');
      const freshCodeMatch = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/);
      const freshCode = freshCodeMatch[1];

      const { req: okReq, res: okRes, next: okNext } = createMockReqRes({
        email: mockEmail,
        code: freshCode,
      });
      await verifyEmailCode(okReq, okRes, okNext);
      assert(okRes.statusCode === 200, 'Correct 6-digit code verifies account with HTTP 200');
      assert(okRes.jsonData.success === true, 'Verification returns success = true');

      const verifiedUserInDb = await User.findOne({ email: mockEmail }).select('+emailVerificationCodeHash');
      assert(verifiedUserInDb.emailVerified === true, 'Database record has emailVerified = true');
      assert(!verifiedUserInDb.emailVerificationCodeHash, 'Code hash cleared from database upon successful verification');

      // 14.11 Reused code returns clear alreadyVerified response
      const { req: reReq, res: reRes, next: reNext } = createMockReqRes({
        email: mockEmail,
        code: freshCode,
      });
      await verifyEmailCode(reReq, reRes, reNext);
      assert(reRes.statusCode === 200, 'Reused verification code returns HTTP 200');
      assert(reRes.jsonData.alreadyVerified === true, 'Reused code reports alreadyVerified = true');

      // 14.12 Verified user logs in and receives token
      const { req: vLogReq, res: vLogRes, next: vLogNext } = createMockReqRes({
        email: mockEmail,
        password: mockPass,
      });
      await loginUser(vLogReq, vLogRes, vLogNext);
      assert(vLogRes.statusCode === 200, 'Verified user logs in successfully with HTTP 200');
      assert(!!vLogRes.jsonData.accessToken, 'Access token issued to verified student');

      // 14.13 Old link endpoint (/verify-email?token=...) still verifies
      const legacyLinkEmail = `legacylink_${Date.now()}@testrunner.com`;
      const legacyToken = 'legacy_token_hex_1234567890abcdef1234567890abcdef';
      const cryptoMod = await import('node:crypto');
      const tokenHash = cryptoMod.createHash('sha256').update(legacyToken).digest('hex');

      await User.create({
        name: 'Legacy Link Candidate',
        email: legacyLinkEmail,
        password: 'Password123',
        emailVerified: false,
        emailVerificationTokenHash: tokenHash,
        emailVerificationExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
      });

      const { req: oldReq, res: oldRes, next: oldNext } = createMockReqRes({}, { token: legacyToken, email: legacyLinkEmail });
      await verifyEmail(oldReq, oldRes, oldNext);
      assert(oldRes.statusCode === 200, 'Old link endpoint successfully verifies with HTTP 200');
      assert(oldRes.jsonData.success === true, 'Old link returns success: true');

      const verifiedLegacyDoc = await User.findOne({ email: legacyLinkEmail });
      assert(verifiedLegacyDoc.emailVerified === true, 'Old link verified user in DB');

      // 14.14 Resend verification on nonexistent email returns 404 and already verified returns 400
      const { req: unkResendReq, res: unkResendRes, next: unkResendNext } = createMockReqRes({
        email: 'nobody_here_999@testrunner.com',
      });
      await resendVerification(unkResendReq, unkResendRes, unkResendNext);
      assert(unkResendRes.statusCode === 404, 'Resend on nonexistent email returns HTTP 404 USER_NOT_FOUND');

      const { req: alrResendReq, res: alrResendRes, next: alrResendNext } = createMockReqRes({
        email: mockEmail,
      });
      await resendVerification(alrResendReq, alrResendRes, alrResendNext);
      assert(alrResendRes.statusCode === 400, 'Resend on already verified account returns HTTP 400 ALREADY_VERIFIED');

      // 14.15 Honesty Guard: Ethereal host with mocked transport must return emailSent: false and sandbox warning
      process.env.SMTP_HOST = 'smtp.ethereal.email';
      const ethEmail = `ethereal_${Date.now()}@testrunner.com`;
      const { req: ethReq, res: ethRes, next: ethNext } = createMockReqRes({
        name: 'Ethereal Test Candidate',
        email: ethEmail,
        password: mockPass,
      });
      await registerUser(ethReq, ethRes, ethNext);
      assert(ethRes.statusCode === 201, 'Ethereal host registration returns HTTP 201');
      assert(ethRes.jsonData.emailSent === false, 'Ethereal host registration reports emailSent = false');
      assert(
        (ethRes.jsonData.message || '').toLowerCase().includes('sandbox'),
        'Registration message explains email service is a test sandbox'
      );

      // Simulate cooldown elapsed so resend proceeds to email dispatch
      await User.updateOne(
        { email: ethEmail },
        { $set: { lastEmailVerificationSentAt: new Date(Date.now() - 35 * 1000) } }
      );

      // Resend on ethereal host also returns emailSent: false and sandbox message
      const { req: ethRsReq, res: ethRsRes, next: ethRsNext } = createMockReqRes({
        email: ethEmail,
      });
      await resendVerification(ethRsReq, ethRsRes, ethRsNext);
      assert(ethRsRes.statusCode === 502, 'Ethereal host resend returns HTTP 502');
      assert(ethRsRes.jsonData.emailSent === false, 'Ethereal host resend reports emailSent = false');
      assert(
        (ethRsRes.jsonData.message || '').toLowerCase().includes('sandbox'),
        'Resend message explains email service is a test sandbox'
      );

      // Reset custom transport and restore SMTP_HOST
      setCustomTransport(null);
      process.env.SMTP_HOST = originalHost;
    }

    // -----------------------------------------------------------------
    // TEST 15: 1-Minute Registration Code TTL Enforcement & Expiry Tests
    // -----------------------------------------------------------------
    console.log('\n15. Testing 1-Minute Code TTL: 59s Acceptance, 61s Rejection, Old Code Rejection, Attempt Counting, Lockout, and 10min Reset TTL...');
    {
      const realDateNow = Date.now;
      let baseTime = realDateNow();
      Date.now = () => baseTime;

      const sentMails = [];
      const mockTransport = {
        sendMail: async (mailOptions) => {
          sentMails.push(mailOptions);
          return { messageId: 'mock-1min-' + realDateNow() };
        },
      };
      setCustomTransport(mockTransport);

      const emailA = `ttl_59s_${realDateNow()}@testrunner.com`;
      const passA = 'TestPass123';

      // 15.1 Registration returns expiresAt and expiresInSeconds = 60
      const { req: regReq, res: regRes, next: regNext } = createMockReqRes({
        name: 'TTL Candidate 59s',
        email: emailA,
        password: passA,
      });
      await registerUser(regReq, regRes, regNext);
      assert(regRes.statusCode === 201, 'Registration returns HTTP 201');
      assert(regRes.jsonData.expiresInSeconds === 60, 'Registration response returns expiresInSeconds = 60');
      assert(!!regRes.jsonData.expiresAt, 'Registration response returns expiresAt ISO timestamp');

      const codeA = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      // 15.2 Wrong code at 10 seconds still counts as an attempt
      baseTime += 10 * 1000; // +10s
      const { req: wReq10, res: wRes10, next: wNext10 } = createMockReqRes({
        email: emailA,
        code: '000000',
      });
      await verifyEmailCode(wReq10, wRes10, wNext10);
      assert(wRes10.statusCode === 400, 'Wrong code at 10s returns HTTP 400');
      assert(wRes10.jsonData.code === 'INVALID_CODE', 'Wrong code at 10s returns INVALID_CODE');
      assert(wRes10.jsonData.message.includes('4 attempt'), 'Wrong code at 10s counted as 1st attempt (4 remaining)');

      // 15.3 Correct code accepted at 59 seconds
      baseTime += 49 * 1000; // +49s (total 59s from registration)
      const { req: ok59Req, res: ok59Res, next: ok59Next } = createMockReqRes({
        email: emailA,
        code: codeA,
      });
      await verifyEmailCode(ok59Req, ok59Res, ok59Next);
      assert(ok59Res.statusCode === 200, 'Correct code accepted at 59 seconds with HTTP 200');
      assert(ok59Res.jsonData.success === true, 'Verification returns success: true at 59 seconds');

      // 15.4 Code rejected at 61 seconds with CODE_EXPIRED and exact message
      const emailB = `ttl_61s_${realDateNow()}@testrunner.com`;
      baseTime = realDateNow(); // fresh base
      const { req: regBReq, res: regBRes, next: regBNext } = createMockReqRes({
        name: 'TTL Candidate 61s',
        email: emailB,
        password: passA,
      });
      await registerUser(regBReq, regBRes, regBNext);
      const codeB = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      // Advance clock by 61 seconds
      baseTime += 61 * 1000; // 61s
      const { req: exp61Req, res: exp61Res, next: exp61Next } = createMockReqRes({
        email: emailB,
        code: codeB,
      });
      await verifyEmailCode(exp61Req, exp61Res, exp61Next);
      assert(exp61Res.statusCode === 400, 'Code at 61 seconds rejected with HTTP 400');
      assert(exp61Res.jsonData.code === 'CODE_EXPIRED', 'Code at 61s returns CODE_EXPIRED');
      assert(
        exp61Res.jsonData.message === 'This code has expired (codes are valid for 1 minute). Please request a new one.',
        'Returns exact expired message for 1 minute code'
      );

      // Verify expired code cleared from database so it cannot be accepted later
      const userBInDb = await User.findOne({ email: emailB }).select('+emailVerificationCodeHash');
      assert(!userBInDb.emailVerificationCodeHash, 'Expired code hash cleared from database');

      // 15.5 Resend cooldown is still 30 seconds
      const emailC = `ttl_cooldown_${realDateNow()}@testrunner.com`;
      baseTime = realDateNow();
      const { req: regCReq, res: regCRes, next: regCNext } = createMockReqRes({
        name: 'Cooldown Candidate',
        email: emailC,
        password: passA,
      });
      await registerUser(regCReq, regCRes, regCNext);
      const codeC1 = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      // Resend at 10s hits cooldown
      baseTime += 10 * 1000;
      const { req: cdReq, res: cdRes, next: cdNext } = createMockReqRes({ email: emailC });
      await resendVerification(cdReq, cdRes, cdNext);
      assert(cdRes.statusCode === 429, 'Resend before 30s returns HTTP 429');
      assert(cdRes.jsonData.code === 'COOLDOWN_ACTIVE', 'Cooldown returns COOLDOWN_ACTIVE');

      // Resend at 31s succeeds and issues fresh code with fresh 60s
      baseTime += 21 * 1000; // total 31s
      const { req: rsCReq, res: rsCRes, next: rsCNext } = createMockReqRes({ email: emailC });
      await resendVerification(rsCReq, rsCRes, rsCNext);
      assert(rsCRes.statusCode === 200, 'Resend after 30s succeeds with HTTP 200');
      assert(rsCRes.jsonData.expiresInSeconds === 60, 'Resend returns expiresInSeconds = 60');
      const codeC2 = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];
      assert(codeC1 !== codeC2, 'Resend generates a new distinct 6-digit code');

      // 15.6 Old code is rejected after resend
      const { req: oldCodeReq, res: oldCodeRes, next: oldCodeNext } = createMockReqRes({
        email: emailC,
        code: codeC1,
      });
      await verifyEmailCode(oldCodeReq, oldCodeRes, oldCodeNext);
      assert(oldCodeRes.statusCode === 400, 'Old code rejected after resend');

      // 15.7 Expired code cannot be reused after resend
      // User B (whose code expired earlier) resends
      baseTime += 35 * 1000;
      const { req: rsBReq, res: rsBRes, next: rsBNext } = createMockReqRes({ email: emailB });
      await resendVerification(rsBReq, rsBRes, rsBNext);
      assert(rsBRes.statusCode === 200, 'User B resend succeeds with HTTP 200');
      const codeB2 = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      // Try using old expired codeB
      const { req: reUseExpReq, res: reUseExpRes, next: reUseExpNext } = createMockReqRes({
        email: emailB,
        code: codeB,
      });
      await verifyEmailCode(reUseExpReq, reUseExpRes, reUseExpNext);
      assert(reUseExpRes.statusCode === 400, 'Old expired code cannot be reused after resend');

      // Fresh codeB2 verifies successfully
      const { req: freshBReq, res: freshBRes, next: freshBNext } = createMockReqRes({
        email: emailB,
        code: codeB2,
      });
      await verifyEmailCode(freshBReq, freshBRes, freshBNext);
      assert(freshBRes.statusCode === 200, 'Fresh code after resend verifies with HTTP 200');

      // 15.8 5 wrong attempts still lock the code
      const emailD = `ttl_lock_${realDateNow()}@testrunner.com`;
      baseTime = realDateNow();
      const { req: regDReq, res: regDRes, next: regDNext } = createMockReqRes({
        name: 'Lockout Candidate',
        email: emailD,
        password: passA,
      });
      await registerUser(regDReq, regDRes, regDNext);
      const codeD = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      for (let attempt = 1; attempt <= 4; attempt++) {
        const { req: wReq, res: wRes, next: wNext } = createMockReqRes({
          email: emailD,
          code: '000000',
        });
        await verifyEmailCode(wReq, wRes, wNext);
        assert(wRes.statusCode === 400, `Attempt ${attempt} returns HTTP 400`);
      }

      // 5th attempt locks
      const { req: wReq5, res: wRes5, next: wNext5 } = createMockReqRes({
        email: emailD,
        code: '000000',
      });
      await verifyEmailCode(wReq5, wRes5, wNext5);
      assert(wRes5.statusCode === 400, '5th attempt returns HTTP 400');
      assert(wRes5.jsonData.code === 'TOO_MANY_ATTEMPTS', '5th attempt returns TOO_MANY_ATTEMPTS');

      // Subsequent attempt with correct code fails
      const { req: lockTryReq, res: lockTryRes, next: lockTryNext } = createMockReqRes({
        email: emailD,
        code: codeD,
      });
      await verifyEmailCode(lockTryReq, lockTryRes, lockTryNext);
      assert(lockTryRes.statusCode === 400, 'Subsequent attempt on locked code rejected');
      assert(lockTryRes.jsonData.code === 'TOO_MANY_ATTEMPTS', 'Locked code returns TOO_MANY_ATTEMPTS');

      // 15.9 Forgot-password reset code is still valid for 10 minutes
      const emailE = `ttl_pw_${realDateNow()}@testrunner.com`;
      baseTime = realDateNow();
      await User.create({
        name: 'PW User',
        email: emailE,
        password: 'Password123',
        emailVerified: true,
      });
      const { req: fpReq, res: fpRes, next: fpNext } = createMockReqRes({ email: emailE });
      await forgotPassword(fpReq, fpRes, fpNext);
      assert(fpRes.statusCode === 200, 'Forgot password returns HTTP 200');

      const pwCode = sentMails[sentMails.length - 1].text.match(/\[\s*([0-9]{6})\s*\]/)[1];

      // Advance clock by 9 minutes (540s) - still valid for 10 minutes
      baseTime += 9 * 60 * 1000;
      const { req: vResetReq, res: vResetRes, next: vResetNext } = createMockReqRes({
        email: emailE,
        code: pwCode,
      });
      await verifyResetCode(vResetReq, vResetRes, vResetNext);
      assert(vResetRes.statusCode === 200, 'Forgot-password code is still valid after 9 minutes (10min TTL)');
      assert(!!vResetRes.jsonData.resetToken, 'Single-use reset token issued at 9 minutes');

      // Restore clock & transport
      Date.now = realDateNow;
      setCustomTransport(null);
    }

    // =========================================================================
    // 10. Account Deletion and Server-Side Cascade Cleanup Tests
    // =========================================================================
    console.log('\n--- 10. Account Deletion & Cascade Purge ---');

    // 10.1 Unauthenticated delete is rejected with 401
    {
      const { req: unauthReq, res: unauthRes, next: unauthNext } = createMockReqRes();
      await deleteAccount(unauthReq, unauthRes, unauthNext);
      assert(unauthRes.statusCode === 401, 'Unauthenticated deleteAccount returns HTTP 401');
      assert(unauthRes.jsonData?.code === 'UNAUTHORIZED', 'Unauthenticated deleteAccount returns UNAUTHORIZED code');
    }

    // 10.2 Authenticated delete cascade deletes user and all associated records from server
    {
      const delUserEmail = `deluser_${Date.now()}@testrunner.com`;
      const delUserPass = 'DelPass123!';
      const userToDel = await User.create({
        name: 'Delete Target User',
        email: delUserEmail,
        password: delUserPass,
        emailVerified: true,
      });

      // Create associated interview, answer, and result records
      const dummyInterview = await Interview.create({
        userId: userToDel._id,
        type: 'technical',
        subject: 'java',
        difficulty: 'medium',
        status: 'completed',
        score: 85,
      });

      const dummyAnswer = await Answer.create({
        userId: userToDel._id,
        interviewId: dummyInterview._id,
        questionId: 'del-q-1',
        questionText: 'What is inheritance in Java?',
        answerText: 'Sample answer for deletion testing',
      });

      const dummyResult = await Result.create({
        userId: userToDel._id,
        interviewId: dummyInterview._id,
        overallScore: 85,
      });

      assert(await User.findById(userToDel._id) !== null, 'Target user exists in MongoDB before deletion');
      assert(await Interview.countDocuments({ userId: userToDel._id }) === 1, 'Interview exists before deletion');
      assert(await Answer.countDocuments({ userId: userToDel._id }) === 1, 'Answer exists before deletion');
      assert(await Result.countDocuments({ userId: userToDel._id }) === 1, 'Result exists before deletion');

      // Execute deleteAccount
      const { req: delReq, res: delRes, next: delNext } = createMockReqRes();
      delReq.user = { _id: userToDel._id };

      await deleteAccount(delReq, delRes, delNext);

      assert(delRes.statusCode === 200, 'Authenticated deleteAccount returns HTTP 200');
      assert(delRes.jsonData?.success === true, 'deleteAccount returns success: true');

      // Verify complete deletion from server (MongoDB)
      const userAfterDel = await User.findById(userToDel._id);
      assert(userAfterDel === null, 'User document is permanently deleted from MongoDB');

      const interviewsAfterDel = await Interview.countDocuments({ userId: userToDel._id });
      assert(interviewsAfterDel === 0, 'All interviews cascaded and purged from server');

      const answersAfterDel = await Answer.countDocuments({ userId: userToDel._id });
      assert(answersAfterDel === 0, 'All answers cascaded and purged from server');

      const resultsAfterDel = await Result.countDocuments({ userId: userToDel._id });
      assert(resultsAfterDel === 0, 'All results cascaded and purged from server');

      // Verify refresh cookie cleared
      const cookieCleared = delRes.cookiesCleared.some((c) => c.name === 'refreshToken');
      assert(cookieCleared, 'Refresh token cookie is cleared on account deletion');

      // Subsequent login attempt must fail with 401
      const { req: postDelLogReq, res: postDelLogRes, next: postDelLogNext } = createMockReqRes({
        email: delUserEmail,
        password: delUserPass,
      });
      await loginUser(postDelLogReq, postDelLogRes, postDelLogNext);
      assert(postDelLogRes.statusCode === 401, 'Deleted account cannot log in (HTTP 401)');
    }

    // FIX 1: Run Failed Evaluation, Retry, and Genuine Zero Tests
    const failedEvalRes = await runFailedEvalTests();
    passedTests += failedEvalRes.passCount;
    totalTests += failedEvalRes.testCount;

    console.log(`\n=======================================================`);
    console.log(`[ALL PASSED] ${passedTests} / ${totalTests} tests succeeded!`);
    console.log(`=======================================================\n`);
  } finally {
    setCustomTransport(null);
    // Clean up test records
    await User.deleteMany({ email: /.*@testrunner\.com$/ });
    await mongoose.disconnect();
  }
}

runTestSuite()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\n[TEST RUNNER ERROR]', err);
    process.exit(1);
  });
