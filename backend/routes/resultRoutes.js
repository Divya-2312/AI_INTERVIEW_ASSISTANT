import express from 'express';
import { getInterviewResult } from '../controllers/resultController.js';
import { protect } from '../middleware/authMiddleware.js';

const router = express.Router();

router.get('/:interviewId', protect, getInterviewResult);

export default router;
