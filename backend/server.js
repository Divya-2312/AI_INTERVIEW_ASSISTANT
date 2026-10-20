import express from 'express';
import dotenv from 'dotenv';
import cors from 'cors';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import { connectDB } from './config/db.js';
import { notFound, errorHandler } from './middleware/errorMiddleware.js';

// Routes
import authRoutes from './routes/authRoutes.js';
import interviewRoutes from './routes/interviewRoutes.js';
import questionRoutes from './routes/questionRoutes.js';
import resultRoutes from './routes/resultRoutes.js';

dotenv.config();

const app = express();

// Security HTTP headers
app.use(helmet());

// Cookie parser for HTTP-only refresh tokens
app.use(cookieParser());

// Connect MongoDB
connectDB();

// CORS Configuration
const allowedOrigin = process.env.CLIENT_URL || 'http://localhost:3000';
app.use(
  cors({
    origin: [allowedOrigin, 'http://127.0.0.1:3001', 'http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:5173', 'http://localhost:5173'],
    credentials: true,
  })
);

// Express JSON middleware
app.use(express.json());

// Health Check Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: 'AI Interview Assistant backend is running',
    timestamp: new Date().toISOString(),
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/interviews', interviewRoutes);
app.use('/api/questions', questionRoutes);
app.use('/api/results', resultRoutes);

// Centralized Error Handling Middleware
app.use(notFound);
app.use(errorHandler);

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`[AI Interview Assistant Backend] Express server running on port ${PORT}`);
});
