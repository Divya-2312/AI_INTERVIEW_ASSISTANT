import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';

// @desc    Get result report for an interview session
// @route   GET /api/results/:interviewId
// @access  Private
export const getInterviewResult = async (req, res, next) => {
  try {
    const { interviewId } = req.params;

    const interview = await Interview.findById(interviewId);

    if (!interview) {
      res.status(404);
      throw new Error('Interview record not found');
    }

    // Ownership check
    if (interview.userId.toString() !== req.user._id.toString()) {
      res.status(403);
      throw new Error('Access denied: Unauthorized to view this result');
    }

    const answers = await Answer.find({ interviewId: interview._id });
    let result = await Result.findOne({ interviewId: interview._id });

    // Calculate real score and attempted count based on ALL questions (e.g. 1/10 attended with 100% is 10%)
    const totalQuestions = interview.questionsCount || 10;
    const validScores = answers.map((a) => a.score).filter((s) => typeof s === 'number');
    const sum = validScores.reduce((acc, s) => acc + s, 0);
    const realOverallScore = Math.round(sum / totalQuestions);

    // Synchronize interview fields if needed
    let interviewUpdated = false;
    if (interview.score !== realOverallScore) {
      interview.score = realOverallScore;
      interviewUpdated = true;
    }
    if (interview.attemptedCount !== answers.length) {
      interview.attemptedCount = answers.length;
      interviewUpdated = true;
    }
    if (interviewUpdated) {
      await interview.save();
    }

    if (!result) {
      // Build dynamic strengths, weaknesses and recommendations from answers
      const isCommItem = (item) => /communication|verbal|articulate|tone|delivery|speech/i.test(item || '');
      const allStrengths = answers.flatMap((a) => {
        const list = a.strengths || [];
        return a.questionFormat === 'coding' ? list.filter((s) => !isCommItem(s)) : list;
      });
      const allWeaknesses = answers.flatMap((a) => {
        const list = a.weaknesses || [];
        return a.questionFormat === 'coding' ? list.filter((w) => !isCommItem(w)) : list;
      });

      const strengths = allStrengths.length > 0
        ? Array.from(new Set(allStrengths)).slice(0, 4)
        : ['Completed response recorded for analysis.', 'Active engagement during mock session.'];
      const weaknesses = allWeaknesses.length > 0
        ? Array.from(new Set(allWeaknesses)).slice(0, 4)
        : ['Review test cases, code syntax, and core problem-solving fundamentals.'];
      const recommendations = [
        `Practice additional ${interview.type === 'technical' ? (interview.subject || 'Java').toUpperCase() : 'HR'} interview questions.`,
        'Elaborate on edge case scenarios and test with sample inputs before submitting.',
      ];

      result = {
        interviewId: interview._id,
        userId: req.user._id,
        overallScore: realOverallScore,
        strengths,
        weaknesses,
        recommendations,
        questionsAttempted: answers.length,
        totalQuestions,
        evaluationStatus: 'completed',
      };
    } else {
      // If result exists but its overallScore or questionsAttempted is outdated
      let changed = false;
      if (result.overallScore !== realOverallScore) {
        result.overallScore = realOverallScore;
        changed = true;
      }
      if (result.questionsAttempted !== answers.length && answers.length > 0) {
        result.questionsAttempted = answers.length;
        changed = true;
      }
      if (result.totalQuestions !== totalQuestions) {
        result.totalQuestions = totalQuestions;
        changed = true;
      }
      if (changed) {
        await result.save();
      }
    }

    res.json({
      success: true,
      interview,
      answers,
      result,
    });
  } catch (error) {
    next(error);
  }
};
