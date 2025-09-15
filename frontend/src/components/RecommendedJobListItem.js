import React from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

// Helper function for formatting salary (unchanged and correct)
const formatSalary = (salary, contract) => {
    const contractText = contract || 'تمام وقت';
    if (!salary || salary.toLowerCase() === 'توافقی') return `قرارداد ${contractText} (حقوق توافقی)`;
    if (salary.toLowerCase() === 'قانون کار') return `قرارداد ${contractText} (طبق قانون کار)`;
    try {
        const number = parseInt(salary, 10);
        if (isNaN(number)) return `قرارداد ${contractText} (حقوق توافقی)`;
        const formattedNumber = new Intl.NumberFormat('en-US').format(number);
        return `قرارداد ${contractText} (حقوق از ${formattedNumber} تومان)`;
    } catch (e) {
        return `قرارداد ${contractText} (حقوق توافقی)`;
    }
};

const RecommendedJobListItem = ({ job }) => {
    const { isAuthenticated } = useAuth();

    const handleJobClick = () => {
        if (isAuthenticated) {
            const token = localStorage.getItem('authToken');
            axios.post('http://127.0.0.1:5000/api/interactions/click', 
                { job_id: job.id },
                { headers: { 'Authorization': `Bearer ${token}` } }
            ).catch(error => {
                console.error("Failed to log job click:", error);
            });
        }
    };

    // --- NEW: A robust function to generate the rich reason text ---
    const generateReasonText = () => {
        const reasonData = job.reason || {};
        const matched_skills = reasonData.matched_skills || [];
        const details = reasonData.details || {};
        
        let reasonParts = [];

        // Part 1: Add matched skills if they exist
        if (matched_skills.length > 0) {
            reasonParts.push(`متناسب با مهارت‌ها: ${matched_skills.join('، ')}`);
        }

        // Part 2: Add a highlight for very recent jobs
        if (details.recency_score && details.recency_score > 0.9) {
            reasonParts.push("اخیراً منتشر شده");
        }

        // If after checking everything, we have no specific reasons, return a default.
        if (reasonParts.length === 0) {
            return "شباهت بالا با پروفایل شما";
        }

        // Join the parts with a separator for a clean look.
        return reasonParts.join(' | ');
    };

    const reason_text = generateReasonText();

    return (
        <div className="job-list-item">
            <div className="job-item-logo">
                <span className="logo-placeholder">{job.company_name.charAt(0)}</span>
            </div>
            <div className="job-item-details">
                <div className="details-header">
                    <h2 className="job-title">{job.title}</h2>
                </div>
                <div className="details-body">
                    {/* --- REVISED: Changed <p> to <span> for better flexbox alignment --- */}
                    <span className="info-item">🏢 {job.company_name}</span>
                    <span className="info-item">📍 {job.city || 'نامشخص'}</span>
                    <span className="info-item">📄 {formatSalary(job.salary, job.contract_type)}</span>
                </div>
                {/* The reason is now on its own line for better readability */}
                <div className="details-reason">
                    <span className="info-item reason">
                        ✨ {reason_text} (امتیاز: {job.score.toFixed(2)})
                    </span>
                </div>
            </div>
            <div className="job-item-action">
                <a 
                    href={job.source_link} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="details-button"
                    onClick={handleJobClick}
                >
                    مشاهده جزئیات
                </a>
            </div>
        </div>
    );
};

export default RecommendedJobListItem;