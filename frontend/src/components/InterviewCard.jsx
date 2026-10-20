import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ChevronRight, Code, Users, Trash2 } from 'lucide-react';
import { Card } from './Card';

export const InterviewCard = ({ interview, onDelete }) => {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const isTechnical = interview.type === 'Technical';
  const badgeClass = isTechnical ? 'badge-tech' : 'badge-hr';

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--success)';
    if (score >= 60) return 'var(--warning)';
    return 'var(--danger)';
  };

  const handleConfirmDelete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!onDelete) return;
    try {
      setDeleting(true);
      await onDelete(interview.id);
    } catch (err) {
      setDeleting(false);
      setConfirming(false);
    }
  };

  return (
    <Card hover className="interview-card">
      <div className="flex-between" style={{ gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className={`interview-icon ${isTechnical ? 'icon-tech' : 'icon-hr'}`}>
            {isTechnical ? <Code size={20} /> : <Users size={20} />}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
              <span className={`badge ${badgeClass}`}>{interview.type}</span>
              {isTechnical && <span className="badge badge-medium">{interview.subject}</span>}
              <span className={`badge badge-${(interview.difficulty || 'Medium').toLowerCase()}`}>
                {interview.difficulty || 'Medium'}
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Calendar size={14} /> {interview.date}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
          {/* Attended Count Column */}
          <div style={{ textAlign: 'right', minWidth: '80px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Attended</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main, #0f172a)' }}>
              {interview.attemptedCount ?? 0} / {interview.totalQuestions || 10}
            </div>
            <div style={{ fontSize: '0.72rem', color: interview.status === 'Completed' ? 'var(--success, #10b981)' : 'var(--text-muted)' }}>
              {interview.status || 'Completed'}
            </div>
          </div>

          {/* Score Column */}
          <div style={{ textAlign: 'right', minWidth: '60px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Score</div>
            {typeof interview.score === 'number' ? (
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: getScoreColor(interview.score) }}>
                {interview.score}%
              </div>
            ) : (
              // Exited before completing: there is no score yet.
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                {interview.score}
              </div>
            )}
          </div>

          <Link to={`/result/${interview.id}`} className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            View <ChevronRight size={16} />
          </Link>

          {onDelete && (
            confirming ? (
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                padding: '0.25rem 0.5rem',
                borderRadius: 'var(--radius-sm, 6px)',
              }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--danger, #ef4444)', fontWeight: 600 }}>Delete?</span>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  disabled={deleting}
                  className="btn btn-sm"
                  style={{
                    background: 'var(--danger, #ef4444)',
                    color: '#ffffff',
                    padding: '0.2rem 0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    borderRadius: '4px',
                    border: 'none',
                    cursor: deleting ? 'not-allowed' : 'pointer'
                  }}
                >
                  {deleting ? '...' : 'Yes'}
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirming(false); }}
                  disabled={deleting}
                  className="btn btn-sm btn-secondary"
                  style={{
                    padding: '0.2rem 0.5rem',
                    fontSize: '0.75rem',
                    borderRadius: '4px'
                  }}
                >
                  No
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirming(true); }}
                title="Delete this interview session"
                aria-label="Delete interview"
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border-color, #e2e8f0)',
                  color: 'var(--text-muted, #64748b)',
                  borderRadius: 'var(--radius-sm, 6px)',
                  padding: '0.4rem 0.5rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--danger, #ef4444)';
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--text-muted, #64748b)';
                  e.currentTarget.style.borderColor = 'var(--border-color, #e2e8f0)';
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                <Trash2 size={16} />
              </button>
            )
          )}
        </div>
      </div>
    </Card>
  );
};
