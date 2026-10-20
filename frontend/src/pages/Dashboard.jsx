import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { InterviewCard } from '../components/InterviewCard';
import { PlayCircle, Award, CheckCircle2, History, User, Sparkles, TrendingUp } from 'lucide-react';

export const Dashboard = () => {
  const { user } = useAuth();
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const list = await apiService.getInterviews();
        setInterviews(list);
      } catch (err) {
        console.error('Failed to load interviews from backend', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  const completedCount = interviews.filter(i => i.status === 'completed').length;
  const attemptedQuestionsTotal = interviews.reduce((sum, i) => sum + (i.attemptedCount || 0), 0);
  const scoredInterviews = interviews.filter(i => typeof i.score === 'number' && i.score !== null);
  
  const avgScoreText = scoredInterviews.length > 0
    ? `${Math.round(scoredInterviews.reduce((acc, curr) => acc + curr.score, 0) / scoredInterviews.length)}%`
    : 'No score yet';

  const bestScoreText = scoredInterviews.length > 0
    ? `${Math.max(...scoredInterviews.map(i => i.score))}%`
    : 'No score yet';

  // Format backend model structure for InterviewCard
  const formattedInterviews = interviews.map(i => {
    const attemptedCount = typeof i.attemptedCount === 'number'
      ? i.attemptedCount
      : (Array.isArray(i.answers) ? i.answers.length : 0);
    const totalQuestions = i.questionsCount || 10;
    const scoreVal = typeof i.score === 'number'
      ? i.score
      : (attemptedCount > 0 ? 0 : 'Not yet finished');

    return {
      id: i._id || i.id,
      date: i.createdAt ? new Date(i.createdAt).toISOString().split('T')[0] : 'Today',
      type: (i.type || 'technical').charAt(0).toUpperCase() + (i.type || 'technical').slice(1),
      subject: (i.subject || 'N/A').toUpperCase(),
      difficulty: (i.difficulty || 'medium').charAt(0).toUpperCase() + (i.difficulty || 'medium').slice(1),
      score: scoreVal,
      status: i.status === 'completed' ? 'Completed' : 'In Progress',
      attemptedCount,
      totalQuestions,
    };
  });

  return (
    <div className="dashboard-page container" style={{ paddingTop: '2rem' }}>
      {/* Welcome Hero */}
      <div className="dashboard-hero card">
        <div className="flex-between dashboard-hero-content">
          <div>
            <div className="hero-welcome-tag"><Sparkles size={16} /> Student Dashboard</div>
            <h1>Welcome back, {user?.name || 'Student'}!</h1>
            <p className="subtitle">
              Target Role: <strong style={{ color: 'var(--primary)' }}>{user?.targetRole || 'Software Engineering Aspirant'}</strong>
            </p>
          </div>
          <div className="dashboard-hero-action">
            <Link to="/interview/setup">
              <Button size="lg" icon={PlayCircle}>Start Mock Interview</Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Dynamic Backend Stats Cards */}
      <div className="grid-4 stats-grid" style={{ margin: '2rem 0' }}>
        <Card className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: '#e0e7ff', color: 'var(--primary)' }}>
            <Award size={24} />
          </div>
          <div>
            <div className="stat-value">{interviews.length}</div>
            <div className="stat-label">Interviews Created</div>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: '#d1fae5', color: 'var(--success)' }}>
            <TrendingUp size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.25rem' }}>{avgScoreText}</div>
            <div className="stat-label">Average Score</div>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: '#fef3c7', color: 'var(--warning)' }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div className="stat-value">{attemptedQuestionsTotal}</div>
            <div className="stat-label">Questions Practiced</div>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-icon-wrapper" style={{ backgroundColor: '#f3e8ff', color: '#7e22ce' }}>
            <Award size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.25rem' }}>{bestScoreText}</div>
            <div className="stat-label">Best Score</div>
          </div>
        </Card>
      </div>

      {/* Recent Interviews Section */}
      <div className="recent-section">
        <div className="flex-between" style={{ marginBottom: '1rem' }}>
          <div>
            <h2>Recent Mock Interviews</h2>
            <p className="subtitle">Review your latest backend-recorded sessions</p>
          </div>
          <Link to="/history" className="btn btn-secondary btn-sm">
            <History size={16} /> View All History
          </Link>
        </div>

        {loading ? (
          <div className="card text-center" style={{ padding: '2rem' }}>Loading interviews from database...</div>
        ) : formattedInterviews.length === 0 ? (
          <Card className="empty-card text-center">
            <p className="subtitle">No mock interviews recorded in database yet.</p>
            <Link to="/interview/setup" style={{ marginTop: '1rem', display: 'inline-block' }}>
              <Button icon={PlayCircle}>Take Your First Interview</Button>
            </Link>
          </Card>
        ) : (
          <div className="interviews-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {formattedInterviews.slice(0, 3).map((item) => (
              <InterviewCard key={item.id} interview={item} />
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid-3" style={{ marginTop: '2.5rem' }}>
        <Card hover className="quick-nav-card text-center">
          <h3>Start New Interview</h3>
          <p className="subtitle" style={{ fontSize: '0.85rem' }}>Technical (Java/DBMS) OR HR track</p>
          <div style={{ marginTop: '1rem' }}>
            <Link to="/interview/setup"><Button size="sm" icon={PlayCircle}>Configure Session</Button></Link>
          </div>
        </Card>

        <Card hover className="quick-nav-card text-center">
          <h3>Interview History</h3>
          <p className="subtitle" style={{ fontSize: '0.85rem' }}>Track your saved interview sessions</p>
          <div style={{ marginTop: '1rem' }}>
            <Link to="/history"><Button variant="secondary" size="sm" icon={History}>View Records</Button></Link>
          </div>
        </Card>

        <Card hover className="quick-nav-card text-center">
          <h3>Student Profile</h3>
          <p className="subtitle" style={{ fontSize: '0.85rem' }}>Manage account credentials and profile</p>
          <div style={{ marginTop: '1rem' }}>
            <Link to="/profile"><Button variant="secondary" size="sm" icon={User}>View Profile</Button></Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
