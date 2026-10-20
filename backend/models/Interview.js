import mongoose from 'mongoose';

const interviewSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    type: {
      type: String,
      enum: ['technical', 'hr'],
      required: true,
    },
    subject: {
      type: String,
      default: 'N/A',
    },
    difficulty: {
      type: String,
      enum: ['easy', 'medium', 'hard'],
      default: 'medium',
    },
    // 'theory' = explain-a-concept questions. 'output_prediction' = candidate
    // is shown a code snippet and must state its exact output. 'coding' =
    // candidate is given a coding problem + test cases and must submit code,
    // generated and graded by the fine-tuned LLaMA model.
    questionFormat: {
      type: String,
      enum: ['theory', 'output_prediction', 'coding'],
      default: 'theory',
    },
    // The full AI-generated question object currently awaiting an answer
    // (questionText, codeSnippet, expectedOutput, expectedConcepts, etc.),
    // persisted so refreshing/resuming the page shows the exact same
    // question instead of falling back to a generic static question bank.
    currentQuestionData: {
      type: mongoose.Schema.Types.Mixed,
      default: null,
    },
    status: {
      type: String,
      enum: ['in-progress', 'completed', 'abandoned'],
      default: 'in-progress',
    },
    currentQuestion: {
      type: Number,
      default: 1,
    },
    questionsCount: {
      type: Number,
      default: 10,
    },
    attemptedCount: {
      type: Number,
      default: 0,
    },
    followUpCount: {
      type: Number,
      default: 0,
    },
    score: {
      type: Number,
      default: null,
    },
    startedAt: {
      type: Date,
      default: Date.now,
    },
    completedAt: {
      type: Date,
    },
  },
  {
    timestamps: true,
  }
);

export const Interview = mongoose.model('Interview', interviewSchema);
