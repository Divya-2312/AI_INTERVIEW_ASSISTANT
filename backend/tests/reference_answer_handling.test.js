import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import assert from 'assert';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { interviewEngine } from '../services/interviewEngine.js';
import { aiService } from '../services/aiService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

async function runTest() {
  console.log('--- Test: Reference Answer Handling (Old & New Follow-ups + Catalogue) ---');
  await mongoose.connect(MONGODB_URI);

  let user = null;
  const createdInterviews = [];

  try {
    user = await User.findOne({ email: 'test_refans_handling@mockmate.io' });
    if (!user) {
      user = await User.create({
        name: 'RefAns Test User',
        email: 'test_refans_handling@mockmate.io',
        password: 'Password123!',
      });
    }

    let capturedAiArgs = [];
    const originalEvaluate = aiService.evaluateAnswer;
    const originalGenFollowUp = aiService.generateFollowUp;
    const originalGenQuestion = aiService.generateQuestion;

    aiService.evaluateAnswer = async (args) => {
      capturedAiArgs.push(args);
      return {
        score: 75,
        relevance: 0.80,
        correctness: 0.70,
        conceptCoverage: 0.70,
        communication: 0.80,
        isIrrelevant: false,
        feedback: 'Good answer explaining core concepts.',
        strengths: ['Clear explanation'],
        weaknesses: [],
        missingConcepts: [],
      };
    };

    aiService.generateFollowUp = async () => ({
      questionText: 'Can you give an example of checked exception handling?',
      expectedConcepts: ['try-catch', 'throws'],
      questionFormat: 'theory',
    });

    aiService.generateQuestion = async () => ({
      questionText: 'What is normalization in DBMS?',
      expectedConcepts: ['1NF', '2NF', '3NF'],
      questionFormat: 'theory',
    });

    // 1. Catalogue question with referenceAnswer in currentQuestionData
    const interview1 = await Interview.create({
      userId: user._id,
      type: 'technical',
      subject: 'java',
      difficulty: 'medium',
      questionFormat: 'theory',
      questionsCount: 5,
      status: 'in-progress',
      currentQuestionData: {
        id: 'java-theory-001',
        questionText: 'Explain the difference between a class and an object in Java.',
        expectedConcepts: ['blueprint', 'instance', 'memory'],
        referenceAnswer: 'A class is a blueprint; an object is a runtime instance created with new.',
      },
    });
    createdInterviews.push(interview1._id);

    console.log('1. Submitting answer for catalogue question with referenceAnswer...');
    capturedAiArgs = [];
    const res1 = await interviewEngine.processAnswer(
      interview1._id,
      user._id,
      'java-theory-001',
      'Explain the difference between a class and an object in Java.',
      'A class defines methods and variables while an object is an instantiated copy with memory.',
      ['blueprint', 'instance'],
      'theory',
      null, null, null, 'java', null,
      'Class vs Object',
      null, null, null, null, 0
    );
    assert.ok(res1 && res1.evaluation, 'Answer submission must return evaluation');
    assert.strictEqual(res1.evaluation.score, 75);
    assert.strictEqual(capturedAiArgs.length, 1);
    assert.strictEqual(
      capturedAiArgs[0].referenceAnswer,
      'A class is a blueprint; an object is a runtime instance created with new.',
      'Catalogue referenceAnswer must be forwarded to AI service'
    );
    console.log('  [PASS] Catalogue question submitted without exception');

    // 2. Old stored follow-up question WITHOUT referenceAnswer field
    const interview2 = await Interview.create({
      userId: user._id,
      type: 'technical',
      subject: 'java',
      difficulty: 'medium',
      questionFormat: 'theory',
      questionsCount: 5,
      status: 'in-progress',
      currentQuestionData: {
        id: 'fu-old-001',
        questionText: 'Can you give a practical example where try-catch is mandatory?',
        expectedConcepts: ['IOException', 'compile time'],
        // NOTE: NO referenceAnswer field present, simulating old follow-up
      },
    });
    createdInterviews.push(interview2._id);

    console.log('2. Submitting answer for old follow-up question WITHOUT referenceAnswer...');
    capturedAiArgs = [];
    const res2 = await interviewEngine.processAnswer(
      interview2._id,
      user._id,
      'fu-old-001',
      'Can you give a practical example where try-catch is mandatory?',
      'When performing file reading with FileInputStream, IOException is checked and requires try-catch.',
      ['IOException'],
      'theory',
      null, null, null, 'java', null,
      'Checked Exception Example',
      null, null, null, null, 0
    );
    assert.ok(res2 && res2.evaluation, 'Answer submission must return evaluation');
    assert.strictEqual(res2.evaluation.score, 75);
    assert.strictEqual(capturedAiArgs.length, 1);
    assert.strictEqual(
      capturedAiArgs[0].referenceAnswer,
      null,
      'referenceAnswer must safely default to null when missing on stored question'
    );
    console.log('  [PASS] Old follow-up question without referenceAnswer submitted without exception');

    // 3. New follow-up question WITH referenceAnswer field
    const interview3 = await Interview.create({
      userId: user._id,
      type: 'technical',
      subject: 'java',
      difficulty: 'medium',
      questionFormat: 'theory',
      questionsCount: 5,
      status: 'in-progress',
      currentQuestionData: {
        id: 'fu-new-001',
        questionText: 'How does try-with-resources prevent resource leaks?',
        expectedConcepts: ['AutoCloseable', 'close()'],
        referenceAnswer: 'Try-with-resources automatically closes AutoCloseable resources at the end of the statement.',
      },
    });
    createdInterviews.push(interview3._id);

    console.log('3. Submitting answer for new follow-up question WITH referenceAnswer...');
    capturedAiArgs = [];
    const res3 = await interviewEngine.processAnswer(
      interview3._id,
      user._id,
      'fu-new-001',
      'How does try-with-resources prevent resource leaks?',
      'Any resource implementing AutoCloseable has its close method invoked automatically even if an exception occurs.',
      ['AutoCloseable'],
      'theory',
      null, null, null, 'java', null,
      'Try with Resources',
      null, null, null, null, 0
    );
    assert.ok(res3 && res3.evaluation, 'Answer submission must return evaluation');
    assert.strictEqual(res3.evaluation.score, 75);
    assert.strictEqual(capturedAiArgs.length, 1);
    assert.strictEqual(
      capturedAiArgs[0].referenceAnswer,
      'Try-with-resources automatically closes AutoCloseable resources at the end of the statement.',
      'New follow-up referenceAnswer must be forwarded to AI service'
    );
    console.log('  [PASS] New follow-up question with referenceAnswer submitted without exception');

    // Restore original functions
    aiService.evaluateAnswer = originalEvaluate;
    aiService.generateFollowUp = originalGenFollowUp;
    aiService.generateQuestion = originalGenQuestion;

    console.log('\n[ALL TESTS PASSED] Reference answer handling verified for catalogue, old follow-up, and new follow-up!');
  } finally {
    for (const id of createdInterviews) {
      await Answer.deleteMany({ interviewId: id });
      await Interview.deleteOne({ _id: id });
    }
    if (user) {
      await User.deleteOne({ _id: user._id });
    }
    await mongoose.disconnect();
  }
}

runTest().catch((err) => {
  console.error('[TEST FAILED]', err);
  process.exit(1);
});
