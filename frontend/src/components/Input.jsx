import React from 'react';

export const Input = ({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  error,
  required = false,
  name,
  rows,
  options,
  helperText,
  style,
  disabled
}) => {
  return (
    <div className="form-group">
      {label && (
        <label className="form-label" htmlFor={name}>
          {label} {required && <span style={{ color: 'var(--danger)' }}>*</span>}
        </label>
      )}
      
      {type === 'textarea' ? (
        <textarea
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          rows={rows || 4}
          disabled={disabled}
          className={`form-textarea ${error ? 'error' : ''}`}
          style={style}
        />
      ) : type === 'select' ? (
        <select
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          className={`form-select ${error ? 'error' : ''}`}
        >
          {options && options.map((opt, i) => (
            <option key={i} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`form-input ${error ? 'error' : ''}`}
        />
      )}

      {helperText && !error && (
        <span className="subtitle" style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
          {helperText}
        </span>
      )}

      {error && <span className="error-text">{error}</span>}
    </div>
  );
};
