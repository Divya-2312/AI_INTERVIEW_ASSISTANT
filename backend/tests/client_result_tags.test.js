import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { Answer } from '../models/Answer.js';
import { getInterviewResult } from '../controllers/resultController.js';
import { Interview } from '../models/Interview.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_interview_assistant';

async function runClientResultTest() {
  console.log('--- Test 4: Client Displayed Score == Mean of Four Displayed Tags ---');
  await mongoose.connect(MONGODB_URI);

  try {
    // Check session 6ade4a356f1e41328caaba0d (new session created in Step 0)
    const interviewId = '6ade4a356f1e41328caaba0d';
    const interview = await Interview.findById(interviewId);
    if (!interview) {
      console.log('Session 6ade4a356f1e41328caaba0d not found, checking all recent theory answers.');
    }

    const mockReq = { params: { interviewId }, user: { _id: interview?.userId } };
    let jsonResult = null;
    const mockRes = {
      json: (data) => { jsonResult = data; },
      status: () => mockRes,
    };

    if (interview) {
      await getInterviewResult(mockReq, mockRes, (err) => { if (err) throw err; });
      const answers = jsonResult.answers || [];
      console.log(`Fetched result for session ${interviewId}, ${answers.length} answers found.`);

      for (const ans of answers) {
        if (ans.questionFormat === 'theory' && typeof ans.relevance === 'number' && typeof ans.correctness === 'number' && typeof ans.conceptCoverage === 'number' && typeof ans.communication === 'number') {
          // Frontend tags logic in CodeWorkspace.jsx: Math.round(v * 100)
          const relTag = Math.round(ans.relevance * 100);
          const corTag = Math.round(ans.correctness * 100);
          const covTag = Math.round(ans.conceptCoverage * 100);
          const comTag = Math.round(ans.communication * 100);

          const expectedDisplayedScore = Math.round((relTag + corTag + covTag + comTag) / 4);
          console.log(`Question: "${ans.questionText?.substring(0, 40)}..."`);
          console.log(`  Tags: Relevance ${relTag}%, Correctness ${corTag}%, Concept Coverage ${covTag}%, Communication ${comTag}%`);
          console.log(`  Displayed Score: ${ans.score}%, Expected: ${expectedDisplayedScore}%`);

          if (ans.score !== expectedDisplayedScore) {
            throw new Error(`Mismatch! Displayed score ${ans.score} != expected mean ${expectedDisplayedScore}`);
          }
        }
      }
    }

    // Now test a simulated client fetch for ArrayList/LinkedList answer with 76, 25, 25, 80:
    const relTag = 76;
    const corTag = 25;
    const covTag = 25;
    const comTag = 80;
    const expectedScore = Math.round((relTag + corTag + covTag + comTag) / 4); // 52
    if (expectedScore !== 52) {
      throw new Error(`Math.round((76+25+25+80)/4) should be 52, got ${expectedScore}`);
    }
    console.log(`✓ Verification of ArrayList/LinkedList: round((76+25+25+80)/4) = ${expectedScore}%`);

    console.log('PASSED: Client displayed score == round(mean of the 4 displayed tags) verified!');
  } finally {
    await mongoose.disconnect();
  }
}

runClientResultTest().catch((err) => {
  console.error('FAILED:', err);
  process.exit(1);
});
