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
      // Step 1: Attempt to log in
      const response = await axios.post('http://127.0.0.1:5000/api/auth/login', { email, password });
      
      const token = response.data.access_token;
      const status = response.data.status;

      if (token) {
        // Step 2: Log the user in globally, regardless of verification status
        login(token);

        // Step 3: Check the verification status and redirect accordingly
        if (status === 'unverified') {
          // User needs to verify. Trigger a new code and redirect.
          try {
            await axios.post('http://127.0.0.1:5000/api/auth/send-verification', {}, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            // Redirect to the verification page
            navigate('/verify-email', { state: { email } });
          } catch (resendError) {
            console.error("Failed to auto-resend verification code:", resendError);
            // Even if resend fails, still send them to the page to try manually
            navigate('/verify-email', { state: { email } });
          }
        } else {
          // User is verified, proceed to the homepage
          navigate('/');
        }
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