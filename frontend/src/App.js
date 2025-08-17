import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import HomePage from './HomePage';

// Placeholders for the new pages
const JobsPage = () => <div style={{textAlign: 'center', padding: '50px'}}><h2>صفحه فرصت‌های شغلی</h2></div>;
const ResumeBuilderPage = () => <div style={{textAlign: 'center', padding: '50px'}}><h2>صفحه رزومه‌ساز</h2></div>;
const ForEmployersPage = () => <div style={{textAlign: 'center', padding: '50px'}}><h2>صفحه کارفرمایان</h2></div>;


function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/resume-builder" element={<ResumeBuilderPage />} />
          <Route path="/for-employers" element={<ForEmployersPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;