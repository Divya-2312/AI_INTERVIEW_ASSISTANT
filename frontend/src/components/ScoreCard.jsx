import React from 'react';
import { Award, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';

export const ScoreCard = ({ score, attemptedCount, totalQuestions }) => {
  const getGrade = (s) => {
    if (s >= 85) return { text: 'Excellent Performance', color: 'var(--success)', icon: CheckCircle };
    if (s >= 70) return { text: 'Good Preparation', color: 'var(--primary)', icon: TrendingUp };
    if (s >= 50) return { text: 'Needs Practice', color: 'var(--warning)', icon: AlertCircle };
    return { text: 'Requires Improvement', color: 'var(--danger)', icon: AlertCircle };
  };

  const grade = getGrade(score);
  const Icon = grade.icon;

  return (
    <div className="score-card-container card" style={{ textAlign: 'center', padding: '2rem 1.5rem' }}>
      <div className="score-circle-outer" style={{ borderColor: grade.color }}>
        <div className="score-number" style={{ color: grade.color }}>
          {score}%
        </div>
        <div className="score-label">Overall Score</div>
      </div>

      <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem', color: grade.color, fontWeight: 700 }}>
        <Icon size={18} /> {grade.text}
      </div>

      <p className="subtitle" style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
        Attempted {attemptedCount} out of {totalQuestions} total questions
      </p>
    </div>
  );
};
