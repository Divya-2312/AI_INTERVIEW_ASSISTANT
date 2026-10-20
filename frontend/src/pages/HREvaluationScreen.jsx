import React, { useState, useEffect, useRef } from 'react';
import { mockmateServerApi } from '../services/mockmateServerApi';
import { Sparkles, Mic, MicOff, RefreshCw, Send, CheckCircle2, AlertTriangle, Award, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export function HREvaluationScreen() {
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [category, setCategory] = useState('');
  const [isLoadingQuestion, setIsLoadingQuestion] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [serverOnline, setServerOnline] = useState(null);

  // Bug 2 fix: persistent ref for the Web Speech recognizer
  const recognitionRef = useRef(null);

  // Check health and load initial question
  const checkServerAndLoad = async (selectedCat = category) => {
    setIsLoadingQuestion(true);
    setError('');
    setResult(null);
    setAnswer('');
    try {
      const health = await mockmateServerApi.checkHealth();
      setServerOnline(health.ok);
      const q = await mockmateServerApi.getRandomQuestion(selectedCat || null);
      setQuestion(q);
    } catch (err) {
      setServerOnline(false);
      setError(`Server unreachable on http://127.0.0.1:8001 (${err.message}). Ensure "python server.py 8001" is running in C:\\mockmate_app.`);
    } finally {
      setIsLoadingQuestion(false);
    }
  };

  useEffect(() => {
    checkServerAndLoad();

    return () => {
      // Clean up speech recognition on unmount
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
    };
  }, []);

  // Web Speech API Voice Transcription
  const toggleSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported in this browser. Please use Google Chrome.');
      return;
    }

    // Bug 2 fix: gracefully stop the active microphone instance
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition; // Bug 2 fix: assign to ref
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        }
      }
      if (finalTranscript) {
        setAnswer((prev) => (prev ? prev + ' ' + finalTranscript.trim() : finalTranscript.trim()));
      }
    };

    try {
      recognition.start();
    } catch (e) {
      console.warn('Speech recognition start failed:', e);
    }
  };

  // Submit Answer to server.py
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!answer.trim()) {
      setError('Please provide an answer before submitting.');
      return;
    }

    // Bug 2 fix: stop microphone before submitting
    recognitionRef.current?.stop();
    setIsEvaluating(true);
    setError('');

    try {
      const evalData = await mockmateServerApi.evaluateHR(question.id, answer.trim());
      setResult(evalData);
    } catch (err) {
      setError(err.message || 'Evaluation failed.');
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleCategoryChange = (cat) => {
    setCategory(cat);
    checkServerAndLoad(cat);
  };

  return (
    <div style={{ maxWidth: '880px', margin: '30px auto', padding: '0 20px', minHeight: '80vh' }}>
      {/* Header & Breadcrumb */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <ArrowLeft size={16} /> Back to Dashboard
          </Link>
          <h1 style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Sparkles size={24} color="#4f46e5" />
            Fine-Tuned HR Interview Simulator
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Powered by the fine-tuned <strong>mockmate-hr100</strong> LLaMA model on port 8001
          </p>
        </div>

        <button
          onClick={() => checkServerAndLoad()}
          disabled={isLoadingQuestion}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            background: 'var(--primary)',
            color: '#ffffff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontWeight: '600',
            cursor: isLoadingQuestion ? 'not-allowed' : 'pointer',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <RefreshCw size={16} className={isLoadingQuestion ? 'spin-animation' : ''} />
          {isLoadingQuestion ? 'Loading...' : 'Random Question'}
        </button>
      </div>

      {/* Category Pills */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {['', 'introduction', 'teamwork', 'conflict', 'leadership', 'adaptability', 'ethics and values'].map((cat) => (
          <button
            key={cat}
            onClick={() => handleCategoryChange(cat)}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '13px',
              border: category === cat ? '1px solid #4f46e5' : '1px solid var(--border-color)',
              background: category === cat ? 'var(--primary-light)' : 'var(--card-bg)',
              color: category === cat ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              fontWeight: category === cat ? '600' : '400',
              textTransform: 'capitalize'
            }}
          >
            {cat || 'All Categories'}
          </button>
        ))}
      </div>

      {/* Server Status Warning */}
      {serverOnline === false && (
        <div style={{
          background: 'var(--danger-light)',
          border: '1px solid #fca5a5',
          borderRadius: 'var(--radius-md)',
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center',
          color: '#991b1b'
        }}>
          <AlertTriangle size={20} color="#dc2626" />
          <div style={{ fontSize: '14px' }}>
            <strong>Local HR AI Engine Offline:</strong> Run <code>python server.py 8001</code> inside <code>C:\mockmate_app</code> with Ollama active.
          </div>
        </div>
      )}

      {error && (
        <div style={{
          background: 'var(--danger-light)',
          color: 'var(--danger)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          marginBottom: '20px',
          fontSize: '14px',
          border: '1px solid #fecaca'
        }}>
          {error}
        </div>
      )}

      {/* Question Card */}
      {question ? (
        <div style={{
          background: 'var(--card-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          marginBottom: '24px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{
              background: 'var(--primary-light)',
              color: 'var(--primary)',
              fontSize: '12px',
              fontWeight: '700',
              padding: '4px 10px',
              borderRadius: '12px',
              textTransform: 'uppercase'
            }}>
              {question.category || 'Behavioral'}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>ID: {question.id}</span>
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-main)', lineHeight: 1.5 }}>
            {question.question}
          </h2>
        </div>
      ) : (
        <div style={{
          background: 'var(--card-bg)',
          borderRadius: 'var(--radius-lg)',
          padding: '30px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-color)',
          marginBottom: '24px'
        }}>
          Loading question from curated 100 benchmark set...
        </div>
      )}

      {/* Answer Form */}
      <form onSubmit={handleSubmit}>
        <div style={{
          background: 'var(--card-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <label style={{ fontWeight: '600', fontSize: '15px', color: 'var(--text-main)' }}>
              Candidate Spoken / Written Response:
            </label>
            <button
              type="button"
              onClick={toggleSpeechRecognition}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: isListening ? '#fee2e2' : 'var(--light-bg)',
                color: isListening ? '#dc2626' : 'var(--text-main)',
                border: isListening ? '1px solid #f87171' : '1px solid var(--border-color)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '13px',
                transition: 'all 0.2s'
              }}
            >
              {isListening ? (
                <>
                  <MicOff size={16} color="#dc2626" />
                  <span>Stop Recording</span>
                </>
              ) : (
                <>
                  <Mic size={16} color="#4f46e5" />
                  <span>Speak via Microphone</span>
                </>
              )}
            </button>
          </div>

          <textarea
            rows={7}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your response or click 'Speak via Microphone' to dictate using Web Speech..."
            disabled={isEvaluating}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              fontSize: '15px',
              lineHeight: 1.6,
              color: 'var(--text-main)',
              background: isEvaluating ? 'var(--light-bg)' : '#ffffff',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box'
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              {answer.trim().split(/\s+/).filter(Boolean).length} words
            </span>

            <button
              type="submit"
              disabled={isEvaluating || !answer.trim() || !question}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 24px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary)',
                color: '#ffffff',
                border: 'none',
                fontWeight: '600',
                fontSize: '15px',
                cursor: (isEvaluating || !answer.trim()) ? 'not-allowed' : 'pointer',
                opacity: (isEvaluating || !answer.trim()) ? 0.6 : 1,
                boxShadow: 'var(--shadow-sm)'
              }}
            >
              <Send size={16} />
              {isEvaluating ? 'Evaluating with Model...' : 'Submit Answer'}
            </button>
          </div>
        </div>
      </form>

      {/* Loading Indicator */}
      {isEvaluating && (
        <div style={{
          textAlign: 'center',
          marginTop: '28px',
          padding: '24px',
          background: 'var(--light-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)'
        }}>
          <p style={{ fontWeight: '500', fontSize: '15px', color: 'var(--text-main)', marginBottom: '6px' }}>
            Running model inference with Ollama... this may take a few seconds.
          </p>
          <p style={{ fontSize: '13px' }}>
            The fine-tuned <strong>mockmate-hr100</strong> model is assessing relevance, STAR competency coverage, and communication quality.
          </p>
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div style={{
          marginTop: '32px',
          padding: '24px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          background: 'var(--card-bg)',
          boxShadow: 'var(--shadow-md)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 'bold' }}>
                AI Evaluation Result
              </span>
              <h3 style={{ margin: '4px 0 0 0', color: 'var(--text-main)', fontSize: '20px' }}>
                Performance Breakdown
              </h3>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: result.score >= 70 ? 'var(--success-light)' : result.score >= 40 ? 'var(--warning-light)' : 'var(--danger-light)',
              padding: '8px 18px',
              borderRadius: '24px',
              border: `1px solid ${result.score >= 70 ? '#86efac' : result.score >= 40 ? '#fde047' : '#fca5a5'}`
            }}>
              <Award size={20} color={result.score >= 70 ? '#16a34a' : result.score >= 40 ? '#d97706' : '#dc2626'} />
              <span style={{
                fontSize: '22px',
                fontWeight: '800',
                color: result.score >= 70 ? '#16a34a' : result.score >= 40 ? '#d97706' : '#dc2626'
              }}>
                {result.score ?? 0} / 100
              </span>
            </div>
          </div>

          {/* Sub-score Badges */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginTop: '16px', marginBottom: '20px' }}>
            <div style={{ background: 'var(--light-bg)', padding: '10px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Relevance</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>{Math.round((result.relevance || 0) * 100)}%</div>
            </div>
            <div style={{ background: 'var(--light-bg)', padding: '10px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Correctness</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>{Math.round((result.correctness || 0) * 100)}%</div>
            </div>
            <div style={{ background: 'var(--light-bg)', padding: '10px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Concept Coverage</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>{Math.round((result.conceptCoverage || 0) * 100)}%</div>
            </div>
            <div style={{ background: 'var(--light-bg)', padding: '10px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Communication</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>{Math.round((result.communication || 0) * 100)}%</div>
            </div>
          </div>

          {result.feedback && (
            <p style={{ color: 'var(--text-main)', fontSize: '15px', lineHeight: 1.6, marginTop: '12px' }}>
              {result.feedback}
            </p>
          )}

          {/* Bug 1 fix: Support isIrrelevant, weaknesses, and improvementSuggestion */}
          {result.isIrrelevant && (
            <p style={{ marginTop: '12px', color: '#dc2626', fontWeight: '500' }}>
              Your answer did not address this question, so it scored 0.
            </p>
          )}

          {result.strengths && result.strengths.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <strong style={{ color: '#16a34a', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <CheckCircle2 size={16} /> Strengths:
              </strong>
              <ul style={{ paddingLeft: '24px', margin: 0 }}>
                {result.strengths.map((s, idx) => (
                  <li key={idx} style={{ color: 'var(--text-main)', marginBottom: '4px', fontSize: '14px' }}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {result.weaknesses && result.weaknesses.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <strong style={{ color: '#ea580c', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <AlertTriangle size={16} /> Areas for Improvement:
              </strong>
              <ul style={{ paddingLeft: '24px', margin: 0 }}>
                {result.weaknesses.map((item, idx) => (
                  <li key={idx} style={{ color: 'var(--text-main)', marginBottom: '4px', fontSize: '14px' }}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {result.improvementSuggestion && (
            <p style={{ marginTop: '16px', color: 'var(--text-main)', fontSize: '14px', background: 'var(--light-bg)', padding: '12px 16px', borderRadius: 'var(--radius-md)', borderLeft: '4px solid #4f46e5' }}>
              <strong style={{ color: '#4f46e5' }}>Tip:</strong> {result.improvementSuggestion}
            </p>
          )}

          {result.scoreReason && (
            <div style={{ marginTop: '16px', fontSize: '12px', color: 'var(--text-muted)' }}>
              <em>Score rationale: {result.scoreReason}</em>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
