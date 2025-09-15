import React from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext'; // We need this to check if the user is logged in

// We include the helper function here to make the component self-contained.
const formatSalary = (salary, contract) => {
    const contractText = contract || 'تمام وقت';
    if (!salary || salary.toLowerCase() === 'توافقی') {
        return `قرارداد ${contractText} (حقوق توافقی)`;
    }
    if (salary.toLowerCase() === 'قانون کار') {
        return `قرارداد ${contractText} (طبق قانون کار)`;
    }
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
    const { isAuthenticated } = useAuth(); // Get the user's authentication status
    // const postedDate = new Date(job.scraped_at).toLocaleDateString('fa-IR');
    
    // --- NEW: Function to handle the click event ---
    const handleJobClick = () => {
        // Only log the click if the user is authenticated
        if (isAuthenticated) {
            const token = localStorage.getItem('authToken');
            
            // This is a "fire-and-forget" request. We don't wait for the response
            // before navigating the user, so their experience is instantaneous.
            axios.post('http://127.0.0.1:5000/api/interactions/click', 
                { job_id: job.id },
                { headers: { 'Authorization': `Bearer ${token}` } }
            ).catch(error => {
                // We can log the error to the console for debugging but won't show it to the user.
                console.error("Failed to log job click:", error);
            });
        }
    }
    // Format the reason text
    const matched_skills = job.reason?.matched_skills || [];
    const reason_text = matched_skills.length > 0 
        ? `متناسب با مهارت‌های شما در: ${matched_skills.join(', ')}` 
        : "شباهت بالا با رزومه شما";

    return (
        <div className="job-list-item">
            <div className="job-item-logo">
                <span className="logo-placeholder">{job.company_name.charAt(0)}</span>
            </div>
            <div className="job-item-details">
                <div className="details-header">
                    <h2 className="job-title">{job.title}</h2>
                    {/* <span className="posted-date">{postedDate}</span> */}
                </div>
                <div className="details-body">
                    <p className="info-item">🏢 {job.company_name}</p>
                    <p className="info-item">📍 {job.city || 'نامشخص'}</p>
                    <p className="info-item">📄 {formatSalary(job.salary, job.contract_type)}</p>
                    <p className="info-item reason">
                        ✨ {reason_text} (درصد اطمینان: {job.score.toFixed(2)})
                    </p>
                </div>
            </div>
            <div className="job-item-action">
                {/* --- REVISED: Added the onClick handler --- */}
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