import React from 'react';
import { Link, useNavigate } from 'react-router-dom'; // Import useNavigate

const Header = () => {
  const navigate = useNavigate(); // Initialize the hook

  const handleAuthClick = () => {
    navigate('/login'); // Navigate to the login page
  };
  
  return (
    <header className="header container">
      <Link to="/" className="logo">کاربین</Link>
      <nav className="nav-links">
        <Link to="/jobs">فرصت‌های شغلی</Link>
        <Link to="/resume-builder">رزومه‌ساز</Link>
        <Link to="/for-employers">بخش کارفرمایان</Link>
      </nav>
      {/* Attach the onClick event */}
      <button className="auth-button" onClick={handleAuthClick}>ورود | ثبت نام</button>
    </header>
  );
};

export default Header;
