import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

const Recommendations = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false); // Changed to boolean
    const { isAuthenticated, logout } = useAuth();

    useEffect(() => {
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }

        const fetchRecommendations = async () => {
            const token = localStorage.getItem('authToken');
            if (!token) {
                setLoading(false); return;
            }

            try {
                const response = await axios.get('http://127.0.0.1:5000/api/recommendations?top_k=6', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                setRecommendations(response.data);
            } catch (err) {
                setError(true); // Set error to true
                if (err.response && [401, 422].includes(err.response.status)) {
                    logout();
                }
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [isAuthenticated, logout]);

    // --- REVISED: Fail silently on error or while loading ---
    if (!isAuthenticated || loading || error || recommendations.length === 0) {
        return null;
    }

    return (
        <div className="job-list-section" style={{ backgroundColor: '#f0f5ff' }}>
            <div className="container">
                <h2>پیشنهادات شغلی برای شما</h2>
                <div className="job-grid">
                    {recommendations.map(job => (
                        // --- REVISED: Job card now matches the homepage style ---
                        <div key={job.id} className="job-card">
                            <h3>{job.title}</h3>
                            <p className="job-card-info">🏢 {job.company_name}</p>
                            <p className="job-card-info">📍 {job.city || 'نامشخص'}</p>
                            <p className="job-card-info" style={{fontSize: '0.8rem', color: '#007bff'}}>
                                ✨ {job.reason}
                            </p>
                            <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="job-details-link">
                                مشاهده جزئیات
                            </a>
                        </div>
                    ))}
                </div>
                {/* --- NEW: "See More" Button --- */}
                <div className="view-more-container">
                    <Link to="/recommendations" className="view-more-button">
                        مشاهده همه پیشنهادات
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default Recommendations;