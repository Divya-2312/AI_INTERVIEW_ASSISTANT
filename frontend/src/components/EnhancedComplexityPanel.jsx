import React, { useState } from 'react';
import {
  Clock,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  Zap,
  Layers,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  TrendingUp,
  Info
} from 'lucide-react';

export const EnhancedComplexityPanel = ({ complexity }) => {
  const [showComparison, setShowComparison] = useState(false);

  if (!complexity) return null;

  const {
    timeComplexity = 'O(N)',
    spaceComplexity = 'O(1)',
    approach = 'Algorithmic Solution',
    isOptimal = true,
    explanation = '',
    executionTimeMs = 0,
    timeLimitMs = 2000,
    status = 'OPTIMAL_PERFORMANCE',
    isTLE = false,
    warning = null,
    optimalApproach = null,
    comparisonApproaches = [],
    tradeoffAdvice = null,
    suggestions = [],
    structuralDetails = {}
  } = complexity;

  const isWarning = status === 'EFFICIENCY_WARNING';
  const isTimeLimitExceeded = isTLE || status === 'TIME_LIMIT_EXCEEDED';

  return (
    <div
      className="enhanced-complexity-card"
      style={{
        margin: '1rem 0',
        padding: '1.25rem',
        background: 'var(--bg-card, #ffffff)',
        border: isTimeLimitExceeded
          ? '1.5px solid var(--danger, #ef4444)'
          : isWarning
          ? '1.5px solid var(--warning, #f59e0b)'
          : '1px solid var(--border-color, #e2e8f0)',
        borderRadius: '10px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: '8px',
              background: isTimeLimitExceeded
                ? 'rgba(239, 68, 68, 0.1)'
                : isWarning
                ? 'rgba(245, 158, 11, 0.1)'
                : 'var(--primary-subtle, rgba(99, 102, 241, 0.1))',
              color: isTimeLimitExceeded
                ? 'var(--danger, #ef4444)'
                : isWarning
                ? 'var(--warning, #d97706)'
                : 'var(--primary, #6366f1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Cpu size={20} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary, #1e293b)' }}>
              Complexity & Performance Analysis
            </h4>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted, #64748b)' }}>
              Identified Approach: <strong style={{ color: 'var(--text-primary, #0f172a)' }}>{approach}</strong>
            </span>
          </div>
        </div>

        {/* Complexity Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'var(--bg-subtle, #f8fafc)', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border-color, #e2e8f0)' }}>
            <Clock size={14} style={{ color: 'var(--primary, #6366f1)' }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Time:</span>
            <code style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--primary, #4338ca)' }}>{timeComplexity}</code>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'var(--bg-subtle, #f8fafc)', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border-color, #e2e8f0)' }}>
            <Layers size={14} style={{ color: '#0ea5e9' }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Aux Space:</span>
            <code style={{ fontWeight: 700, fontSize: '0.84rem', color: '#0369a1' }}>{spaceComplexity}</code>
          </div>

          {isOptimal ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', fontWeight: 600, padding: '0.25rem 0.55rem', borderRadius: '999px', background: 'rgba(16, 185, 129, 0.1)', color: '#059669' }}>
              <CheckCircle2 size={12} /> Optimal
            </span>
          ) : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', fontWeight: 600, padding: '0.25rem 0.55rem', borderRadius: '999px', background: 'rgba(245, 158, 11, 0.1)', color: '#d97706' }}>
              <TrendingUp size={12} /> Can be Optimized
            </span>
          )}
        </div>
      </div>

      {/* Runtime & Time Limit Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-subtle, #f8fafc)',
          padding: '0.5rem 0.85rem',
          borderRadius: '6px',
          fontSize: '0.82rem',
          marginBottom: '0.85rem',
          border: '1px solid var(--border-color, #e2e8f0)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Zap size={14} style={{ color: '#f59e0b' }} />
          <span>Measured Execution Time: <strong>{executionTimeMs} ms</strong></span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>Time Limit: <strong>{timeLimitMs} ms</strong></span>
        </div>

        <div>
          {isTimeLimitExceeded ? (
            <span style={{ color: 'var(--danger, #ef4444)', fontWeight: 700 }}>Time Limit Exceeded</span>
          ) : isWarning ? (
            <span style={{ color: '#d97706', fontWeight: 600 }}>Efficiency Caution</span>
          ) : (
            <span style={{ color: '#059669', fontWeight: 600 }}>Within Time Limit</span>
          )}
        </div>
      </div>

      {/* TLE or Efficiency Warning Banner */}
      {isTimeLimitExceeded && (
        <div
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.65rem',
            padding: '0.75rem 1rem',
            background: 'rgba(239, 68, 68, 0.08)',
            borderLeft: '4px solid var(--danger, #ef4444)',
            borderRadius: '4px',
            marginBottom: '0.85rem',
            color: '#b91c1c'
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.84rem', lineHeight: '1.45' }}>
            <strong>Time Limit Exceeded:</strong> {warning || 'Execution took longer than the configured time limit. Check for infinite loops or exponential complexity.'}
          </div>
        </div>
      )}

      {!isTimeLimitExceeded && isWarning && warning && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.65rem',
            padding: '0.75rem 1rem',
            background: 'rgba(245, 158, 11, 0.08)',
            borderLeft: '4px solid #f59e0b',
            borderRadius: '4px',
            marginBottom: '0.85rem',
            color: '#92400e'
          }}
        >
          <Info size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#d97706' }} />
          <div style={{ fontSize: '0.84rem', lineHeight: '1.45' }}>
            <strong>Performance Warning:</strong> {warning}
          </div>
        </div>
      )}

      {/* Complexity Explanation */}
      {explanation && (
        <div style={{ fontSize: '0.84rem', color: 'var(--text-muted, #475569)', lineHeight: '1.5', marginBottom: '0.75rem' }}>
          {explanation}
        </div>
      )}

      {/* Optimization Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div style={{ marginTop: '0.6rem', padding: '0.65rem 0.85rem', background: 'var(--bg-subtle, #f8fafc)', borderRadius: '6px', fontSize: '0.82rem' }}>
          <strong style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>Optimization Suggestions:</strong>
          <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-muted)' }}>
            {suggestions.map((s, idx) => (
              <li key={idx} style={{ marginBottom: '0.2rem' }}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Toggle Comparison Table */}
      {comparisonApproaches && comparisonApproaches.length > 1 && (
        <div style={{ marginTop: '0.85rem' }}>
          <button
            type="button"
            onClick={() => setShowComparison(!showComparison)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--primary, #6366f1)',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: 0
            }}
          >
            {showComparison ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            {showComparison ? 'Hide Alternative Approaches' : `Compare with Other Approaches (${comparisonApproaches.length})`}
          </button>

          {showComparison && (
            <div style={{ marginTop: '0.75rem', overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color, #e2e8f0)', background: 'var(--bg-subtle, #f8fafc)' }}>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Approach</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Time</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Aux Space</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Trade-Off / Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonApproaches.map((app, i) => {
                    const isCurrent = app.name === approach || app.timeComplexity === timeComplexity;
                    return (
                      <tr
                        key={i}
                        style={{
                          borderBottom: '1px solid var(--border-color, #e2e8f0)',
                          background: isCurrent ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                        }}
                      >
                        <td style={{ padding: '0.55rem 0.6rem', fontWeight: isCurrent ? 700 : 500 }}>
                          {app.name} {isCurrent && <span style={{ color: 'var(--primary)', fontSize: '0.72rem' }}>(Your Code)</span>}
                        </td>
                        <td style={{ padding: '0.55rem 0.6rem' }}>
                          <code style={{ fontWeight: 600 }}>{app.timeComplexity}</code>
                        </td>
                        <td style={{ padding: '0.55rem 0.6rem' }}>
                          <code style={{ fontWeight: 600 }}>{app.spaceComplexity}</code>
                        </td>
                        <td style={{ padding: '0.55rem 0.6rem', color: 'var(--text-muted)' }}>
                          {app.tradeOff || app.summary}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {tradeoffAdvice && (
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  * {tradeoffAdvice}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

