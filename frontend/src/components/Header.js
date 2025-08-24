import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Import useAuth
import LoginPromptModal from './LoginPromptModal'; // Import the modal

const Header = () => {
    const navigate = useNavigate();
    const { isAuthenticated, logout } = useAuth(); // Use the auth context
    const [isModalOpen, setIsModalOpen] = useState(false); // State for modal

    const handleProfileClick = () => {
        if (isAuthenticated) {
            navigate('/profile');
        } else {
            setIsModalOpen(true); // Open the modal if not logged in
        }
    };

    const handleAuthClick = () => {
        if (isAuthenticated) {
            logout();
            navigate('/'); // Redirect to home on logout
        } else {
            navigate('/login');
        }
    };

    return (
        <>
            <LoginPromptModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onConfirm={() => {
                    setIsModalOpen(false);
                    navigate('/login');
                }}
            />
            <header className="header container">
                <Link to="/" className="logo">کاربین</Link>
                <nav className="nav-links">
                    <Link to="/jobs">فرصت‌های شغلی</Link>
                    {/* The profile link is now a button to handle the click logic */}
                    <button onClick={handleProfileClick} className="nav-button-link">پروفایل من</button>
                    <Link to="/for-employers">بخش کارفرمایان</Link>
                </nav>
                {/* Dynamically change button text */}
                <button className="auth-button" onClick={handleAuthClick}>
                    {isAuthenticated ? 'خروج از حساب' : 'ورود | ثبت نام'}
                </button>
            </header>
        </>
    );
};

export default Header;