/**
 * Test Suite: HR Session Question Limits and Authoritative Slot Enforcement
 * 
 * Verifies:
 * 1. Submitting 15 answers in a row: Exactly 10 answers created, subsequent requests rejected with 409.
 * 2. Parallel submissions for the same slot: Only 1 answer document created, idempotent evaluation returned.
 * 3. Submitting after completion: Rejected with 409 Conflict.
 * 4. Question uniqueness and category diversity: HR questions are unique within session, covering >= 5 categories with <= 2 per category.
 */

import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';
import { interviewEngine } from '../services/interviewEngine.js';
import { submitAnswer } from '../controllers/interviewController.js';
import { aiService } from '../services/aiService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

const createMockReqRes = (body = {}, params = {}, user = {}) => {
  const req = {
    body,
    params,
    user,
  };

  const res = {
    statusCode: 200,
    jsonData: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(data) {
      this.jsonData = data;
      return this;
    },
  };

  const next = (err) => {
    if (err) {
      res.statusCode = err.statusCode || err.status || 500;
      res.jsonData = { success: false, message: err.message };
    }
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
  console.log('--- HR Session 10-Question Authoritative Limits Suite ---');
  console.log('=======================================================\n');

  try {
    await mongoose.connect(MONGODB_URI);
    console.log('[DB] Connected to MongoDB.\n');

    // Clean up test records
    await User.deleteMany({ email: /.*@hrlimitstest\.com$/ });

    const testUser = await User.create({
      name: 'HR Limit Tester',
      email: `tester_${Date.now()}@hrlimitstest.com`,
      password: 'HashedPassword123!',
      degree: 'B.Tech IT',
      university: 'Tech University',
      targetRole: 'Software Engineer',
      emailVerified: true,
    });

    // Mock aiService evaluateAnswer and generateQuestion for fast deterministic tests
    const origEvaluateAnswer = aiService.evaluateAnswer;
    const origGenerateQuestion = aiService.generateQuestion;

    aiService.evaluateAnswer = async () => ({
      score: 85,
      correctness: 85,
      relevance: 90,
      accuracy: 80,
      communication: 85,
      conceptCoverage: 85,
      isIrrelevant: false,
      feedback: 'Solid answer.',
      strengths: ['Clear examples'],
      weaknesses: ['Add quantifiable impact'],
      improvementSuggestion: 'Provide a metric.',
      scoreReason: 'Good explanation.',
      whyNot100: null,
    });

    let qCounter = 1;
    aiService.generateQuestion = async () => {
      qCounter++;
      return {
        id: `hr-q-${qCounter}`,
        questionText: `Mock HR Question ${qCounter}?`,
        category: `Category ${qCounter % 5}`,
        difficulty: 'medium',
        expectedConcepts: ['STAR', 'Communication'],
        questionFormat: 'theory',
      };
    };

    // -----------------------------------------------------------------
    // TEST 1: Submit 15 answers in a row to an interview
    // -----------------------------------------------------------------
    console.log('1. Testing 15 sequential answer submissions...');
    {
      const interview = await Interview.create({
        userId: testUser._id,
        type: 'hr',
        subject: 'N/A',
        difficulty: 'medium',
        questionFormat: 'theory',
        status: 'in-progress',
        currentQuestion: 1,
        questionsCount: 10,
        attemptedCount: 0,
        followUpCount: 0,
        currentQuestionData: {
          id: 'hr-q-1',
          questionText: 'Mock HR Question 1?',
          category: 'Introduction',
        },
      });

      const submissionResults = [];
      for (let i = 1; i <= 15; i++) {
        const { req, res, next } = createMockReqRes(
          {
            questionId: `q-slot-${i}`,
            questionIndex: i - 1,
            questionText: `Question text ${i}`,
            answerText: `This is candidate answer number ${i} which provides detailed information about projects.`,
          },
          { id: interview._id.toString() },
          testUser
        );

        await submitAnswer(req, res, next);
        submissionResults.push({ index: i, statusCode: res.statusCode, data: res.jsonData });
      }

      // First 10 should succeed (HTTP 200)
      for (let i = 0; i < 10; i++) {
        assert(submissionResults[i].statusCode === 200, `Answer ${i + 1}/10 accepted with HTTP 200`);
      }

      // Next 5 (11 to 15) must be rejected with HTTP 409
      for (let i = 10; i < 15; i++) {
        assert(submissionResults[i].statusCode === 409, `Answer ${i + 1}/15 rejected with HTTP 409`);
      }

      // Verify DB state
      const savedAnswers = await Answer.find({ interviewId: interview._id });
      assert(savedAnswers.length === 10, 'Exactly 10 answers exist in the database');

      const updatedInterview = await Interview.findById(interview._id);
      assert(updatedInterview.status === 'completed', 'Interview status transitioned to completed');
      assert(updatedInterview.attemptedCount === 10, 'Interview attemptedCount is strictly 10');

      const resultDoc = await Result.findOne({ interviewId: interview._id });
      assert(resultDoc !== null, 'Result document created');
      assert(resultDoc.questionsAttempted === 10, 'Result questionsAttempted is strictly 10');
      assert(resultDoc.totalQuestions === 10, 'Result totalQuestions is strictly 10');
    }

    // -----------------------------------------------------------------
    // TEST 2: Parallel submissions for the exact same slot
    // -----------------------------------------------------------------
    console.log('\n2. Testing parallel race condition for the same slot...');
    {
      const interview = await Interview.create({
        userId: testUser._id,
        type: 'hr',
        subject: 'N/A',
        difficulty: 'medium',
        questionFormat: 'theory',
        status: 'in-progress',
        currentQuestion: 1,
        questionsCount: 10,
        attemptedCount: 0,
        currentQuestionData: {
          id: 'hr-race-1',
          questionText: 'Tell me about yourself?',
        },
      });

      const { req: reqA, res: resA, next: nextA } = createMockReqRes(
        {
          questionId: 'hr-race-1',
          questionIndex: 0,
          questionText: 'Tell me about yourself?',
          answerText: 'I am a software engineer with passion for building scalable systems.',
        },
        { id: interview._id.toString() },
        testUser
      );

      const { req: reqB, res: resB, next: nextB } = createMockReqRes(
        {
          questionId: 'hr-race-1',
          questionIndex: 0,
          questionText: 'Tell me about yourself?',
          answerText: 'I am a software engineer with passion for building scalable systems.',
        },
        { id: interview._id.toString() },
        testUser
      );

      // Submit both concurrently in parallel
      await Promise.all([submitAnswer(reqA, resA, nextA), submitAnswer(reqB, resB, nextB)]);

      assert(resA.statusCode === 200, 'Request A succeeded with HTTP 200');
      assert(resB.statusCode === 200, 'Request B succeeded with HTTP 200');

      // Verify that only 1 answer exists in MongoDB for this slot
      const answersForSlot = await Answer.find({ interviewId: interview._id, questionIndex: 0 });
      assert(answersForSlot.length === 1, 'Exactly 1 Answer document was created for slot 0');

      const totalAnswers = await Answer.find({ interviewId: interview._id });
      assert(totalAnswers.length === 1, 'Interview has total 1 answer document');
    }

    // -----------------------------------------------------------------
    // TEST 3: Submit after interview completion
    // -----------------------------------------------------------------
    console.log('\n3. Testing submission after interview is completed...');
    {
      const interview = await Interview.create({
        userId: testUser._id,
        type: 'hr',
        subject: 'N/A',
        difficulty: 'medium',
        status: 'completed',
        questionsCount: 10,
        attemptedCount: 10,
      });

      const { req, res, next } = createMockReqRes(
        {
          questionId: 'q-after-completion',
          questionIndex: 10,
          questionText: 'Late question',
          answerText: 'Answering after interview is done.',
        },
        { id: interview._id.toString() },
        testUser
      );

      await submitAnswer(req, res, next);
      assert(res.statusCode === 409, 'Late submission rejected with HTTP 409 Conflict');
    }

    // -----------------------------------------------------------------
    // TEST 4: HR question uniqueness and category diversity
    // -----------------------------------------------------------------
    console.log('\n4. Testing HR question uniqueness and category coverage...');
    {
      // Restore real generateQuestion logic to test the actual catalog and category diversity
      aiService.generateQuestion = origGenerateQuestion;

      const previousQuestions = [];
      const previousCategories = [];
      const categoriesSeen = new Set();
      const questionIdsSeen = new Set();
      const categoryCounts = {};

      for (let i = 1; i <= 10; i++) {
        const q = await aiService.generateQuestion({
          interviewType: 'hr',
          subject: 'N/A',
          difficulty: 'medium',
          previousQuestions,
          previousCategories,
          questionNumber: i,
          questionFormat: 'theory',
        });

        const qId = q.id || q.questionId || q.questionText;
        assert(!questionIdsSeen.has(qId), `Question #${i} ID (${qId}) is unique within session`);
        questionIdsSeen.add(qId);
        previousQuestions.push(q.questionText);
        if (q.id) previousQuestions.push(q.id);

        const cat = (q.category || '').toLowerCase();
        categoriesSeen.add(cat);
        previousCategories.push(q.category);
        categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
        assert(categoryCounts[cat] <= 2, `Category "${q.category}" appears at most 2 times (current: ${categoryCounts[cat]})`);
      }

      console.log(`  Categories covered (${categoriesSeen.size}): ${Array.from(categoriesSeen).join(', ')}`);
      assert(categoriesSeen.size >= 5, `HR session covers at least 5 different categories (actual: ${categoriesSeen.size})`);
    }

    // Cleanup
    aiService.evaluateAnswer = origEvaluateAnswer;
    aiService.generateQuestion = origGenerateQuestion;
    await User.deleteMany({ email: /.*@hrlimitstest\.com$/ });

    console.log('\n=======================================================');
    console.log(`TEST RESULTS: ${passedTests}/${totalTests} PASSED (0 FAILED)`);
    console.log('=======================================================\n');

    await mongoose.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('\n[FATAL TEST ERROR]:', err);
    await mongoose.disconnect();
    process.exit(1);
  }
}

runTestSuite();
