
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Header from './components/Header';
import Footer from './components/Footer';
import IranMap from './assets/iran-map.jpg';
import ProfessionsIllustration from './assets/professions.jpg';
import CvIllustration from './assets/cv-illustration.jpg';
import { useAuth } from './context/AuthContext';
import LoginPromptModal from './components/LoginPromptModal';
import JobCard from './components/JobCard'; // Import the new reusable component
import RelevantJobs from './components/RelevantJobs'; // Import our new component

// --- Sub-components for HomePage ---
const HeroSection = () => (
  <section className="hero container">
    <h1>شغل رویایی خود را پیدا کنید</h1>
    <p>با کاربین، به هزاران فرصت شغلی در سراسر کشور دسترسی پیدا کنید و با سیستم هوشمند پیشنهاد شغل، بهترین گزینه را برای خود بیابید.</p>
    <img src={IranMap} alt="نقشه ایران" className="hero-map" />
  </section>
);

const FeatureSection = ({ title, text, image, imageSide, onClick }) => (
    <section className={`feature-section container ${onClick ? 'clickable' : ''}`} style={{ flexDirection: imageSide === 'left' ? 'row-reverse' : 'row' }} onClick={onClick}>
        <div className="feature-text"><h2>{title}</h2><p>{text}</p></div>
        <div className="feature-image"><img src={image} alt={title} /></div>
    </section>
);

// --- Main HomePage Component ---
const HomePage = () => {
    const [jobs, setJobs] = useState([]);
    const { isAuthenticated } = useAuth();
    const navigate = useNavigate();
    const [isModalOpen, setIsModalOpen] = useState(false);

    useEffect(() => {
        const fetchJobs = async () => {
            try {
                const response = await axios.get('http://127.0.0.1:5000/api/jobs/latest');
                setJobs(response.data);
            } catch (error) {
                console.error("Error fetching latest job data:", error);
            }
        };
        fetchJobs();
    }, []);

    const handleProfileFeatureClick = () => {
        if (isAuthenticated) {
            navigate('/profile');
        } else {
            setIsModalOpen(true);
        }
    };

    return (
        <>
            <LoginPromptModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onConfirm={() => { setIsModalOpen(false); navigate('/login'); }} />
            <Header />
            <main>
                <HeroSection />
                <FeatureSection
                    title="فرصت‌های شغلی"
                    text="به جدیدترین فرصت‌های شغلی که در تمامی سایت‌های کاریابی در سراسر ایران منتشر شده اند بصورت یکپارچه دسترسی پیدا کنید."
                    image={ProfessionsIllustration}
                    imageSide="left"
                    onClick={() => navigate('/jobs')}
                />
                <FeatureSection
                    title="رزومه شخصی"
                    text="با تکمیل رزومه خود، فرصت‌های شغلی مناسب خود در سراسر ایران را، توسط قوی ترین سیستم پیشنهاد دهنده بصورت روزانه دریافت کنید."
                    image={CvIllustration}
                    imageSide="right"
                    onClick={handleProfileFeatureClick}
                />
                
                {/* Latest Jobs Section */}
                <section className="job-list-section">
                    <div className="container">
                        <h2>آخرین فرصت‌های شغلی</h2>
                        <div className="job-grid">
                            {jobs.map(job => <JobCard key={job.id} job={job} />)}
                        </div>
                        <div className="view-more-container">
                            <Link to="/jobs" className="view-more-button">
                                مشاهده همه فرصت‌ها
                            </Link>
                        </div>
                    </div>
                </section>

                {/* --- REVISED: Recommendations replaced with RelevantJobs --- */}
                {isAuthenticated && <RelevantJobs />}

            </main>
            <Footer />
        </>
    );
};

export default HomePage;