import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { User, GraduationCap, Target, Calendar, LogOut } from 'lucide-react';

export const Profile = () => {
  const { user, logout, deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [profileData, setProfileData] = useState(user);
  const [interviewCount, setInterviewCount] = useState(0);

  // Modal and deletion states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  useEffect(() => {
    const loadProfileAndStats = async () => {
      try {
        const meRes = await apiService.getMe();
        if (meRes.success && meRes.user) {
          setProfileData(meRes.user);
        }
        const interviews = await apiService.getInterviews();
        setInterviewCount(interviews.length);
      } catch (err) {
        console.error('Failed to load profile', err);
      }
    };

    loadProfileAndStats();
  }, []);

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    setDeleteError('');
    try {
      await deleteAccount();
      setShowDeleteModal(false);
      navigate('/login', {
        replace: true,
        state: { accountDeleted: true },
      });
    } catch (err) {
      console.error('Failed to delete account', err);
      setDeleteError(err.message || 'Failed to delete account from server. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <div className="profile-page container" style={{ paddingTop: '2rem', maxWidth: '850px' }}>
      <div className="profile-header card flex-between" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div className="profile-avatar">
            <User size={36} color="#ffffff" />
          </div>
          <div>
            <h2>{profileData?.name || 'Student Account'}</h2>
            <p className="subtitle">{profileData?.email}</p>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: '1.5rem', marginBottom: '2rem' }}>
        <Card>
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
            Academic & Target Details
          </h3>
          <div className="profile-info-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <GraduationCap size={18} color="var(--primary)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Degree Program</div>
                <div style={{ fontWeight: 600 }}>{profileData?.degree || 'B.Tech Computer Science'}</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Target size={18} color="var(--primary)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target Career Role</div>
                <div style={{ fontWeight: 600 }}>{profileData?.targetRole || 'Software Development Engineer (SDE)'}</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Calendar size={18} color="var(--primary)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Institution</div>
                <div style={{ fontWeight: 600 }}>{profileData?.university || 'Anna University'}</div>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
            Account Stats
          </h3>
          <div className="profile-stats-grid" style={{ padding: '1rem', textAlign: 'center', backgroundColor: '#f8fafc', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--primary)' }}>
              {interviewCount}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              Total Sessions Stored
            </div>
          </div>
        </Card>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '3rem' }}>
        {/* Account Security */}
        <Card className="flex-between" style={{ alignItems: 'center' }}>
          <div>
            <h4>Account Security</h4>
            <p className="subtitle" style={{ fontSize: '0.85rem' }}>
              Authenticated via JWT token stored in secure context
            </p>
          </div>
          <Button variant="secondary" icon={LogOut} onClick={logout} id="logout-btn">
            Logout Account
          </Button>
        </Card>

        {/* Delete Your Account */}
        <Card className="flex-between" style={{ alignItems: 'center' }}>
          <div>
            <h4>Delete Your Account</h4>
            <p className="subtitle" style={{ fontSize: '0.85rem' }}>
              Permanently delete your account and all associated data from the server
            </p>
          </div>
          <Button
            variant="danger"
            onClick={() => {
              setDeleteError('');
              setShowDeleteModal(true);
            }}
            id="delete-account-btn"
          >
            Delete Account
          </Button>
        </Card>
      </div>

      {/* Delete Account Confirmation Modal */}
      {showDeleteModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !isDeleting) {
              setShowDeleteModal(false);
            }
          }}
        >
          <div
            className="modal-card card"
            style={{
              maxWidth: '460px',
              padding: '1.75rem',
            }}
          >
            <h3 id="delete-modal-title" style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', color: '#111827' }}>
              Delete Your Account?
            </h3>

            <p style={{ fontSize: '0.9rem', color: '#4b5563', lineHeight: 1.5, margin: '0.75rem 0 1.25rem' }}>
              Are you sure you want to delete your account <strong>({profileData?.email})</strong>?
              All your interview history, practice answers, and performance evaluations will be
              permanently erased from the server.
            </p>

            {deleteError && (
              <div
                style={{
                  padding: '0.75rem',
                  backgroundColor: '#fee2e2',
                  color: '#991b1b',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  marginBottom: '1.25rem',
                }}
              >
                {deleteError}
              </div>
            )}

            <div className="flex-between" style={{ gap: '0.75rem', marginTop: '1.5rem' }}>
              <Button
                variant="secondary"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
                style={{ flex: 1 }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDeleteAccount}
                disabled={isDeleting}
                style={{ flex: 1.2 }}
                id="confirm-delete-account-btn"
              >
                {isDeleting ? 'Deleting...' : 'Delete Account'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
