/**
 * Pure function for candidate performance calculation.
 * Follows the canonical scoring formulas:
 * - sessionScore = round-half-up(sum of question scores / questionsCount), unanswered = 0
 * - moduleScores = mean question score per question type present
 * - parameterProfile = mean of accuracy, correctness, relevance, concept_coverage over answers that have them
 * - level bands: 80-100 Excellent, 65-79 Good, 50-64 Average, 0-49 Needs improvement (design choice of this application)
 * - passMark: 50
 */

export function roundHalfUp(val) {
  if (typeof val !== 'number' || isNaN(val)) return 0;
  return Math.floor(val + 0.5);
}

export function calculateLevel(score) {
  const s = Math.max(0, Math.min(100, roundHalfUp(score)));
  if (s >= 80) return 'Excellent';
  if (s >= 65) return 'Good';
  if (s >= 50) return 'Average';
  return 'Needs improvement';
}

export function generatePerformanceReport(interview, answers = []) {
  const questionsCount = interview?.questionsCount || 10;
  const answeredList = (answers || []).filter((a) => a && typeof a.score === 'number');
  
  // 1. Session Score (unanswered questions count as 0)
  const sumScores = answeredList.reduce((acc, a) => acc + a.score, 0);
  const sessionScore = roundHalfUp(sumScores / (questionsCount || 10));

  // 2. Module Scores (mean question score per question type present)
  const moduleMap = {};
  for (const a of answeredList) {
    const mod = a.questionFormat || a.questionType || (a.language === 'sql' ? 'sql' : 'theory');
    if (!moduleMap[mod]) {
      moduleMap[mod] = { sum: 0, count: 0 };
    }
    moduleMap[mod].sum += a.score;
    moduleMap[mod].count += 1;
  }
  const moduleScores = {};
  for (const [mod, data] of Object.entries(moduleMap)) {
    moduleScores[mod] = data.count > 0 ? roundHalfUp(data.sum / data.count) : 0;
  }

  // 3. Parameter Profile (accuracy, correctness, relevance, concept_coverage)
  const paramAccum = {
    accuracy: { sum: 0, count: 0 },
    correctness: { sum: 0, count: 0 },
    relevance: { sum: 0, count: 0 },
    concept_coverage: { sum: 0, count: 0 },
  };

  for (const a of answeredList) {
    const fp = a.formula?.parameters;
    const extract = (key, legacyKey) => {
      if (fp && typeof fp[key] === 'number') return fp[key];
      const val = a[legacyKey || key];
      if (typeof val === 'number') {
        return val <= 1.0 && val > 0 ? Math.round(val * 100) : val;
      }
      return null;
    };

    const acc = extract('accuracy', 'accuracy');
    const cor = extract('correctness', 'correctness');
    const rel = extract('relevance', 'relevance');
    const cov = extract('concept_coverage', 'conceptCoverage') ?? extract('concept_coverage', 'concept_coverage');

    if (acc !== null) { paramAccum.accuracy.sum += acc; paramAccum.accuracy.count += 1; }
    if (cor !== null) { paramAccum.correctness.sum += cor; paramAccum.correctness.count += 1; }
    if (rel !== null) { paramAccum.relevance.sum += rel; paramAccum.relevance.count += 1; }
    if (cov !== null) { paramAccum.concept_coverage.sum += cov; paramAccum.concept_coverage.count += 1; }
  }

  const parameterProfile = {
    accuracy: paramAccum.accuracy.count > 0 ? roundHalfUp(paramAccum.accuracy.sum / paramAccum.accuracy.count) : null,
    correctness: paramAccum.correctness.count > 0 ? roundHalfUp(paramAccum.correctness.sum / paramAccum.correctness.count) : null,
    relevance: paramAccum.relevance.count > 0 ? roundHalfUp(paramAccum.relevance.sum / paramAccum.relevance.count) : null,
    concept_coverage: paramAccum.concept_coverage.count > 0 ? roundHalfUp(paramAccum.concept_coverage.sum / paramAccum.concept_coverage.count) : null,
  };

  // Determine weakest and strongest area among parameters present
  const presentParams = Object.entries(parameterProfile).filter(([_, v]) => typeof v === 'number');
  let strongestArea = null;
  let weakestArea = null;

  if (presentParams.length > 0) {
    presentParams.sort((a, b) => b[1] - a[1]);
    const labels = {
      accuracy: 'Accuracy',
      correctness: 'Correctness',
      relevance: 'Relevance',
      concept_coverage: 'Concept Coverage',
    };
    strongestArea = labels[presentParams[0][0]] || presentParams[0][0];
    weakestArea = labels[presentParams[presentParams.length - 1][0]] || presentParams[presentParams.length - 1][0];
  }

  // 4. Level & Counts
  const level = calculateLevel(sessionScore);
  const correctCount = answeredList.filter((a) => a.score >= 50).length;

  return {
    sessionScore,
    moduleScores,
    parameterProfile: {
      ...parameterProfile,
      strongestArea,
      weakestArea,
    },
    level,
    levelBandsNote: 'Score bands (80-100 Excellent, 65-79 Good, 50-64 Average, 0-49 Needs improvement) are a design choice of this application.',
    passMark: 50,
    counts: {
      totalQuestions: questionsCount,
      attempted: (answers || []).length,
      answered: answeredList.length,
      correct: correctCount,
    },
  };
}
