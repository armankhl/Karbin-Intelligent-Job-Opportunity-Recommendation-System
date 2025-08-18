import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => (
  <footer className="footer">
    <div className="container">
      <div className="footer-grid">
        <div className="footer-about">
          <h4>کاربین</h4>
          <p>پلتفرم هوشمند کاریابی برای کمک به متخصصان برای یافتن بهترین فرصت‌ها و کمک به شرکت‌ها برای جذب بهترین استعدادها.</p>
        </div>
        <div className="footer-column">
          <h5>درباره ما</h5>
          <ul>
            <li><Link to="/about-company">درباره شرکت</Link></li>
            <li><Link to="/team">تیم ما</Link></li>
            <li><Link to="/press">اخبار</Link></li>
          </ul>
        </div>
        <div className="footer-column">
          <h5>همکاری با ما</h5>
          <ul>
            <li><Link to="/jobs">فرصت‌های شغلی</Link></li>
            <li><Link to="/remote-jobs">همکاری از راه دور</Link></li>
            <li><Link to="/post-a-job">ثبت آگهی شغلی</Link></li>
          </ul>
        </div>
        <div className="footer-column">
          <h5>منابع</h5>
          <ul>
            <li><Link to="/blog">وبلاگ</Link></li>
            <li><Link to="/guides">راهنما</Link></li>
            <li><Link to="/faq">سوالات متداول</Link></li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <p>تمامی حقوق برای کاربین محفوظ است. © 1404</p>
      </div>
    </div>
  </footer>
);

export default Footer;