import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './ProfileDropdown.css';
import DefaultAvatar from '../assets/default-avatar.svg'; // <-- IMPORT THE NEW SVG

const ProfileDropdown = ({ user, onLogout }) => {
    const [isOpen, setIsOpen] = useState(false);
    const navigate = useNavigate();
    const dropdownRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleNavigation = (path) => {
        navigate(path);
        setIsOpen(false);
    };

    const handleLogout = () => {
        onLogout();
        setIsOpen(false);
    };

    return (
        <div className="profile-dropdown" ref={dropdownRef}>
            <button onClick={() => setIsOpen(!isOpen)} className="profile-trigger">
                {/* Use the imported SVG as an image */}
                <span className={`dropdown-arrow-icon ${isOpen ? 'open' : ''}`}>▼</span>
                <img src={DefaultAvatar} alt="Profile" className="profile-trigger-avatar" />
            </button>
            

            {isOpen && (
                <div className="dropdown-menu">
                    <div className="dropdown-header">
                        {/* Use the imported SVG here as well */}
                        <img src={DefaultAvatar} alt="User Avatar" className="dropdown-avatar" />
                        <div className="dropdown-info">
                            <span className="user-name">{user.first_name || 'کاربر'} {user.last_name || 'جدید'}</span>
                            <span className="user-title">{user.professional_title || 'پروفایل خود را تکمیل کنید'}</span>
                        </div>
                    </div>
                    <ul className="dropdown-list">
                        <li className="dropdown-item" onClick={() => handleNavigation('/profile')}>
                            📄 رزومه من
                        </li>
                        <li className="dropdown-item" onClick={() => handleNavigation('/recommendations')}>
                            ✨ مشاغل پیشنهادی
                        </li>
                        <li className="dropdown-item logout" onClick={handleLogout}>
                            🚪 خروج از حساب
                        </li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default ProfileDropdown;