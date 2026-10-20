import { Question } from '../models/Question.js';

// NOTE: This endpoint only reads from MongoDB (the `Question` collection).
// There is no hardcoded static question bank here -- the adaptive
// interview flow (see interviewEngine.js / aiService.js) generates every
// theory and "predict the output" question live from the fine-tuned LLaMA
// model, not from a database. This route is a simple browse/listing
// endpoint for whatever questions have actually been seeded into Mongo, if
// any; it intentionally returns an empty list rather than fabricating
// canned questions when the collection is empty.

// @desc    Get questions by query filter (type, subject, difficulty)
// @route   GET /api/questions
// @access  Public / Private
export const getQuestions = async (req, res, next) => {
  try {
    const { type, subject, difficulty } = req.query;

    let filter = {};
    if (type) {
      filter.type = type.toLowerCase();
    }
    if (subject && filter.type === 'technical') {
      filter.subject = subject.toLowerCase();
    }
    if (difficulty) {
      filter.difficulty = difficulty.toLowerCase();
    }

    const questions = await Question.find(filter);

    res.json({
      success: true,
      count: questions.length,
      questions,
    });
  } catch (error) {
    next(error);
  }
};
