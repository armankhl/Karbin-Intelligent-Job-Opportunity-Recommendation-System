import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Use axios directly
import { useAuth } from '../context/AuthContext';

const Recommendations = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { isAuthenticated, token, logout } = useAuth(); // Get token and logout

    useEffect(() => {
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }

        const fetchRecommendations = async () => {
            if (!isAuthenticated || !token) {
                setLoading(false);
                return;
            }

            try {
                const response = await axios.get('http://127.0.0.1:5000/api/recommendations?top_k=6', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                setRecommendations(response.data);
            } catch (err) {
                setError('Could not fetch recommendations.');
                if (err.response && [401, 422].includes(err.response.status)) {
                    logout();
                }
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [isAuthenticated, token, logout]);

    if (!isAuthenticated) {
        return null;
    }

    if (loading) {
        return <div className="container"><p>در حال بارگذاری پیشنهادات شغلی برای شما...</p></div>;
    }

    if (error) {
        return <div className="container"><p>{error}</p></div>;
    }

    if (recommendations.length === 0) {
        return (
            <div className="container">
                <h2>پیشنهادات شغلی برای شما</h2>
                <p>پیشنهاد مناسبی یافت نشد. لطفا پروفایل خود را تکمیل کنید.</p>
            </div>
        );
    }

    return (
        <div className="job-list-section" style={{ backgroundColor: '#f0f5ff' }}>
            <div className="container">
                <h2>پیشنهادات شغلی برای شما</h2>
                <div className="job-grid">
                    {recommendations.map(job => (
                        <div key={job.id} className="job-card">
                            <h3>{job.title}</h3>
                            <p className="job-card-info">🏢 {job.company_name}</p>
                            <p className="job-card-info">📍 {job.city}</p>
                            <p className="job-card-info" style={{fontSize: '0.8rem', color: '#007bff'}}>
                                ✨ {job.reason} (Score: {job.score.toFixed(2)})
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Recommendations;