import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import HomePage from './HomePage';
import UserLogin from './pages/auth/UserLogin';
import LoginPassword from './pages/auth/LoginPassword';
import UserSignup from './pages/auth/UserSignup';
import ProfilePage from './pages/ProfilePage';
import RecommendedJobsPage from './pages/RecommendedJobsPage'; // IMPORT THE NEW PAGE

// Placeholders for other pages
const JobsPage = () => <div style={{textAlign: 'center', padding: '50px'}}><h2>صفحه فرصت‌های شغلی</h2></div>;
const ForgotPassword = () => <div>Forgot Password Page</div>;
const VerifyEmail = () => <div>Verify Email Page</div>;

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/login" element={<UserLogin />} />
          <Route path="/login-password" element={<LoginPassword />} />
          <Route path="/signup" element={<UserSignup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/recommendations" element={<RecommendedJobsPage />} /> {/* ADD THIS ROUTE */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;