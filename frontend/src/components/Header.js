import React, { useState, useEffect, useCallback } from 'react'; // 1. Import useCallback
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoginPromptModal from './LoginPromptModal';
import ProfileDropdown from './ProfileDropdown';

const Header = () => {
    const navigate = useNavigate();
    const { isAuthenticated, user, logout } = useAuth();
    
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [lastScrollY, setLastScrollY] = useState(0);
    const [isHeaderVisible, setHeaderVisible] = useState(true);

    // --- FIX: The controlHeader function is now wrapped in useCallback ---
    // This function will only be recreated if `lastScrollY` changes.
    const controlHeader = useCallback(() => {
        if (typeof window !== 'undefined') {
            if (window.scrollY > lastScrollY && window.scrollY > 100) {
                setHeaderVisible(false);
            } else {
                setHeaderVisible(true);
            }
            setLastScrollY(window.scrollY);
        }
    }, [lastScrollY]); // The dependency for useCallback

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.addEventListener('scroll', controlHeader);
            return () => window.removeEventListener('scroll', controlHeader);
        }
    // --- FIX: We now safely include `controlHeader` in the dependency array ---
    }, [controlHeader]);

    const handleProtectedLinkClick = (path) => {
        if (isAuthenticated) {
            navigate(path);
        } else {
            setIsModalOpen(true);
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
            <header className={`header ${isHeaderVisible ? 'header-visible' : 'header-hidden'}`}>
                <div className="container header-content">
                    <Link to="/" className="logo">کاربین</Link>
                    <nav className="nav-links">
                        <Link to="/">خانه</Link>
                        <Link to="/jobs">فرصت‌های شغلی</Link>
                        <button onClick={() => handleProtectedLinkClick('/recommendations')} className="nav-button-link">
                            فرصت‌های پیشنهادی
                        </button>
                    </nav>
                    <div className="header-auth-section">
                        {isAuthenticated && user ? (
                            <ProfileDropdown user={user} onLogout={logout} />
                        ) : (
                            <button className="auth-button" onClick={() => navigate('/login')}>
                                ورود | ثبت نام
                            </button>
                        )}
                    </div>
                </div>
            </header>
        </>
    );
};

export default Header;