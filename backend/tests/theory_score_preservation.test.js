import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { User } from '../models/User.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';
import { interviewEngine } from '../services/interviewEngine.js';
import { aiService } from '../services/aiService.js';
import { getInterviewResult } from '../controllers/resultController.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

async function runTest() {
  console.log('--- Test 3: Server Score Preservation & Summary Average ---');
  await mongoose.connect(MONGODB_URI);

  try {
    // 1. Setup mock user and interview
    let user = await User.findOne({ email: 'test_score_server@mockmate.io' });
    if (!user) {
      user = await User.create({
        name: 'Score Test User',
        email: 'test_score_server@mockmate.io',
        password: 'Password123!',
      });
    }

    const interview = await Interview.create({
      userId: user._id,
      type: 'technical',
      subject: 'java',
      difficulty: 'medium',
      questionFormat: 'theory',
      questionsCount: 2,
      status: 'in-progress',
      currentQuestionData: {
        id: 'java-theory-test-01',
        questionText: 'Test theory question 1',
        expectedConcepts: ['Concept A', 'Concept B'],
      },
    });

    // 2. Mock aiService.evaluateAnswer to return specific AI service scores
    const origEvaluate = aiService.evaluateAnswer;
    
    // First answer: AI service returns score 52
    aiService.evaluateAnswer = async () => ({
      score: 52,
      relevance: 0.76,
      correctness: 0.25,
      conceptCoverage: 0.25,
      communication: 0.80,
      isIrrelevant: false,
      feedback: 'Partial understanding demonstrated.',
      strengths: ['Identified main concept'],
      weaknesses: ['Missed implementation details'],
      scoreReason: 'Score = average of Relevance, Correctness, Concept Coverage and Communication: 52%.',
    });

    const res1 = await interviewEngine.processAnswer(
      interview._id,
      user._id,
      'java-theory-test-01',
      'Test theory question 1',
      'Test answer text 1',
      ['Concept A', 'Concept B'],
      'theory',
      null, null, null, null, null, null, null, null, null, null,
      0
    );

    // Verify saved answer 1 preserved AI-service score 52
    const savedAns1 = await Answer.findOne({ interviewId: interview._id, questionIndex: 0 });
    if (!savedAns1 || savedAns1.score !== 52) {
      throw new Error(`Expected saved answer score 52, got ${savedAns1?.score}`);
    }
    if (typeof savedAns1.accuracy !== 'number' || !savedAns1.formula) {
      throw new Error('Every saved answer must include numeric accuracy and a formula object');
    }
    console.log('✓ Answer 1 saved score preserved from AI service:', savedAns1.score);

    // Second answer: AI service returns score 68
    aiService.evaluateAnswer = async () => ({
      score: 68,
      relevance: 0.85,
      correctness: 0.60,
      conceptCoverage: 0.65,
      communication: 0.60,
      isIrrelevant: false,
      feedback: 'Good technical response.',
      strengths: ['Clear terminology'],
      weaknesses: [],
      scoreReason: 'Score = average of Relevance, Correctness, Concept Coverage and Communication: 68%.',
    });

    const res2 = await interviewEngine.processAnswer(
      interview._id,
      user._id,
      'java-theory-test-02',
      'Test theory question 2',
      'Test answer text 2',
      ['Concept C'],
      'theory',
      null, null, null, null, null, null, null, null, null, null,
      1
    );

    const savedAns2 = await Answer.findOne({ interviewId: interview._id, questionIndex: 1 });
    if (!savedAns2 || savedAns2.score !== 68) {
      throw new Error(`Expected saved answer score 68, got ${savedAns2?.score}`);
    }
    if (typeof savedAns2.accuracy !== 'number' || !savedAns2.formula) {
      throw new Error('Every saved answer must include numeric accuracy and a formula object');
    }
    console.log('✓ Answer 2 saved score preserved from AI service:', savedAns2.score);

    // Restore original aiService.evaluateAnswer
    aiService.evaluateAnswer = origEvaluate;

    // 3. Complete interview and check summary average
    // Total questions = 2, scores = 52 and 68. Expected mean: round((52 + 68) / 2) = 60
    const mockReq = { params: { interviewId: interview._id.toString() }, user };
    let jsonResult = null;
    const mockRes = {
      json: (data) => { jsonResult = data; },
      status: () => mockRes,
    };

    await getInterviewResult(mockReq, mockRes, (err) => { if (err) throw err; });

    const expectedSummaryScore = Math.round((52 + 68) / 2); // 60
    if (jsonResult.result.overallScore !== expectedSummaryScore) {
      throw new Error(`Expected summary overallScore ${expectedSummaryScore}, got ${jsonResult.result.overallScore}`);
    }
    console.log('✓ Interview summary overallScore equals exact mean of saved answers:', jsonResult.result.overallScore);

    // Cleanup test data
    await Answer.deleteMany({ interviewId: interview._id });
    await Result.deleteMany({ interviewId: interview._id });
    await Interview.deleteOne({ _id: interview._id });
    await User.deleteOne({ _id: user._id });

    console.log('PASSED: Server score preservation and summary average test passed!');
  } finally {
    await mongoose.disconnect();
  }
}

runTest().catch((err) => {
  console.error('FAILED:', err);
  process.exit(1);
});
