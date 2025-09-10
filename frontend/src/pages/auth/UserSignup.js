import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios'; // Use axios directly
import '../../AuthForm.css';
import { useAuth } from '../../context/AuthContext'; // FIX 2: Import useAuth to get the login function

const UserSignup = () => {
    const location = useLocation();
    const initialEmail = location.state?.email || '';
    const [name, setName] = useState('');
    const [email, setEmail] = useState(initialEmail);
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const navigate = useNavigate();
    const { login } = useAuth(); // FIX 3: Get the login function from the context

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            alert("Passwords do not match!");
            return;
        }
        try {
            // FIX 4: Use 'api' client and store the result in 'response'
            const response = await axios.post('http://127.0.0.1:5000/api/auth/register', { name, email, password });
            if (response.data.access_token) {
              login(response.data.access_token); // Now this will work
              navigate('/');
            }
        } catch (error) {
            console.error('Registration failed:', error);
            alert('Registration failed. Email might already be in use.');
        }
    };

    // ... (The JSX part of the component is unchanged and correct) ...
    return (
      <div className="auth-container">
        <div className="auth-logo">▲■●</div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <h1>ثبت‌نام کارجو</h1>
          <p>به کاربین خوش آمدید</p>
          <input  type="email" name="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="auth-input" placeholder="ایمیل" required />
          <input type="text" name="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className="auth-input" placeholder="نام و نام خانوادگی" required />
          <input type="password" name="new-password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className="auth-input" placeholder="رمز ورود" required />
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="auth-input" placeholder="تایید رمز ورود" required />
          <button type="submit" className="auth-button-primary">ثبت نام</button>
        </form>
      </div>
    );
};

export default UserSignup;