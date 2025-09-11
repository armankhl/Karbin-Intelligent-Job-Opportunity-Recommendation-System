import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoginPromptModal from './LoginPromptModal';

const Header = () => {
    const navigate = useNavigate();
    const { isAuthenticated, logout } = useAuth();
    const [isModalOpen, setIsModalOpen] = useState(false);

    const [lastScrollY, setLastScrollY] = useState(0);
    const [isHeaderVisible, setHeaderVisible] = useState(true);

    const controlHeader = () => {
        if (typeof window !== 'undefined') {
            if (window.scrollY > lastScrollY && window.scrollY > 100) { // Hide only after scrolling a bit
                setHeaderVisible(false);
            } else {
                setHeaderVisible(true);
            }
            setLastScrollY(window.scrollY);
        }
    };

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.addEventListener('scroll', controlHeader);
            return () => {
                window.removeEventListener('scroll', controlHeader);
            };
        }
    }, [lastScrollY]);

    const handleProtectedLinkClick = (path) => {
        if (isAuthenticated) {
            navigate(path);
        } else {
            setIsModalOpen(true);
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
            {/* The outer header is now full-width */}
            <header className={`header ${isHeaderVisible ? 'header-visible' : 'header-hidden'}`}>
                {/* This inner div now acts as the centered container for the content */}
                <div className="container header-content">
                    <Link to="/" className="logo">کاربین</Link>
                    <nav className="nav-links">
                        <Link to="/jobs">فرصت‌های شغلی</Link>
                        <button onClick={() => handleProtectedLinkClick('/profile')} className="nav-button-link">
                            پروفایل من
                        </button>
                        <button onClick={() => handleProtectedLinkClick('/recommendations')} className="nav-button-link">
                            فرصت‌های شغلی پیشنهادی
                        </button>
                    </nav>
                    <button className="auth-button" onClick={handleAuthClick}>
                        {isAuthenticated ? 'خروج از حساب' : 'ورود | ثبت نام'}
                    </button>
                </div>
            </header>
        </>
    );
};

export default Header;