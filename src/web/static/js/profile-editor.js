/**
 * Profile Editor JavaScript
 * Handles form navigation, dynamic list management, and API interactions
 */

// Section order for navigation
const SECTIONS = ['basic-info', 'summary', 'skills', 'experience', 'education', 'certifications'];
let currentSectionIndex = 0;

// Counters for dynamic items
let skillCount = 0;
let experienceCount = 0;
let educationCount = 0;
let certificationCount = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSectionTabs();
    loadExistingProfile();
    setupFormValidation();
    setupWordCounter();
});

/**
 * Section Navigation
 */
function initializeSectionTabs() {
    document.querySelectorAll('.section-tab').forEach((tab, index) => {
        tab.addEventListener('click', () => goToSection(index));
    });
}

function goToSection(index) {
    // Update current index
    currentSectionIndex = index;

    // Update tabs
    document.querySelectorAll('.section-tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === index);
    });

    // Update sections
    document.querySelectorAll('.form-section').forEach((section, i) => {
        section.classList.toggle('active', i === index);
    });

    // Update navigation buttons
    document.getElementById('prev-btn').disabled = index === 0;
    document.getElementById('next-btn').textContent =
        index === SECTIONS.length - 1 ? 'Save Profile' : 'Next \u2192';

    // Scroll to top of form
    document.querySelector('.profile-form').scrollIntoView({ behavior: 'smooth' });
}

function nextSection() {
    if (currentSectionIndex < SECTIONS.length - 1) {
        goToSection(currentSectionIndex + 1);
    } else {
        saveProfile();
    }
}

function prevSection() {
    if (currentSectionIndex > 0) {
        goToSection(currentSectionIndex - 1);
    }
}

/**
 * Dynamic List Management - Skills
 */
function addSkill(data = null) {
    skillCount++;
    const template = document.getElementById('skill-template');
    const html = template.innerHTML.replace(/{index}/g, skillCount);

    const container = document.getElementById('skills-list');
    const div = document.createElement('div');
    div.innerHTML = html;
    const item = div.firstElementChild;
    container.appendChild(item);

    // Populate if data provided
    if (data) {
        const nameInput = item.querySelector('[name$=".name"]');
        const levelInput = item.querySelector('[name$=".level"]');
        const yearsInput = item.querySelector('[name$=".years"]');
        const keywordsInput = item.querySelector('[name$=".keywords"]');

        if (nameInput) nameInput.value = data.name || '';
        if (levelInput) levelInput.value = data.level || 'intermediate';
        if (yearsInput) yearsInput.value = data.years || '';
        if (keywordsInput) keywordsInput.value = (data.keywords || []).join(', ');
    }

    updateCompleteness();
}

function removeSkill(index) {
    const item = document.querySelector(`.skill-item[data-index="${index}"]`);
    if (item) {
        item.remove();
        updateCompleteness();
    }
}

/**
 * Dynamic List Management - Experience
 */
function addExperience(data = null) {
    experienceCount++;
    const template = document.getElementById('experience-template');
    const html = template.innerHTML.replace(/{index}/g, experienceCount);

    const container = document.getElementById('experience-list');
    const div = document.createElement('div');
    div.innerHTML = html;
    const item = div.firstElementChild;
    container.appendChild(item);

    // Populate if data provided
    if (data) {
        const companyInput = item.querySelector('[name$=".company"]');
        const roleInput = item.querySelector('[name$=".role"]');
        const startDateInput = item.querySelector('[name$=".start_date"]');
        const endDateInput = item.querySelector('[name$=".end_date"]');
        const currentInput = item.querySelector('[name$=".current"]');
        const descInput = item.querySelector('[name$=".description"]');
        const achievementsInput = item.querySelector('[name$=".achievements"]');
        const techInput = item.querySelector('[name$=".technologies"]');

        if (companyInput) companyInput.value = data.company || '';
        if (roleInput) roleInput.value = data.role || '';
        if (startDateInput) startDateInput.value = formatDateForInput(data.start_date);
        if (endDateInput) endDateInput.value = formatDateForInput(data.end_date);
        if (currentInput) currentInput.checked = data.current || false;
        if (descInput) descInput.value = data.description || '';
        if (achievementsInput) achievementsInput.value = (data.achievements || []).join('\n');
        if (techInput) techInput.value = (data.technologies || []).join(', ');

        if (data.current && endDateInput) {
            endDateInput.disabled = true;
        }
    }

    updateCompleteness();
}

