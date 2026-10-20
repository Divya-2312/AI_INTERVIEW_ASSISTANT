import { interviewEngine } from '../services/interviewEngine.js';
import { aiService } from '../services/aiService.js';
import { Interview } from '../models/Interview.js';
import { Answer } from '../models/Answer.js';
import { Result } from '../models/Result.js';

function makeJavaStarterStub(code) {
  if (!code || typeof code !== 'string' || !code.trim()) {
    return 'public class Solution {\n    public int solve() {\n        // Write your code here\n        return 0;\n    }\n}';
  }

  const cleanCode = code.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
  const classMatch = cleanCode.match(/\b(?:public\s+)?class\s+([A-Za-z0-9_]+)/);
  const className = classMatch ? classMatch[1] : 'Solution';

  const methodRegex = /\b(?:public|protected|private)?\s*(static\s+)?([A-Za-z0-9_]+(?:<[A-Za-z0-9_,\s<>]+>)?(?:\[\s*\])*)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{/;
  const methodMatch = cleanCode.match(methodRegex);
  if (!methodMatch) {
    return `public class ${className} {\n    public int solve() {\n        // Write your code here\n        return 0;\n    }\n}`;
  }

  const isStatic = !!methodMatch[1];
  const returnType = methodMatch[2].trim();
  const methodName = methodMatch[3].trim();
  const params = methodMatch[4].trim();

  const fullSig = `${isStatic ? 'public static ' : 'public '}${returnType} ${methodName}(${params})`;

  const retClean = returnType.replace(/\s+/g, '');
  let defaultRet = '        return null;\n';
  if (retClean === 'void') {
    defaultRet = '';
  } else if (['int', 'long', 'short', 'byte'].includes(retClean)) {
    defaultRet = '        return 0;\n';
  } else if (['double', 'float'].includes(retClean)) {
    defaultRet = '        return 0.0;\n';
  } else if (retClean === 'boolean') {
    defaultRet = '        return false;\n';
  } else if (retClean === 'char') {
    defaultRet = "        return ' ';\n";
  } else if (retClean === 'String' || retClean === 'java.lang.String') {
    defaultRet = '        return "";\n';
  } else if (retClean === 'int[]') {
    defaultRet = '        return new int[0];\n';
  } else if (retClean === 'String[]') {
    defaultRet = '        return new String[0];\n';
  } else if (retClean.endsWith('[]')) {
    const base = retClean.slice(0, -2);
    defaultRet = `        return new ${base}[0];\n`;
  } else if (retClean.includes('List')) {
    defaultRet = '        return new java.util.ArrayList<>();\n';
  } else if (retClean.includes('Map')) {
    defaultRet = '        return new java.util.HashMap<>();\n';
  } else if (retClean.includes('Set')) {
    defaultRet = '        return new java.util.HashSet<>();\n';
  }

  return `public class ${className} {\n    ${fullSig} {\n        // Write your code here\n${defaultRet}    }\n}`;
}

function sanitizeQuestionForClient(q) {
  if (!q) return q;
  const copy = typeof q.toObject === 'function' ? q.toObject() : { ...q };
  delete copy.referenceSolution;
  delete copy.solution;
  delete copy._referenceQuery;
  if (copy.questionFormat === 'output_prediction') {
    delete copy.expectedOutput;
  }
  if (copy.questionFormat === 'coding' && (copy.language === 'java' || copy.subject === 'java' || !copy.language)) {
    if (copy.starterCode) {
      const hasLogic = /\b(for|while|do)\s*\(|\bif\s*\(|\bswitch\s*\(/.test(copy.starterCode) ||
        (copy.starterCode.split(';').length > 3);
      if (hasLogic) {
        copy.starterCode = makeJavaStarterStub(copy.starterCode);
      }
    }
  }
  return copy;
}

export const createInterview = async (req, res, next) => {
  try {
    const { type, subject, difficulty, questionFormat } = req.body;
    const result = await interviewEngine.startSession(req.user._id, type, subject, difficulty, questionFormat);

    const safeFirstQuestion = sanitizeQuestionForClient(result.question);
    const safeInterview = result.interview.toObject();
    if (safeInterview.currentQuestionData) {
      safeInterview.currentQuestionData = sanitizeQuestionForClient(safeInterview.currentQuestionData);
    }

    res.status(201).json({
      success: true,
      message: 'Interview session started',
      interview: safeInterview,
      firstQuestion: safeFirstQuestion,
    });
  } catch (error) {
    next(error);
  }
};

export const getUserInterviews = async (req, res, next) => {
  try {
    const interviews = await Interview.find({ userId: req.user._id }).sort({ createdAt: -1 });

    const populated = await Promise.all(
      interviews.map(async (interview) => {
        const interviewObj = interview.toObject();
        const answers = await Answer.find({ interviewId: interview._id });
        const totalQuestions = interview.questionsCount || 10;
        interviewObj.attemptedCount = answers.length;
        interviewObj.totalQuestions = totalQuestions;

        // Calculate overall score based on all questions (e.g., 1/10 attended with 100% is 10%)
        if (answers.length > 0) {
          const validScores = answers.map((a) => a.score).filter((s) => typeof s === 'number');
          const sum = validScores.reduce((a, b) => a + b, 0);
          const computedScore = Math.round(sum / totalQuestions);
          interviewObj.score = computedScore;
          if (interview.score !== computedScore || interview.attemptedCount !== answers.length) {
            interview.score = computedScore;
            interview.attemptedCount = answers.length;
            await interview.save();
          }
        }
        return interviewObj;
      })
    );

    res.json({ success: true, count: populated.length, interviews: populated });
  } catch (error) {
    next(error);
  }
};

export const getInterviewById = async (req, res, next) => {
  try {
    const interview = await Interview.findById(req.params.id);
    if (!interview) {
      res.status(404);
      throw new Error('Interview not found');
    }
    if (interview.userId.toString() !== req.user._id.toString()) {
      res.status(403);
      throw new Error('Access denied');
    }
    const answers = await Answer.find({ interviewId: interview._id });
    const totalQuestions = interview.questionsCount || 10;
    const interviewObj = interview.toObject();
    interviewObj.attemptedCount = answers.length;
    interviewObj.totalQuestions = totalQuestions;

    if (answers.length > 0) {
      const validScores = answers.map((a) => a.score).filter((s) => typeof s === 'number');
      const sum = validScores.reduce((a, b) => a + b, 0);
      interviewObj.score = Math.round(sum / totalQuestions);
    }

    if (interviewObj.currentQuestionData && interview.status === 'in-progress') {
      interviewObj.currentQuestionData = sanitizeQuestionForClient(interviewObj.currentQuestionData);
    }
    res.json({ success: true, interview: { ...interviewObj, answers } });
  } catch (error) {
    next(error);
  }
};

export const submitAnswer = async (req, res, next) => {
  try {
    const {
      questionId, questionText, answerText, expectedConcepts, questionFormat,
      expectedOutput, explanation, testCases, language, codeSnippet, title,
      hrDeliveryMetrics, schema, sampleData, referenceSolution
    } = req.body;

    if (!answerText || answerText.trim().length === 0) {
      res.status(400);
      throw new Error('Answer text cannot be empty');
    }

    const result = await interviewEngine.processAnswer(
      req.params.id,
      req.user._id,
      questionId,
      questionText,
      answerText,
      expectedConcepts,
      questionFormat,
      expectedOutput,
      explanation,
      testCases,
      language,
      codeSnippet,
      title,
      hrDeliveryMetrics,
      schema,
      sampleData,
      referenceSolution
    );

    const answerDoc = result.answerDoc || result.answer;
    const returnedEval = {
      ...(result.evaluation || {}),
      referenceSolution: answerDoc?.referenceSolution || null,
      questionId: answerDoc?.questionId || questionId || null,
      title: answerDoc?.title || title || null,
      questionText: answerDoc?.questionText || questionText || null,
    };

    res.status(200).json({
      success: true,
      evaluation: returnedEval,
      answer: answerDoc,
      nextQuestion: sanitizeQuestionForClient(result.nextQuestion),
      isFollowUp: result.isFollowUp,
      interviewStatus: result.interviewStatus,
    });
  } catch (error) {
    next(error);
  }
};

export const completeInterview = async (req, res, next) => {
  try {
    const interview = await Interview.findById(req.params.id);
    if (!interview) {
      res.status(404);
      throw new Error('Interview not found');
    }
    if (interview.userId.toString() !== req.user._id.toString()) {
      res.status(403);
      throw new Error('Unauthorized');
    }

    interview.status = 'completed';
    interview.completedAt = new Date();

    const answers = await Answer.find({ interviewId: interview._id });
    const totalQuestions = interview.questionsCount || 10;
    interview.attemptedCount = answers.length;

    const validScores = answers.map((a) => a.score).filter((s) => typeof s === 'number');
    const sum = validScores.reduce((acc, curr) => acc + curr, 0);
    const overallScore = Math.round(sum / totalQuestions);

    interview.score = overallScore;
    interview.currentQuestionData = null;
    await interview.save();

    // Create or update aggregate Result model
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
      : ['Continue practicing core concepts, edge cases, and problem-solving accuracy.'];
    const recommendations = [
      `Continue practicing core ${interview.type === 'technical' ? (interview.subject || 'Java').toUpperCase() : 'HR'} interview questions.`,
      'Elaborate on edge case scenarios and test with sample inputs before submitting.',
    ];

    let result = await Result.findOne({ interviewId: interview._id });
    if (!result) {
      result = await Result.create({
        interviewId: interview._id,
        userId: req.user._id,
        overallScore: avgScore,
        strengths,
        weaknesses,
        recommendations,
        questionsAttempted: answers.length,
        totalQuestions: interview.questionsCount || 10,
      });
    } else {
      result.overallScore = avgScore;
      result.questionsAttempted = answers.length;
      result.totalQuestions = interview.questionsCount || 10;
      result.strengths = strengths;
      result.weaknesses = weaknesses;
      result.recommendations = recommendations;
      await result.save();
    }

    res.json({ success: true, message: 'Interview completed', interview, result });
  } catch (error) {
    next(error);
  }
};

export const getQuestionSolution = async (req, res, next) => {
  try {
    const interview = await Interview.findById(req.params.id);
    if (!interview) {
      return res.status(404).json({ success: false, error: 'Interview not found' });
    }
    if (interview.userId.toString() !== req.user._id.toString()) {
      return res.status(403).json({ success: false, error: 'Access denied' });
    }

    const type = (interview.type || '').toLowerCase();
    const qData = interview.currentQuestionData || {};
    const format = (qData.questionFormat || interview.questionFormat || '').toLowerCase();
    const subject = (interview.subject || '').toLowerCase();

    // Solutions are not available for HR track
    if (type === 'hr') {
      return res.status(400).json({
        success: false,
        error: 'Solutions are not available for HR questions',
      });
    }

    // Check submission state: Solution is ONLY available after submission of answer
    const requestedKey = req.query.questionKey;
    const isCompleted = interview.status === 'completed';

    // Find any answers submitted for this interview
    const answers = await Answer.find({ interviewId: interview._id }).sort({ createdAt: -1 });

    // Find if the specific requested question has already been answered
    let matchingAnswer = null;
    if (requestedKey) {
      matchingAnswer = answers.find((a) => {
        if (a._id && a._id.toString() === requestedKey) return true;
        if (a.questionId && a.questionId === requestedKey) return true;
        if (a.questionFormat === 'output_prediction') {
          return (
            (a.codeSnippet && a.codeSnippet.trim() === requestedKey.trim()) ||
            (a.questionText && a.questionText === requestedKey)
          );
        }
        return (
          (a.questionText && a.questionText === requestedKey) ||
          (a.title && a.title === requestedKey) ||
          (a.codeSnippet && a.codeSnippet === requestedKey)
        );
      });
    }

    // In-progress enforcement: Candidate CANNOT view a solution before answering
    if (!isCompleted) {
      if (requestedKey) {
        if (!matchingAnswer) {
          return res.status(403).json({
            success: false,
            code: 'SOLUTION_LOCKED',
            message: 'Solution is locked until you submit your answer for this question.',
          });
        }
      } else {
        // No key passed - check if current question has been answered
        const currentAnswered = answers.find((a) => {
          if (qData.questionId && a.questionId === qData.questionId) return true;
          if (format === 'output_prediction' || a.questionFormat === 'output_prediction') {
            return qData.codeSnippet && a.codeSnippet && qData.codeSnippet.trim() === a.codeSnippet.trim();
          }
          return (
            (qData.questionText && a.questionText === qData.questionText) ||
            (qData.title && a.title === qData.title)
          );
        });

        if (!currentAnswered) {
          return res.status(403).json({
            success: false,
            code: 'SOLUTION_LOCKED',
            message: 'Solution is locked until you submit your answer for this question.',
          });
        }
        matchingAnswer = currentAnswered;
      }
    } else {
      // Completed interview: default to latest answer if no key match
      if (!matchingAnswer && answers.length > 0) {
        matchingAnswer = answers[0];
      }
    }

    const targetFormat = matchingAnswer?.questionFormat || format;
    const language = (qData.language || matchingAnswer?.language || (subject === 'dbms' ? 'sql' : 'java')).toLowerCase();

    let solution = null;
    if (targetFormat === 'coding') {
      const isInvalidSql = (s) => typeof s === 'string' && (/select\s+\*\s+from\s+records/i.test(s) || /\bfrom\s+records\b/i.test(s));

      const candidates = [
        matchingAnswer?.referenceSolution,
        matchingAnswer?.correctedQuery,
        matchingAnswer?.correctedCode,
        qData.referenceSolution,
        qData.solution,
        qData._referenceQuery,
      ].filter(Boolean);

      solution = candidates.find(s => !isInvalidSql(s)) || null;

      if (!solution && matchingAnswer) {
        if (matchingAnswer.score >= 80 || (typeof matchingAnswer.passedCount === 'number' && matchingAnswer.passedCount === matchingAnswer.totalCount && matchingAnswer.totalCount > 0)) {
          solution = matchingAnswer.codeSnippet || matchingAnswer.answerText;
        } else if (matchingAnswer.codeSnippet || matchingAnswer.answerText) {
          solution = matchingAnswer.codeSnippet || matchingAnswer.answerText;
        }
      }
    } else if (targetFormat === 'output_prediction') {
      solution =
        matchingAnswer?.expectedOutput ||
        qData.expectedOutput ||
        qData.correctAnswer ||
        null;
    } else if (targetFormat === 'theory') {
      solution =
        matchingAnswer?.referenceSolution ||
        matchingAnswer?.idealAnswer ||
        qData.idealAnswer ||
        qData.referenceSolution ||
        null;

      if (!solution) {
        const concepts = qData.expectedConcepts || matchingAnswer?.expectedConcepts || [];
        const explanation =
          matchingAnswer?.improvementSuggestion ||
          matchingAnswer?.feedback ||
          qData.explanation ||
          '';
        if (concepts.length > 0 || explanation) {
          solution = `Key Expected Concepts:\n${concepts.map((c) => `• ${c}`).join('\n')}${
            explanation ? `\n\nReference Explanation:\n${explanation}` : ''
          }`;
        }
      }
    }

    return res.status(200).json({
      success: true,
      format: targetFormat,
      language,
      solution: solution || null,
      message: solution ? undefined : 'Solution not available for this question',
    });
  } catch (error) {
    next(error);
  }
};

export const deleteInterview = async (req, res, next) => {
  try {
    const interview = await Interview.findById(req.params.id);
    if (!interview) {
      return res.status(404).json({ success: false, error: 'Interview not found' });
    }
    if (interview.userId.toString() !== req.user._id.toString()) {
      return res.status(403).json({ success: false, error: 'Access denied: You can only delete your own interviews' });
    }

    // Cascade delete: remove associated answers and result
    await Answer.deleteMany({ interviewId: interview._id });
    await Result.deleteMany({ interviewId: interview._id });
    await interview.deleteOne();

    res.json({
      success: true,
      message: 'Interview session and associated records deleted successfully',
      deletedId: req.params.id,
    });
  } catch (error) {
    next(error);
  }
};

