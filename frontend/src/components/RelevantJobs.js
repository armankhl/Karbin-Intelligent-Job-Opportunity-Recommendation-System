import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import JobCard from './JobCard'; // Import our reusable JobCard

const RelevantJobs = () => {
    const [relevantJobs, setRelevantJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const { isAuthenticated, logout } = useAuth();

    useEffect(() => {
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }

        const fetchRelevantJobs = async () => {
            const token = localStorage.getItem('authToken');
            if (!token) {
                setLoading(false); return;
            }

            try {
                // Call the existing /api/jobs endpoint with the relevance sort
                const params = new URLSearchParams({
                    sortBy: 'relevance',
                    page: 1, // We only want the first page for the homepage
                });

                const response = await axios.get(`http://127.0.0.1:5000/api/jobs?${params.toString()}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                // We'll show 6 jobs in this section
                setRelevantJobs(response.data.jobs.slice(0, 6));

            } catch (err) {
                console.error("Could not fetch relevant jobs:", err);
                if (err.response && [401, 422].includes(err.response.status)) {
                    logout();
                }
            } finally {
                setLoading(false);
            }
        };

        fetchRelevantJobs();
    }, [isAuthenticated, logout]);

    // Fail silently if not authenticated, loading, or if there are no results.
    if (!isAuthenticated || loading || relevantJobs.length === 0) {
        return null;
    }

    return (
        <div className="job-list-section" style={{ backgroundColor: '#f0f5ff' }}>
            <div className="container">
                <h2>مرتبط‌ترین فرصت‌های شغلی</h2>
                <div className="job-grid">
                    {relevantJobs.map(job => (
                        <JobCard key={job.id} job={job} />
                    ))}
                </div>
                <div className="view-more-container">
                    {/* This button can link to the full jobs page with the relevance sort pre-selected */}
                    <Link to="/jobs?sortBy=relevance" className="view-more-button">
                        مشاهده همه موارد
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default RelevantJobs;