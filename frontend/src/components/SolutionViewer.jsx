import React, { useState, useEffect } from 'react';
import { Code2, Copy, Check, Info, Lock } from 'lucide-react';
import { apiService } from '../services/api';

/**
 * Fair-use policy: viewing the solution incurs zero penalty.
 * Configured as a single constant so it can be adjusted in the future if required.
 */
export const SOLUTION_VIEW_PENALTY = 0;

export const SolutionViewer = ({
  interviewId,
  format = 'coding',
  language = 'java',
  questionKey,
  preloadedSolution = null,
  buttonText = 'Solution',
  disabled = false,
  disabledTooltip = 'Submit your answer first to view the solution',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [solution, setSolution] = useState(preloadedSolution);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Reset state when the active question changes
  useEffect(() => {
    setIsOpen(false);
    setSolution(preloadedSolution || null);
    setError(null);
    setLoading(false);
    setCopied(false);
  }, [questionKey, preloadedSolution]);

  const handleToggle = async () => {
    if (disabled) return;

    if (isOpen) {
      setIsOpen(false);
      return;
    }

    setIsOpen(true);

    // If solution is already cached or preloaded, do not fetch again
    if (solution || preloadedSolution) {
      return;
    }

    if (!interviewId) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getQuestionSolution(interviewId, questionKey);
      if (data && data.solution) {
        setSolution(data.solution);
      } else {
        setSolution(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to load solution');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    const textToCopy = solution || preloadedSolution;
    if (!textToCopy) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(textToCopy).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }).catch(() => {});
    } else {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = textToCopy;
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (_) {}
      document.body.removeChild(textarea);
    }
  };

  const displaySolution = solution || preloadedSolution;
  const isOutputPrediction = format === 'output_prediction';
  const isTheory = format === 'theory';

  return (
    <div className="mm-solution-wrapper">
      <button
        type="button"
        className={`mm-solution-btn ${isOpen ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={disabled ? undefined : handleToggle}
        aria-expanded={isOpen}
        disabled={disabled}
        title={disabled ? disabledTooltip : (isOpen ? 'Hide solution' : 'View solution')}
      >
        {disabled ? <Lock size={13} /> : <Code2 size={13} />}
        <span>{buttonText}</span>
      </button>

      {isOpen && !disabled && (
        <div className="mm-solution-panel">
          <div className="mm-solution-notice">
            <Info size={13} />
            <span>Viewing the solution will not change your score.</span>
          </div>

          {loading && (
            <div className="mm-solution-loading">
              Loading solution...
            </div>
          )}

          {error && (
            <div className="mm-solution-error">
              {error}
            </div>
          )}

          {!loading && !error && !displaySolution && (
            <div className="mm-solution-empty">
              Solution not available for this question.
            </div>
          )}

          {!loading && !error && displaySolution && (
            <div className="mm-solution-content">
              <div className="mm-solution-header">
                <span className="mm-solution-title">
                  {isOutputPrediction ? 'Expected Output' : isTheory ? 'Reference Explanation' : 'Correct Solution'}
                </span>
                <button
                  type="button"
                  className="mm-solution-copy-btn"
                  onClick={handleCopy}
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <>
                      <Check size={13} color="var(--success, #10b981)" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              <pre className={`mm-solution-pre ${isOutputPrediction ? 'mm-output-pre' : isTheory ? 'mm-theory-pre' : 'mm-code-pre'}`}>
                <code>{displaySolution}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
