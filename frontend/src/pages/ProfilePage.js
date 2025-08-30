import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './ProfilePage.css';

const LOGGED_IN_USER_ID = 1;

const ProfilePage = () => {
    const [profile, setProfile] = useState({
        first_name: '', last_name: '', phone_number: '', professional_title: '',
        seniority_level: 'Junior', employment_types: [], preferred_cities: [], expected_salary: ''
    });
    const [workExperiences, setWorkExperiences] = useState([]);
    const [educations, setEducations] = useState([]);
    const [skills, setSkills] = useState([]);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const response = await axios.get(`http://127.0.0.1:5000/api/profile/${LOGGED_IN_USER_ID}`);
                const data = response.data;
                if (data && data.user_id) {
                    setProfile({
                        first_name: data.first_name || '', last_name: data.last_name || '',
                        phone_number: data.phone_number || '', professional_title: data.professional_title || '',
                        seniority_level: data.seniority_level || 'Junior',
                        employment_types: data.employment_types ? data.employment_types.split(',').filter(t => t) : [],
                        preferred_cities: data.preferred_cities ? data.preferred_cities.split(',').filter(c => c) : [],
                        expected_salary: data.expected_salary || ''
                    });
                    setWorkExperiences(data.work_experiences || []);
                    setEducations(data.educations || []);
                    setSkills(data.skills || []);
                }
            } catch (error) {
                console.error("Failed to fetch profile:", error);
            }
        };
        fetchProfile();
    }, []);

    const handleProfileChange = (e) => {
        const { name, value } = e.target;
        setProfile(prev => ({ ...prev, [name]: value }));
    };

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
        const fullProfile = {
            profile,
            work_experiences: workExperiences,
            educations,
            skills
        };
        try {
            await axios.post(`http://127.0.0.1:5000/api/profile/${LOGGED_IN_USER_ID}`, fullProfile);
            alert('Profile saved successfully!');
        } catch (error) {
            console.error('Failed to save profile:', error);
            alert('Error saving profile.');
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
                    
                    {/* --- Job Preferences Section (THIS IS THE NEW PART) --- */}
                    <div className="profile-section">
                        <h2>ترجیحات شغلی</h2>
                        <div className="form-grid">
                            <div className="form-group">
                                <label>سطح ارشدیت</label>
                                <select name="seniority_level" value={profile.seniority_level} onChange={handleProfileChange} className="form-select">
                                    <option value="Intern">کارآموز</option>
                                    <option value="Junior">جونیور</option>
                                    <option value="Mid-level">میدلول</option>
                                    <option value="Senior">سنیور</option>
                                    <option value="Lead/Manager">مدیر/سرپرست</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>حقوق درخواستی (ماهانه به تومان)</label>
                                <input
                                    type="number"
                                    name="expected_salary"
                                    value={profile.expected_salary}
                                    onChange={handleProfileChange}
                                    className="form-input"
                                    placeholder="مثال: 5000000"
                                />
                            </div>
                            <div className="form-group full-width">
                                <label>نوع قرارداد (با Enter جدا کنید)</label>
                                <div className="tag-input-container">
                                    {profile.employment_types.map((type, index) => (
                                        <div key={index} className="tag-item">
                                            <span>{type}</span>
                                            <button type="button" onClick={() => removeTag(index, profile.employment_types, (newList) => setProfile(p => ({...p, employment_types: newList})))}>×</button>
                                        </div>
                                    ))}
                                    <input type="text" onKeyDown={(e) => handleTagKeyDown(e, profile.employment_types, (newList) => setProfile(p => ({...p, employment_types: newList})))} placeholder="تمام‌وقت، دورکاری..." />
                                </div>
                            </div>
                            <div className="form-group full-width">
                                <label>شهرهای مورد نظر برای کار (با Enter جدا کنید)</label>
                                <div className="tag-input-container">
                                    {profile.preferred_cities.map((city, index) => (
                                        <div key={index} className="tag-item">
                                            <span>{city}</span>
                                            <button type="button" onClick={() => removeTag(index, profile.preferred_cities, (newList) => setProfile(p => ({...p, preferred_cities: newList})))}>×</button>
                                        </div>
                                    ))}
                                    <input type="text" onKeyDown={(e) => handleTagKeyDown(e, profile.preferred_cities, (newList) => setProfile(p => ({...p, preferred_cities: newList})))} placeholder="تهران، اصفهان..." />
                                </div>
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