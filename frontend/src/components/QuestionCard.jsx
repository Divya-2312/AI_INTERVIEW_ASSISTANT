import React from 'react';
import { HelpCircle, BookOpen, Terminal, FileCode2 } from 'lucide-react';

export const QuestionCard = ({ question, index, total }) => {
  return (
    <div className="question-card card">
      <div className="flex-between" style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="question-number-badge">
            Question {index + 1} of {total}
          </span>
          {question.category && (
            <span className="badge badge-tech" style={{ textTransform: 'none' }}>
              <BookOpen size={12} /> {question.category}
            </span>
          )}
        </div>
        <span className={`badge badge-${(question.difficulty || 'Medium').toLowerCase()}`}>
          {question.difficulty || 'Medium'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div className="q-icon-box">
          <HelpCircle size={22} color="var(--primary)" />
        </div>
        <div style={{ flex: 1 }}>
          {question.title && (
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
              {question.title}
            </h2>
          )}
          <div
            className="question-text"
            style={{
              fontSize: question.title ? '0.95rem' : '1.25rem',
              color: 'var(--text-main)',
              marginBottom: '0.75rem',
              // Judge-style statements carry real newlines between the
              // Input/Output/Constraints/Example sections -- keep them.
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
            }}
          >
            {question.question}
          </div>

          {question.codeSnippet && (
            <div style={{ marginBottom: '0.75rem' }}>
              <span className="concepts-label" style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Terminal size={14} /> Code:
              </span>
              <pre
                style={{
                  background: 'var(--bg-code, #1e1e2e)',
                  color: '#e2e8f0',
                  padding: '1rem',
                  borderRadius: '8px',
                  overflowX: 'auto',
                  fontSize: '0.85rem',
                  lineHeight: 1.5,
                }}
              >
                <code>{question.codeSnippet}</code>
              </pre>
            </div>
          )}

          {question.starterCode && (
            <div style={{ marginBottom: '0.75rem' }}>
              <span className="concepts-label" style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <FileCode2 size={14} /> Write your solution inside this method{question.language ? ` (${question.language})` : ''}:
              </span>
              <pre
                style={{
                  background: 'var(--bg-code, #1e1e2e)',
                  color: '#e2e8f0',
                  padding: '1rem',
                  borderRadius: '8px',
                  overflowX: 'auto',
                  fontSize: '0.85rem',
                  lineHeight: 1.5,
                }}
              >
                <code>{question.starterCode}</code>
              </pre>
            </div>
          )}

          {(question.testCases || []).length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <span className="concepts-label" style={{ marginBottom: '0.4rem', display: 'block' }}>
                Sample test inputs (expected outputs are revealed after you submit):
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {question.testCases.map((tc, i) => (
                  <div
                    key={i}
                    style={{
                      background: 'var(--bg-subtle, #f8fafc)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '0.5rem 0.75rem',
                      fontSize: '0.85rem',
                    }}
                  >
                    {tc.label && <strong style={{ marginRight: '0.4rem' }}>{tc.label}:</strong>}
                    <code>Input: {tc.input === '' ? '(none)' : tc.input}</code>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
