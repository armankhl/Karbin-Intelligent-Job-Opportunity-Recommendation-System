import React from 'react';
import { Link } from 'react-router-dom';

// Import Components
import Header from './components/Header';
import Footer from './components/Footer';

// Import Assets
import IranMap from './assets/iran-map.jpg';
import ProfessionsIllustration from './assets/professions.jpg';
import CvIllustration from './assets/cv-illustration.jpg';

// --- MOCK DATA ---
// IMPORTANT: Added a 'source_link' to each job for the new feature.
const mockJobs = [
  {
    id: 1,
    title: 'توسعه‌دهنده بک‌اند (مسلط به Python-Laravel)',
    company: 'آرتان تجارت تورال سنا',
    city: 'تهران، تهران',
    source_link: 'https://jobinja.ir/jobs/1' // Example link
  },
  {
    id: 2,
    title: 'کارشناس پشتیبانی نرم‌افزار (پردیس)',
    company: 'فناوری اطلاعات صنوبری',
    city: 'تهران، بومهن',
    source_link: 'https://jobinja.ir/jobs/2' // Example link
  },
  {
    id: 3,
    title: 'برنامه‌نویس جاوا (Back-End)',
    company: 'هلدینگ فناوری نوآوری آراد',
    city: 'تهران، تهران',
    source_link: 'https://jobinja.ir/jobs/3' // Example link
  },
  {
    id: 4,
    title: 'کارشناس دواپس (DevOps)',
    company: 'شرکت نرم‌افزاری پیشرو',
    city: 'اصفهان، اصفهان',
    source_link: 'https://jobinja.ir/jobs/4' // Example link
  },
  {
    id: 5,
    title: 'طراح رابط کاربری (UI/UX)',
    company: 'استودیو خلاقیت وب',
    city: 'مشهد، خراسان رضوی',
    source_link: 'https://jobinja.ir/jobs/5' // Example link
  },
];

// --- Sub-components for HomePage ---
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
    <h3>{job.title}</h3>
    <p className="job-card-info">🏢 {job.company}</p>
    <p className="job-card-info">📍 {job.city}</p>
    <a href={job.source_link} target="_blank" rel="noopener noreferrer" className="job-details-link">
      مشاهده جزئیات
    </a>
  </div>
);

// --- Main HomePage Component ---
const HomePage = () => {
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
              {mockJobs.map(job => (
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