function removeExperience(index) {
    const item = document.querySelector(`.experience-item[data-index="${index}"]`);
    if (item) {
        item.remove();
        updateCompleteness();
    }
}

function toggleEndDate(checkbox, index) {
    const endDateInput = document.querySelector(`[name="experiences[${index}].end_date"]`);
    if (endDateInput) {
        endDateInput.disabled = checkbox.checked;
        if (checkbox.checked) {
            endDateInput.value = '';
        }
    }
}

/**
 * Dynamic List Management - Education
 */
function addEducation(data = null) {
    educationCount++;
    const template = document.getElementById('education-template');
    const html = template.innerHTML.replace(/{index}/g, educationCount);

    const container = document.getElementById('education-list');
    const div = document.createElement('div');
    div.innerHTML = html;
    const item = div.firstElementChild;
    container.appendChild(item);

    // Populate if data provided
    if (data) {
        const instInput = item.querySelector('[name$=".institution"]');
        const degreeInput = item.querySelector('[name$=".degree"]');
        const fieldInput = item.querySelector('[name$=".field"]');
        const gpaInput = item.querySelector('[name$=".gpa"]');
        const startDateInput = item.querySelector('[name$=".start_date"]');
        const endDateInput = item.querySelector('[name$=".end_date"]');
        const coursesInput = item.querySelector('[name$=".relevant_courses"]');

        if (instInput) instInput.value = data.institution || '';
        if (degreeInput) degreeInput.value = data.degree || '';
        if (fieldInput) fieldInput.value = data.field || '';
        if (gpaInput) gpaInput.value = data.gpa || '';
        if (startDateInput) startDateInput.value = formatDateForInput(data.start_date);
        if (endDateInput) endDateInput.value = formatDateForInput(data.end_date);
        if (coursesInput) coursesInput.value = (data.relevant_courses || []).join(', ');
    }

    updateCompleteness();
}

function removeEducation(index) {
    const item = document.querySelector(`.education-item[data-index="${index}"]`);
    if (item) {
        item.remove();
        updateCompleteness();
    }
}

/**
 * Dynamic List Management - Certifications
 */
function addCertification(data = null) {
    certificationCount++;
    const template = document.getElementById('certification-template');
    const html = template.innerHTML.replace(/{index}/g, certificationCount);

    const container = document.getElementById('certifications-list');
    const div = document.createElement('div');
    div.innerHTML = html;
    const item = div.firstElementChild;
    container.appendChild(item);

    // Populate if data provided
    if (data) {
        const nameInput = item.querySelector('[name$=".name"]');
        const issuerInput = item.querySelector('[name$=".issuer"]');
        const obtainedInput = item.querySelector('[name$=".date_obtained"]');
        const expiryInput = item.querySelector('[name$=".expiry_date"]');
        const credIdInput = item.querySelector('[name$=".credential_id"]');

        if (nameInput) nameInput.value = data.name || '';
        if (issuerInput) issuerInput.value = data.issuer || '';
        if (obtainedInput) obtainedInput.value = formatDateForInput(data.date_obtained);
        if (expiryInput) expiryInput.value = formatDateForInput(data.expiry_date);
        if (credIdInput) credIdInput.value = data.credential_id || '';
    }

    updateCompleteness();
}

function removeCertification(index) {
    const item = document.querySelector(`.certification-item[data-index="${index}"]`);
    if (item) {
        item.remove();
        updateCompleteness();
    }
}

/**
 * Load Existing Profile
 */
