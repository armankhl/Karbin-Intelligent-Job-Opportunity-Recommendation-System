import React from 'react';

const JobCard = ({ job }) => (
  <div className="job-card">
    <h3>{job.title}</h3>
    <p className="job-card-info">🏢 {job.company_name}</p> 
    <p className="job-card-info">📍 {job.city || job.province || 'نامشخص'}</p>
    <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="job-details-link">
      مشاهده جزئیات
    </a>
  </div>
);

export default JobCard;