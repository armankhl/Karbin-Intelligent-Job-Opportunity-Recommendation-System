import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../../AuthForm.css'; // Reuse the same styles

const VerifyEmail = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email; // Get email from the signup page

    const [code, setCode] = useState('');
    const [resendTimer, setResendTimer] = useState(60);
    const [isResending, setIsResending] = useState(false);

    // Countdown timer effect
    useEffect(() => {
        if (resendTimer > 0) {
            const timerId = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
            return () => clearTimeout(timerId);
        }
    }, [resendTimer]);

    const handleVerify = async (e) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('authToken');
            await axios.post('http://127.0.0.1:5000/api/auth/verify-code', { code }, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            alert('Email verified successfully! Welcome to KarBin.');
            navigate('/'); // Redirect to homepage on success
        } catch (error) {
            console.error('Verification failed:', error);
            alert(error.response?.data?.error || 'Invalid or expired code.');
        }
    };

    const handleResend = async () => {
        if (resendTimer > 0) return; // Prevent clicking while timer is active
        setIsResending(true);
        try {
            const token = localStorage.getItem('authToken');
            await axios.post('http://127.0.0.1:5000/api/auth/send-verification', {}, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setResendTimer(60); // Reset the timer
            alert('A new verification code has been sent.');
        } catch (error) {
            console.error('Resend failed:', error);
            alert(error.response?.data?.error || 'Failed to resend code.');
        } finally {
            setIsResending(false);
        }
    };

    if (!email) {
        // Handle case where user lands here directly without an email
        return (
            <div className="auth-container">
                <p>Invalid state. Please start from the signup page.</p>
            </div>
        );
    }
    
    return (
        <div className="auth-container">
            <div className="auth-logo">▲■●</div>
            <form className="auth-form" onSubmit={handleVerify}>
                <h1>تایید ایمیل</h1>
                <p>کد ۶ رقمی ارسال شده به <strong>{email}</strong> را وارد کنید.</p>
                <input
                    type="text"
                    className="auth-input"
                    placeholder="کد تایید"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    required
                    maxLength="6"
                />
                <button type="submit" className="auth-button-primary">تایید</button>
            </form>
            <div style={{ marginTop: '20px' }}>
                <button 
                    onClick={handleResend} 
                    disabled={resendTimer > 0 || isResending}
                    className="auth-link"
                    style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                >
                    {isResending 
                        ? 'در حال ارسال...' 
                        : (resendTimer > 0 ? `ارسال مجدد کد (${resendTimer})` : 'ارسال مجدد کد')}
                </button>
            </div>
        </div>
    );
};

export default VerifyEmail;