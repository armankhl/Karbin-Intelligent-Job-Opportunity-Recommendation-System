import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => (
  <header className="header container">
    <Link to="/" className="logo">کاربین</Link>
    <nav className="nav-links">
      <Link to="/jobs">فرصت‌های شغلی</Link>
      <Link to="/resume-builder">رزومه‌ساز</Link>
      <Link to="/for-employers">بخش کارفرمایان</Link>
    </nav>
    <button className="auth-button">ورود | ثبت نام</button>
  </header>
);

export default Header;