async function loadExistingProfile() {
    try {
        const response = await fetch('/api/profile/editor-data');
        if (!response.ok) {
            // No existing profile, start fresh
            addSkill();  // Add one empty skill
            addExperience();  // Add one empty experience
            updateCompleteness();
            return;
        }

        const profile = await response.json();
        populateForm(profile);
        updateCompleteness();

    } catch (error) {
        console.log('No existing profile found, starting fresh');
        addSkill();
        addExperience();
        updateCompleteness();
    }
}

function populateForm(profile) {
    // Basic info
    const fullNameInput = document.getElementById('full_name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const locationInput = document.getElementById('location');
    const linkedinInput = document.getElementById('linkedin_url');
    const githubInput = document.getElementById('github_url');

    if (fullNameInput) fullNameInput.value = profile.full_name || '';
    if (emailInput) emailInput.value = profile.email || '';
    if (phoneInput) phoneInput.value = profile.phone || '';
    if (locationInput) locationInput.value = profile.location || '';
    if (linkedinInput) linkedinInput.value = profile.linkedin_url || '';
    if (githubInput) githubInput.value = profile.github_url || '';

    // Summary
    const titleInput = document.getElementById('title');
    const yearsExpInput = document.getElementById('years_experience');
    const summaryInput = document.getElementById('summary');

    if (titleInput) titleInput.value = profile.title || '';
    if (yearsExpInput) yearsExpInput.value = profile.years_experience || '';
    if (summaryInput) summaryInput.value = profile.summary || '';
    updateWordCount();

    // Skills
    if (profile.skills && profile.skills.length > 0) {
        profile.skills.forEach(skill => addSkill(skill));
    } else {
        addSkill();
    }

    // Experience
    if (profile.experiences && profile.experiences.length > 0) {
        profile.experiences.forEach(exp => addExperience(exp));
    } else {
        addExperience();
    }

    // Education
    if (profile.education && profile.education.length > 0) {
        profile.education.forEach(edu => addEducation(edu));
    } else {
        addEducation();
    }

    // Certifications
    if (profile.certifications && profile.certifications.length > 0) {
        profile.certifications.forEach(cert => addCertification(cert));
    }
}

/**
 * Save Profile
 */
async function saveProfile() {
    const profile = collectFormData();

    // Basic validation
    if (!profile.full_name || !profile.email) {
        showToastMessage('Please fill in required fields (name and email)', 'error');
        goToSection(0);
        return;
    }

    try {
        const response = await fetch('/api/profile/editor-save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profile),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }

        showToastMessage('Profile saved successfully!', 'success');
        updateCompleteness();

    } catch (error) {
        showToastMessage(`Error saving profile: ${error.message}`, 'error');
    }
}

function collectFormData() {
    const form = document.getElementById('profile-form');

    const profile = {
        // Basic info
        full_name: (document.getElementById('full_name')?.value || '').trim(),
        email: (document.getElementById('email')?.value || '').trim(),
        phone: (document.getElementById('phone')?.value || '').trim() || null,
        location: (document.getElementById('location')?.value || '').trim(),
        linkedin_url: (document.getElementById('linkedin_url')?.value || '').trim() || null,
        github_url: (document.getElementById('github_url')?.value || '').trim() || null,

        // Summary
        title: (document.getElementById('title')?.value || '').trim(),
        years_experience: parseFloat(document.getElementById('years_experience')?.value) || 0,
        summary: (document.getElementById('summary')?.value || '').trim(),

        // Collections
        skills: collectSkills(),
        experiences: collectExperiences(),
        education: collectEducation(),
        certifications: collectCertifications(),
    };

    return profile;
}

function collectSkills() {
    const skills = [];
    document.querySelectorAll('.skill-item').forEach(item => {
        const nameInput = item.querySelector('[name$=".name"]');
        const name = nameInput ? nameInput.value.trim() : '';
        if (name) {
            const levelInput = item.querySelector('[name$=".level"]');
            const yearsInput = item.querySelector('[name$=".years"]');
            const keywordsInput = item.querySelector('[name$=".keywords"]');

            skills.push({
                name: name,
                level: levelInput ? levelInput.value : 'intermediate',
                years: yearsInput ? (parseFloat(yearsInput.value) || null) : null,
                keywords: keywordsInput ? parseCommaSeparated(keywordsInput.value) : [],
            });
        }
    });
    return skills;
}

function collectExperiences() {
    const experiences = [];
    document.querySelectorAll('.experience-item').forEach(item => {
        const companyInput = item.querySelector('[name$=".company"]');
        const roleInput = item.querySelector('[name$=".role"]');
        const company = companyInput ? companyInput.value.trim() : '';
        const role = roleInput ? roleInput.value.trim() : '';
        if (company && role) {
            const startDateInput = item.querySelector('[name$=".start_date"]');
            const endDateInput = item.querySelector('[name$=".end_date"]');
            const currentInput = item.querySelector('[name$=".current"]');
            const descInput = item.querySelector('[name$=".description"]');
            const achievementsInput = item.querySelector('[name$=".achievements"]');
            const techInput = item.querySelector('[name$=".technologies"]');

            experiences.push({
                company: company,
                role: role,
                start_date: startDateInput ? (startDateInput.value || null) : null,
                end_date: endDateInput ? (endDateInput.value || null) : null,
                current: currentInput ? currentInput.checked : false,
                description: descInput ? descInput.value.trim() : '',
                achievements: achievementsInput ? parseLineSeparated(achievementsInput.value) : [],
                technologies: techInput ? parseCommaSeparated(techInput.value) : [],
            });
        }
    });
    return experiences;
}

function collectEducation() {
    const education = [];
    document.querySelectorAll('.education-item').forEach(item => {
        const instInput = item.querySelector('[name$=".institution"]');
        const institution = instInput ? instInput.value.trim() : '';
        if (institution) {
            const degreeInput = item.querySelector('[name$=".degree"]');
            const fieldInput = item.querySelector('[name$=".field"]');
            const gpaInput = item.querySelector('[name$=".gpa"]');
            const startDateInput = item.querySelector('[name$=".start_date"]');
            const endDateInput = item.querySelector('[name$=".end_date"]');
            const coursesInput = item.querySelector('[name$=".relevant_courses"]');

            education.push({
                institution: institution,
                degree: degreeInput ? degreeInput.value.trim() : '',
                field: fieldInput ? fieldInput.value.trim() : '',
                gpa: gpaInput ? (parseFloat(gpaInput.value) || null) : null,
                start_date: startDateInput ? (startDateInput.value || null) : null,
                end_date: endDateInput ? (endDateInput.value || null) : null,
                relevant_courses: coursesInput ? parseCommaSeparated(coursesInput.value) : [],
            });
        }
    });
    return education;
}

function collectCertifications() {
    const certifications = [];
    document.querySelectorAll('.certification-item').forEach(item => {
        const nameInput = item.querySelector('[name$=".name"]');
        const name = nameInput ? nameInput.value.trim() : '';
        if (name) {
            const issuerInput = item.querySelector('[name$=".issuer"]');
            const obtainedInput = item.querySelector('[name$=".date_obtained"]');
            const expiryInput = item.querySelector('[name$=".expiry_date"]');
            const credIdInput = item.querySelector('[name$=".credential_id"]');

            certifications.push({
                name: name,
                issuer: issuerInput ? issuerInput.value.trim() : '',
                date_obtained: obtainedInput ? (obtainedInput.value || null) : null,
                expiry_date: expiryInput ? (expiryInput.value || null) : null,
                credential_id: credIdInput ? (credIdInput.value.trim() || null) : null,
            });
        }
    });
    return certifications;
}

/**
 * Export to YAML
 */
async function exportYAML() {
    const profile = collectFormData();

    try {
        const response = await fetch('/api/profile/export-yaml', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profile),
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'profile.yaml';
        a.click();
        URL.revokeObjectURL(url);

        showToastMessage('Profile exported!', 'success');

    } catch (error) {
        showToastMessage(`Export failed: ${error.message}`, 'error');
    }
}

/**
 * Update Completeness Score
 */
async function updateCompleteness() {
    try {
        // Assess profile without saving
        const profile = collectFormData();

        const response = await fetch('/api/profile/assess', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profile),
        });

        if (!response.ok) {
            return;
        }

        const assessment = await response.json();

        // Update score display
        const scoreValue = document.getElementById('score-value');
        const scoreGrade = document.getElementById('score-grade');
        const scoreSuggestion = document.getElementById('score-suggestion');
        const scoreCircle = document.getElementById('score-circle');

        if (scoreValue) scoreValue.textContent = assessment.overall_score;
        if (scoreGrade) scoreGrade.textContent = formatGrade(assessment.grade);
        if (scoreSuggestion) scoreSuggestion.textContent = assessment.top_suggestions[0] || '';

        // Update circle color
        if (scoreCircle) {
            scoreCircle.className = 'score-circle ' + assessment.grade;
        }

        // Update section tabs
        updateSectionIndicators(assessment.section_scores);

    } catch (error) {
        console.error('Failed to update completeness:', error);
    }
}

