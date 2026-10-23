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
//     ("What is the exact output of the following code?"), regardless
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
        previousCategories: [],
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
  async processAnswer(interviewId, userId, questionId, questionText, answerText, expectedConcepts, questionFormat, expectedOutput, explanation, testCases, language, codeSnippet, title, hrDeliveryMetrics, schema, sampleData, referenceSolution, questionIndex) {
    const interview = await Interview.findById(interviewId);
    if (!interview) {
      const err = new Error('Interview session not found');
      err.statusCode = 404;
      throw err;
    }

    const maxQuestions = interview.questionsCount || DEFAULT_QUESTION_COUNT;
    const targetQId = questionId || 'q-' + Date.now();

    // 1. Idempotency check: if this questionId or slot was already evaluated/saved, return it directly
    const existingAnswers = await Answer.find({ interviewId: interview._id }).sort({ questionIndex: 1, createdAt: 1 });
    const matchedAnswer = existingAnswers.find(
      (a) => a.questionId === targetQId || (typeof questionIndex === 'number' && a.questionIndex === questionIndex)
    );
    if (matchedAnswer) {
      return {
        evaluation: {
          score: matchedAnswer.score,
          conceptCoverage: matchedAnswer.conceptCoverage,
          correctness: matchedAnswer.correctness,
          relevance: matchedAnswer.relevance,
          communication: matchedAnswer.communication,
          ...(interview.type === 'hr' && typeof matchedAnswer.accuracy === 'number'
            ? { accuracy: matchedAnswer.accuracy }
            : {}),
          isIrrelevant: matchedAnswer.isIrrelevant,
          feedback: matchedAnswer.feedback,
          strengths: matchedAnswer.strengths,
          weaknesses: matchedAnswer.weaknesses,
          coveredConcepts: matchedAnswer.coveredConcepts || [],
          partiallyCoveredConcepts: matchedAnswer.partiallyCoveredConcepts || [],
          missingConcepts: matchedAnswer.missingConcepts || [],
          improvementSuggestion: matchedAnswer.improvementSuggestion,
          scoreReason: matchedAnswer.scoreReason,
          whyNot100: matchedAnswer.whyNot100,
          referenceSolution: matchedAnswer.referenceSolution,
          questionId: matchedAnswer.questionId,
          questionText: matchedAnswer.questionText,
          title: matchedAnswer.title,
          questionFormat: matchedAnswer.questionFormat,
          language: matchedAnswer.language,
          subject: interview.subject,
        },
        answerDoc: matchedAnswer,
        interviewStatus: interview.status,
        nextQuestion: interview.currentQuestionData,
        isFollowUp: matchedAnswer.isFollowUp || false,
      };
    }

    // 2. Reject if interview is already completed or question limit reached
    if (interview.status !== 'in-progress' || existingAnswers.length >= maxQuestions) {
      const err = new Error(
        interview.status !== 'in-progress'
          ? `Interview session is ${interview.status}`
          : `Interview question limit of ${maxQuestions} reached`
      );
      err.statusCode = 409;
      err.status = 409;
      throw err;
    }

    // 3. Atomic reservation of the question slot
    const updatedInterview = await Interview.findOneAndUpdate(
      {
        _id: interview._id,
        status: 'in-progress',
        attemptedCount: { $lt: maxQuestions },
      },
      {
        $inc: { attemptedCount: 1 },
      },
      { new: true }
    );

    if (!updatedInterview) {
      // Check again if a concurrent request finished this question
      const latestExisting = await Answer.findOne({
        interviewId: interview._id,
        $or: [{ questionId: targetQId }, ...(typeof questionIndex === 'number' ? [{ questionIndex }] : [])],
      });
      if (latestExisting) {
        return {
          evaluation: {
            score: latestExisting.score,
            conceptCoverage: latestExisting.conceptCoverage,
            correctness: latestExisting.correctness,
            relevance: latestExisting.relevance,
            communication: latestExisting.communication,
            ...(interview.type === 'hr' && typeof latestExisting.accuracy === 'number'
              ? { accuracy: latestExisting.accuracy }
              : {}),
            isIrrelevant: latestExisting.isIrrelevant,
            feedback: latestExisting.feedback,
            strengths: latestExisting.strengths,
            weaknesses: latestExisting.weaknesses,
            improvementSuggestion: latestExisting.improvementSuggestion,
            scoreReason: latestExisting.scoreReason,
            whyNot100: latestExisting.whyNot100,
            referenceSolution: latestExisting.referenceSolution,
            questionId: latestExisting.questionId,
            questionText: latestExisting.questionText,
            title: latestExisting.title,
            questionFormat: latestExisting.questionFormat,
            language: latestExisting.language,
            subject: interview.subject,
          },
          answerDoc: latestExisting,
          interviewStatus: interview.status,
          nextQuestion: interview.currentQuestionData,
          isFollowUp: latestExisting.isFollowUp || false,
        };
      }
      const err = new Error(`Interview question limit of ${maxQuestions} reached or session no longer in-progress`);
      err.statusCode = 409;
      err.status = 409;
      throw err;
    }

    const assignedSlot = typeof questionIndex === 'number' ? questionIndex : existingAnswers.length;

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
    const codeSnip = codeSnippet || interview.currentQuestionData?.codeSnippet || null;

    // 4. Evaluate answer via AI Service
    let evalResult;
    try {
      evalResult = await aiService.evaluateAnswer({
        interviewType: interview.type,
        subject: interview.subject,
        question: questionText,
        answer: answerText,
        expectedConcepts: expectedConcepts || [],
        questionFormat: questionFormat || interview.questionFormat || 'theory',
        expectedOutput: expOut,
        explanation: explanation || interview.currentQuestionData?.explanation || null,
        testCases: (testCases && testCases.some(tc => tc.expectedOutput !== undefined))
          ? testCases
          : (interview.currentQuestionData?.testCases || testCases || null),
        language: language || null,
        schema: sqlSchema,
        sampleData: sData,
        referenceSolution: refSol,
        hrDeliveryMetrics: interview.type === 'hr' ? hrDeliveryMetrics || null : null,
      });
    } catch (evalErr) {
      await Interview.updateOne({ _id: interview._id }, { $inc: { attemptedCount: -1 } });
      throw evalErr;
    }

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

    // 5. Store Answer in MongoDB with unique compound index on (interviewId, questionIndex)
    const isNoComm =
      questionFormat === 'output_prediction' ||
      questionFormat === 'coding' ||
      language === 'sql' ||
      (interview.subject === 'dbms' && (language === 'sql' || questionFormat === 'coding' || /^\s*(?:--[^\n]*\n\s*)*SELECT\b/i.test(answerText || '')));

    if (isNoComm) {
      evalResult.communication = null;
    }

    const answerPayload = {
      interviewId: interview._id,
      userId,
      questionId: targetQId,
      questionIndex: assignedSlot,
      questionText,
      codeSnippet: codeSnippet || null,
      title: title || null,
      category: interview.currentQuestionData?.category || null,
      answerText,
      score: evalResult.score,
      conceptCoverage: evalResult.conceptCoverage,
      correctness: evalResult.correctness,
      relevance: evalResult.relevance,
      communication: isNoComm ? null : evalResult.communication,
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
      evaluatedBy: evalResult.evaluatedBy || null,
      llamaRubric: evalResult.llamaRubric || null,
      evidence: evalResult.evidence || null,
      formulaVersion: evalResult.formulaVersion || null,
      llamaEvaluation: evalResult.llamaEvaluation || null,
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
    };

    let answerDoc;
    try {
      answerDoc = await Answer.create(answerPayload);
    } catch (saveErr) {
      if (saveErr.code === 11000) {
        // Compound index conflict: rollback attemptedCount and return saved answer
        await Interview.updateOne({ _id: interview._id }, { $inc: { attemptedCount: -1 } });
        const concurrentAnswer = await Answer.findOne({
          interviewId: interview._id,
          questionIndex: assignedSlot,
        });
        if (concurrentAnswer) {
          return {
            evaluation: {
              score: concurrentAnswer.score,
              conceptCoverage: concurrentAnswer.conceptCoverage,
              correctness: concurrentAnswer.correctness,
              relevance: concurrentAnswer.relevance,
              communication: concurrentAnswer.communication,
              ...(interview.type === 'hr' && typeof concurrentAnswer.accuracy === 'number'
                ? { accuracy: concurrentAnswer.accuracy }
                : {}),
              isIrrelevant: concurrentAnswer.isIrrelevant,
              feedback: concurrentAnswer.feedback,
              strengths: concurrentAnswer.strengths,
              weaknesses: concurrentAnswer.weaknesses,
              improvementSuggestion: concurrentAnswer.improvementSuggestion,
              scoreReason: concurrentAnswer.scoreReason,
              whyNot100: concurrentAnswer.whyNot100,
              referenceSolution: concurrentAnswer.referenceSolution,
              questionId: concurrentAnswer.questionId,
              questionText: concurrentAnswer.questionText,
            },
            answerDoc: concurrentAnswer,
            interviewStatus: interview.status,
            nextQuestion: interview.currentQuestionData,
            isFollowUp: concurrentAnswer.isFollowUp || false,
          };
        }
      }
      await Interview.updateOne({ _id: interview._id }, { $inc: { attemptedCount: -1 } });
      throw saveErr;
    }

    // 6. Update Interview Progress State (strictly derived from saved answers and never exceeds maxQuestions)
    const rawAnswers = await Answer.find({ interviewId: interview._id }).sort({ questionIndex: 1, createdAt: 1 });
    const allAnswers = rawAnswers;
    interview.attemptedCount = Math.min(allAnswers.length, maxQuestions);

    // Follow-ups count as one of the 10 slots; max 3 follow-ups; only if under maxQuestions
    const isHr = interview.type === 'hr';
    const randomRoll = Math.floor(Math.random() * 100);
    const shouldAskFollowUp =
      interview.questionFormat !== 'output_prediction' &&
      interview.questionFormat !== 'coding' &&
      randomRoll < FOLLOW_UP_PERCENTAGE &&
      interview.followUpCount < (isHr ? 3 : MAX_FOLLOW_UPS) &&
      interview.attemptedCount < maxQuestions &&
      answerText.trim().length > 30;

    let nextQuestion = null;

    if (interview.attemptedCount >= maxQuestions) {
      // Complete Session - strictly 10 questions
      interview.status = 'completed';
      interview.completedAt = new Date();

      // Calculate overall score based on all questions
      const totalQuestions = maxQuestions;
      const validScores = allAnswers.map((a) => a.score).filter((s) => typeof s === 'number');
      const sum = validScores.reduce((acc, curr) => acc + curr, 0);
      const overallScore = Math.round(sum / totalQuestions);

      interview.score = overallScore;
      interview.currentQuestionData = null;
      await interview.save();

      // Aggregate Result model (exclude communication factors for coding, output prediction, and dbms sql answers)
      const isCommItem = (item) => /communication|verbal|articulate|tone|delivery|speech/i.test(item || '');
      const allStrengths = allAnswers.flatMap((a) => {
        const list = a.strengths || [];
        const isTechnicalNoComm = a.questionFormat === 'coding' || a.questionFormat === 'output_prediction' || a.language === 'sql' || interview.subject === 'dbms';
        return isTechnicalNoComm ? list.filter((s) => !isCommItem(s)) : list;
      });
      const allWeaknesses = allAnswers.flatMap((a) => {
        const list = a.weaknesses || [];
        const isTechnicalNoComm = a.questionFormat === 'coding' || a.questionFormat === 'output_prediction' || a.language === 'sql' || interview.subject === 'dbms';
        return isTechnicalNoComm ? list.filter((w) => !isCommItem(w)) : list;
      });

      await Result.findOneAndUpdate(
        { interviewId: interview._id },
        {
          userId,
          overallScore,
          strengths: Array.from(new Set(allStrengths)).slice(0, 4),
          weaknesses: Array.from(new Set(allWeaknesses)).slice(0, 4),
          recommendations: [
            `Continue practicing core ${interview.type === 'technical' ? interview.subject.toUpperCase() : 'HR'} interview questions.`,
            'Elaborate on edge case scenarios and real project experiences.',
          ],
          questionsAttempted: interview.attemptedCount,
          totalQuestions: maxQuestions,
        },
        { upsert: true, new: true }
      );
    } else {
      // Generate Next Question
      const prevQuestions = allAnswers.flatMap((a) => [questionSignature(a), a.questionId].filter(Boolean));
      const prevCategories = allAnswers.map((a) => a.category).filter(Boolean);
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
            previousQuestions: prevQuestions,
          });
        } else {
          const prevAnswers = allAnswers.map((a) => a.answerText);

          nextQuestion = await aiService.generateQuestion({
            interviewType: interview.type,
            subject: interview.subject,
            difficulty: interview.difficulty,
            previousQuestions: prevQuestions,
            previousCategories: prevCategories,
            previousAnswers: prevAnswers,
            questionNumber: allAnswers.length + 1,
            questionFormat: interview.questionFormat || 'theory',
          });
        }
      } catch (genError) {
        await Answer.deleteOne({ _id: answerDoc._id });
        interview.attemptedCount = Math.max(0, interview.attemptedCount - 1);
        await interview.save();
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
