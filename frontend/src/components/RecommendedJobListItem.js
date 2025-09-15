import React from 'react';

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
    // const postedDate = new Date(job.scraped_at).toLocaleDateString('fa-IR');
    
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
                <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="details-button">
                    مشاهده جزئیات
                </a>
            </div>
        </div>
    );
};

export default RecommendedJobListItem;