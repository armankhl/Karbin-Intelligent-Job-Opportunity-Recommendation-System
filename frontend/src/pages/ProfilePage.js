import React, { useState, useEffect, useRef } from 'react';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './ProfilePage.css';
import axios from 'axios'; // Use axios directly
import { useAuth } from '../context/AuthContext'; // FIX 2: Import useAuth

const IRAN_PROVINCES = [
    'آذربایجان شرقی', 'آذربایجان غربی', 'اردبیل', 'اصفهان', 'البرز', 'ایلام', 'بوشهر',
    'تهران', 'چهارمحال و بختیاری', 'خراسان جنوبی', 'خراسان رضوی', 'خراسان شمالی',
    'خوزستان', 'زنجان', 'سمنان', 'سیستان و بلوچستان', 'فارس', 'قزوین', 'قم', 'کردستان',
    'کرمان', 'کرمانشاه', 'کهگیلویه و بویراحمد', 'گلستان', 'گیلان', 'لرستان', 'مازندران',
    'مرکزی', 'هرمزگان', 'همدان', 'یزد'
];

const EXPERIENCE_LEVELS = [
    { value: 0, label: 'کمتر از یک سال' },
    { value: 1, label: 'یک تا سه سال' },
    { value: 3, label: 'سه تا شش سال' },
    { value: 6, label: 'بیش از شش سال' }
];

