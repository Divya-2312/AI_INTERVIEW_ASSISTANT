import mongoose from 'mongoose';

export const connectDB = async () => {
  try {
    const conn = await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant', {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
    console.log(`[MongoDB] Database connected successfully: ${conn.connection.host}`);
  } catch (error) {
    console.error(`[MongoDB] Database connection error: ${error.message}`);
    // Non-fatal warning log for development environments where local mongo is optional
    console.warn('[MongoDB] Server running, but MongoDB connection failed. Ensure MONGODB_URI is reachable.');
  }
};
