import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios'; // Use axios directly
import '../../AuthForm.css';

const UserLogin = () => {
  const [email, setEmail] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // FIX: Use the 'api' client and a relative path
      const response = await axios.post('http://127.0.0.1:5000/api/auth/check-email', { email });
      if (response.data.exists) {
        navigate('/login-password', { state: { email } });
      } else {
        navigate('/signup', { state: { email } });
      }
    } catch (error) {
      console.error('Error checking email:', error);
    }
  };

  // ... (The JSX part of the component is unchanged and correct) ...
  return (
    <div className="auth-container">
      <div className="auth-logo">▲■●</div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>ورود یا ثبت‌نام کارجو</h1>
        <p>ایمیل خود را وارد کنید</p>
        <input
          type="email"
          className="auth-input"
          placeholder="longliveiran@gmail.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          name="email"
          autoComplete="email"
        />
        <button type="submit" className="auth-button-primary">ورود</button>
        <a href="/employer-login" className="auth-link">کارفرما هستید؟ ورود به بخش کارفرمایی</a>
      </form>
    </div>
  );
};

export default UserLogin;