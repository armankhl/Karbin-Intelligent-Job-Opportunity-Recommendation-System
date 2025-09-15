import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './RecommendedJobsPage.css';
import RecommendedJobListItem from '../components/RecommendedJobListItem'; // <-- Import the CORRECT component

const JOBS_PER_PAGE = 5;

const RecommendedJobsPage = () => {
    const [allRecommendations, setAllRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { isAuthenticated, logout } = useAuth();
    const [currentPage, setCurrentPage] = useState(1);

    useEffect(() => {
        const fetchRecommendations = async () => {
            if (!isAuthenticated) {
                setLoading(false);
                setError("برای مشاهده این صفحه باید وارد شوید.");
                return;
            }
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get('http://127.0.0.1:5000/api/recommendations?top_k=24', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                setAllRecommendations(response.data);
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

    
    // --- Pagination Logic ---
    const totalPages = Math.ceil(allRecommendations.length / JOBS_PER_PAGE);
    const startIndex = (currentPage - 1) * JOBS_PER_PAGE;
    const endIndex = startIndex + JOBS_PER_PAGE;
    const currentJobs = allRecommendations.slice(startIndex, endIndex);

    
    const handleNextPage = () => {
        if (currentPage < totalPages) {
            setCurrentPage(currentPage + 1);
        }
    };
    
    const handlePrevPage = () => {
        if (currentPage > 1) {
            setCurrentPage(currentPage - 1);
        }
    };

    const renderContent = () => {
        if (loading) { return <p className="status-message">در حال بارگذاری پیشنهادات شغلی برای شما...</p>; }
        if (error) { return <p className="status-message error">{error}</p>; }
        if (allRecommendations.length === 0) {
            return (
                <div className="no-results">
                    <h2>پیشنهاد مناسبی یافت نشد</h2>
                    <p>برای دریافت نتایج بهتر، لطفا پروفایل خود را با دقت تکمیل کنید.</p>
                </div>
            );
        }
    
        return (
            <>
                <div className="job-list">
                    {currentJobs.map(job => (
                        <RecommendedJobListItem key={job.id} job={job} />
                    ))}
                </div>
                {totalPages > 1 && (
                    <div className="pagination-controls">
                        <button onClick={handlePrevPage} disabled={currentPage <= 1}>
                            صفحه قبل
                        </button>
                        <span>صفحه {currentPage} از {totalPages}</span>
                        <button onClick={handleNextPage} disabled={currentPage >= totalPages}>
                            صفحه بعد
                        </button>
                    </div>
                )}
            </>
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