/**
 * Centralized Interview Engine
 * Controls state, difficulty adaptation, question sequence, follow-up probability, and evaluation
 */

import { aiService } from './aiService.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';

const DEFAULT_QUESTION_COUNT = 10;
const FOLLOW_UP_PERCENTAGE = parseInt(process.env.FOLLOW_UP_PERCENTAGE || '25', 10);
const MAX_FOLLOW_UPS = parseInt(process.env.MAX_FOLLOW_UPS || '3', 10);

// Builds the text used to tell "have we already asked this?" apart for a
// given saved Answer, and to feed the AI service's duplicate-avoidance /
// duplicate-rejection logic (see ai-service/app/models/llama_provider.py).
//
// This can NOT just be `answer.questionText` for every format:
//   - output_prediction's questionText is always the same fixed sentence
//     ("What is the exact output of the following code?..."), regardless
//     of which code snippet was actually shown -- the snippet is the only
//     part that varies, so it's the only part worth comparing.
//   - coding's questionText is the full unique problem statement, so it's
//     already a good signature on its own; prefixing the title just makes
//     two different problems that start similarly easier to tell apart.
//   - theory's questionText is itself the whole (unique) question, so it's
//     used as-is.
function questionSignature(answer) {
  if (answer.questionFormat === 'output_prediction') {
    return answer.codeSnippet || answer.questionText;
  }
  if (answer.questionFormat === 'coding') {
    return answer.title ? `${answer.title}: ${answer.questionText}` : answer.questionText;
  }
  return answer.questionText;
}

