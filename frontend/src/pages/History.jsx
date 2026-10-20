import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { InterviewCard } from '../components/InterviewCard';
import { Card } from '../components/Card';
import { Filter, PlayCircle, CheckCircle2, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/Button';

export const History = () => {
  const [interviews, setInterviews] = useState([]);
  const [filterType, setFilterType] = useState('All'); // 'All', 'technical', 'hr'
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null); // { type: 'success' | 'error', message: string }

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const list = await apiService.getInterviews();
        setInterviews(list);
      } catch (err) {
        console.error('Failed to load history from backend', err);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  const handleDelete = async (id) => {
    try {
      await apiService.deleteInterview(id);
      setInterviews(prev => prev.filter(item => (item._id || item.id) !== id));
      setNotification({
        type: 'success',
        message: 'Interview session and associated records deleted successfully.',
      });
      setTimeout(() => setNotification(null), 4000);
    } catch (err) {
      console.error('Failed to delete interview', err);
      setNotification({
        type: 'error',
        message: err.message || 'Failed to delete interview record.',
      });
      setTimeout(() => setNotification(null), 4000);
      throw err;
    }
  };

  const filtered = interviews.filter(item => {
    if (filterType === 'All') return true;
    return (item.type || '').toLowerCase() === filterType.toLowerCase();
  });

  const formattedList = filtered.map(i => {
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
    <div className="history-page container" style={{ paddingTop: '2rem', maxWidth: '1000px' }}>
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h2>My Interview History</h2>
          <p className="subtitle">Database records of your past mock interview sessions.</p>
        </div>

        <Link to="/interview/setup">
          <Button icon={PlayCircle}>Start New Interview</Button>
        </Link>
      </div>

      {/* Notification Toast/Banner */}
      {notification && (
        <div style={{
          padding: '0.75rem 1.25rem',
          marginBottom: '1.5rem',
          borderRadius: 'var(--radius-md, 8px)',
          fontSize: '0.9rem',
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          background: notification.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          color: notification.type === 'success' ? 'var(--success, #10b981)' : 'var(--danger, #ef4444)',
          border: `1px solid ${notification.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
        }}>
          {notification.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="filter-bar card flex-between" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          <Filter size={18} /> Filter by Track:
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {[
            { label: 'All', value: 'All' },
            { label: 'Technical', value: 'technical' },
            { label: 'HR', value: 'hr' }
          ].map(opt => (
            <button
              key={opt.value}
              className={`filter-btn ${filterType === opt.value ? 'active' : ''}`}
              onClick={() => setFilterType(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* History List */}
      {loading ? (
        <Card className="text-center" style={{ padding: '2rem' }}>Loading interview history from database...</Card>
      ) : formattedList.length === 0 ? (
        <Card className="text-center empty-card" style={{ padding: '3rem' }}>
          <p className="subtitle">No interview records found for track filter "{filterType}".</p>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {formattedList.map(item => (
            <InterviewCard key={item.id} interview={item} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
};
