import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import {
  Code,
  Users,
  CheckCircle,
  ArrowRight,
  AlertCircle,
  Terminal,
  FileText,
  FileCode2
} from 'lucide-react';

export const InterviewSetup = () => {
  const navigate = useNavigate();

  const [interviewType, setInterviewType] = useState('');
  const [subject, setSubject] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [questionFormat, setQuestionFormat] = useState('theory');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleTypeSelect = (type) => {
    setInterviewType(type);
    setError('');

    if (type === 'hr') {
      setSubject('');
      setQuestionFormat('theory');
    } else if (type === 'technical' && !subject) {
      setSubject('java');
    }
  };

  // DBMS should only disable Output Prediction, not Coding (SQL Coding).
  const handleSubjectChange = (newSubject) => {
    setSubject(newSubject);

    if (newSubject === 'dbms' && questionFormat === 'output_prediction') {
      setQuestionFormat('theory');
    }
  };

  const handleStartInterview = async () => {
    setError('');

    if (!interviewType) {
      setError('Please select an Interview Track.');
      return;
    }

    if (interviewType === 'technical' && !subject) {
      setError('Please select a Technical Subject.');
      return;
    }

    setLoading(true);

    try {
      const res = await apiService.createInterview(
        interviewType,
        subject,
        difficulty,
        questionFormat
      );

      const interview = res.interview;
      const targetId = interview?._id || interview?.id;
      if (!targetId || !res.firstQuestion?.questionText) {
        throw new Error(res.message || 'The server did not return an interview session and first question.');
      }

      navigate(`/interview/${targetId}`, {
        state: { firstQuestion: res.firstQuestion }
      });
    } catch (err) {
      console.error('Start Interview failed:', err);
      setError(err.message || 'Failed to initialize interview.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="setup-page container"
      style={{ paddingTop: '2rem', maxWidth: '900px' }}
    >
      <div className="section-header text-center" style={{ marginBottom: '2rem' }}>
        <h2>Configure Your AI Mock Interview</h2>
        <p className="subtitle">
          Choose track, domain and difficulty to begin your interview.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={20} />
            {error}
          </div>
        </div>
      )}

      {/* STEP 1 */}

      <div className="setup-step">
        <label className="setup-step-label">
          Step 1: Choose Interview Track
        </label>

        <div className="grid-2 setup-cards">

          <div
            className={`selection-card ${
              interviewType === 'technical' ? 'selected' : ''
            }`}
            onClick={() => handleTypeSelect('technical')}
          >
            <div className="selection-card-header">
              <div className="card-icon">
                <Code size={24} />
              </div>

              {interviewType === 'technical' && (
                <CheckCircle className="check-icon" size={22} />
              )}
            </div>

            <h3>Technical Interview</h3>

            <p className="subtitle">
              Java programming and DBMS interview questions.
            </p>
          </div>

          <div
            className={`selection-card ${
              interviewType === 'hr' ? 'selected' : ''
            }`}
            onClick={() => handleTypeSelect('hr')}
          >
            <div className="selection-card-header">
              <div className="card-icon hr-icon">
                <Users size={24} />
              </div>

              {interviewType === 'hr' && (
                <CheckCircle className="check-icon" size={22} />
              )}
            </div>

            <h3>HR Interview</h3>

            <p className="subtitle">
              Behavioral and communication questions.
            </p>
          </div>

        </div>
      </div>

      {/* STEP 2 */}

      {interviewType === 'technical' && (
        <div className="setup-step" style={{ marginTop: '2rem' }}>

          <label className="setup-step-label">
            Step 2: Choose Technical Subject
          </label>

          <div className="grid-2 setup-cards">

            <div
              className={`selection-card ${
                subject === 'java' ? 'selected' : ''
              }`}
              onClick={() => handleSubjectChange('java')}
            >
              <div className="selection-card-header">
                <span className="badge badge-tech">Language</span>

                {subject === 'java' && (
                  <CheckCircle className="check-icon" size={20} />
                )}
              </div>

              <h4>Java Programming</h4>

              <p className="subtitle">
                OOPs, Collections, Exceptions and JVM.
              </p>
            </div>

            <div
              className={`selection-card ${
                subject === 'dbms' ? 'selected' : ''
              }`}
              onClick={() => handleSubjectChange('dbms')}
            >
              <div className="selection-card-header">
                <span className="badge badge-tech">Database</span>

                {subject === 'dbms' && (
                  <CheckCircle className="check-icon" size={20} />
                )}
              </div>

              <h4>DBMS & SQL</h4>

              <p className="subtitle">
                Normalization, ACID, Joins, Transactions and SQL.
              </p>
            </div>

          </div>
        </div>
      )}

      {/* STEP 3 */}

      {interviewType === 'technical' && (
        <div className="setup-step" style={{ marginTop: '2rem' }}>

          <label className="setup-step-label">
            Step 3: Choose Question Style
          </label>

          <p className="subtitle" style={{ marginBottom: '1rem' }}>
            {subject === 'dbms'
              ? 'Answer DBMS theory questions or write complete SQL queries.'
              : 'Choose theory, output prediction or Java coding questions.'}
          </p>

          {subject === 'dbms' ? (

            <div className="grid-2 setup-cards">

              {/* DBMS THEORY */}

              <div
                className={`selection-card ${
                  questionFormat === 'theory' ? 'selected' : ''
                }`}
                onClick={() => setQuestionFormat('theory')}
              >
                <div className="selection-card-header">
                  <span className="badge badge-tech">
                    <FileText size={14} /> Explanation
                  </span>

                  {questionFormat === 'theory' && (
                    <CheckCircle className="check-icon" size={20} />
                  )}
                </div>

                <h4>Theory Questions</h4>

                <p className="subtitle">
                  Explain DBMS concepts like Normalization, ACID Properties,
                  Transactions, Indexing and Joins.
                </p>
              </div>

              {/* DBMS SQL (internally uses "coding") */}

              <div
                className={`selection-card ${
                  questionFormat === 'coding' ? 'selected' : ''
                }`}
                onClick={() => setQuestionFormat('coding')}
              >
                <div className="selection-card-header">
                  <span className="badge badge-tech">
                    <FileCode2 size={14} /> SQL
                  </span>

                  {questionFormat === 'coding' && (
                    <CheckCircle className="check-icon" size={20} />
                  )}
                </div>

                <h4>SQL Coding Questions</h4>

                <p className="subtitle">
                  Write the complete SQL query. No starter code will be provided.
                </p>
              </div>

            </div>

          ) : (

            <div className="grid-3 setup-cards">

              {/* JAVA THEORY */}

              <div
                className={`selection-card ${
                  questionFormat === 'theory' ? 'selected' : ''
                }`}
                onClick={() => setQuestionFormat('theory')}
              >
                <div className="selection-card-header">
                  <span className="badge badge-tech">
                    <FileText size={14} /> Explanation
                  </span>

                  {questionFormat === 'theory' && (
                    <CheckCircle className="check-icon" size={20} />
                  )}
                </div>

                <h4>Theory Questions</h4>

                <p className="subtitle">
                  Explain concepts in your own words.
                </p>
              </div>

              {/* JAVA OUTPUT */}

              <div
                className={`selection-card ${
                  questionFormat === 'output_prediction' ? 'selected' : ''
                }`}
                onClick={() => setQuestionFormat('output_prediction')}
              >
                <div className="selection-card-header">
                  <span className="badge badge-tech">
                    <Terminal size={14} /> Code
                  </span>

                  {questionFormat === 'output_prediction' && (
                    <CheckCircle className="check-icon" size={20} />
                  )}
                </div>

                <h4>Predict the Output</h4>

                <p className="subtitle">
                  Predict exactly what the Java code prints.
                </p>
              </div>

              {/* JAVA CODING */}

              <div
                className={`selection-card ${
                  questionFormat === 'coding' ? 'selected' : ''
                }`}
                onClick={() => {
                  setQuestionFormat('coding');
                  setSubject('java');
                }}
              >
                <div className="selection-card-header">
                  <span className="badge badge-tech">
                    <FileCode2 size={14} /> Coding
                  </span>

                  {questionFormat === 'coding' && (
                    <CheckCircle className="check-icon" size={20} />
                  )}
                </div>

                <h4>Java Coding Questions</h4>

                <p className="subtitle">
                  Solve LeetCode-style Java coding problems.
                </p>
              </div>

            </div>

          )}

        </div>
      )}

      {/* STEP 4 */}

      {interviewType && (
        <div className="setup-step" style={{ marginTop: '2rem' }}>
          <label className="setup-step-label">
            Step {interviewType === 'technical' ? '4' : '2'}: Select Difficulty
          </label>

          <div className="difficulty-selector-row">
            {['easy', 'medium', 'hard'].map((lvl) => (
              <button
                key={lvl}
                type="button"
                className={`difficulty-btn ${
                  difficulty === lvl ? 'active' : ''
                } badge-${lvl}`}
                onClick={() => setDifficulty(lvl)}
              >
                {lvl.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* SUMMARY */}

      {interviewType && (
        <Card className="summary-box" style={{ marginTop: '2rem' }}>

          <h3>Session Parameters</h3>

          <div className="grid-3 summary-details">

            <div>
              <span className="summary-label">Track</span>
              <div className="summary-value">
                <strong>{interviewType.toUpperCase()}</strong>
              </div>
            </div>

            <div>
              <span className="summary-label">Subject</span>
              <div className="summary-value">
                <strong>
                  {interviewType === 'technical'
                    ? subject.toUpperCase()
                    : 'GENERAL HR'}
                </strong>
              </div>
            </div>

            <div>
              <span className="summary-label">Difficulty</span>
              <div className="summary-value">
                <strong>{difficulty.toUpperCase()}</strong>
              </div>
            </div>

          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              marginTop: '1.5rem'
            }}
          >
            <Button
              size="lg"
              icon={ArrowRight}
              onClick={handleStartInterview}
              disabled={loading}
            >
              {loading ? 'Starting Interview...' : 'Start Interview'}
            </Button>
          </div>

        </Card>
      )}
    </div>
  );
};