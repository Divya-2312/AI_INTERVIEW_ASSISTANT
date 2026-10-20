import React from 'react';

export const Card = ({ children, title, subtitle, className = '', hover = false, action, style }) => {
  return (
    <div className={`card ${hover ? 'card-hover' : ''} ${className}`} style={style}>
      {(title || action) && (
        <div className="flex-between card-header" style={{ marginBottom: subtitle ? '0.25rem' : '1rem' }}>
          <div>
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="subtitle" style={{ fontSize: '0.875rem' }}>{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
};
