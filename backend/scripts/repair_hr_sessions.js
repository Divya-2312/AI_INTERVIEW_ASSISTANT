/**
 * One-time repair script to fix existing interviews where attemptedCount > questionsCount.
 * 
 * Rules:
 * 1. Find all interviews where attemptedCount > questionsCount.
 * 2. Log every planned modification before writing to the database.
 * 3. Cap attemptedCount to questionsCount (keeps all data/answers intact).
 * 4. Cap corresponding Result questionsAttempted to totalQuestions.
 * 5. Backfill questionIndex on legacy Answer documents and build unique compound index (interviewId, questionIndex).
 */

import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load env without modifying or displaying any .env file
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

async function repairSessions() {
  console.log('Connecting to database...');
  await mongoose.connect(MONGODB_URI);
  console.log('Connected to MongoDB.');

  const db = mongoose.connection.db;
  const interviewsCollection = db.collection('interviews');
  const resultsCollection = db.collection('results');
  const answersCollection = db.collection('answers');

  // 1. Find all interviews where attemptedCount > questionsCount
  const badInterviews = await interviewsCollection
    .find({
      $expr: {
        $gt: [
          '$attemptedCount',
          { $ifNull: ['$questionsCount', 10] },
        ],
      },
    })
    .toArray();

  console.log(`\n=== PLAN: Found ${badInterviews.length} interviews to repair ===`);
  if (badInterviews.length === 0) {
    console.log('No inconsistent interviews found. All interviews have attemptedCount <= questionsCount.');
  } else {
    for (const it of badInterviews) {
      const qCount = it.questionsCount || 10;
      console.log(
        `[PLAN] Interview ID: ${it._id} | Type: ${it.type} | Current attemptedCount: ${it.attemptedCount} -> Cap to: ${qCount}`
      );
    }
  }

  // 2. Find all results where questionsAttempted > totalQuestions
  const badResults = await resultsCollection
    .find({
      $expr: {
        $gt: [
          '$questionsAttempted',
          { $ifNull: ['$totalQuestions', 10] },
        ],
      },
    })
    .toArray();

  console.log(`\n=== PLAN: Found ${badResults.length} results to repair ===`);
  for (const res of badResults) {
    const tCount = res.totalQuestions || 10;
    console.log(
      `[PLAN] Result ID: ${res._id} | Interview ID: ${res.interviewId} | Current questionsAttempted: ${res.questionsAttempted} -> Cap to: ${tCount}`
    );
  }

  // 3. Find all interviews with unindexed or duplicated answer slots
  const allAnswers = await answersCollection.find({}).sort({ createdAt: 1, _id: 1 }).toArray();
  const answersByInterview = new Map();
  for (const ans of allAnswers) {
    const iId = String(ans.interviewId);
    if (!answersByInterview.has(iId)) answersByInterview.set(iId, []);
    answersByInterview.get(iId).push(ans);
  }

  const answersToReindex = [];
  for (const [iId, ansList] of answersByInterview.entries()) {
    const seenIndices = new Set();
    let hasConflictOrMissing = false;
    for (const a of ansList) {
      if (typeof a.questionIndex !== 'number' || seenIndices.has(a.questionIndex)) {
        hasConflictOrMissing = true;
        break;
      }
      seenIndices.add(a.questionIndex);
    }
    if (hasConflictOrMissing) {
      ansList.forEach((a, idx) => {
        answersToReindex.push({ _id: a._id, interviewId: iId, oldIndex: a.questionIndex, newIndex: idx });
      });
    }
  }

  console.log(`\n=== PLAN: Found ${answersToReindex.length} answers to assign distinct questionIndex ===`);
  for (const a of answersToReindex.slice(0, 15)) {
    console.log(`[PLAN] Answer ID: ${a._id} (Interview: ${a.interviewId}) -> Set questionIndex: ${a.newIndex}`);
  }
  if (answersToReindex.length > 15) {
    console.log(`... and ${answersToReindex.length - 15} more.`);
  }

  console.log('\nApplying planned repairs...');

  // Apply interview capping
  let interviewsRepaired = 0;
  for (const it of badInterviews) {
    const qCount = it.questionsCount || 10;
    const res = await interviewsCollection.updateOne(
      { _id: it._id },
      { $set: { attemptedCount: qCount } }
    );
    if (res.modifiedCount > 0) {
      interviewsRepaired++;
      console.log(`[DONE] Repaired Interview ${it._id}: attemptedCount set to ${qCount}`);
    }
  }

  // Apply result capping
  let resultsRepaired = 0;
  for (const r of badResults) {
    const tCount = r.totalQuestions || 10;
    const res = await resultsCollection.updateOne(
      { _id: r._id },
      { $set: { questionsAttempted: tCount } }
    );
    if (res.modifiedCount > 0) {
      resultsRepaired++;
      console.log(`[DONE] Repaired Result ${r._id}: questionsAttempted set to ${tCount}`);
    }
  }

  // Apply answer reindexing
  let answersUpdated = 0;
  for (const a of answersToReindex) {
    const res = await answersCollection.updateOne(
      { _id: a._id },
      { $set: { questionIndex: a.newIndex } }
    );
    if (res.modifiedCount > 0) {
      answersUpdated++;
    }
  }
  console.log(`[DONE] Assigned questionIndex to ${answersUpdated} legacy answers.`);

  // Build unique compound index (interviewId, questionIndex)
  console.log('Ensuring compound unique index on answers(interviewId, questionIndex)...');
  try {
    await answersCollection.createIndex({ interviewId: 1, questionIndex: 1 }, { unique: true });
    console.log('[DONE] Unique index { interviewId: 1, questionIndex: 1 } is now active.');
  } catch (idxErr) {
    console.error('[WARN] Could not create unique index:', idxErr.message);
  }

  console.log(`\n=== REPAIR COMPLETE ===`);
  console.log(`Interviews repaired: ${interviewsRepaired}/${badInterviews.length}`);
  console.log(`Results repaired: ${resultsRepaired}/${badResults.length}`);
  console.log(`Answers indexed: ${answersUpdated}/${answersToReindex.length}`);

  await mongoose.disconnect();
  console.log('Disconnected from MongoDB.');
}

repairSessions().catch((err) => {
  console.error('Error during repair:', err);
  process.exit(1);
});
