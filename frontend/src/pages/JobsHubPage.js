import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './JobsHubPage.css';
import JobListItem from '../components/JobListItem';

const JobsHubPage = () => {
    const { isAuthenticated } = useAuth();
    const [jobs, setJobs] = useState([]);
    const [pagination, setPagination] = useState({ currentPage: 1, totalPages: 1 });
    const [filters, setFilters] = useState({ search: '', province: '', category_id: '' });
    const [sortBy, setSortBy] = useState('newest');
    const [loading, setLoading] = useState(true);
    
    const [provinces, setProvinces] = useState([]);
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        const IRAN_PROVINCES = [
            'آذربایجان شرقی', 'آذربایجان غربی', 'اردبیل', 'اصفهان', 'البرز', 'ایلام', 'بوشهر',
            'تهران', 'چهارمحال و بختیاری', 'خراسان جنوبی', 'خراسان رضوی', 'خراسان شمالی',
            'خوزستان', 'زنجان', 'سمنان', 'سیستان و بلوچستان', 'فارس', 'قزوین', 'قم', 'کردستان',
            'کرمان', 'کرمانشاه', 'کهگیلویه و بویراحمد', 'گلستان', 'گیلان', 'لرستان', 'مازندران',
            'مرکزی', 'هرمزگان', 'همدان', 'یزد'
        ];
        setProvinces(IRAN_PROVINCES);

        const fetchCategories = async () => {
            try {
                const res = await axios.get('http://127.0.0.1:5000/api/categories');
                setCategories(res.data);
            } catch (error) { console.error("Could not fetch categories", error); }
        };
        fetchCategories();
    }, []);

    useEffect(() => {
        const fetchJobs = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams({
                    page: pagination.currentPage,
                    search: filters.search,
                    province: filters.province,
                    category_id: filters.category_id,
                    sortBy: sortBy,
                });
                const token = localStorage.getItem('authToken');
                const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
                const response = await axios.get(`http://127.0.0.1:5000/api/jobs?${params.toString()}`, { headers });
                
                setJobs(response.data.jobs);
                setPagination({
                    currentPage: response.data.current_page,
                    totalPages: response.data.total_pages
                });
            } catch (error) {
                console.error("Failed to fetch jobs:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchJobs();
    }, [filters, sortBy, pagination.currentPage]);

    const handleFilterChange = (e) => {
        setFilters(prev => ({ ...prev, [e.target.name]: e.target.value }));
        setPagination(prev => ({ ...prev, currentPage: 1 }));
    };

    const handleSortChange = (e) => {
        setSortBy(e.target.value);
        setPagination(prev => ({ ...prev, currentPage: 1 }));
    };

    const handleNextPage = () => {
        if (pagination.currentPage < pagination.totalPages) {
            setPagination(prev => ({ ...prev, currentPage: prev.currentPage + 1 }));
        }
    };
    
    const handlePrevPage = () => {
        if (pagination.currentPage > 1) {
            setPagination(prev => ({ ...prev, currentPage: prev.currentPage - 1 }));
        }
    };

    return (
        <>
            <Header />
            <div className="jobs-hub-container">
                <h1 className="page-title">آخرین فرصت‌های شغلی</h1>
                <div className="filter-bar">
                    <input type="text" name="search" placeholder="جستجوی عنوان شغلی..." onChange={handleFilterChange} />
                    <select name="province" value={filters.province} onChange={handleFilterChange}>
                        <option value="">همه استان‌ها</option>
                        {provinces.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <select name="category_id" value={filters.category_id} onChange={handleFilterChange}>
                        <option value="">همه دسته‌بندی‌ها</option>
                        {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    <select name="sortBy" value={sortBy} onChange={handleSortChange} className="sort-select">
                        <option value="newest">جدیدترین</option>
                        <option value="pay">بیشترین حقوق</option>
                        {isAuthenticated && <option value="relevance">مرتبط‌ ترین</option>}
                    </select>
                </div>

                {loading ? <p className="status-message">در حال بارگذاری...</p> : (
                    <>
                        <div className="job-list">
                            {jobs.map(job => (
                                <JobListItem key={job.id} job={job} />
                            ))}
                        </div>
                        <div className="pagination-controls">
                            <button onClick={handlePrevPage} disabled={pagination.currentPage <= 1}>
                                صفحه قبل
                            </button>
                            <span>صفحه {pagination.currentPage} از {pagination.totalPages}</span>
                            <button onClick={handleNextPage} disabled={pagination.currentPage >= pagination.totalPages}>
                                صفحه بعد
                            </button>
                        </div>
                    </>
                )}
            </div>
            <Footer />
        </>
    );
};

export default JobsHubPage;