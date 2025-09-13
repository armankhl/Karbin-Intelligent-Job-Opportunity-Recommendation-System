import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../../AuthForm.css';
import { useAuth } from '../../context/AuthContext';

const UserSignup = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { login } = useAuth();

    const initialEmail = location.state?.email || '';
    const [email, setEmail] = useState(initialEmail);
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            alert("Passwords do not match!");
            return;
        }
        try {
            // Step 1: Register the user
            const registerResponse = await axios.post('http://127.0.0.1:5000/api/auth/register', {email, password });
            
            if (registerResponse.data.access_token) {
                // Step 2: Log the user in to get a token for the next request
                const token = registerResponse.data.access_token;
                login(token); // Update global auth state

                // Step 3: Automatically request a verification email
                await axios.post('http://127.0.0.1:5000/api/auth/send-verification', {}, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                // Step 4: Redirect to the verification page, passing the email
                navigate('/verify-email', { state: { email } });
            }
        } catch (error) {
            console.error('Registration failed:', error);
            alert('Registration failed. The email might already be in use.');
        }
    };

  return (
    <div className="auth-container">
      <div className="auth-logo">▲■●</div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>ثبت‌نام کارجو</h1>
        <p>به کاربین خوش آمدید</p>
          <input  type="email" name="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="auth-input" placeholder="ایمیل" required />
          <input type="password" name="new-password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className="auth-input" placeholder="رمز ورود" required />
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="auth-input" placeholder="تکرار رمز عبور" required />
        <button type="submit" className="auth-button-primary">ثبت نام</button>
      </form>
    </div>
  );
};

export default UserSignup;