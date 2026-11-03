import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';
import { submitAnswer } from '../controllers/interviewController.js';
import { aiService } from '../services/aiService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

const createMockReqRes = (body = {}, params = {}) => {
  const req = {
    body,
    params,
    user: null,
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
    if (err) throw err;
  };
  return { req, res, next };
};

export async function runFailedEvalTests() {
  console.log('\n--- Running FIX 1: Failed Evaluation & Retry Tests ---');
  let testCount = 0;
  let passCount = 0;

  function assert(cond, msg) {
    testCount++;
    if (!cond) {
      console.error(`  [FAIL] ${msg}`);
      throw new Error(`Assertion failed: ${msg}`);
    }
    passCount++;
    console.log(`  [PASS] ${msg}`);
  }

  const isConnected = mongoose.connection.readyState === 1;
  if (!isConnected) {
    await mongoose.connect(MONGODB_URI);
  }

  const origEvaluate = aiService.evaluateAnswer;
  const origGenerate = aiService.generateQuestion;

  const testEmail = `test_faileval_${Date.now()}@testrunner.com`;

  try {
    let user = await User.create({
      name: 'Failed Eval Tester',
      email: testEmail,
      password: 'Password123!',
      emailVerified: true,
    });

    const interview = await Interview.create({
      userId: user._id,
      type: 'technical',
      subject: 'java',
      difficulty: 'medium',
      questionFormat: 'theory',
      questionsCount: 3,
      status: 'in-progress',
      attemptedCount: 0,
      currentQuestion: 1,
      score: null,
      currentQuestionData: {
        id: 'q-test-failed-eval-1',
        questionText: 'Explain the principles of OOP in Java.',
        expectedConcepts: ['Encapsulation', 'Inheritance', 'Polymorphism', 'Abstraction'],
      },
    });

    const interviewId = interview._id.toString();

    // -------------------------------------------------------------
    // Test 1: AI service returns source: "error" (e.g. model unreachable)
    // -------------------------------------------------------------
    aiService.evaluateAnswer = async () => ({
      source: 'error',
      error: 'evaluation engine unavailable, please retry',
      score: 0,
    });

    const { req: errReq, res: errRes, next: errNext } = createMockReqRes(
      {
        questionId: 'q-test-failed-eval-1',
        questionText: 'Explain the principles of OOP in Java.',
        answerText: 'OOP stands for Object Oriented Programming with 4 main pillars.',
        expectedConcepts: ['Encapsulation', 'Inheritance', 'Polymorphism', 'Abstraction'],
        questionFormat: 'theory',
      },
      { id: interviewId }
    );
    errReq.user = { _id: user._id };

    await submitAnswer(errReq, errRes, errNext);

    assert(errRes.statusCode === 503, 'Failed evaluation returns HTTP 503');
    assert(errRes.jsonData?.code === 'EVALUATION_UNAVAILABLE', 'Returns EVALUATION_UNAVAILABLE error code');
    assert(
      typeof errRes.jsonData?.message === 'string' &&
        errRes.jsonData.message.toLowerCase().includes('evaluation engine unavailable'),
      'Returns clear message "evaluation engine unavailable, please retry"'
    );

    // Verify database state: Answer NOT saved, attemptedCount unchanged, session score unchanged, question not advanced
    const answersAfterError = await Answer.find({ interviewId: interview._id });
    assert(answersAfterError.length === 0, 'Error response is NOT saved as an Answer in database');

    const interviewAfterError = await Interview.findById(interview._id);
    assert(interviewAfterError.attemptedCount === 0, 'Interview attemptedCount remains unchanged (0)');
    assert(interviewAfterError.score === null, 'Interview session score remains unchanged (null)');
    assert(interviewAfterError.currentQuestion === 1, 'Interview currentQuestion number remains 1 (not advanced)');
    assert(
      interviewAfterError.currentQuestionData?.id === 'q-test-failed-eval-1',
      'Current question remains unchanged and current'
    );

    // -------------------------------------------------------------
    // Test 2: Retry after recovery saves normally
    // -------------------------------------------------------------
    aiService.evaluateAnswer = async () => ({
      source: 'model',
      score: 85,
      relevance: 0.9,
      correctness: 0.85,
      conceptCoverage: 0.85,
      communication: 0.9,
      isIrrelevant: false,
      feedback: 'Good explanation of OOP pillars.',
    });

    aiService.generateQuestion = async () => ({
      id: 'q-test-failed-eval-2',
      questionId: 'q-test-failed-eval-2',
      questionText: 'What is the difference between Comparable and Comparator in Java?',
      expectedConcepts: ['compareTo', 'compare', 'java.lang', 'java.util'],
      questionFormat: 'theory',
      source: 'model',
      modelUsed: 'llama3.2:3b',
    });

    const { req: retryReq, res: retryRes, next: retryNext } = createMockReqRes(
      {
        questionId: 'q-test-failed-eval-1',
        questionText: 'Explain the principles of OOP in Java.',
        answerText: 'OOP stands for Object Oriented Programming with 4 main pillars.',
        expectedConcepts: ['Encapsulation', 'Inheritance', 'Polymorphism', 'Abstraction'],
        questionFormat: 'theory',
      },
      { id: interviewId }
    );
    retryReq.user = { _id: user._id };

    await submitAnswer(retryReq, retryRes, retryNext);

    assert(retryRes.statusCode === 200, 'Retry after recovery returns HTTP 200');
    assert(retryRes.jsonData?.evaluation?.score === 85, 'Retry after recovery evaluates with normal score (85)');

    const answersAfterRetry = await Answer.find({ interviewId: interview._id });
    assert(answersAfterRetry.length === 1, 'Retry after recovery successfully saves Answer document');
    assert(answersAfterRetry[0].score === 85, 'Saved Answer has correct score (85)');

    const interviewAfterRetry = await Interview.findById(interview._id);
    assert(interviewAfterRetry.attemptedCount === 1, 'Interview attemptedCount increased to 1 after successful retry');
    assert(
      interviewAfterRetry.currentQuestionData?.id === 'q-test-failed-eval-2',
      'Session advanced to next question after successful retry'
    );

    // -------------------------------------------------------------
    // Test 3: Genuine 0 score (unrelated / irrelevant answer) is still saved as 0
    // -------------------------------------------------------------
    aiService.evaluateAnswer = async () => ({
      source: 'rule',
      score: 0,
      relevance: 0.0,
      correctness: 0.0,
      conceptCoverage: 0.0,
      communication: 0.2,
      isIrrelevant: true,
      feedback: 'The response is completely unrelated to the question asked.',
    });

    const { req: zeroReq, res: zeroRes, next: zeroNext } = createMockReqRes(
      {
        questionId: 'q-test-failed-eval-2',
        questionText: 'What is the difference between Comparable and Comparator in Java?',
        answerText: 'I love eating pepperoni pizza on Friday nights with soda.',
        expectedConcepts: ['compareTo', 'compare'],
        questionFormat: 'theory',
      },
      { id: interviewId }
    );
    zeroReq.user = { _id: user._id };

    await submitAnswer(zeroReq, zeroRes, zeroNext);

    assert(zeroRes.statusCode === 200, 'Genuine 0 (irrelevant answer) returns HTTP 200');
    assert(zeroRes.jsonData?.evaluation?.score === 0, 'Returned evaluation has score 0');
    assert(zeroRes.jsonData?.evaluation?.isIrrelevant === true, 'Returned evaluation marked isIrrelevant: true');

    const answersAfterZero = await Answer.find({ interviewId: interview._id }).sort({ createdAt: 1 });
    assert(answersAfterZero.length === 2, 'Genuine 0 answer is saved in database');
    assert(answersAfterZero[1].score === 0, 'Genuine 0 answer saved with score: 0');

    const interviewAfterZero = await Interview.findById(interview._id);
    assert(interviewAfterZero.attemptedCount === 2, 'attemptedCount incremented to 2 for genuine 0 answer');

    console.log(`\n[FIX 1 TESTS COMPLETED] ${passCount} / ${testCount} passed!\n`);
    return { testCount, passCount };
  } finally {
    aiService.evaluateAnswer = origEvaluate;
    aiService.generateQuestion = origGenerate;
    await Answer.deleteMany({ userId: { $in: await User.find({ email: testEmail }).distinct('_id') } });
    await Interview.deleteMany({ userId: { $in: await User.find({ email: testEmail }).distinct('_id') } });
    await User.deleteMany({ email: testEmail });
  }
}

// Execute directly if run as CLI
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runFailedEvalTests()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
