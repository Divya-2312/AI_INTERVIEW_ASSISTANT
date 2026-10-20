import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { ScoreCard } from '../components/ScoreCard';
import { ScoreBreakdown, SolutionReveal, SolutionViewer } from '../components/CodeWorkspace';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { CheckCircle2, AlertTriangle, Lightbulb, PlayCircle, LayoutDashboard, Sparkles, Clock } from 'lucide-react';

export const Result = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const res = await apiService.getResult(id);
        if (res && res.interview) {
          setData(res);
        } else {
          const direct = await apiService.getInterviewById(id);
          setData({ interview: direct, answers: direct.answers || [] });
        }
      } catch (err) {
        console.error('Failed to load result', err);
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="flex-center" style={{ minHeight: '60vh' }}>
        <div>Loading your results...</div>
      </div>
    );
  }

  if (!data || !data.interview) {
    return (
      <div className="container text-center" style={{ paddingTop: '4rem' }}>
        <h2>Result Record Not Found</h2>
        <Button onClick={() => navigate('/history')}>Back to History</Button>
      </div>
    );
  }

  const { interview, answers = [], result = {} } = data;

  const totalQuestions = interview.questionsCount || result.totalQuestions || 10;

  // Accurately determine overall score based on ALL questions (e.g. 1/10 attended with 100% score is 10%)
  const validScores = answers.map((a) => a.score).filter((s) => typeof s === 'number');
  const computedScore = Math.round(validScores.reduce((sum, s) => sum + s, 0) / totalQuestions);

  const overallScore = typeof result.overallScore === 'number'
    ? result.overallScore
    : (typeof interview.score === 'number' ? interview.score : computedScore);

  const attemptedCount = typeof interview.attemptedCount === 'number'
    ? interview.attemptedCount
    : (result.questionsAttempted ?? answers.length);

  const strengths = result.strengths || [
    'Demonstrated clear conceptual communication during core questions.',
    'Diligently completed responses across the session.'
  ];

  const weaknesses = result.weaknesses || [
    'Expand on specific real-world implementation examples.',
    'Address technical edge cases more explicitly.'
  ];

  const recommendations = result.recommendations || [
    `Practice additional ${interview.type === 'technical' ? (interview.subject || 'Java').toUpperCase() : 'HR'} interview questions.`,
    'Structure responses clearly using the STAR framework or technical examples.'
  ];

  return (
    <div className="result-page container" style={{ paddingTop: '2rem', maxWidth: '1000px' }}>
      {/* Header Banner */}
      <div className="result-header card flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <span className="badge badge-tech" style={{ marginBottom: '0.5rem' }}>
            <Sparkles size={12} /> Performance Assessment
          </span>
          <h1>Mock Interview Performance</h1>
          <p className="subtitle">
            {(interview.type || 'Technical').toUpperCase()} {interview.subject && interview.subject !== 'N/A' ? `(${interview.subject.toUpperCase()})` : ''} • Completed on {interview.createdAt ? new Date(interview.createdAt).toLocaleDateString() : 'Today'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link to="/interview/setup">
            <Button icon={PlayCircle}>Try Another Session</Button>
          </Link>
          <Link to="/dashboard">
            <Button variant="secondary" icon={LayoutDashboard}>Dashboard</Button>
          </Link>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        {/* Score Gauge Card */}
        <div style={{ gridColumn: 'span 1' }}>
          <ScoreCard 
            score={overallScore} 
            attemptedCount={attemptedCount} 
            totalQuestions={totalQuestions} 
          />
        </div>

        {/* Strengths & Improvement Summary */}
        <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Card className="summary-section-card strength-card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#065f46', marginBottom: '0.75rem' }}>
              <CheckCircle2 size={20} /> Identified Strengths
            </h3>
            <ul className="analysis-list">
              {strengths.map((s, idx) => (
                <li key={idx}>{s}</li>
              ))}
            </ul>
          </Card>

          <Card className="summary-section-card improvement-card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#92400e', marginBottom: '0.75rem' }}>
              <AlertTriangle size={20} /> Key Areas to Improve
            </h3>
            <ul className="analysis-list">
              {weaknesses.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      {/* Recommendations Card */}
      <Card className="recommendation-card" style={{ marginBottom: '2.5rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: 'var(--primary)' }}>
          <Lightbulb size={20} /> Recommendations for Next Session
        </h3>
        <ul className="analysis-list">
          {recommendations.map((rec, idx) => (
            <li key={idx}>{rec}</li>
          ))}
        </ul>
      </Card>

      {/* Question-by-Question Breakdown */}
      <div className="breakdown-section">
        <h2>Detailed Question Breakdown ({answers.length})</h2>
        <p className="subtitle" style={{ marginBottom: '1.5rem' }}>
          Individual question evaluations with a breakdown of why each score wasn't 100%.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {answers.map((ans, idx) => (
            <Card key={ans._id || idx} className="breakdown-item-card">
              <div className="flex-between" style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="question-number-badge">Question {idx + 1}</span>
                  {ans.isFollowUp && (
                    <span className="badge badge-medium"><Sparkles size={12} /> Adaptive Follow-Up</span>
                  )}
                </div>
                <span className="badge badge-tech" style={{ fontSize: '0.8rem' }}>
                  Score: {ans.score !== null ? `${ans.score}%` : 'Evaluated'}
                </span>
              </div>

              <h4 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>{ans.questionText}</h4>
              <ScoreBreakdown evaluation={ans} />

              {ans.timeComplexity && (
                <div
                  style={{
                    margin: '0.6rem 0',
                    padding: '0.6rem 0.8rem',
                    background: 'var(--bg-subtle, #f8fafc)',
                    border: '1px solid var(--border-color, #e2e8f0)',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.6rem',
                  }}
                >
                  <Clock size={16} style={{ color: 'var(--primary, #6366f1)', marginTop: '2px', flexShrink: 0 }} />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Time Complexity:</span>
                      <span className="badge badge-tech" style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.82rem' }}>
                        {ans.timeComplexity}
                      </span>
                      {ans.spaceComplexity && (
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          Space: <code style={{ fontWeight: 600 }}>{ans.spaceComplexity}</code>
                        </span>
                      )}
                    </div>
                    {ans.timeComplexityExplanation && (
                      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {ans.timeComplexityExplanation}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {ans.isIrrelevant && (
                <div role="alert" style={{ marginBottom: '0.75rem', padding: '0.65rem 0.75rem', border: '1px solid var(--danger)', borderRadius: '6px', color: 'var(--danger)', fontWeight: 700 }}>
                  <div>IRRELEVANT ANSWER</div>
                  <div style={{ marginTop: '0.2rem', fontSize: '0.85rem', fontWeight: 500 }}>Your response does not address the question asked.</div>
                </div>
              )}

              <div className="answer-review-box">
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  YOUR RESPONSE:
                </div>
                <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                  {ans.answerText || '(No answer provided)'}
                </p>
              </div>

              {ans.improvementSuggestion && (
                <p style={{ margin: '0.75rem 0 0', fontSize: '0.9rem', color: 'var(--text-main)' }}>{ans.improvementSuggestion}</p>
              )}

              {(ans.scoreReason || ans.feedback || ans.whyNot100) && (
                <div className="feedback-review-box" style={{ marginTop: '0.75rem' }}>
                  {ans.score < 100 ? (
                    <>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#92400e', marginBottom: '0.25rem' }}>
                        WHY NOT 100%
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        {ans.whyNot100 || ans.scoreReason || ans.feedback}
                      </p>
                    </>
                  ) : (
                    <>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '0.25rem' }}>
                        FEEDBACK
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        {ans.feedback || ans.scoreReason}
                      </p>
                    </>
                  )}
                </div>
              )}

              {ans.score < 98 && (ans.weaknesses || []).length > 0 && (
                <div style={{ marginTop: '0.6rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
                    TOPIC(S) TO REVIEW
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {ans.weaknesses.map((w, i) => (
                      <span key={i} className="badge badge-medium" style={{ fontSize: '0.75rem' }}>{w}</span>
                    ))}
                  </div>
                </div>
              )}

              {interview.type === 'hr' && ans.deliveryMetrics && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    SPEECH DELIVERY
                  </div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', margin: '0 0 0.35rem' }}>
                    Filler words: {ans.deliveryMetrics.fillerWordCount} ({ans.deliveryMetrics.fillerFrequencyPer100Words} per 100 words)
                    {' · '}Long pauses: {ans.deliveryMetrics.noticeablePauseCount}
                    {' · '}Repeated words or phrases: {ans.deliveryMetrics.repetitionCount}
                  </p>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0 0 0.35rem' }}>
                    Sentence completeness: {ans.deliveryMetrics.sentenceCompleteness === 'likely_complete' ? 'likely complete' : 'possible fragment'}
                  </p>
                  {(ans.deliveryMetrics.observations || []).length > 0 ? (
                    <ul className="analysis-list">
                      {ans.deliveryMetrics.observations.map((observation, observationIndex) => (
                        <li key={observationIndex}>{observation}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                      No notable delivery patterns were detected by the transcript heuristics.
                    </p>
                  )}
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.4rem 0 0' }}>
                    Approximate findings from browser-recognized text and callback timing, not audio or prosody analysis.
                  </p>
                </div>
              )}

              {ans.questionFormat === 'coding' && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                  <SolutionViewer
                    preloadedSolution={ans.referenceSolution || ans.correctedCode || null}
                    format="coding"
                    language={ans.language || (interview?.category?.toLowerCase().includes('sql') ? 'sql' : 'java')}
                    questionKey={ans._id || ans.questionId}
                  />
                </div>
              )}
              {ans.questionFormat === 'output_prediction' && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                  <SolutionViewer
                    preloadedSolution={ans.expectedOutput || null}
                    format="output_prediction"
                    questionKey={ans._id || ans.questionId}
                  />
                </div>
              )}
              {ans.questionFormat === 'theory' &&
                (interview?.subject === 'java' ||
                  interview?.subject === 'dbms' ||
                  interview?.category?.toLowerCase().includes('java') ||
                  interview?.category?.toLowerCase().includes('dbms') ||
                  interview?.category?.toLowerCase().includes('sql')) && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                    <SolutionViewer
                      preloadedSolution={
                        ans.referenceSolution ||
                        ans.idealAnswer ||
                        (ans.expectedConcepts?.length
                          ? `Key Expected Concepts:\n• ${ans.expectedConcepts.join('\n• ')}${
                              ans.improvementSuggestion || ans.feedback
                                ? `\n\nReference Explanation:\n${ans.improvementSuggestion || ans.feedback}`
                                : ''
                            }`
                          : null)
                      }
                      format="theory"
                      buttonText="Reference Solution"
                      questionKey={ans._id || ans.questionId}
                    />
                  </div>
                )}
              {ans.stepByStepExplanation && ans.questionFormat !== 'coding' && ans.questionFormat !== 'output_prediction' && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    HOW THE OUTPUT IS DERIVED
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0, whiteSpace: 'pre-wrap' }}>
                    {ans.stepByStepExplanation}
                  </p>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};