export const interviewEngine = {
  // Start Session & Get First Question
  async startSession(userId, type, subject, difficulty, questionFormat) {
    const interview = await Interview.create({
      userId,
      type,
      subject: type === 'technical' ? subject : 'N/A',
      difficulty: difficulty || 'medium',
      questionFormat: type === 'technical' ? (questionFormat || 'theory') : 'theory',
      status: 'in-progress',
      currentQuestion: 1,
      questionsCount: DEFAULT_QUESTION_COUNT,
      followUpCount: 0,
    });

    let firstQuestion;
    try {
      firstQuestion = await aiService.generateQuestion({
        interviewType: type,
        subject: type === 'technical' ? subject : 'N/A',
        difficulty: difficulty || 'medium',
        previousQuestions: [],
        previousAnswers: [],
        questionNumber: 1,
        questionFormat: interview.questionFormat,
      });
    } catch (error) {
      // Generation requires the fine-tuned LLaMA model and has no database
      // fallback -- don't leave a half-started, question-less interview
      // sitting in history if it couldn't be generated.
      await Interview.deleteOne({ _id: interview._id });
      throw error;
    }

    // Persist the exact generated question so a page refresh / resume
    // shows this same question (and its questionFormat/codeSnippet)
    // instead of falling back to a generic static question bank.
    interview.currentQuestionData = firstQuestion;
    await interview.save();

    return {
      interview,
      question: firstQuestion,
    };
  },

  // Process Submitted Answer and Decide Next Action
  async processAnswer(interviewId, userId, questionId, questionText, answerText, expectedConcepts, questionFormat, expectedOutput, explanation, testCases, language, codeSnippet, title, hrDeliveryMetrics, schema, sampleData, referenceSolution) {
    const interview = await Interview.findById(interviewId);
    if (!interview) throw new Error('Interview session not found');

    const isInvalidSqlPlaceholder = (s) => typeof s === 'string' && (/select\s+\*\s+from\s+records/i.test(s) || /\bfrom\s+records\b/i.test(s));
    let rawRefSol = referenceSolution ||
      interview.currentQuestionData?.referenceSolution ||
      interview.currentQuestionData?._referenceQuery ||
      interview.currentQuestionData?.solution ||
      null;
    const refSol = isInvalidSqlPlaceholder(rawRefSol) ? null : rawRefSol;
    const expOut = expectedOutput || interview.currentQuestionData?.expectedOutput || null;
    const sqlSchema = schema || interview.currentQuestionData?.schema || null;
    const sData = sampleData || interview.currentQuestionData?.sampleData || null;

    // 1. Evaluate answer via AI Service
    const evalResult = await aiService.evaluateAnswer({
      interviewType: interview.type,
      subject: interview.subject,
      question: questionText,
      answer: answerText,
      expectedConcepts: expectedConcepts || [],
      questionFormat: questionFormat || interview.questionFormat || 'theory',
      expectedOutput: expOut,
      explanation: explanation || null,
      testCases: testCases || null,
      language: language || null,
      schema: sqlSchema,
      sampleData: sData,
      referenceSolution: refSol,
      hrDeliveryMetrics: interview.type === 'hr' ? hrDeliveryMetrics || null : null,
    });

    if (evalResult.isIrrelevant === true) {
      Object.assign(evalResult, {
        score: 0,
        relevance: 0,
        correctness: 0,
        conceptCoverage: 0,
        communication: 0,
        strengths: [],
        weaknesses: [],
        missingConcepts: [],
        scoreReason: 'The answer is unrelated to the question.',
        improvementSuggestion: 'Provide an answer that directly addresses the question.',
        // HR: the required wording, and the 4th factor of the HR average zeroed too.
        ...(interview.type === 'hr'
          ? {
              accuracy: 0,
              feedback: 'Not related to the question.',
              scoreReason: 'Not related to the question.',
            }
          : {}),
      });
    }

    // 2. Store Answer in MongoDB
    const answerDoc = await Answer.create({
      interviewId: interview._id,
      userId,
      questionId: questionId || 'q-' + Date.now(),
      questionText,
      codeSnippet: codeSnippet || null,
      title: title || null,
      answerText,
      score: evalResult.score,
      conceptCoverage: evalResult.conceptCoverage,
      correctness: evalResult.correctness,
      relevance: evalResult.relevance,
      communication: evalResult.communication,
      ...(interview.type === 'hr' && typeof evalResult.accuracy === 'number'
        ? { accuracy: evalResult.accuracy }
        : {}),
      isIrrelevant: evalResult.isIrrelevant,
      feedback: evalResult.feedback,
      strengths: evalResult.strengths,
      weaknesses: evalResult.weaknesses,
      coveredConcepts: evalResult.coveredConcepts || [],
      partiallyCoveredConcepts: evalResult.partiallyCoveredConcepts || [],
      missingConcepts: evalResult.missingConcepts,
      improvementSuggestion: evalResult.improvementSuggestion || null,
      scoreReason: evalResult.scoreReason,
      stepByStepExplanation: evalResult.stepByStepExplanation || null,
      testCaseResults: evalResult.testCaseResults || undefined,
      passedCount: evalResult.passedCount !== undefined ? evalResult.passedCount : null,
      totalCount: evalResult.totalCount !== undefined ? evalResult.totalCount : null,
      judgeMode: evalResult.judgeMode || null,
      whyNot100: evalResult.whyNot100 || null,
      compileError: evalResult.compileError || null,
      correctedCode: evalResult.correctedCode || null,
      correctedQuery: evalResult.correctedQuery || null,
      correctionSummary: evalResult.correctionSummary || null,
      timeComplexity: evalResult.timeComplexity || null,
      spaceComplexity: evalResult.spaceComplexity || null,
      timeComplexityExplanation: evalResult.timeComplexityExplanation || null,
      referenceSolution: (() => {
        if (refSol && !isInvalidSqlPlaceholder(refSol)) return refSol;
        if (evalResult.correctedQuery && !isInvalidSqlPlaceholder(evalResult.correctedQuery)) return evalResult.correctedQuery;
        if (evalResult.correctedCode && !isInvalidSqlPlaceholder(evalResult.correctedCode)) return evalResult.correctedCode;
        if (refSol) return refSol;
        if (evalResult.score >= 80 || (typeof evalResult.passedCount === 'number' && evalResult.passedCount === evalResult.totalCount && evalResult.totalCount > 0)) {
          return codeSnippet || answerText;
        }
        return null;
      })(),
      expectedOutput: expOut,
      ...(interview.type === 'hr' && evalResult.deliveryMetrics
        ? { deliveryMetrics: evalResult.deliveryMetrics }
        : {}),
      questionFormat: questionFormat || interview.questionFormat || 'theory',
      isFollowUp: false,
    });

    // 3. Update Interview Progress State
    const allAnswers = await Answer.find({ interviewId: interview._id });
    interview.attemptedCount = allAnswers.length;

    // Check follow-up eligibility (20-30% chance & under MAX_FOLLOW_UPS limit).
    // Follow-ups are always plain theory-style questions, so they're skipped
    // entirely in output_prediction/coding mode -- otherwise a code-based
    // interview would randomly switch back to a theory question mid-session.
    const randomRoll = Math.floor(Math.random() * 100);
    const shouldAskFollowUp =
      interview.questionFormat !== 'output_prediction' &&
      interview.questionFormat !== 'coding' &&
      randomRoll < FOLLOW_UP_PERCENTAGE &&
      interview.followUpCount < MAX_FOLLOW_UPS &&
      answerText.trim().length > 30;

    let nextQuestion = null;

    if (interview.attemptedCount >= interview.questionsCount) {
      // Complete Session
      interview.status = 'completed';
      interview.completedAt = new Date();

      // Calculate overall score based on all questions
      const totalQuestions = interview.questionsCount || 10;
      const validScores = allAnswers.map((a) => a.score).filter((s) => typeof s === 'number');
      const sum = validScores.reduce((acc, curr) => acc + curr, 0);
      const overallScore = Math.round(sum / totalQuestions);

      interview.score = overallScore;
      interview.currentQuestionData = null;
      await interview.save();

      // Aggregate Result model (exclude communication factors for coding answers)
      const isCommItem = (item) => /communication|verbal|articulate|tone|delivery|speech/i.test(item || '');
      const allStrengths = allAnswers.flatMap((a) => {
        const list = a.strengths || [];
        return a.questionFormat === 'coding' ? list.filter((s) => !isCommItem(s)) : list;
      });
      const allWeaknesses = allAnswers.flatMap((a) => {
        const list = a.weaknesses || [];
        return a.questionFormat === 'coding' ? list.filter((w) => !isCommItem(w)) : list;
      });

      await Result.create({
        interviewId: interview._id,
        userId,
        overallScore: avgScore,
        strengths: Array.from(new Set(allStrengths)).slice(0, 4),
        weaknesses: Array.from(new Set(allWeaknesses)).slice(0, 4),
        recommendations: [
          `Continue practicing core ${interview.type === 'technical' ? interview.subject.toUpperCase() : 'HR'} interview questions.`,
          'Elaborate on edge case scenarios and real project experiences.',
        ],
        questionsAttempted: interview.attemptedCount,
        totalQuestions: interview.questionsCount,
      });
    } else {
      // Generate Next Question
      //
      // Built from questionSignature(), NOT a plain a.questionText map --
      // for output_prediction, questionText is always the same fixed
      // instruction sentence, so using it directly here would hand the AI
      // service a list of identical, useless "already asked" strings and
      // defeat duplicate-avoidance/rejection entirely for that format. See
      // questionSignature()'s docstring above.
      const prevQuestions = allAnswers.map((a) => questionSignature(a));
      try {
        if (shouldAskFollowUp) {
          interview.followUpCount += 1;
          nextQuestion = await aiService.generateFollowUp({
            interviewType: interview.type,
            subject: interview.subject,
            difficulty: interview.difficulty,
            previousQuestion: questionText,
            studentAnswer: answerText,
            expectedConcepts,
            // So the AI service knows every question already asked this
            // session (not just the immediately previous one) and can
            // avoid generating a follow-up that repeats an earlier one.
            previousQuestions: prevQuestions,
          });
        } else {
          const prevAnswers = allAnswers.map((a) => a.answerText);

          nextQuestion = await aiService.generateQuestion({
            interviewType: interview.type,
            subject: interview.subject,
            difficulty: interview.difficulty,
            previousQuestions: prevQuestions,
            previousAnswers: prevAnswers,
            questionNumber: allAnswers.length + 1,
            questionFormat: interview.questionFormat || 'theory',
          });
        }
      } catch (genError) {
        // The answer was already graded and saved above (evalResult exists),
        // but the NEXT question could not be generated (e.g. the AI
        // microservice/Ollama dropped mid-session). Previously this threw
        // straight out of processAnswer: the frontend's try/catch never
        // reached `setLastEvalFeedback`, so the candidate's score silently
        // vanished, the on-screen question never advanced, and re-clicking
        // Submit created ANOTHER graded Answer for the very same question --
        // which is exactly what looked like "the same question repeating".
        // Roll back the just-created answer so a retry is clean, and
        // surface the evaluation to the caller anyway so the score isn't
        // lost even though there's no next question yet.
        await Answer.deleteOne({ _id: answerDoc._id });
        interview.attemptedCount = Math.max(0, interview.attemptedCount - 1);
        const err = new Error(
          genError.message ||
            'Your answer was graded, but the next question could not be generated because the AI ' +
              'engine is unavailable. Please try submitting again once it is back online.'
        );
        err.evaluationForDisplay = evalResult;
        throw err;
      }

      interview.currentQuestion = allAnswers.length + 1;
      interview.currentQuestionData = nextQuestion;
      await interview.save();
    }

    return {
      evaluation: evalResult,
      answerDoc,
      interviewStatus: interview.status,
      nextQuestion,
      isFollowUp: shouldAskFollowUp,
    };
  },
};
