import express from 'express';
import {
  createInterview,
  getUserInterviews,
  getInterviewById,
  submitAnswer,
  completeInterview,
  getQuestionSolution,
  deleteInterview,
  submitSpeechDelivery,
} from '../controllers/interviewController.js';
import { protect } from '../middleware/authMiddleware.js';

const router = express.Router();

router.route('/')
  .post(protect, createInterview)
  .get(protect, getUserInterviews);

router.route('/:id')
  .get(protect, getInterviewById)
  .delete(protect, deleteInterview);

router.route('/:id/solution')
  .get(protect, getQuestionSolution);

router.route('/:id/answers')
  .post(protect, submitAnswer);

router.route('/:id/complete')
  .post(protect, completeInterview);

router.route('/:id/speech-delivery')
  .post(protect, express.raw({ type: () => true, limit: '15mb' }), submitSpeechDelivery);

export default router;
