import express from 'express';
import {
  createInterview,
  getUserInterviews,
  getInterviewById,
  submitAnswer,
  completeInterview,
  getQuestionSolution,
  deleteInterview,
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

export default router;
