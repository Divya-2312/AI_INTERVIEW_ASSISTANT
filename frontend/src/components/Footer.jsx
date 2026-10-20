import React from 'react';
import { Bot, GraduationCap } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="footer-wrapper">
      <div className="container footer-content">
        <div className="footer-brand">
          <div className="footer-logo">
            <Bot size={20} />
            <span>AI Interview Assistant</span>
          </div>
          <p className="footer-desc">
            Mock interview preparation for students, with instant, detailed feedback on every answer.
          </p>
        </div>

        <div className="footer-info">
          <h4>Project Scope</h4>
          <ul>
            <li>Technical Interviews (Java, DBMS)</li>
            <li>HR Behavioral Interviews</li>
            <li>Detailed Performance Analytics</li>
            <li>Extensible Multi-Subject Architecture</li>
          </ul>
        </div>

        <div className="footer-phase">
          <p className="phase-text">
            Practice real interview questions and get a clear breakdown of what to improve.
          </p>
        </div>
      </div>
      <div className="footer-bottom">
        <div className="container flex-between">
          <p>&copy; {new Date().getFullYear()} AI Interview Assistant. Final Year Student Project.</p>
          <p className="tech-stack-tag"><GraduationCap size={16} /> Student Preparation Platform</p>
        </div>
      </div>
    </footer>
  );
};
