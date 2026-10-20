import mongoose from 'mongoose';

async function patchDb(dbUri) {
  console.log('Connecting to', dbUri);
  const conn = await mongoose.createConnection(dbUri).asPromise();
  const interviewsColl = conn.collection('interviews');
  const answersColl = conn.collection('answers');
  const resultsColl = conn.collection('results');

  const interviews = await interviewsColl.find({}).toArray();
  console.log('Total interviews:', interviews.length);

  for (const interview of interviews) {
    const totalQuestions = interview.questionsCount || 10;
    const answers = await answersColl.find({ interviewId: interview._id }).toArray();
    const validScores = answers.map(a => a.score).filter(s => typeof s === 'number');
    const sum = validScores.reduce((a, b) => a + b, 0);
    const finalScore = answers.length > 0
      ? Math.round(sum / totalQuestions)
      : null;

    const attemptedCount = answers.length;

    const updateObj = { attemptedCount: attemptedCount, questionsCount: totalQuestions };
    if (finalScore !== null) {
      updateObj.score = finalScore;
    }

    await interviewsColl.updateOne(
      { _id: interview._id },
      { $set: updateObj }
    );

    if (answers.length > 0 && finalScore !== null) {
      const existingResult = await resultsColl.findOne({ interviewId: interview._id });
      if (!existingResult) {
        await resultsColl.insertOne({
          interviewId: interview._id,
          userId: interview.userId,
          overallScore: finalScore,
          strengths: ['Completed response recorded for analysis.', 'Active engagement during mock session.'],
          weaknesses: ['Review edge cases, code accuracy, and syntax fundamentals.'],
          recommendations: ['Practice additional questions and test code before submitting.'],
          questionsAttempted: attemptedCount,
          totalQuestions: interview.questionsCount || 10,
          createdAt: new Date(),
          updatedAt: new Date()
        });
        console.log(`Interview ${interview._id}: Created Result document with score ${finalScore}, attempted ${attemptedCount}`);
      } else {
        await resultsColl.updateOne(
          { _id: existingResult._id },
          {
            $set: {
              overallScore: finalScore,
              questionsAttempted: attemptedCount,
              totalQuestions: interview.questionsCount || 10
            }
          }
        );
        console.log(`Interview ${interview._id}: Updated Result document with score ${finalScore}, attempted ${attemptedCount}`);
      }
    }
  }

  await conn.close();
  console.log('Done patching', dbUri);
}

async function main() {
  await patchDb('mongodb://localhost:27017/ai_interview_assistant');
  await patchDb('mongodb://localhost:27017/mockmate_ai');
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
