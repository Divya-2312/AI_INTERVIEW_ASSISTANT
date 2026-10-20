import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
import { QuestionCard } from '../components/QuestionCard';
import { CodeWorkspace, JudgeResultPanel, ScoreBreakdown, SolutionViewer } from '../components/CodeWorkspace';
import { ProgressBar } from '../components/ProgressBar';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { ArrowRight, LogOut, Send, Mic, Sparkles, AlertCircle } from 'lucide-react';

// The Web Speech API will still try to force-fit whatever it hears into the
// language it's told to expect (en-US) -- when the candidate actually speaks
// a different language it doesn't refuse, it guesses wildly and hands back
// nonsense English words. Since we can't inspect the actual audio, we treat
// two signals as "this wasn't really English" and reject rather than fill
// the answer box with garbage:
//   1. Any character outside basic Latin script + common punctuation.
//   2. A low per-word recognition confidence on the FINAL result (interim
//      results don't carry a meaningful confidence value in Chrome).
const NON_LATIN_TEXT = /[^\x00-\x7F]/;
const MIN_CONFIDENCE = 0.55;

const normalizeEvaluation = (evaluation) =>
  evaluation?.isIrrelevant === true
    ? {
        ...evaluation,
        score: 0,
        relevance: 0,
        correctness: 0,
        conceptCoverage: 0,
        communication: 0,
        ...(typeof evaluation.accuracy === 'number' ? { accuracy: 0 } : {}),
      }
    : evaluation;

// Recent Chrome versions auto-punctuate each "final" result in continuous
// recognition mode -- i.e. every time the recognizer decides a pause was
// the end of a phrase, it appends a period to that chunk on its own. Since
// continuous dictation naturally has a short pause after almost every
// sentence/clause, joining those chunks with spaces produced "text. text.
// text." -- a full stop after every single pause, not just at real
// sentence ends. This app doesn't add that punctuation; it strips a lone
// trailing full stop Chrome added to each intermediate chunk, and instead
// adds sentence-ending punctuation only when the whole answer is finished.
const stripAutoFullStop = (text) => text.replace(/[.]+\s*$/, '').trim();

