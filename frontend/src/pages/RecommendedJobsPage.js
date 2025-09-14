import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './RecommendedJobsPage.css';

const RecommendedJobsPage = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { isAuthenticated, logout } = useAuth();

    useEffect(() => {
        const fetchRecommendations = async () => {
            if (!isAuthenticated) {
                setLoading(false);
                setError("برای مشاهده این صفحه باید وارد شوید.");
                return;
            }

            try {
                const token = localStorage.getItem('authToken');
                
                // top_k=24 is a reasonable number for a dedicated recommendations page.
                const response = await axios.get('http://127.0.0.1:5000/api/recommendations?top_k=24', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                setRecommendations(response.data);

            } catch (err) {
                setError('خطا در دریافت پیشنهادات. لطفا دوباره تلاش کنید.');
                console.error(err);
                if (err.response && [401, 422].includes(err.response.status)) {
                    logout();
                }
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [isAuthenticated, logout]);

    const renderContent = () => {
        if (loading) {
            return <p className="status-message">در حال بارگذاری پیشنهادات شغلی برای شما...</p>;
        }
    
        if (error) {
            return <p className="status-message error">{error}</p>;
        }
    
        if (recommendations.length === 0) {
            return (
                <div className="no-results">
                    <h2>پیشنهاد مناسبی یافت نشد</h2>
                    <p>برای دریافت نتایج بهتر، لطفا پروفایل خود را با دقت تکمیل کنید.</p>
                </div>
            );
        }
    
        return (
            <div className="job-grid">
                {recommendations.map(job => {
                    const matched_skills = job.reason?.matched_skills || [];
                    const reason_text = matched_skills.length > 0 
                        ? `متناسب با مهارت‌های شما در: ${matched_skills.join(', ')} ` 
                        : "شباهت بالا با رزومه شما";
    
                    return (
                        <div key={job.id} className="job-card">
                            <h3>{job.title}</h3>
                            <p className="job-card-info">🏢 {job.company_name}</p>
                            <p className="job-card-info">📍 {job.city || 'نامشخص'}</p>
                            <p className="job-card-info reason">
                                ✨ {reason_text} (درصد اطمینان: {job.score.toFixed(2)})
                            </p>
                            <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="job-details-link">
                                مشاهده جزئیات
                            </a>
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <>
            <Header />
            <div className="page-container">
                <h1 className="page-title">فرصت‌های شغلی پیشنهادی برای شما</h1>
                {renderContent()}
            </div>
            <Footer />
        </>
    );
};

export default RecommendedJobsPage;