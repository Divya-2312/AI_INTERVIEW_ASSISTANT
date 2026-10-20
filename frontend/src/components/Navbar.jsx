import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Bot, User, LogOut, History, PlayCircle, LayoutDashboard, Menu, X, Sparkles } from 'lucide-react';

export const Navbar = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <header className="navbar-wrapper">
      <nav className="navbar container">
        <Link to={isAuthenticated ? "/dashboard" : "/"} className="navbar-logo">
          <div className="logo-icon">
            <Bot size={24} color="#ffffff" />
          </div>
          <span className="logo-text">AI Interview <span className="logo-highlight">Assistant</span></span>
        </Link>

        {/* Desktop Links */}
        <div className="navbar-links desktop-links">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className={`nav-item ${isActive('/dashboard') ? 'active' : ''}`}>
                <LayoutDashboard size={18} /> Dashboard
              </Link>
              <Link to="/interview/setup" className={`nav-item ${isActive('/interview/setup') ? 'active' : ''}`}>
                <PlayCircle size={18} /> Start Interview
              </Link>
              <Link to="/history" className={`nav-item ${isActive('/history') ? 'active' : ''}`}>
                <History size={18} /> History
              </Link>
              <Link to="/profile" className={`nav-item ${isActive('/profile') ? 'active' : ''}`}>
                <User size={18} /> Profile
              </Link>
              <button onClick={handleLogout} className="btn btn-outline btn-sm logout-btn">
                <LogOut size={16} /> Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`}>Home</Link>
              <Link to="/login" className="btn btn-secondary btn-sm">Login</Link>
              <Link to="/register" className="btn btn-primary btn-sm">Register</Link>
            </>
          )}
        </div>

        {/* Mobile menu toggle */}
        <button 
          className="mobile-menu-toggle" 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </nav>

      {/* Mobile Links */}
      {mobileMenuOpen && (
        <div className="mobile-dropdown">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" onClick={() => setMobileMenuOpen(false)}>Dashboard</Link>
              <Link to="/interview/setup" onClick={() => setMobileMenuOpen(false)}>Start Interview</Link>
              <Link to="/history" onClick={() => setMobileMenuOpen(false)}>History</Link>
              <Link to="/profile" onClick={() => setMobileMenuOpen(false)}>Profile</Link>
              <button onClick={() => { setMobileMenuOpen(false); handleLogout(); }}>Logout</button>
            </>
          ) : (
            <>
              <Link to="/" onClick={() => setMobileMenuOpen(false)}>Home</Link>
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>Login</Link>
              <Link to="/register" onClick={() => setMobileMenuOpen(false)}>Register</Link>
            </>
          )}
        </div>
      )}
    </header>
  );
};
