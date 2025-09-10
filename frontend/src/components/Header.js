import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoginPromptModal from './LoginPromptModal';

const Header = () => {
    const navigate = useNavigate();
    const { isAuthenticated, logout } = useAuth();
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleProtectedLinkClick = (path) => {
        if (isAuthenticated) {
            navigate(path);
        } else {
            setIsModalOpen(true); // Open the modal if not logged in
        }
    };

    const handleAuthClick = () => {
        if (isAuthenticated) {
            logout();
            navigate('/');
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
                    {/* Public link to all jobs */}
                    <Link to="/jobs">فرصت‌های شغلی</Link>

                    {/* Protected link to the profile page */}
                    <button onClick={() => handleProtectedLinkClick('/profile')} className="nav-button-link">
                        پروفایل من
                    </button>
                    
                    {/* REVISED: Protected link to the recommendations page */}
                    <button onClick={() => handleProtectedLinkClick('/recommendations')} className="nav-button-link">
                    فرصت‌های شغلی پیشنهادی
                    </button>
                </nav>
                <button className="auth-button" onClick={handleAuthClick}>
                    {isAuthenticated ? 'خروج از حساب' : 'ورود | ثبت نام'}
                </button>
            </header>
        </>
    );
};

export default Header;