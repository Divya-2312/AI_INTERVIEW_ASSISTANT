export const notFound = (req, res, next) => {
  const error = new Error(`Not Found - ${req.originalUrl}`);
  res.status(404);
  next(error);
};

export const errorHandler = (err, req, res, next) => {
  const statusCode = res.statusCode === 200 ? 500 : res.statusCode;
  res.status(statusCode).json({
    success: false,
    message: err.message || 'Internal Server Error',
    // Set only when an answer was successfully graded but a later step
    // (e.g. generating the next question) failed -- lets the frontend show
    // the score the candidate actually earned instead of losing it, even
    // though the request as a whole errored. See interviewEngine.processAnswer.
    evaluation: err.evaluationForDisplay || undefined,
    stack: process.env.NODE_ENV === 'production' ? null : err.stack,
  });
};
