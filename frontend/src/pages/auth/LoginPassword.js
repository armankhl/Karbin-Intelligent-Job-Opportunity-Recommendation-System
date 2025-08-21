import React, { useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../../AuthForm.css';

const LoginPassword = () => {
  const location = useLocation();
  const email = location.state?.email; // Get email from previous page
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
        await axios.post('http://127.0.0.1:5000/api/auth/login', { email, password });
        alert('ورود شما با موفقیت انجام شد.');
        // Redirect to user home page
        navigate('/'); 
    } catch (error) {
        console.error('Login failed:', error);
        alert('Login failed: Invalid credentials.');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-logo">▲■●</div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>ورود کارجو</h1>
        <p>رمز عبور خود را وارد کنید</p>
        <input
          type="password"
          className="auth-input"
          placeholder="رمز عبور"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" className="auth-button-primary">ورود</button>
        <Link to="/forgot-password" className="auth-link">رمز عبور خود را فراموش کرده‌اید؟</Link>
      </form>
    </div>
  );
};

export default LoginPassword;