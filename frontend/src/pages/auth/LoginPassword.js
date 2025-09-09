import React, { useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import axios from 'axios'; // Use axios directly
import '../../AuthForm.css';
import { useAuth } from '../../context/AuthContext';

const LoginPassword = () => {
  const location = useLocation();
  const email = location.state?.email;
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // FIX: Use the 'api' client and a relative path
      const response = await axios.post('http://127.0.0.1:5000/api/auth/login', { email, password });
      if (response.data.access_token) {
          login(response.data.access_token);
          navigate('/');
      }
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed: Invalid credentials.');
    }
  };

  // ... (The JSX part of the component is unchanged and correct) ...
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
          name="password"
          autoComplete="current-password"
        />
        <button type="submit" className="auth-button-primary">ورود</button>
        <Link to="/forgot-password" className="auth-link">رمز عبور خود را فراموش کرده‌اید؟</Link>
      </form>
    </div>
  );
};

export default LoginPassword;