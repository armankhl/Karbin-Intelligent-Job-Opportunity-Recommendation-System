import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import HomePage from './HomePage';
import UserLogin from './pages/auth/UserLogin';
import LoginPassword from './pages/auth/LoginPassword';
import UserSignup from './pages/auth/UserSignup';
import ProfilePage from './pages/ProfilePage';
import RecommendedJobsPage from './pages/RecommendedJobsPage';
import JobsHubPage from './pages/JobsHubPage';
import VerifyEmail from './pages/auth/VerifyEmail';

// Placeholders for other pages
const ForgotPassword = () => <div>Forgot Password Page</div>;

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<UserLogin />} />
          <Route path="/login-password" element={<LoginPassword />} />
          <Route path="/signup" element={<UserSignup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/recommendations" element={<RecommendedJobsPage />} />
          <Route path="/jobs" element={<JobsHubPage />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;