function updateSectionIndicators(sectionScores) {
    const sectionMap = {
        'basic_info': 0,
        'summary': 1,
        'skills': 2,
        'experience': 3,
        'education': 4,
        'certifications': 5,
    };

    sectionScores.forEach(section => {
        const index = sectionMap[section.section];
        if (index !== undefined) {
            const tab = document.querySelectorAll('.section-tab')[index];
            if (tab) {
                tab.classList.toggle('complete', section.score >= 70);
            }
        }
    });
}

/**
 * Utility Functions
 */
function formatDateForInput(dateStr) {
    if (!dateStr) return '';
    // Handle ISO format or just date
    if (typeof dateStr === 'string') {
        return dateStr.split('T')[0];
    }
    // Handle Date object
    if (dateStr instanceof Date) {
        return dateStr.toISOString().split('T')[0];
    }
    return '';
}

function parseCommaSeparated(str) {
    if (!str) return [];
    return str.split(',').map(s => s.trim()).filter(s => s);
}

function parseLineSeparated(str) {
    if (!str) return [];
    return str.split('\n').map(s => s.trim()).filter(s => s);
}

function formatGrade(grade) {
    const grades = {
        'excellent': 'Excellent',
        'good': 'Good',
        'fair': 'Fair',
        'needs_work': 'Needs Work',
        'incomplete': 'Incomplete',
    };
    return grades[grade] || grade;
}