const ProfilePage = () => {
    const { isAuthenticated, token, logout } = useAuth(); // Get token and logout
    const [profile, setProfile] = useState({
        first_name: '', last_name: '', phone_number: '', professional_title: '',
        expected_salary: '', wants_full_time: false, wants_part_time: false,
        wants_remote: false, wants_onsite: false, wants_internship: false, experience_level: 0,
        preferred_provinces: [],
    });
    const [workExperiences, setWorkExperiences] = useState([]);
    const [educations, setEducations] = useState([]);
    const [skills, setSkills] = useState([]);
    const [provinceSearch, setProvinceSearch] = useState('');
    const [isProvinceDropdownOpen, setProvinceDropdownOpen] = useState(false);
    const provinceRef = useRef(null);

    // Effect for handling clicks outside the province dropdown
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (provinceRef.current && !provinceRef.current.contains(event.target)) {
                setProvinceDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [provinceRef]);
    useEffect(() => {
        const fetchProfile = async () => {
            // Guard clause: only fetch if authenticated and token exists.
            if (!isAuthenticated || !token) return;

            // --- FIX 1: Correctly structured try...catch block ---
            try {
                // FIX 2: Use the secure, JWT-based endpoint
                const response = await axios.get('http://127.0.0.1:5000/api/profile', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                const data = response.data;
                if (data && data.user_id) {
                    setProfile({
                        first_name: data.first_name || '', last_name: data.last_name || '',
                        phone_number: data.phone_number || '', professional_title: data.professional_title || '',
                        wants_full_time: data.wants_full_time || false,
                        wants_part_time: data.wants_part_time || false,
                        wants_remote: data.wants_remote || false,
                        wants_onsite: data.wants_onsite || false,
                        wants_internship: data.wants_internship || false,
                        preferred_provinces: data.preferred_provinces ? data.preferred_provinces.split(',').filter(p => p) : [],
                        expected_salary: data.expected_salary || ''
                    });
                    setWorkExperiences(data.work_experiences || []);
                    setEducations(data.educations || []);
                    setSkills(data.skills || []);
                }
            } catch (error) { // The catch block now correctly follows the try block
                console.error("Failed to fetch profile:", error);
                if (error.response && [401, 422].includes(error.response.status)) {
                    logout();
                }
            }
        };
        fetchProfile();
    }, [isAuthenticated, token, logout]); // Depend on token to re-fetch on login


    // <-- FIX 3: A single, robust handler for all simple form inputs (text, number, checkbox)
    const handleProfileChange = (e) => {
        const { name, value, type, checked } = e.target;
        setProfile(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };
    
    const handleProvinceSelect = (province) => {
        setProfile(prev => {
            const currentProvinces = prev.preferred_provinces;
            const newProvinces = currentProvinces.includes(province)
                ? currentProvinces.filter(p => p !== province)
                : [...currentProvinces, province];
            return { ...prev, preferred_provinces: newProvinces };
        });
        setProvinceSearch(''); // Clear search after selection
    };

    const filteredProvinces = IRAN_PROVINCES.filter(p => p.includes(provinceSearch));

    // --- (The other handlers for dynamic sections and tags remain the same and are correct) ---

    const handleDynamicChange = (index, e, section, setSection) => {
        const { name, value } = e.target;
        const list = [...section];
        list[index][name] = value;
        setSection(list);
    };
    
        const addDynamicItem = (setSection, newItem) => {
        setSection(prev => [...prev, newItem]);
    };
    
    
    const removeDynamicItem = (index, section, setSection) => {
        const list = [...section];
        list.splice(index, 1);
        setSection(list);
    };
    
    const handleTagKeyDown = (e, tagList, setTagList) => {
        if (e.key === 'Enter' && e.target.value.trim() !== '') {
            e.preventDefault();
            setTagList([...tagList, e.target.value.trim()]);
            e.target.value = '';
        }
    };

    const removeTag = (index, tagList, setTagList) => {
        setTagList(tagList.filter((_, i) => i !== index));
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const fullProfilePayload = {
                profile: { ...profile, preferred_provinces: profile.preferred_provinces.join(',') },
                work_experiences: workExperiences,
                educations: educations,
                skills: skills
            };
            await axios.post('http://127.0.0.1:5000/api/profile', fullProfilePayload, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            alert('پروفایل با موفقیت ذخیره شد!');
        } catch (error) {
            console.error('Failed to save profile:', error);
            alert('خطا در ذخیره‌سازی پروفایل.');
            if (error.response && [401, 422].includes(error.response.status)) {
                logout();
            }
        }
    };

    return (
        <>
            <Header />
            <div className="profile-container">
                <form onSubmit={handleSubmit}>
                    {/* --- Basic Information Section --- */}
                    <div className="profile-section">
                        <h2>اطلاعات پایه</h2>
                        <div className="form-grid">
                            <div className="form-group"><label>نام</label><input type="text" name="first_name" value={profile.first_name} onChange={handleProfileChange} className="form-input" /></div>
                            <div className="form-group"><label>نام خانوادگی</label><input type="text" name="last_name" value={profile.last_name} onChange={handleProfileChange} className="form-input" /></div>
                            <div className="form-group"><label>شماره تماس</label><input type="tel" name="phone_number" value={profile.phone_number} onChange={handleProfileChange} className="form-input" /></div>
                            <div className="form-group"><label>عنوان حرفه‌ای</label><input type="text" name="professional_title" value={profile.professional_title} onChange={handleProfileChange} className="form-input" /></div>
                        </div>
                    </div>

                    {/* --- Work Experience Section --- */}
                    <div className="profile-section">
                        <h2>سابقه کاری</h2>
                        {/* --- NEW Dropdown for Overall Experience --- */}
                        <div className="form-group full-width" style={{ marginBottom: '25px' }}>
                            <label>سطح تجربه کلی</label>
                            <select
                                name="experience_level"
                                value={profile.experience_level}
                                onChange={handleProfileChange}
                                className="form-select"
                            >
                                {EXPERIENCE_LEVELS.map(level => (
                                    <option key={level.value} value={level.value}>
                                        {level.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        
                        {workExperiences.map((exp, index) => (
                            <div key={index} className="dynamic-section-item">
                                <button type="button" className="remove-item-btn" onClick={() => removeDynamicItem(index, workExperiences, setWorkExperiences)}>×</button>
                                <div className="form-grid">
                                    <div className="form-group"><label>عنوان شغلی</label><input type="text" name="job_title" value={exp.job_title} onChange={(e) => handleDynamicChange(index, e, workExperiences, setWorkExperiences)} className="form-input" /></div>
                                    <div className="form-group"><label>نام شرکت</label><input type="text" name="company_name" value={exp.company_name} onChange={(e) => handleDynamicChange(index, e, workExperiences, setWorkExperiences)} className="form-input" /></div>
                                    <div className="form-group full-width"><label>توضیحات</label><textarea name="description" value={exp.description} onChange={(e) => handleDynamicChange(index, e, workExperiences, setWorkExperiences)} className="form-textarea"></textarea></div>
                                </div>
                            </div>
                        ))}
                        <button type="button" className="add-item-btn" onClick={() => addDynamicItem(setWorkExperiences, { job_title: '', company_name: '', description: '' })}>+ افزودن سابقه کاری</button>
                    </div>

                     {/* --- Education Section --- */}
                     <div className="profile-section">
                        <h2>تحصیلات</h2>
                        {educations.map((edu, index) => (
                            <div key={index} className="dynamic-section-item">
                                <button type="button" className="remove-item-btn" onClick={() => removeDynamicItem(index, educations, setEducations)}>×</button>
                                <div className="form-grid">
                                    <div className="form-group"><label>مقطع تحصیلی</label><input type="text" name="degree" value={edu.degree} onChange={(e) => handleDynamicChange(index, e, educations, setEducations)} className="form-input" /></div>
                                    <div className="form-group"><label>رشته تحصیلی</label><input type="text" name="field_of_study" value={edu.field_of_study} onChange={(e) => handleDynamicChange(index, e, educations, setEducations)} className="form-input" /></div>
                                    <div className="form-group full-width"><label>نام دانشگاه</label><input type="text" name="university_name" value={edu.university_name} onChange={(e) => handleDynamicChange(index, e, educations, setEducations)} className="form-input" /></div>
                                </div>
                            </div>
                        ))}
                        <button type="button" className="add-item-btn" onClick={() => addDynamicItem(setEducations, { degree: '', field_of_study: '', university_name: '' })}>+ افزودن تحصیلات</button>
                    </div>

                    {/* --- Skills Section --- */}
                    <div className="profile-section">
                        <h2>مهارت‌ها</h2>
                        <div className="form-group">
                            <label>مهارت‌های خود را با Enter جدا کنید</label>
                            <div className="tag-input-container">
                                {skills.map((skill, index) => (
                                    <div key={index} className="tag-item"><span>{skill}</span><button type="button" onClick={() => removeTag(index, skills, setSkills)}>×</button></div>
                                ))}
                                <input type="text" onKeyDown={(e) => handleTagKeyDown(e, skills, setSkills)} placeholder="Python, React, etc." />
                            </div>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h2>ترجیحات شغلی</h2>
                        <div className="form-grid">
                            <div className="form-group">
                                <label>نوع همکاری</label>
                                <div className="checkbox-group">
                                    <div className="checkbox-option"><input type="checkbox" id="wants_full_time" name="wants_full_time" checked={profile.wants_full_time} onChange={handleProfileChange} /><label htmlFor="wants_full_time">تمام وقت</label></div>
                                    <div className="checkbox-option"><input type="checkbox" id="wants_part_time" name="wants_part_time" checked={profile.wants_part_time} onChange={handleProfileChange}/><label htmlFor="wants_part_time">پاره وقت</label></div>
                                </div>
                            </div>
                            <div className="form-group">
                                <label>محل کار</label>
                                <div className="checkbox-group">
                                    <div className="checkbox-option"><input type="checkbox" id="wants_onsite" name="wants_onsite" checked={profile.wants_onsite} onChange={handleProfileChange}/><label htmlFor="wants_onsite">حضوری</label></div>
                                    <div className="checkbox-option"><input type="checkbox" id="wants_remote" name="wants_remote" checked={profile.wants_remote} onChange={handleProfileChange}/><label htmlFor="wants_remote">دورکاری</label></div>
                                </div>
                            </div>
                        </div>
                        <div className="form-group checkbox-option" style={{ marginTop: '20px' }}>
                            <input type="checkbox" id="wants_internship" name="wants_internship" checked={profile.wants_internship} onChange={handleProfileChange} />
                            <label htmlFor="wants_internship">مایل به شرکت در دوره‌های کارآموزی هستم</label>
                        </div>
                        <div className="form-group full-width" ref={provinceRef}>
                        <label>استان‌های مورد نظر برای کار</label>
                            <div className="province-selector">
                                <div className="province-input-area" onClick={() => setProvinceDropdownOpen(!isProvinceDropdownOpen)}>
                                    <div className="province-tags">
                                        {profile.preferred_provinces.map(province => (
                                            <span key={province} className="province-tag">
                                                {province}
                                                <button type="button" onClick={(e) => {e.stopPropagation(); handleProvinceSelect(province);}}>×</button>
                                            </span>
                                        ))}
                                    </div>
                                    <input type="text" className="province-search-input" placeholder={profile.preferred_provinces.length === 0 ? "انتخاب استان..." : ""} value={provinceSearch} onChange={(e) => setProvinceSearch(e.target.value)} />
                                    <span className="dropdown-arrow">▼</span>
                                </div>
                                {isProvinceDropdownOpen && (
                                    <div className="province-dropdown">
                                        {filteredProvinces.length > 0 ? filteredProvinces.map(province => (
                                            <div key={province} className={`province-list-item ${profile.preferred_provinces.includes(province) ? 'selected' : ''}`} onClick={() => handleProvinceSelect(province)}>
                                                {province}
                                            </div>
                                        )) : <div className="province-list-item">موردی یافت نشد</div>}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    
                    <button type="submit" className="submit-btn">ذخیره اطلاعات</button>
                </form>
            </div>
            <Footer />
        </>
    );
};

export default ProfilePage;