// The Web Speech API gives no real signal for "this was a different
// language" beyond per-word confidence for the language it was TOLD to
// expect (en-*) -- it never says "I think this was Spanish/Hindi/etc.".
// Script-based detection (NON_LATIN_TEXT) only catches languages that use
// a non-Latin script; a language typed in plain ASCII (Malay, Indonesian,
// Swahili, romanized/transliterated speech, etc.) sails straight through
// as if it were valid English. As a second, independent signal: real
// English sentences of any length almost always contain at least one very
// common English function word (the, is, a, to, and, of, in, that, this,
// ...). A recognized chunk with several words but NONE of these is a
// strong sign the recognizer force-fit non-English audio into
// English-sounding nonsense. This is a heuristic, not true language
// detection -- it can't be 100% reliable client-side without sending raw
// audio to a server-side multilingual model, but it catches a large,
// previously-undetected class of "spoke a different language" cases that
// the script check alone missed.
const ENGLISH_FUNCTION_WORDS = new Set([
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on',
  'and', 'or', 'but', 'that', 'this', 'it', 'with', 'for', 'as', 'be',
  'i', 'you', 'we', 'they', 'he', 'she', 'not', 'so', 'if', 'because',
  'have', 'has', 'will', 'would', 'can', 'could', 'should', 'my', 'your',
  'when', 'then', 'there', 'what', 'which', 'how', 'do', 'does',
]);
const looksImplausiblyEnglish = (text) => {
  const words = text.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length < 5) return false; // too short for this signal to be reliable
  return !words.some((w) => ENGLISH_FUNCTION_WORDS.has(w.replace(/[^a-z']/g, '')));
};

// These delivery metrics are approximations derived from browser speech-recognition
// text and result-callback timestamps, not raw audio or true prosody analysis.
const computeHRDeliveryMetrics = (segments) => {
  const transcript = segments.map((segment) => segment.text).join(' ').trim();
  const words = transcript.toLowerCase().match(/[a-z']+/g) || [];
  const fillerMatches = transcript.match(/\b(?:um+|uh+|like|you\s+know|actually|basically|i\s+mean)\b/gi) || [];
  const segmentTimestamps = segments.map((segment) => segment.timestamp);
  const noticeablePauseCount = segmentTimestamps.slice(1).reduce((count, timestamp, index) => (
    timestamp - segmentTimestamps[index] > 1800 ? count + 1 : count
  ), 0);
  let repetitionCount = 0;
  for (let start = 0; start < words.length; start++) {
    let repeatedPhraseLength = 0;
    for (let length = Math.min(5, words.length - start); length > 0; length--) {
      const phrase = words.slice(start, start + length).join(' ');
      const nextStart = start + length;
      const maxRestartGap = Math.min(words.length - length, nextStart + 5);
      for (let candidate = nextStart; candidate <= maxRestartGap; candidate++) {
        if (words.slice(candidate, candidate + length).join(' ') === phrase) {
          repeatedPhraseLength = length;
          break;
        }
      }
      if (repeatedPhraseLength > 0) break;
    }
    if (repeatedPhraseLength > 0) {
      repetitionCount += 1;
      start += repeatedPhraseLength - 1;
    }
  }

  const finalWord = words[words.length - 1] || '';
  const endsWithOpenPhrase = new Set([
    'and', 'but', 'because', 'to', 'of', 'for', 'with', 'that', 'which', 'when',
    'if', 'is', 'are', 'was', 'were', 'am', 'be', 'been', 'have', 'has', 'can', 'will',
  ]).has(finalWord);
  const hasSubjectAndVerb = /\b(?:i|we|they|he|she|it|this|that|there|the|a|an|my|our|people)\b[\s\S]*\b(?:am|is|are|was|were|be|been|have|has|had|do|does|did|can|could|will|would|work|worked|learn|learned|manage|managed|lead|led|help|helped|want|wanted|think|thought|believe|believed|feel|felt|make|made|take|took|use|used|handle|handled|solve|solved)\b/i.test(transcript);
  const likelyCompleteSentence = words.length >= 4 && !endsWithOpenPhrase && hasSubjectAndVerb;

  return {
    fillerWordCount: fillerMatches.length,
    fillerFrequencyPer100Words: words.length ? Number((fillerMatches.length * 100 / words.length).toFixed(1)) : 0,
    noticeablePauseCount,
    repetitionCount,
    sentenceCompleteness: likelyCompleteSentence ? 'likely_complete' : 'possible_fragment',
    segmentTimestamps,
  };
};

export const Interview = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [interview, setInterview] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(location.state?.firstQuestion || null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [questionCount, setQuestionCount] = useState(1);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [validationError, setValidationError] = useState('');
  const [lastEvalFeedback, setLastEvalFeedback] = useState(null);
  const [pendingNextQuestion, setPendingNextQuestion] = useState(null);
  const [isInterviewCompleted, setIsInterviewCompleted] = useState(false);
  const [isFollowUpBadge, setIsFollowUpBadge] = useState(false);
  const [showExitModal, setShowExitModal] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [speechError, setSpeechError] = useState('');
  const speechSegmentsRef = React.useRef([]);
  // Once an answer is submitted it is locked (no edits, no speech input) until the next question loads.
  const [answerLocked, setAnswerLocked] = useState(false);
  const answerLockedRef = React.useRef(false);
  const languageRejectedRef = React.useRef(false);
  const interviewTypeRef = React.useRef(null);
  interviewTypeRef.current = interview?.type;
  // Web Speech API accuracy depends heavily on matching the acoustic model
  // to the speaker's accent -- 'en-US' alone routinely mis-hears real
  // English words from non-US accents (e.g. "related" -> "regulated",
  // "capability" -> "accountability"). Letting the candidate pick the
  // closest English variant is the single biggest accuracy lever available
  // client-side; there is no way to guarantee 100% accuracy from the
  // browser API itself.
  const [speechLang, setSpeechLang] = useState('en-IN');
  const recognitionRef = React.useRef(null);
  // Tracks text already committed from finished (final) speech results, kept
  // separate from interim guesses so a rejected/garbled interim chunk never
  // gets baked into the answer permanently.
  const committedTranscriptRef = React.useRef('');

  useEffect(() => {
    const SpeechRecognitionApi = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionApi) {
      setSpeechSupported(false);
      return;
    }
    const recognition = new SpeechRecognitionApi();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = speechLang;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      // A submitted answer must stay exactly as submitted -- late results are ignored.
      if (answerLockedRef.current) return;
      let interim = '';
      let sawUnrecognizable = false;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const alt = result[0];
        const text = alt.transcript || '';
        const confidence = typeof alt.confidence === 'number' ? alt.confidence : 1;

        if (result.isFinal) {
          // Reject this chunk outright rather than accept a low-confidence
          // or non-English guess into the transcript -- accuracy matters
          // more than always having *something* in the box.
          if (
            NON_LATIN_TEXT.test(text) ||
            (confidence > 0 && confidence < MIN_CONFIDENCE) ||
            looksImplausiblyEnglish(text)
          ) {
            sawUnrecognizable = true;
            continue;
          }
          // Strip Chrome's auto-inserted end-of-chunk period before joining
          // -- otherwise continuous dictation reads back with a full stop
          // after every natural pause instead of only at real sentence ends.
          const cleaned = stripAutoFullStop(text);
          if (interviewTypeRef.current === 'hr' && cleaned) {
            speechSegmentsRef.current.push({ text: cleaned, timestamp: Date.now() });
          }
          committedTranscriptRef.current = `${committedTranscriptRef.current} ${cleaned}`.trim();
        } else if (!NON_LATIN_TEXT.test(text)) {
          interim += text;
        }
      }

      // Speech answers are English only: anything the recognizer could not
      // confidently hear as English is rejected, never graded as an answer.
      if (sawUnrecognizable) {
        languageRejectedRef.current = true;
        setSpeechError("Couldn't understand the language.");
      } else if ((interim || committedTranscriptRef.current) && !languageRejectedRef.current) {
        setSpeechError('');
      }

      const combined = `${committedTranscriptRef.current} ${interim}`.trim();
      // When a chunk was rejected, always refresh the box -- even to empty -- so
      // the non-English guess shown while speaking can't remain as the answer.
      if (combined || sawUnrecognizable) setCurrentAnswer(combined);
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      const messages = {
        'no-speech': "I didn't hear anything. Please try again.",
        'audio-capture': 'No microphone was found. Please check your device.',
        'not-allowed': 'Microphone access was blocked. Please allow microphone permission.',
        'language-not-supported': 'English speech recognition is not available on this device.',
        network: 'A network error interrupted speech recognition. Please try again.',
      };
      setSpeechError(messages[event.error] || "Sorry, I couldn't understand that. Please try again in English.");
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
    };
  }, [speechLang]);

  const toggleSpeechInput = () => {
    if (!recognitionRef.current || answerLockedRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      if (currentQuestion?.questionFormat !== 'coding') setCurrentAnswer('');
      committedTranscriptRef.current = '';
      speechSegmentsRef.current = [];
      languageRejectedRef.current = false;
      setSpeechError('');
      if (validationError) setValidationError('');
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  useEffect(() => {
    const loadInterview = async () => {
      try {
        const session = await apiService.getInterviewById(id);
        if (!session) {
          navigate('/dashboard');
          return;
        }
        setInterview(session);

        // Keep the progress counter accurate when resuming a session
        // that already has some answers recorded.
        const answeredCount = (session.answers || []).length;
        if (answeredCount > 0) {
          setQuestionCount(Math.min(answeredCount + 1, session.questionsCount || answeredCount + 1));
        }

        if (!currentQuestion) {
          // Resume: use the exact question the AI generated for this
          // interview (persisted server-side), not a generic static bank,
          // so the correct format (theory vs. predict-the-output, with
          // its code snippet) is preserved across refreshes.
          const q = session.currentQuestionData;
          if (q) {
          setCurrentQuestion({
  questionText: q.questionText || q.question,
  questionType: q.questionType || 'normal',
  questionFormat: q.questionFormat || 'theory',
  codeSnippet: q.codeSnippet || null,
  expectedOutput: q.expectedOutput || null,
  explanation: q.explanation || null,
  category: q.category || 'General',
  difficulty: q.difficulty || session.difficulty,
  expectedConcepts: q.expectedConcepts || [],
  language: q.language || null,
  starterCode: q.starterCode || null,
  testCases: q.testCases || null,
  title: q.title || null,

  // ADD THESE TWO LINES
  schema: q.schema || null,
  sampleData: q.sampleData || null,
});
            if ((q.questionFormat || '') === 'coding' && q.starterCode) {
              setCurrentAnswer(q.starterCode);
            }
          }
        }
      } catch (err) {
        console.error('Session loading error', err);
      } finally {
        setLoading(false);
      }
    };

    loadInterview();
  }, [id, navigate]);

  useEffect(() => {
    // Whenever question changes, ensure prior evaluation state is never leaked
    if (!pendingNextQuestion) {
      setLastEvalFeedback(null);
    }
  }, [currentQuestion?.id, currentQuestion?.questionText]);

  const handleAnswerSubmit = async () => {
    if (!currentAnswer.trim()) {
      setValidationError(
        currentQuestion?.questionFormat === 'coding'
          ? 'Please write your code before submitting.'
          : 'Please type your response before submitting.'
      );
      return;
    }

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    // Lock the answer exactly as submitted (text, editor and speech input).
    answerLockedRef.current = true;
    setAnswerLocked(true);
    setEvaluating(true);
    setValidationError('');
    setLastEvalFeedback(null);

    try {
      const payload = {
        questionId: currentQuestion?.id || `q-${questionCount}`,
        questionText: currentQuestion?.questionText || currentQuestion?.question,
        answerText: currentAnswer.trim(),
        expectedConcepts: currentQuestion?.expectedConcepts || [],
        questionFormat: currentQuestion?.questionFormat || 'theory',
        expectedOutput: currentQuestion?.expectedOutput || null,
        explanation: currentQuestion?.explanation || null,
        testCases: currentQuestion?.testCases || null,
        language: currentQuestion?.language || null,
        ...(interview.type === 'hr' && speechSegmentsRef.current.length > 0
          ? { hrDeliveryMetrics: computeHRDeliveryMetrics(speechSegmentsRef.current) }
          : {}),
        // Carried through so the backend can record the real
        // distinguishing content for this question (codeSnippet for
        // "predict the output", title for coding) -- without these, every
        // output_prediction question would look identical in question
        // history, since its questionText is always the same fixed prompt
        // sentence, and no-repeat detection would be blind to it.
        codeSnippet: currentQuestion?.codeSnippet || null,
        title: currentQuestion?.title || null,
      };

      const res = await apiService.submitAnswer(interview._id || interview.id, payload);

      const normalizedEval = normalizeEvaluation(res.evaluation);
      if (normalizedEval) {
        normalizedEval.referenceSolution =
          res.answer?.referenceSolution ||
          res.evaluation?.referenceSolution ||
          res.evaluation?.correctedCode ||
          res.evaluation?.correctedQuery ||
          res.answer?.codeSnippet ||
          null;
        normalizedEval.questionId = res.evaluation?.questionId || res.answer?.questionId || payload.questionId;
        normalizedEval.questionText = res.evaluation?.questionText || payload.questionText;
        normalizedEval.title = res.evaluation?.title || payload.title;
        normalizedEval.questionKey =
          res.evaluation?.questionKey ||
          payload.questionText ||
          payload.title ||
          payload.questionId;
      }
      setLastEvalFeedback(normalizedEval);
      setIsFollowUpBadge(res.isFollowUp);
      setEvaluating(false);

      if (res.interviewStatus === 'completed' || !res.nextQuestion) {
        setIsInterviewCompleted(true);
      } else {
        setPendingNextQuestion(res.nextQuestion);
      }
    } catch (err) {
      // If the answer was actually graded server-side but the next question
      // couldn't be generated (AI engine hiccup), show that real score
      // instead of just an error -- see api.js / errorMiddleware.js.
      if (err.evaluation) {
        // The answer WAS graded, so it stays locked; resubmitting the same text is
        // the existing retry flow for "graded but next question failed".
        const normalizedErrEval = normalizeEvaluation(err.evaluation);
        if (normalizedErrEval) {
          normalizedErrEval.referenceSolution =
            err.answer?.referenceSolution ||
            err.evaluation?.referenceSolution ||
            err.evaluation?.correctedCode ||
            null;
        }
        setLastEvalFeedback(normalizedErrEval);
      } else {
        // Never accepted by the server -> it was not really submitted; let the candidate retry.
        answerLockedRef.current = false;
        setAnswerLocked(false);
      }
      setValidationError(
        err.message || 'Error processing your response. Please try again.'
      );
      setEvaluating(false);
    }
  };

  const handleAdvanceToNextQuestion = () => {
    if (pendingNextQuestion) {
      setCurrentQuestion(pendingNextQuestion);
      setQuestionCount((prev) => prev + 1);
      setCurrentAnswer(
        pendingNextQuestion?.questionFormat === 'coding' && pendingNextQuestion?.starterCode
          ? pendingNextQuestion.starterCode
          : ''
      );
      setPendingNextQuestion(null);
    }
    setLastEvalFeedback(null);
    setIsFollowUpBadge(false);
    committedTranscriptRef.current = '';
    speechSegmentsRef.current = [];
    languageRejectedRef.current = false;
    setSpeechError('');
    answerLockedRef.current = false;
    setAnswerLocked(false);
    setValidationError('');
  };

  const handleFinishInterview = async () => {
    try {
      setEvaluating(true);
      await apiService.completeInterview(interview._id || interview.id);
      navigate(`/result/${interview._id || interview.id}`);
    } catch (err) {
      console.error('Error completing interview:', err);
      navigate(`/result/${interview._id || interview.id}`);
    }
  };

  if (loading) {
    return (
      <div className="flex-center" style={{ minHeight: '60vh' }}>
        <div>Loading interview...</div>
      </div>
    );
  }

  if (!interview || !currentQuestion) {
    return (
      <div className="container text-center" style={{ paddingTop: '4rem' }}>
        <h2>Interview Session Unavailable</h2>
        <Button onClick={() => navigate('/dashboard')}>Return to Dashboard</Button>
      </div>
    );
  }

  const totalQ = interview.questionsCount || 10;

  return (
    <div className="interview-session-page container" style={{ paddingTop: '1.5rem', maxWidth: currentQuestion.questionFormat === 'coding' ? '1200px' : '900px' }}>
      {/* Top Bar */}
      <div className="flex-between session-top-bar" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className={`badge ${interview.type === 'technical' ? 'badge-tech' : 'badge-hr'}`}>
            {(interview.type || 'Technical').toUpperCase()}
          </span>
          {interview.type === 'technical' && (
            <span className="badge badge-medium">{(interview.subject || 'Java').toUpperCase()}</span>
          )}
          <span className={`badge badge-${(interview.difficulty || 'medium').toLowerCase()}`}>
            {(interview.difficulty || 'Medium').toUpperCase()}
          </span>
          {isFollowUpBadge && (
            <span className="badge badge-hard" style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
              <Sparkles size={12} /> Adaptive Follow-Up Question
            </span>
          )}
        </div>

        <Button variant="danger" size="sm" icon={LogOut} onClick={() => setShowExitModal(true)}>
          Exit Session
        </Button>
      </div>

      <ProgressBar current={questionCount} total={totalQ} />

      {/* Question: coding gets the full judge-platform split view;
          theory/output-prediction keep the plain question card. */}
      {currentQuestion.questionFormat === 'coding' ? (
        <div style={{ margin: '1.5rem 0' }}>
          <CodeWorkspace
            interviewId={interview?._id || interview?.id || id}
            question={{
              questionText: currentQuestion.questionText || currentQuestion.question,
  title: currentQuestion.title,
  category: currentQuestion.category,
  difficulty: currentQuestion.difficulty || interview.difficulty,
  starterCode: currentQuestion.starterCode,
  testCases: currentQuestion.testCases,
  language: currentQuestion.language,
  schema: currentQuestion.schema,
  sampleData: currentQuestion.sampleData,
  referenceSolution: lastEvalFeedback?.referenceSolution || currentQuestion.referenceSolution || null,
}}       value={currentAnswer}
            onChange={(v) => {
              if (answerLocked) return;
              setCurrentAnswer(v);
              if (validationError) setValidationError('');
            }}
            onReset={() => { if (!answerLocked) setCurrentAnswer(currentQuestion.starterCode || ''); }}
            disabled={evaluating || answerLocked}
            isSubmitted={!!lastEvalFeedback}
          />
          {validationError && (
            <div className="speech-error-banner" style={{ marginTop: '0.6rem' }}>
              <span>{validationError}</span>
            </div>
          )}
        </div>
      ) : (
        <div style={{ margin: '1.5rem 0' }}>
          <QuestionCard
            question={{
              question: currentQuestion.questionText || currentQuestion.question,
              category: currentQuestion.category || 'Domain Concepts',
              difficulty: currentQuestion.difficulty || interview.difficulty,
              expectedConcepts: currentQuestion.expectedConcepts || [],
              codeSnippet: currentQuestion.codeSnippet || null,
              starterCode: null,
              language: currentQuestion.language || null,
              testCases: null,
              title: currentQuestion.title || null,
              questionFormat: currentQuestion.questionFormat || 'theory',
            }}
            index={questionCount - 1}
            total={totalQ}
          />
        </div>
      )}

      {/* Answer Area (coding submits straight from the editor above; the
          judge platform doesn't need a second text box) */}
      {currentQuestion.questionFormat !== 'coding' && (
      <Card className="answer-section-card">
        <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
          <label className="form-label" style={{ marginBottom: 0 }}>
            Your Response
          </label>
          <span className="subtitle" style={{ fontSize: '0.8rem' }}>
            {currentAnswer.length} characters
          </span>
        </div>

        {currentQuestion.questionFormat === 'output_prediction' && (
          <div style={{ marginBottom: '0.85rem' }}>
            <SolutionViewer
              interviewId={interview?._id || interview?.id || id}
              format="output_prediction"
              language={currentQuestion.language || 'java'}
              questionKey={currentQuestion.codeSnippet || currentQuestion.questionId || currentQuestion.questionText || currentQuestion.question || currentQuestion.title}
              disabled={!lastEvalFeedback}
              disabledTooltip="Submit your answer first to view the expected output"
              preloadedSolution={lastEvalFeedback?.expectedOutput || null}
            />
          </div>
        )}

        {currentQuestion.questionFormat === 'theory' &&
          (interview?.subject === 'java' ||
            interview?.subject === 'dbms' ||
            currentQuestion.subject === 'java' ||
            currentQuestion.subject === 'dbms') && (
            <div style={{ marginBottom: '0.85rem' }}>
              <SolutionViewer
                interviewId={interview?._id || interview?.id || id}
                format="theory"
                language={currentQuestion.language || (interview?.subject === 'dbms' ? 'sql' : 'java')}
                questionKey={currentQuestion.questionText || currentQuestion.question || currentQuestion.title}
                disabled={!lastEvalFeedback}
                disabledTooltip="Submit your answer first to view the reference solution"
                buttonText="Reference Solution"
                preloadedSolution={
                  lastEvalFeedback?.idealAnswer ||
                  lastEvalFeedback?.referenceSolution ||
                  (lastEvalFeedback?.expectedConcepts?.length
                    ? `Key Expected Concepts:\n• ${lastEvalFeedback.expectedConcepts.join('\n• ')}${
                        lastEvalFeedback.improvementSuggestion || lastEvalFeedback.feedback
                          ? `\n\nReference Explanation:\n${
                              lastEvalFeedback.improvementSuggestion || lastEvalFeedback.feedback
                            }`
                          : ''
                      }`
                    : null)
                }
              />
            </div>
          )}

        <Input
          type="textarea"
          rows={6}
          placeholder={
            currentQuestion.questionFormat === 'output_prediction'
              ? 'Type the exact output the code will print...'
              : 'Type your complete response here. Provide key terms and clear explanations...'
          }
          value={currentAnswer}
          disabled={answerLocked}
          onChange={(e) => {
            if (answerLocked) return;
            setCurrentAnswer(e.target.value);
            if (validationError) setValidationError('');
          }}
          error={validationError}
        />

        {/* Performance Assessment (shown after submitting an answer) */}
        {lastEvalFeedback && !evaluating && (
          <div className="performance-assessment-box" style={{ marginTop: '1rem', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-subtle, #f8fafc)' }}>
            <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Performance Assessment</span>
              <span style={{ fontWeight: 700, fontSize: '1.1rem', color: lastEvalFeedback.score >= 70 ? 'var(--success)' : lastEvalFeedback.score >= 40 ? '#92400e' : 'var(--danger)' }}>
                {lastEvalFeedback.score}%
              </span>
            </div>
            {lastEvalFeedback.isIrrelevant && (
              <div role="alert" style={{ marginBottom: '0.75rem', padding: '0.65rem 0.75rem', border: '1px solid var(--danger)', borderRadius: '6px', color: 'var(--danger)', fontWeight: 700 }}>
                <div>IRRELEVANT ANSWER</div>
                <div style={{ marginTop: '0.2rem', fontSize: '0.85rem', fontWeight: 500 }}>Your response does not address the question asked.</div>
              </div>
            )}
            {lastEvalFeedback.score < 100 ? (
              <>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Why not 100%
                </div>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', margin: 0 }}>
                  {lastEvalFeedback.whyNot100 || lastEvalFeedback.scoreReason || lastEvalFeedback.feedback}
                </p>
              </>
            ) : (
              lastEvalFeedback.feedback && (
                <p style={{ fontSize: '0.9rem', color: 'var(--success)', margin: 0, fontWeight: 500 }}>
                  {lastEvalFeedback.feedback}
                </p>
              )
            )}
            <ScoreBreakdown evaluation={lastEvalFeedback} />

            {(lastEvalFeedback.score < 98 || lastEvalFeedback.isIrrelevant) &&
              ((lastEvalFeedback.weaknesses || []).length > 0 || (lastEvalFeedback.missingConcepts || []).length > 0) && (
              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Topic(s) to review
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {(lastEvalFeedback.weaknesses?.length ? lastEvalFeedback.weaknesses : lastEvalFeedback.missingConcepts || []).map((w, i) => (
                    <span key={i} className="badge badge-medium" style={{ fontSize: '0.75rem' }}>{w}</span>
                  ))}
                </div>
              </div>
            )}

            {lastEvalFeedback.improvementSuggestion && (
              <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  {(lastEvalFeedback.deeperConcepts || []).length > 0 ? `Go further: ${lastEvalFeedback.deeperConcepts.join(', ')}` : 'How to improve'}
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', margin: 0, whiteSpace: 'pre-wrap' }}>
                  {lastEvalFeedback.improvementSuggestion}
                </p>
              </div>
            )}

            {lastEvalFeedback.stepByStepExplanation && (
              <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  How the output is derived
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', margin: 0, whiteSpace: 'pre-wrap' }}>
                  {lastEvalFeedback.stepByStepExplanation}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Voice Input */}
        <div className="voice-placeholder-box flex-between">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: isListening ? 'var(--danger)' : 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Mic size={16} />
            <span>
              {!speechSupported
                ? 'Voice input is not supported in this browser'
                : isListening
                ? 'Listening... speak your answer'
                : 'Speech Answer Mode — speak your response instead of typing'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {speechSupported && !isListening && (
              <select
                className="form-select"
                style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', width: 'auto' }}
                value={speechLang}
                disabled={answerLocked}
                onChange={(e) => setSpeechLang(e.target.value)}
                title="Accent recognition works best when this matches how you speak"
              >
                <option value="en-IN">English (India)</option>
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
                <option value="en-AU">English (Australia)</option>
              </select>
            )}
            {speechSupported ? (
              <Button
                variant={isListening ? 'danger' : 'secondary'}
                size="sm"
                disabled={answerLocked}
                onClick={toggleSpeechInput}
              >
                {isListening ? 'Stop' : 'Speak Answer'}
              </Button>
            ) : (
              <span className="badge badge-medium" style={{ fontSize: '0.7rem' }}>Text Mode Only</span>
            )}
          </div>
        </div>

        {speechSupported && !isListening && currentAnswer && (
          <div className="subtitle" style={{ fontSize: '0.78rem', marginTop: '0.35rem' }}>
            Tip: browser speech recognition isn't perfect — please review the transcribed text above and correct any words before submitting.
          </div>
        )}

        {speechError && (
          <div className="speech-error-banner">
            <AlertCircle size={14} />
            <span>{speechError}</span>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex-between answer-actions" style={{ marginTop: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Question {questionCount} of {totalQ}
          </div>

          {lastEvalFeedback ? (
            isInterviewCompleted || questionCount >= totalQ ? (
              <Button onClick={handleFinishInterview} disabled={evaluating} icon={Send}>
                {evaluating ? 'Finalizing...' : 'View Final Results'}
              </Button>
            ) : (
              <Button onClick={handleAdvanceToNextQuestion} icon={ArrowRight}>
                Next Question &rarr;
              </Button>
            )
          ) : (
            <Button 
              onClick={handleAnswerSubmit} 
              disabled={evaluating}
              icon={questionCount === totalQ ? Send : ArrowRight}
            >
              {evaluating ? 'Submitting & Grading...' : questionCount === totalQ ? 'Submit & Finish' : 'Submit Answer'}
            </Button>
          )}
        </div>
      </Card>
      )}

      {/* Coding format: submit control + judge-style result console live
          outside the plain answer Card, right under the split-pane editor. */}
      {currentQuestion.questionFormat === 'coding' && (
        <Card className="answer-section-card" style={{ marginTop: '1rem' }}>
          <div className="flex-between answer-actions">
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Question {questionCount} of {totalQ}
            </div>
            {lastEvalFeedback ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <SolutionViewer
                  interviewId={interview?._id || interview?.id || id}
                  format="coding"
                  language={currentQuestion?.language || (interview?.subject === 'dbms' ? 'sql' : 'java')}
                  preloadedSolution={
                    lastEvalFeedback?.referenceSolution ||
                    lastEvalFeedback?.correctedCode ||
                    lastEvalFeedback?.correctedQuery ||
                    null
                  }
                  questionKey={
                    currentQuestion?.questionText ||
                    currentQuestion?.title ||
                    currentQuestion?.id ||
                    lastEvalFeedback?.questionKey
                  }
                  disabled={false}
                />
                {isInterviewCompleted || questionCount >= totalQ ? (
                  <Button onClick={handleFinishInterview} disabled={evaluating} icon={Send}>
                    {evaluating ? 'Finalizing...' : 'View Final Results'}
                  </Button>
                ) : (
                  <Button onClick={handleAdvanceToNextQuestion} icon={ArrowRight}>
                    Next Question &rarr;
                  </Button>
                )}
              </div>
            ) : (
              <Button
                onClick={handleAnswerSubmit}
                disabled={evaluating}
                icon={questionCount === totalQ ? Send : ArrowRight}
              >
                {evaluating ? 'Running & Grading...' : questionCount === totalQ ? 'Submit & Finish Interview' : 'Submit Solution'}
              </Button>
            )}
          </div>

          {lastEvalFeedback && !evaluating && (
            <>
              <div className="performance-assessment-box" style={{ marginTop: '1rem', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)', backgroundColor: 'var(--light-bg)' }}>
                <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Performance Assessment</span>
                  <span style={{ fontWeight: 700, fontSize: '1.1rem', color: lastEvalFeedback.score >= 70 ? 'var(--success)' : lastEvalFeedback.score >= 40 ? '#92400e' : 'var(--danger)' }}>
                    {lastEvalFeedback.score}%
                  </span>
                </div>
                {lastEvalFeedback.isIrrelevant && (
                  <div role="alert" style={{ marginBottom: '0.75rem', padding: '0.65rem 0.75rem', border: '1px solid var(--danger)', borderRadius: '6px', color: 'var(--danger)', fontWeight: 700 }}>
                    <div>IRRELEVANT ANSWER</div>
                    <div style={{ marginTop: '0.2rem', fontSize: '0.85rem', fontWeight: 500 }}>Your response does not address the question asked.</div>
                  </div>
                )}
                {lastEvalFeedback.score < 100 ? (
                  <>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                      Why not 100%
                    </div>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', margin: 0 }}>
                      {lastEvalFeedback.whyNot100 || lastEvalFeedback.scoreReason || lastEvalFeedback.feedback}
                    </p>
                  </>
                ) : (
                  lastEvalFeedback.feedback && (
                    <p style={{ fontSize: '0.9rem', color: 'var(--success)', margin: 0, fontWeight: 500 }}>
                      {lastEvalFeedback.feedback}
                    </p>
                  )
                )}
                <ScoreBreakdown evaluation={lastEvalFeedback} />
              </div>
              <JudgeResultPanel
                evaluation={lastEvalFeedback}
                interviewId={interview?._id || interview?.id || id}
                questionKey={
                  currentQuestion?.questionText ||
                  currentQuestion?.title ||
                  currentQuestion?.id ||
                  lastEvalFeedback?.questionKey
                }
                language={currentQuestion?.language || (interview?.subject === 'dbms' ? 'sql' : 'java')}
                preloadedSolution={
                  lastEvalFeedback?.referenceSolution ||
                  lastEvalFeedback?.correctedCode ||
                  lastEvalFeedback?.correctedQuery ||
                  null
                }
              />
            </>
          )}
        </Card>
      )}

      {/* Exit Modal Confirmation */}
      {showExitModal && (
        <div className="modal-overlay">
          <div className="modal-card card">
            <h3>Exit Mock Interview?</h3>
            <p className="subtitle" style={{ margin: '1rem 0' }}>
              Are you sure you want to exit? Your progress in this session will be abandoned.
            </p>
            <div className="flex-between" style={{ marginTop: '1.5rem' }}>
              <Button variant="secondary" onClick={() => setShowExitModal(false)}>Resume Session</Button>
              <Button variant="danger" onClick={() => navigate('/dashboard')}>Confirm Exit</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
