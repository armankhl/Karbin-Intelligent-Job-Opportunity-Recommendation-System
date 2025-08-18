import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios'; // Make sure you've run 'npm install axios'

// Import Components
import Header from './components/Header';
import Footer from './components/Footer';

// Import Assets (using your .jpg files)
import IranMap from './assets/iran-map.jpg';
import ProfessionsIllustration from './assets/professions.jpg';
import CvIllustration from './assets/cv-illustration.jpg';

// We will fetch real data, so MOCK_DATA is no longer needed.

// --- Sub-components for HomePage (No changes needed here) ---
const HeroSection = () => (
    <section className="hero container">
      <h1>شغل رویایی خود را پیدا کنید</h1>
      <p>با کاربین، به هزاران فرصت شغلی در سراسر کشور دسترسی پیدا کنید و با سیستم هوشمند پیشنهاد شغل، بهترین گزینه را برای خود بیابید.</p>
      <img src={IranMap} alt="نقشه ایران" className="hero-map" />
    </section>
);
  
const FeatureSection = ({ title, text, image, imageSide = 'right' }) => (
      <section className="feature-section container" style={{ flexDirection: imageSide === 'left' ? 'row-reverse' : 'row' }}>
        <div className="feature-text">
          <h2>{title}</h2>
          <p>{text}</p>
        </div>
        <div className="feature-image">
          <img src={image} alt={title} />
        </div>
      </section>
);
  
const JobCard = ({ job }) => (
    <div className="job-card">
      {/* Use the correct field names from your API response */}
      <h3>{job.title}</h3>
      <p className="job-card-info">🏢 {job.company_name}</p> 
      <p className="job-card-info">📍 {job.city}</p>
      {/* The link now uses the REAL source_link from the database */}
      <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="job-details-link">
        مشاهده جزئیات
      </a>
    </div>
);

// --- Main HomePage Component ---
const HomePage = () => {
  // State to store the jobs fetched from the API
  const [jobs, setJobs] = useState([]);

  // useEffect hook to fetch data when the component mounts
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        // Fetch data from your running Python API
        const response = await axios.get('http://127.0.0.1:5000/api/jobs/latest');
        setJobs(response.data); // Update the state with the fetched jobs
      } catch (error) {
        console.error("Error fetching job data:", error);
        // You could set some error state here to show a message to the user
      }
    };

    fetchJobs();
  }, []); // The empty array ensures this effect runs only once

  return (
    <>
      <Header />
      <main>
        <HeroSection />
        <FeatureSection
          title="فرصت‌های شغلی"
          text="به جدیدترین فرصت‌های شغلی که در تمامی سایت‌های کاریابی در سراسر ایران منتشر شده اند بصورت یکپارچه دسترسی پیدا کنید."
          image={ProfessionsIllustration}
          imageSide="left"
        />
        <FeatureSection
          title="رزومه شخصی"
          text="با تکمیل رزومه خود، فرصت‌های شغلی مناسب خود در سراسر ایران را، توسط قوی ترین سیستم پیشنهاد دهنده بصورت روزانه دریافت کنید."
          image={CvIllustration}
          imageSide="right"
        />
        <section className="job-list-section">
          <div className="container">
            <h2>آخرین فرصت‌های شغلی</h2>
            <div className="job-grid">
              {/* Map over the 'jobs' state instead of mock data */}
              {jobs.map(job => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
};

export default HomePage;