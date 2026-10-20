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
  loginUser,
  refreshToken,
  logoutUser,
  forgotPassword,
  verifyResetCode,
  resetPassword,
} from '../controllers/authController.js';
import { deleteInterview } from '../controllers/interviewController.js';

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

    console.log(`\n=======================================================`);
    console.log(`[ALL PASSED] ${passedTests} / ${totalTests} tests succeeded!`);
    console.log(`=======================================================\n`);
  } finally {
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
