/**
 * Test Suite: Solution Access Enforcement for Java & DBMS Modules
 * Verifies that reference solutions remain strictly locked (HTTP 403)
 * until the candidate has submitted their answer for the question.
 */
import http from 'http';
import mongoose from 'mongoose';
import { User } from '../models/User.js';

const BASE_URL = 'http://localhost:5000/api';
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

function request(method, path, body = null, token = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(`${BASE_URL}${path}`);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    }

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, data: parsed });
        } catch (e) {
          resolve({ status: res.statusCode, raw: data });
        }
      });
    });

    req.on('error', reject);
    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

async function runTests() {
  console.log('\n================================================================');
  console.log('--- Solution Button Locked/Unlocked Requirement Test Suite ---');
  console.log('================================================================\n');

  let passed = 0;
  let failed = 0;

  function assert(condition, testName) {
    if (condition) {
      console.log(`  [PASS] ${testName}`);
      passed++;
    } else {
      console.error(`  [FAIL] ${testName}`);
      failed++;
    }
  }

  try {
    await mongoose.connect(MONGODB_URI);

    // 1. Authenticate with a test account
    const email = `sol_test_${Date.now()}@test.com`;
    const password = 'Password@123';

    const regRes = await request('POST', '/auth/register', {
      name: 'Solution Tester',
      email,
      password,
    });
    assert(regRes.status === 201, 'Test user registered');

    // Auto-verify email directly in DB
    await User.updateOne({ email }, { emailVerified: true });
    assert(true, 'Test user email verified in DB');

    const loginRes = await request('POST', '/auth/login', { email, password });
    assert(loginRes.status === 200 && loginRes.data.accessToken, 'Test user logged in and token received');
    const authToken = loginRes.data.accessToken;

    // All Java and DBMS module variations
    const modules = [
      {
        subject: 'java',
        format: 'coding',
        title: 'Java Coding Module',
      },
      {
        subject: 'java',
        format: 'output_prediction',
        title: 'Java Output Prediction Module',
      },
      {
        subject: 'java',
        format: 'theory',
        title: 'Java Theory Module',
      },
      {
        subject: 'dbms',
        format: 'coding',
        title: 'DBMS SQL Coding Module',
      },
      {
        subject: 'dbms',
        format: 'theory',
        title: 'DBMS Theory Module',
      },
    ];

    for (const mod of modules) {
      console.log(`\n------------------------------------------------------------`);
      console.log(`Testing: ${mod.title} [Subject: ${mod.subject}, Format: ${mod.format}]`);
      console.log(`------------------------------------------------------------`);

      // 1. Start interview session for this specific subject and format
      const startRes = await request(
        'POST',
        '/interviews',
        {
          type: 'technical',
          subject: mod.subject,
          difficulty: 'medium',
          questionFormat: mod.format,
        },
        authToken
      );

      assert(startRes.status === 201 && startRes.data.interview, `Interview created for ${mod.title}`);
      const interview = startRes.data.interview;
      const interviewId = interview._id;
      const question = startRes.data.firstQuestion;

      assert(!!question && !!question.questionText, `Generated question received: "${question?.questionText?.slice(0, 45)}..."`);

      const questionKey = (mod.format === 'output_prediction' && question.codeSnippet)
        ? question.codeSnippet
        : (question.questionId || question.questionText);

      // 2. CHECK: Solution endpoint with questionKey before submission MUST BE LOCKED (403)
      const preCheckWithKey = await request(
        'GET',
        `/interviews/${interviewId}/solution?questionKey=${encodeURIComponent(questionKey)}`,
        null,
        authToken
      );
      assert(
        preCheckWithKey.status === 403,
        `Before submission (with questionKey): HTTP 403 Forbidden`
      );
      assert(
        preCheckWithKey.data?.code === 'SOLUTION_LOCKED',
        `Before submission (with questionKey): code == 'SOLUTION_LOCKED'`
      );

      // 3. CHECK: Solution endpoint without questionKey before submission MUST BE LOCKED (403)
      const preCheckNoKey = await request(
        'GET',
        `/interviews/${interviewId}/solution`,
        null,
        authToken
      );
      assert(
        preCheckNoKey.status === 403,
        `Before submission (no query param): HTTP 403 Forbidden`
      );
      assert(
        preCheckNoKey.data?.code === 'SOLUTION_LOCKED',
        `Before submission (no query param): code == 'SOLUTION_LOCKED'`
      );

      // 4. Submit Answer for this question
      const answerPayload = {
        questionId: question.questionId,
        questionText: question.questionText,
        answerText: mod.format === 'coding'
          ? (mod.subject === 'dbms' ? 'SELECT * FROM employees WHERE salary > 50000;' : 'public class Solution { public static void main(String[] args) {} }')
          : 'My conceptual or predicted answer for this question.',
        questionFormat: mod.format,
        expectedConcepts: question.expectedConcepts,
        expectedOutput: question.expectedOutput,
        explanation: question.explanation,
        testCases: question.testCases,
        language: question.language || (mod.subject === 'dbms' ? 'sql' : 'java'),
        codeSnippet: question.codeSnippet,
        title: question.title,
        schema: question.schema,
        sampleData: question.sampleData,
        referenceSolution: question.referenceSolution,
      };

      const submitRes = await request(
        'POST',
        `/interviews/${interviewId}/answers`,
        answerPayload,
        authToken
      );
      assert(submitRes.status === 200, `Answer submitted successfully (HTTP 200)`);

      // 5. CHECK: Solution endpoint with questionKey after submission MUST BE UNLOCKED (200)
      const postCheckWithKey = await request(
        'GET',
        `/interviews/${interviewId}/solution?questionKey=${encodeURIComponent(questionKey)}`,
        null,
        authToken
      );
      assert(
        postCheckWithKey.status === 200,
        `After submission (with questionKey): HTTP 200 OK`
      );
      assert(
        postCheckWithKey.data?.success === true && postCheckWithKey.data?.solution !== null,
        `After submission (with questionKey): Solution data returned successfully`
      );

      // 6. CHECK: Solution endpoint without questionKey while next question is active must remain LOCKED (403)
      const postCheckNoKey = await request(
        'GET',
        `/interviews/${interviewId}/solution`,
        null,
        authToken
      );
      assert(
        postCheckNoKey.status === 403 && postCheckNoKey.data?.code === 'SOLUTION_LOCKED',
        `After submitting question #1: Active next question remains locked (HTTP 403 SOLUTION_LOCKED) if query param omitted`
      );
    }

    console.log('\n================================================================');
    console.log(`Summary: ${passed} Passed, ${failed} Failed`);
    console.log('================================================================\n');

    await mongoose.disconnect();
    process.exit(failed > 0 ? 1 : 0);
  } catch (err) {
    console.error('Test run failed with error:', err);
    await mongoose.disconnect();
    process.exit(1);
  }
}

runTests();
