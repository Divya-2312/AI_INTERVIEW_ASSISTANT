import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { User, GraduationCap, Target, Calendar, LogOut } from 'lucide-react';

export const Profile = () => {
  const { user, logout } = useAuth();
  const [profileData, setProfileData] = useState(user);
  const [interviewCount, setInterviewCount] = useState(0);

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

      <Card className="flex-between">
        <div>
          <h4>Account Security</h4>
          <p className="subtitle" style={{ fontSize: '0.85rem' }}>
            Authenticated via JWT token stored in secure context
          </p>
        </div>
        <Button variant="danger" icon={LogOut} onClick={logout}>
          Logout Account
        </Button>
      </Card>
    </div>
  );
};