function showToastMessage(message, type = 'info') {
    // Use global showToast if available
    if (typeof showToast === 'function') {
        showToast(type, type.charAt(0).toUpperCase() + type.slice(1), message);
        return;
    }

    // Fallback: create simple toast
    const existing = document.querySelector('.editor-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type} show editor-toast`;
    toast.style.position = 'fixed';
    toast.style.bottom = '1.5rem';
    toast.style.right = '1.5rem';
    toast.style.padding = '1rem 1.5rem';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    toast.style.zIndex = '1000';
    toast.style.color = 'white';
    toast.style.background = type === 'success' ? '#059669' : type === 'error' ? '#dc2626' : '#2563eb';
    toast.textContent = message;
    document.body.appendChild(toast);

    // Remove after delay
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function setupFormValidation() {
    // Add real-time validation feedback
    document.querySelectorAll('input[required], select[required]').forEach(input => {
        input.addEventListener('blur', () => {
            input.classList.toggle('invalid', !input.validity.valid);
        });
    });
}

function setupWordCounter() {
    const summary = document.getElementById('summary');
    if (summary) {
        summary.addEventListener('input', updateWordCount);
    }
}

function updateWordCount() {
    const summary = document.getElementById('summary');
    const countEl = document.getElementById('summary-count');
    if (summary && countEl) {
        const count = summary.value.trim().split(/\s+/).filter(w => w).length;
        countEl.textContent = count;
    }
}

// Debounce completeness updates
let completenessTimeout;
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('profile-form');
    if (form) {
        form.addEventListener('input', () => {
            clearTimeout(completenessTimeout);
            completenessTimeout = setTimeout(updateCompleteness, 1000);
        });
    }
});
