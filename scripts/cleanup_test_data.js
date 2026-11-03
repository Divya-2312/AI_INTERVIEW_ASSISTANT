#!/usr/bin/env node
/**
 * scripts/cleanup_test_data.js
 *
 * Cleanup script for repeated-questions test data.
 * Dry-run by default.
 *
 * Targets ONLY users whose email:
 *   - is exactly 'test_repeat@test.com'
 *   - or 'repeat_user_same@test.com'
 *   - or matches regex ^repeat_user_diff_[0-9]+@test\.com$
 *
 * Finds and counts referenced documents in:
 *   - users
 *   - interviews (userId)
 *   - answers (userId or interviewId)
 *   - results (userId or interviewId)
 *   - questions (any matching userId/interviewId if present)
 *   - analytics (any matching userId/interviewId if present)
 *
 * Deletes ONLY when executed with --confirm.
 */

import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BACKEND_DIR = path.resolve(__dirname, '../backend');
const backendRequire = createRequire(path.join(BACKEND_DIR, 'package.json'));

const mongoose = backendRequire('mongoose');
const dotenv = backendRequire('dotenv');

// Load environment variables without printing
dotenv.config({ path: path.join(BACKEND_DIR, '.env') });

// Import models
const { User } = await import(pathToFileURL(path.join(BACKEND_DIR, 'models/User.js')).href);
const { Interview } = await import(pathToFileURL(path.join(BACKEND_DIR, 'models/Interview.js')).href);
const { Answer } = await import(pathToFileURL(path.join(BACKEND_DIR, 'models/Answer.js')).href);
const { Result } = await import(pathToFileURL(path.join(BACKEND_DIR, 'models/Result.js')).href);
const { Question } = await import(pathToFileURL(path.join(BACKEND_DIR, 'models/Question.js')).href);

const TARGET_EXACT_EMAILS = ['test_repeat@test.com', 'repeat_user_same@test.com'];
const TARGET_EMAIL_REGEX = /^repeat_user_diff_[0-9]+@test\.com$/;

async function runCleanup() {
  const isConfirm = process.argv.includes('--confirm');
  const mongoUri = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/ai_interview_assistant';

  await mongoose.connect(mongoUri);

  try {
    // 1. Find target test users
    const allUsers = await User.find({}).select('_id email name createdAt').lean();
    const matchedUsers = allUsers.filter(u => {
      const email = (u.email || '').trim().toLowerCase();
      if (TARGET_EXACT_EMAILS.includes(email)) return true;
      return TARGET_EMAIL_REGEX.test(email);
    });

    const userIds = matchedUsers.map(u => u._id);

    // 2. Find interviews referencing these users
    const matchedInterviews = await Interview.find({ userId: { $in: userIds } }).select('_id userId type subject status createdAt').lean();
    const interviewIds = matchedInterviews.map(i => i._id);

    // 3. Find answers referencing these users or interviews
    const answerFilter = {
      $or: [
        { userId: { $in: userIds } },
        { interviewId: { $in: interviewIds } }
      ]
    };
    const matchedAnswersCount = userIds.length > 0 ? await Answer.countDocuments(answerFilter) : 0;

    // 4. Find results referencing these users or interviews
    const resultFilter = {
      $or: [
        { userId: { $in: userIds } },
        { interviewId: { $in: interviewIds } }
      ]
    };
    const matchedResultsCount = userIds.length > 0 ? await Result.countDocuments(resultFilter) : 0;

    // 5. Check questions collection for any reference to test users/interviews
    let matchedQuestionsCount = 0;
    try {
      matchedQuestionsCount = userIds.length > 0 ? await Question.countDocuments({
        $or: [
          { userId: { $in: userIds } },
          { interviewId: { $in: interviewIds } }
        ]
      }) : 0;
    } catch {
      matchedQuestionsCount = 0;
    }

    // 6. Check analytics collection if it exists
    let matchedAnalyticsCount = 0;
    const collections = await mongoose.connection.db.listCollections().toArray();
    const hasAnalytics = collections.some(c => c.name === 'analytics');
    if (hasAnalytics && userIds.length > 0) {
      matchedAnalyticsCount = await mongoose.connection.db.collection('analytics').countDocuments({
        $or: [
          { userId: { $in: userIds } },
          { interviewId: { $in: interviewIds } }
        ]
      });
    }

    console.log('='.repeat(75));
    if (isConfirm) {
      console.log('                 TEST DATA CLEANUP - CONFIRMED EXECUTION');
    } else {
      console.log('                    TEST DATA CLEANUP - DRY RUN');
      console.log('               (No data will be modified without --confirm)');
    }
    console.log('='.repeat(75));

    console.log('\n[Target Filter Criteria]');
    console.log(`- Exact emails : ${TARGET_EXACT_EMAILS.join(', ')}`);
    console.log(`- Regex pattern: ${TARGET_EMAIL_REGEX.toString()}`);

    console.log(`\n[Matched Users Found: ${matchedUsers.length}]`);
    if (matchedUsers.length === 0) {
      console.log('  No test users currently exist in database.');
    } else {
      matchedUsers.forEach((u, i) => {
        console.log(`  ${(i + 1).toString().padStart(2, ' ')}. Email: ${u.email.padEnd(35, ' ')} | ID: ${u._id}`);
      });
    }

    console.log('\n[Referenced Documents Count Per Collection]');
    console.log(`  • users       : ${matchedUsers.length}`);
    console.log(`  • interviews  : ${matchedInterviews.length}`);
    console.log(`  • answers     : ${matchedAnswersCount}`);
    console.log(`  • results     : ${matchedResultsCount}`);
    console.log(`  • questions   : ${matchedQuestionsCount} (catalog questions untouched)`);
    console.log(`  • analytics   : ${matchedAnalyticsCount} (collection ${hasAnalytics ? 'exists' : 'does not exist'})`);

    if (!isConfirm) {
      console.log('\n' + '-'.repeat(75));
      console.log('STATUS: Dry run completed successfully. ZERO documents were deleted.');
      console.log('To execute permanent deletion of these test documents, run:');
      console.log('  node scripts/cleanup_test_data.js --confirm');
      console.log('-'.repeat(75));
    } else {
      console.log('\n' + '-'.repeat(75));
      console.log('EXECUTING DELETION of matched test documents...');

      let deletedResults = 0;
      let deletedAnswers = 0;
      let deletedInterviews = 0;
      let deletedUsers = 0;

      if (userIds.length > 0) {
        const resDel = await Result.deleteMany(resultFilter);
        deletedResults = resDel.deletedCount || 0;

        const ansDel = await Answer.deleteMany(answerFilter);
        deletedAnswers = ansDel.deletedCount || 0;

        const intDel = await Interview.deleteMany({ _id: { $in: interviewIds } });
        deletedInterviews = intDel.deletedCount || 0;

        const usrDel = await User.deleteMany({ _id: { $in: userIds } });
        deletedUsers = usrDel.deletedCount || 0;
      }

      console.log(`Successfully deleted:`);
      console.log(`  • ${deletedResults} results`);
      console.log(`  • ${deletedAnswers} answers`);
      console.log(`  • ${deletedInterviews} interviews`);
      console.log(`  • ${deletedUsers} test users`);
      console.log('Cleanup complete. Real candidate data remains completely untouched.');
      console.log('-'.repeat(75));
    }
  } finally {
    await mongoose.disconnect();
  }
}

runCleanup().catch(err => {
  console.error('[Error] Cleanup failed:', err);
  process.exit(1);
});
