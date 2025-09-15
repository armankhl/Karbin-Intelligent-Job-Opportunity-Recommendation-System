import React from 'react';

// The helper function for formatting is unchanged and correct.
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

const JobListItem = ({ job }) => {
    const postedDate = new Date(job.scraped_at).toLocaleDateString('fa-IR');

    return (
        <div className="job-list-item">
            <div className="job-item-logo">
                <span className="logo-placeholder">{job.company_name.charAt(0)}</span>
            </div>
            <div className="job-item-details">
                <div className="details-header">
                    <h2 className="job-title">{job.title}</h2>
                    <span className="posted-date">{postedDate}</span>
                </div>
                {/* --- THE CORE CHANGE IS HERE --- */}
                {/* We are changing the container to a div and the items to <p> tags */}
                <div className="details-body">
                    <p className="info-item">🏢 {job.company_name}</p>
                    <p className="info-item">📍 {job.province || 'نامشخص'}</p>
                    <p className="info-item">📄 {formatSalary(job.salary, job.contract_type)}</p>
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

export default JobListItem;