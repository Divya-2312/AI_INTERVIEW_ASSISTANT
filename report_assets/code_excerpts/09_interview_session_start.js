// backend/controllers/interviewController.js:14-46
export const createInterview = async (req, res, next) => {
  try {
    const { type, subject, difficulty, questionFormat, questionsCount } = req.body;
    const initialFormat = questionFormat || 'theory';

    // 1. Generate Question 1 from AI service
    const firstQuestion = await generateNextQuestion({
      interviewType: type,
      subject,
      difficulty,
      questionFormat: initialFormat,
      previousQuestions: [],
      previousAnswers: [],
      questionNumber: 1,
    });

    // 2. Persist Interview document in MongoDB
    const interview = await Interview.create({
      userId: req.user._id,
      type,
      subject: type === 'hr' ? 'N/A' : (subject || 'N/A'),
      difficulty: difficulty || 'medium',
      questionFormat: initialFormat,
      questionsCount: questionsCount ? Number(questionsCount) : 10,
      currentQuestion: 1,
      currentQuestionData: firstQuestion,
      status: 'in-progress',
    });

    res.status(201).json({
      success: true,
      interview,
      question: firstQuestion,
    });
  } catch (error) {
    next(error);
  }
};
