import mongoose from 'mongoose';

const answerSchema = new mongoose.Schema(
  {
    interviewId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Interview',
      required: true,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    questionId: {
      type: String,
      required: true,
    },
    questionText: {
      type: String,
      required: true,
    },
    // For output_prediction: the actual code snippet the candidate was
    // shown. questionText for this format is always the same fixed
    // instruction sentence ("What is the exact output..."), so it cannot be
    // used on its own to tell two questions apart -- codeSnippet is the
    // real distinguishing content and is what duplicate-detection (both
    // here and in the AI service) is keyed on for this format.
    codeSnippet: {
      type: String,
      default: null,
    },
    // For coding: the short problem title (e.g. "Factorial of a Number"),
    // carried through so question-history signatures can include it.
    title: {
      type: String,
      default: null,
    },
    answerText: {
      type: String,
      required: true,
    },
    score: {
      type: Number,
      default: null,
    },
    conceptCoverage: {
      type: Number,
      default: null,
    },
    correctness: {
      type: Number,
      default: null,
    },
    relevance: {
      type: Number,
      default: null,
    },
    communication: {
      type: Number,
      default: null,
    },
    // HR only: 4th factor of the HR average (correctness, relevance, accuracy, communication).
    accuracy: {
      type: Number,
      default: null,
    },
    isIrrelevant: {
      type: Boolean,
      default: false,
    },
    feedback: {
      type: String,
      default: null,
    },
    strengths: [String],
    weaknesses: [String],
    coveredConcepts: [String],
    partiallyCoveredConcepts: [String],
    missingConcepts: [String],
    improvementSuggestion: {
      type: String,
      default: null,
    },
    // HR only: approximate speech-delivery findings (fillers, pauses, repetition).
    deliveryMetrics: {
      type: mongoose.Schema.Types.Mixed,
      default: undefined,
    },
    // Plain-English explanation of why the score isn't 100%.
    scoreReason: {
      type: String,
      default: null,
    },
    // For output_prediction questions: numbered walk-through of how the
    // correct output was derived from the code, shown after grading. Also
    // reused for "coding" to show the reference approach after grading.
    stepByStepExplanation: {
      type: String,
      default: null,
    },
    // For "coding" questions: per-test-case pass/fail breakdown returned
    // by the AI grading service.
    // For "coding" questions where at least one test case failed: the
    // candidate's own code with the minimum fix applied, plus what changed.
    correctedCode: {
      type: String,
      default: null,
    },
    correctedQuery: {
  type: String,
  default: null,
},
    correctionSummary: {
      type: String,
      default: null,
    },
    testCaseResults: {
      type: [mongoose.Schema.Types.Mixed],
      default: undefined,
    },
    passedCount: {
      type: Number,
      default: null,
    },
    totalCount: {
      type: Number,
      default: null,
    },
    judgeMode: {
      type: String,
      default: null,
    },
    whyNot100: {
      type: String,
      default: null,
    },
    compileError: {
      type: String,
      default: null,
    },
    timeComplexity: {
      type: String,
      default: null,
    },
    spaceComplexity: {
      type: String,
      default: null,
    },
    timeComplexityExplanation: {
      type: String,
      default: null,
    },
    referenceSolution: {
      type: String,
      default: null,
    },
    expectedOutput: {
      type: String,
      default: null,
    },
    questionFormat: {
      type: String,
      enum: ['theory', 'output_prediction', 'coding'],
      default: 'theory',
    },
    isFollowUp: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
  }
);

export const Answer = mongoose.model('Answer', answerSchema);
