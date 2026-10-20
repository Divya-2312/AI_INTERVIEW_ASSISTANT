import mongoose from 'mongoose';

const questionSchema = new mongoose.Schema(
  {
    questionText: {
      type: String,
      required: [true, 'Question text is required'],
    },
    type: {
      type: String,
      enum: ['technical', 'hr'],
      required: true,
    },
    subject: {
      type: String,
      enum: ['java', 'dbms', 'general', 'N/A'],
      default: 'N/A',
    },
    difficulty: {
      type: String,
      enum: ['easy', 'medium', 'hard'],
      default: 'medium',
    },
    category: {
      type: String,
      default: 'General',
    },
    questionType: {
      type: String,
      enum: ['normal', 'follow_up'],
      default: 'normal',
    },
    questionFormat: {
      type: String,
      enum: ['theory', 'output_prediction'],
      default: 'theory',
    },
    codeSnippet: {
      type: String,
      default: null,
    },
    expectedOutput: {
      type: String,
      default: null,
    },
    expectedConcepts: [
      {
        type: String,
      },
    ],
  },
  {
    timestamps: true,
  }
);

export const Question = mongoose.model('Question', questionSchema);
