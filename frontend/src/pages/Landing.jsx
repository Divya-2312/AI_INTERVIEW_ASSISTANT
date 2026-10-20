import React from 'react';
import { Link } from 'react-router-dom';
import { Bot, Code, Users, Award, Sparkles, ArrowRight, CheckCircle2, ShieldCheck, Cpu } from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

export const Landing = () => {
  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="container hero-container">
          <div className="hero-badge">
            <Sparkles size={16} /> AI-Powered Interview Preparation Platform
          </div>
          <h1 className="hero-title">
            Master Technical & HR Interviews with <span className="highlight">AI Interview Assistant</span>
          </h1>
          <p className="hero-subtitle">
            Practice real-world interview questions, evaluate your responses, identify your strengths and weaknesses, and boost your job readiness with structured self-evaluation.
          </p>
          <div className="hero-actions">
            <Link to="/register">
              <Button size="lg" icon={ArrowRight}>Get Started Free</Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" size="lg">Login to Account</Button>
            </Link>
          </div>

          <div className="hero-stats-row grid-3">
            <div className="stat-pill">
              <span className="stat-number">Technical</span>
              <span className="stat-desc">Java & DBMS Subject Tracks</span>
            </div>
            <div className="stat-pill">
              <span className="stat-number">HR & Behavioral</span>
              <span className="stat-desc">Communication & Situational Prep</span>
            </div>
            <div className="stat-pill">
              <span className="stat-number">Self-Evaluation</span>
              <span className="stat-desc">Detailed Feedback & Recommendations</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Pillars Section */}
      <section className="features-section container">
        <div className="section-header text-center">
          <h2>Choose Your Targeted Interview Track</h2>
          <p className="subtitle">Select either Technical mastery or HR behavioral preparation for your mock session.</p>
        </div>

        <div className="grid-2 track-cards">
          <Card className="track-card tech-track">
            <div className="track-icon"><Code size={28} /></div>
            <h3>Technical Interview Track</h3>
            <p className="subtitle">
              Demonstrate core engineering principles, algorithm fundamentals, database structures, and language constructs.
            </p>
            <ul className="track-list">
              <li><CheckCircle2 size={16} color="var(--success)" /> Java OOPs, Exception Handling, JDK/JVM architecture</li>
              <li><CheckCircle2 size={16} color="var(--success)" /> DBMS Normalization, ACID properties, Joins & Indexing</li>
              <li><CheckCircle2 size={16} color="var(--success)" /> Extensible architecture for future technical domains</li>
            </ul>
            <div className="track-footer">
              <Link to="/interview/setup">
                <Button variant="outline" size="sm" icon={ArrowRight}>Setup Technical Mock</Button>
              </Link>
            </div>
          </Card>

          <Card className="track-card hr-track">
            <div className="track-icon hr-icon"><Users size={28} /></div>
            <h3>HR & Behavioral Track</h3>
            <p className="subtitle">
              Refine your personal introduction, highlight soft skills, teamwork, situational handling, and career objectives.
            </p>
            <ul className="track-list">
              <li><CheckCircle2 size={16} color="var(--success)" /> Self Introduction, Strengths & Weaknesses analysis</li>
              <li><CheckCircle2 size={16} color="var(--success)" /> Conflict management & STAR behavioral scenarios</li>
              <li><CheckCircle2 size={16} color="var(--success)" /> Long-term career goals & team collaboration prep</li>
            </ul>
            <div className="track-footer">
              <Link to="/interview/setup">
                <Button variant="outline" size="sm" icon={ArrowRight}>Setup HR Mock</Button>
              </Link>
            </div>
          </Card>
        </div>
      </section>

      {/* How it Works / Features */}
      <section className="workflow-section">
        <div className="container">
          <div className="section-header text-center">
            <h2>Key Platform Capabilities</h2>
            <p className="subtitle">Built to guide students step-by-step through interview readiness.</p>
          </div>

          <div className="grid-3">
            <Card hover>
              <div className="feature-icon"><Bot size={24} /></div>
              <h4>Structured Setup</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                Tailor your session with difficulty settings and strict subject isolation (Technical OR HR).
              </p>
            </Card>

            <Card hover>
              <div className="feature-icon"><Award size={24} /></div>
              <h4>Performance Evaluation</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                Receive immediate breakdown reports with overall scores, strengths, and targeted improvement plans.
              </p>
            </Card>

            <Card hover>
              <div className="feature-icon"><Cpu size={24} /></div>
              <h4>Adaptive Growth Architecture</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                Adaptive AI-generated questions, intelligent concept evaluation, and follow-up questioning.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Disclaimer / Notice */}
      <section className="container notice-box">
        <div className="notice-content">
          <ShieldCheck size={28} color="var(--primary)" />
          <div>
            <h4>Student-Focused Learning Platform</h4>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              AI Interview Assistant is an educational self-preparation platform designed exclusively for students. It is not a recruiter hiring tool.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
