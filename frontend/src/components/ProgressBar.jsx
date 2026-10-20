import React from 'react';

export const ProgressBar = ({ current, total }) => {
  const percentage = Math.round((current / total) * 100);

  return (
    <div className="progress-bar-container">
      <div className="flex-between progress-label-row">
        <span className="progress-text">Progress: Step {current} of {total}</span>
        <span className="progress-percentage">{percentage}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
};
