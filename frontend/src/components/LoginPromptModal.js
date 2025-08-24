import React from 'react';
import './LoginPromptModal.css'; // We will create this CSS file next

const LoginPromptModal = ({ isOpen, onClose, onConfirm }) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <p>برای دسترسی به پروفایل من، لازم است ابتدا به حساب کاربریتان وارد شوید.</p>
                <div className="modal-actions">
                    <button onClick={onConfirm} className="modal-btn confirm">ورود | ثبت نام</button>
                    <button onClick={onClose} className="modal-btn cancel">لغو</button>
                </div>
            </div>
        </div>
    );
};

export default LoginPromptModal;