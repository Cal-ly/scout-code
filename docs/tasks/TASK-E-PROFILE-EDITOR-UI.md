# Task: Web UI Profile Editor

## Overview

**Task ID:** SCOUT-PROFILE-EDITOR  
**Priority:** Medium  
**Estimated Effort:** 2-3 hours  
**Dependencies:** Task C (Profile Completeness) recommended but not required

Add a web-based profile editor that allows users to create and edit their profile through forms instead of manually editing YAML files.

---

## Context

### Current State
- Location: `/home/cally/projects/scout-code/`
- Web UI: `src/web/` using FastAPI + Jinja2 templates
- Static files: `src/web/static/`
- Templates: `src/web/templates/`
- Profiles stored as YAML in `data/profile.yaml`
- Users must manually edit YAML (error-prone, tedious)

### Problem
- YAML editing is error-prone (indentation, types)
- Non-technical users struggle with YAML
- No validation feedback until load fails
- No way to create profile from scratch in UI

### Solution
Build a multi-step form-based profile editor with:
1. Section-by-section editing (Basic Info, Summary, Skills, Experience, Education, Certifications)
2. Real-time validation
3. Live preview of completeness score (uses Task C if available)
4. Export to YAML for backup
5. Clean, professional UI consistent with existing Scout design

---

## Implementation Requirements

### 1. Create Profile Editor Template

**File:** `src/web/templates/profile_editor.html`

```html
{% extends "base.html" %}

{% block title %}Profile Editor - Scout{% endblock %}

{% block head %}
<link rel="stylesheet" href="/static/css/profile-editor.css">
{% endblock %}

{% block content %}
<div class="container">
    <div class="editor-header">
        <h1>Profile Editor</h1>
        <div class="editor-actions">
            <button type="button" class="btn btn-secondary" onclick="exportYAML()">
                Export YAML
            </button>
            <button type="button" class="btn btn-primary" onclick="saveProfile()">
                Save Profile
            </button>
        </div>
    </div>

    <!-- Completeness Score Banner -->
    <div id="completeness-banner" class="completeness-banner">
        <div class="score-circle">
            <span id="score-value">--</span>
        </div>
        <div class="score-details">
            <span id="score-grade" class="grade">Loading...</span>
            <span id="score-suggestion" class="suggestion"></span>
        </div>
    </div>

    <!-- Section Navigation -->
    <div class="section-nav">
        <button class="section-tab active" data-section="basic-info">Basic Info</button>
        <button class="section-tab" data-section="summary">Summary</button>
        <button class="section-tab" data-section="skills">Skills</button>
        <button class="section-tab" data-section="experience">Experience</button>
        <button class="section-tab" data-section="education">Education</button>
        <button class="section-tab" data-section="certifications">Certifications</button>
    </div>

    <!-- Form Sections -->
    <form id="profile-form" class="profile-form">
        <!-- Basic Info Section -->
        <div id="section-basic-info" class="form-section active">
            <h2>Basic Information</h2>
            <p class="section-description">Your contact details and professional links.</p>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="full_name">Full Name *</label>
                    <input type="text" id="full_name" name="full_name" required
                           placeholder="Alex Andersen">
                </div>
                <div class="form-group">
                    <label for="email">Email *</label>
                    <input type="email" id="email" name="email" required
                           placeholder="alex@example.com">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="phone">Phone</label>
                    <input type="tel" id="phone" name="phone"
                           placeholder="+45 12 34 56 78">
                </div>
                <div class="form-group">
                    <label for="location">Location *</label>
                    <input type="text" id="location" name="location" required
                           placeholder="Copenhagen, Denmark">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="linkedin_url">LinkedIn URL</label>
                    <input type="url" id="linkedin_url" name="linkedin_url"
                           placeholder="https://linkedin.com/in/yourprofile">
                </div>
                <div class="form-group">
                    <label for="github_url">GitHub URL</label>
                    <input type="url" id="github_url" name="github_url"
                           placeholder="https://github.com/yourusername">
                </div>
            </div>
        </div>

        <!-- Summary Section -->
        <div id="section-summary" class="form-section">
            <h2>Professional Summary</h2>
            <p class="section-description">Your title, experience, and professional bio.</p>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="title">Professional Title *</label>
                    <input type="text" id="title" name="title" required
                           placeholder="Senior Software Engineer">
                </div>
                <div class="form-group">
                    <label for="years_experience">Years of Experience</label>
                    <input type="number" id="years_experience" name="years_experience"
                           min="0" max="50" step="0.5" placeholder="7">
                </div>
            </div>
            
            <div class="form-group full-width">
                <label for="summary">Professional Summary</label>
                <textarea id="summary" name="summary" rows="5"
                          placeholder="A brief summary of your professional background, expertise, and career goals. Aim for 50-100 words."></textarea>
                <span class="char-count"><span id="summary-count">0</span> words</span>
            </div>
        </div>

        <!-- Skills Section -->
        <div id="section-skills" class="form-section">
            <h2>Skills</h2>
            <p class="section-description">Your technical and professional skills. Aim for 8-15 skills.</p>
            
            <div id="skills-list" class="dynamic-list">
                <!-- Skills will be added here dynamically -->
            </div>
            
            <button type="button" class="btn btn-add" onclick="addSkill()">
                + Add Skill
            </button>
        </div>

        <!-- Experience Section -->
        <div id="section-experience" class="form-section">
            <h2>Work Experience</h2>
            <p class="section-description">Your work history, starting with the most recent.</p>
            
            <div id="experience-list" class="dynamic-list">
                <!-- Experiences will be added here dynamically -->
            </div>
            
            <button type="button" class="btn btn-add" onclick="addExperience()">
                + Add Experience
            </button>
        </div>

        <!-- Education Section -->
        <div id="section-education" class="form-section">
            <h2>Education</h2>
            <p class="section-description">Your academic background.</p>
            
            <div id="education-list" class="dynamic-list">
                <!-- Education entries will be added here dynamically -->
            </div>
            
            <button type="button" class="btn btn-add" onclick="addEducation()">
                + Add Education
            </button>
        </div>

        <!-- Certifications Section -->
        <div id="section-certifications" class="form-section">
            <h2>Certifications</h2>
            <p class="section-description">Professional certifications and credentials.</p>
            
            <div id="certifications-list" class="dynamic-list">
                <!-- Certifications will be added here dynamically -->
            </div>
            
            <button type="button" class="btn btn-add" onclick="addCertification()">
                + Add Certification
            </button>
        </div>
    </form>

    <!-- Navigation Buttons -->
    <div class="form-navigation">
        <button type="button" class="btn btn-secondary" id="prev-btn" onclick="prevSection()" disabled>
            ← Previous
        </button>
        <button type="button" class="btn btn-primary" id="next-btn" onclick="nextSection()">
            Next →
        </button>
    </div>
</div>

<!-- Skill Template (hidden) -->
<template id="skill-template">
    <div class="list-item skill-item" data-index="{index}">
        <div class="item-header">
            <span class="item-title">Skill #{index}</span>
            <button type="button" class="btn-remove" onclick="removeSkill({index})">×</button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Skill Name *</label>
                <input type="text" name="skills[{index}].name" required
                       placeholder="Python" list="common-skills">
            </div>
            <div class="form-group">
                <label>Proficiency Level</label>
                <select name="skills[{index}].level">
                    <option value="beginner">Beginner</option>
                    <option value="intermediate" selected>Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="expert">Expert</option>
                </select>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Years of Experience</label>
                <input type="number" name="skills[{index}].years" min="0" max="50" step="0.5"
                       placeholder="3">
            </div>
            <div class="form-group">
                <label>Keywords (comma-separated)</label>
                <input type="text" name="skills[{index}].keywords"
                       placeholder="python3, asyncio, typing">
            </div>
        </div>
    </div>
</template>

<!-- Experience Template (hidden) -->
<template id="experience-template">
    <div class="list-item experience-item" data-index="{index}">
        <div class="item-header">
            <span class="item-title">Experience #{index}</span>
            <button type="button" class="btn-remove" onclick="removeExperience({index})">×</button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Company *</label>
                <input type="text" name="experiences[{index}].company" required
                       placeholder="TechCorp ApS">
            </div>
            <div class="form-group">
                <label>Role/Title *</label>
                <input type="text" name="experiences[{index}].role" required
                       placeholder="Senior Software Engineer">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Start Date *</label>
                <input type="date" name="experiences[{index}].start_date" required>
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" name="experiences[{index}].end_date">
                <label class="checkbox-label">
                    <input type="checkbox" name="experiences[{index}].current"
                           onchange="toggleEndDate(this, {index})">
                    Current position
                </label>
            </div>
        </div>
        <div class="form-group full-width">
            <label>Description</label>
            <textarea name="experiences[{index}].description" rows="3"
                      placeholder="Describe your responsibilities and achievements..."></textarea>
        </div>
        <div class="form-group full-width">
            <label>Key Achievements (one per line)</label>
            <textarea name="experiences[{index}].achievements" rows="3"
                      placeholder="Reduced API latency by 50%&#10;Led migration to Kubernetes&#10;Mentored 3 junior developers"></textarea>
        </div>
        <div class="form-group full-width">
            <label>Technologies Used (comma-separated)</label>
            <input type="text" name="experiences[{index}].technologies"
                   placeholder="Python, FastAPI, PostgreSQL, AWS">
        </div>
    </div>
</template>

<!-- Education Template (hidden) -->
<template id="education-template">
    <div class="list-item education-item" data-index="{index}">
        <div class="item-header">
            <span class="item-title">Education #{index}</span>
            <button type="button" class="btn-remove" onclick="removeEducation({index})">×</button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Institution *</label>
                <input type="text" name="education[{index}].institution" required
                       placeholder="University of Copenhagen">
            </div>
            <div class="form-group">
                <label>Degree *</label>
                <input type="text" name="education[{index}].degree" required
                       placeholder="M.Sc. Computer Science">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Field of Study *</label>
                <input type="text" name="education[{index}].field" required
                       placeholder="Computer Science">
            </div>
            <div class="form-group">
                <label>GPA (optional)</label>
                <input type="number" name="education[{index}].gpa" min="0" max="12" step="0.1"
                       placeholder="10.5">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Start Date *</label>
                <input type="date" name="education[{index}].start_date" required>
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" name="education[{index}].end_date">
            </div>
        </div>
        <div class="form-group full-width">
            <label>Relevant Courses (comma-separated)</label>
            <input type="text" name="education[{index}].relevant_courses"
                   placeholder="Distributed Systems, Machine Learning, Cloud Computing">
        </div>
    </div>
</template>

<!-- Certification Template (hidden) -->
<template id="certification-template">
    <div class="list-item certification-item" data-index="{index}">
        <div class="item-header">
            <span class="item-title">Certification #{index}</span>
            <button type="button" class="btn-remove" onclick="removeCertification({index})">×</button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Certification Name *</label>
                <input type="text" name="certifications[{index}].name" required
                       placeholder="AWS Solutions Architect - Associate">
            </div>
            <div class="form-group">
                <label>Issuing Organization *</label>
                <input type="text" name="certifications[{index}].issuer" required
                       placeholder="Amazon Web Services">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Date Obtained *</label>
                <input type="date" name="certifications[{index}].date_obtained" required>
            </div>
            <div class="form-group">
                <label>Expiry Date (if applicable)</label>
                <input type="date" name="certifications[{index}].expiry_date">
            </div>
        </div>
        <div class="form-group">
            <label>Credential ID (optional)</label>
            <input type="text" name="certifications[{index}].credential_id"
                   placeholder="AWS-SAA-12345">
        </div>
    </div>
</template>

<!-- Common Skills Datalist -->
<datalist id="common-skills">
    <option value="Python">
    <option value="JavaScript">
    <option value="TypeScript">
    <option value="Java">
    <option value="Go">
    <option value="Rust">
    <option value="C#">
    <option value="C++">
    <option value="Ruby">
    <option value="PHP">
    <option value="Swift">
    <option value="Kotlin">
    <option value="React">
    <option value="Vue.js">
    <option value="Angular">
    <option value="Node.js">
    <option value="Django">
    <option value="FastAPI">
    <option value="Flask">
    <option value="Spring Boot">
    <option value="PostgreSQL">
    <option value="MySQL">
    <option value="MongoDB">
    <option value="Redis">
    <option value="Elasticsearch">
    <option value="Docker">
    <option value="Kubernetes">
    <option value="AWS">
    <option value="GCP">
    <option value="Azure">
    <option value="Terraform">
    <option value="Git">
    <option value="CI/CD">
    <option value="Linux">
    <option value="REST API">
    <option value="GraphQL">
    <option value="Machine Learning">
    <option value="Data Analysis">
    <option value="Agile">
    <option value="Scrum">
</datalist>

<script src="/static/js/profile-editor.js"></script>
{% endblock %}
```

### 2. Create CSS Stylesheet

**File:** `src/web/static/css/profile-editor.css`

```css
/* Profile Editor Styles */

.editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.editor-header h1 {
    margin: 0;
    font-size: 1.75rem;
}

.editor-actions {
    display: flex;
    gap: 0.75rem;
}

/* Completeness Banner */
.completeness-banner {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1rem 1.5rem;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
}

.score-circle {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: var(--primary-color, #2563eb);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    font-weight: 700;
    flex-shrink: 0;
}

.score-circle.excellent { background: #10b981; }
.score-circle.good { background: #3b82f6; }
.score-circle.fair { background: #f59e0b; }
.score-circle.needs-work { background: #ef4444; }

.score-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.score-details .grade {
    font-weight: 600;
    font-size: 1.1rem;
}

.score-details .suggestion {
    color: #6b7280;
    font-size: 0.9rem;
}

/* Section Navigation */
.section-nav {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
}

.section-tab {
    padding: 0.625rem 1rem;
    border: 1px solid var(--border-color, #e0e0e0);
    background: white;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    white-space: nowrap;
    transition: all 0.2s;
}

.section-tab:hover {
    background: #f3f4f6;
}

.section-tab.active {
    background: var(--primary-color, #2563eb);
    color: white;
    border-color: var(--primary-color, #2563eb);
}

.section-tab.complete::after {
    content: " ✓";
    color: #10b981;
}

.section-tab.active.complete::after {
    color: white;
}

/* Form Sections */
.form-section {
    display: none;
    animation: fadeIn 0.3s ease;
}

.form-section.active {
    display: block;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.form-section h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
}

.section-description {
    color: #6b7280;
    margin-bottom: 1.5rem;
}

/* Form Layout */
.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}

@media (max-width: 640px) {
    .form-row {
        grid-template-columns: 1fr;
    }
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.form-group.full-width {
    grid-column: 1 / -1;
}

.form-group label {
    font-weight: 500;
    font-size: 0.9rem;
    color: #374151;
}

.form-group input,
.form-group select,
.form-group textarea {
    padding: 0.625rem 0.75rem;
    border: 1px solid var(--border-color, #d1d5db);
    border-radius: 6px;
    font-size: 0.95rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: none;
    border-color: var(--primary-color, #2563eb);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-group input:invalid:not(:placeholder-shown) {
    border-color: #ef4444;
}

.form-group textarea {
    resize: vertical;
    min-height: 80px;
}

.char-count {
    font-size: 0.8rem;
    color: #9ca3af;
    text-align: right;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: normal;
    cursor: pointer;
    margin-top: 0.5rem;
}

.checkbox-label input[type="checkbox"] {
    width: auto;
    padding: 0;
}

/* Dynamic Lists */
.dynamic-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1rem;
}

.list-item {
    padding: 1.25rem;
    background: #f9fafb;
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: 8px;
}

.item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
}

.item-title {
    font-weight: 600;
    color: #374151;
}

.btn-remove {
    width: 28px;
    height: 28px;
    border: none;
    background: #fee2e2;
    color: #ef4444;
    border-radius: 6px;
    cursor: pointer;
    font-size: 1.25rem;
    line-height: 1;
    transition: background 0.2s;
}

.btn-remove:hover {
    background: #fecaca;
}

/* Buttons */
.btn {
    padding: 0.625rem 1.25rem;
    border: none;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--primary-color, #2563eb);
    color: white;
}

.btn-primary:hover {
    background: #1d4ed8;
}

.btn-primary:disabled {
    background: #93c5fd;
    cursor: not-allowed;
}

.btn-secondary {
    background: white;
    color: #374151;
    border: 1px solid var(--border-color, #d1d5db);
}

.btn-secondary:hover {
    background: #f3f4f6;
}

.btn-secondary:disabled {
    color: #9ca3af;
    cursor: not-allowed;
}

.btn-add {
    width: 100%;
    padding: 0.75rem;
    background: white;
    border: 2px dashed var(--border-color, #d1d5db);
    color: #6b7280;
    border-radius: 8px;
}

.btn-add:hover {
    border-color: var(--primary-color, #2563eb);
    color: var(--primary-color, #2563eb);
    background: #f0f7ff;
}

/* Form Navigation */
.form-navigation {
    display: flex;
    justify-content: space-between;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-color, #e0e0e0);
}

/* Toast Notifications */
.toast {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    padding: 1rem 1.5rem;
    background: #1f2937;
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(100px);
    opacity: 0;
    transition: all 0.3s ease;
    z-index: 1000;
}

.toast.show {
    transform: translateY(0);
    opacity: 1;
}

.toast.success {
    background: #059669;
}

.toast.error {
    background: #dc2626;
}

/* Empty State */
.empty-state {
    text-align: center;
    padding: 2rem;
    color: #9ca3af;
}

.empty-state p {
    margin-bottom: 1rem;
}
```

### 3. Create JavaScript

**File:** `src/web/static/js/profile-editor.js`

```javascript
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
        index === SECTIONS.length - 1 ? 'Save Profile' : 'Next →';
    
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
        item.querySelector('[name$=".name"]').value = data.name || '';
        item.querySelector('[name$=".level"]').value = data.level || 'intermediate';
        item.querySelector('[name$=".years"]').value = data.years || '';
        item.querySelector('[name$=".keywords"]').value = (data.keywords || []).join(', ');
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
        item.querySelector('[name$=".company"]').value = data.company || '';
        item.querySelector('[name$=".role"]').value = data.role || '';
        item.querySelector('[name$=".start_date"]').value = formatDateForInput(data.start_date);
        item.querySelector('[name$=".end_date"]').value = formatDateForInput(data.end_date);
        item.querySelector('[name$=".current"]').checked = data.current || false;
        item.querySelector('[name$=".description"]').value = data.description || '';
        item.querySelector('[name$=".achievements"]').value = (data.achievements || []).join('\n');
        item.querySelector('[name$=".technologies"]').value = (data.technologies || []).join(', ');
        
        if (data.current) {
            item.querySelector('[name$=".end_date"]').disabled = true;
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
    endDateInput.disabled = checkbox.checked;
    if (checkbox.checked) {
        endDateInput.value = '';
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
        item.querySelector('[name$=".institution"]').value = data.institution || '';
        item.querySelector('[name$=".degree"]').value = data.degree || '';
        item.querySelector('[name$=".field"]').value = data.field || '';
        item.querySelector('[name$=".gpa"]').value = data.gpa || '';
        item.querySelector('[name$=".start_date"]').value = formatDateForInput(data.start_date);
        item.querySelector('[name$=".end_date"]').value = formatDateForInput(data.end_date);
        item.querySelector('[name$=".relevant_courses"]').value = (data.relevant_courses || []).join(', ');
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
        item.querySelector('[name$=".name"]').value = data.name || '';
        item.querySelector('[name$=".issuer"]').value = data.issuer || '';
        item.querySelector('[name$=".date_obtained"]').value = formatDateForInput(data.date_obtained);
        item.querySelector('[name$=".expiry_date"]').value = formatDateForInput(data.expiry_date);
        item.querySelector('[name$=".credential_id"]').value = data.credential_id || '';
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
        const response = await fetch('/api/profile/data');
        if (!response.ok) {
            // No existing profile, start fresh
            addSkill();  // Add one empty skill
            addExperience();  // Add one empty experience
            return;
        }
        
        const profile = await response.json();
        populateForm(profile);
        updateCompleteness();
        
    } catch (error) {
        console.log('No existing profile found, starting fresh');
        addSkill();
        addExperience();
    }
}

function populateForm(profile) {
    // Basic info
    document.getElementById('full_name').value = profile.full_name || '';
    document.getElementById('email').value = profile.email || '';
    document.getElementById('phone').value = profile.phone || '';
    document.getElementById('location').value = profile.location || '';
    document.getElementById('linkedin_url').value = profile.linkedin_url || '';
    document.getElementById('github_url').value = profile.github_url || '';
    
    // Summary
    document.getElementById('title').value = profile.title || '';
    document.getElementById('years_experience').value = profile.years_experience || '';
    document.getElementById('summary').value = profile.summary || '';
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
        showToast('Please fill in required fields (name and email)', 'error');
        goToSection(0);
        return;
    }
    
    try {
        const response = await fetch('/api/profile/save', {
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
        
        showToast('Profile saved successfully!', 'success');
        updateCompleteness();
        
    } catch (error) {
        showToast(`Error saving profile: ${error.message}`, 'error');
    }
}

function collectFormData() {
    const form = document.getElementById('profile-form');
    
    const profile = {
        // Basic info
        full_name: form.querySelector('#full_name').value.trim(),
        email: form.querySelector('#email').value.trim(),
        phone: form.querySelector('#phone').value.trim() || null,
        location: form.querySelector('#location').value.trim(),
        linkedin_url: form.querySelector('#linkedin_url').value.trim() || null,
        github_url: form.querySelector('#github_url').value.trim() || null,
        
        // Summary
        title: form.querySelector('#title').value.trim(),
        years_experience: parseFloat(form.querySelector('#years_experience').value) || 0,
        summary: form.querySelector('#summary').value.trim(),
        
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
        const name = item.querySelector('[name$=".name"]').value.trim();
        if (name) {
            skills.push({
                name: name,
                level: item.querySelector('[name$=".level"]').value,
                years: parseFloat(item.querySelector('[name$=".years"]').value) || null,
                keywords: parseCommaSeparated(item.querySelector('[name$=".keywords"]').value),
            });
        }
    });
    return skills;
}

function collectExperiences() {
    const experiences = [];
    document.querySelectorAll('.experience-item').forEach(item => {
        const company = item.querySelector('[name$=".company"]').value.trim();
        const role = item.querySelector('[name$=".role"]').value.trim();
        if (company && role) {
            experiences.push({
                company: company,
                role: role,
                start_date: item.querySelector('[name$=".start_date"]').value || null,
                end_date: item.querySelector('[name$=".end_date"]').value || null,
                current: item.querySelector('[name$=".current"]').checked,
                description: item.querySelector('[name$=".description"]').value.trim(),
                achievements: parseLineSeparated(item.querySelector('[name$=".achievements"]').value),
                technologies: parseCommaSeparated(item.querySelector('[name$=".technologies"]').value),
            });
        }
    });
    return experiences;
}

function collectEducation() {
    const education = [];
    document.querySelectorAll('.education-item').forEach(item => {
        const institution = item.querySelector('[name$=".institution"]').value.trim();
        if (institution) {
            education.push({
                institution: institution,
                degree: item.querySelector('[name$=".degree"]').value.trim(),
                field: item.querySelector('[name$=".field"]').value.trim(),
                gpa: parseFloat(item.querySelector('[name$=".gpa"]').value) || null,
                start_date: item.querySelector('[name$=".start_date"]').value || null,
                end_date: item.querySelector('[name$=".end_date"]').value || null,
                relevant_courses: parseCommaSeparated(item.querySelector('[name$=".relevant_courses"]').value),
            });
        }
    });
    return education;
}

function collectCertifications() {
    const certifications = [];
    document.querySelectorAll('.certification-item').forEach(item => {
        const name = item.querySelector('[name$=".name"]').value.trim();
        if (name) {
            certifications.push({
                name: name,
                issuer: item.querySelector('[name$=".issuer"]').value.trim(),
                date_obtained: item.querySelector('[name$=".date_obtained"]').value || null,
                expiry_date: item.querySelector('[name$=".expiry_date"]').value || null,
                credential_id: item.querySelector('[name$=".credential_id"]').value.trim() || null,
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
        
        showToast('Profile exported!', 'success');
        
    } catch (error) {
        showToast(`Export failed: ${error.message}`, 'error');
    }
}

/**
 * Update Completeness Score
 */
async function updateCompleteness() {
    try {
        // First save temporarily to assess
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
        const scoreCircle = document.querySelector('.score-circle');
        
        scoreValue.textContent = assessment.overall_score;
        scoreGrade.textContent = formatGrade(assessment.grade);
        scoreSuggestion.textContent = assessment.top_suggestions[0] || '';
        
        // Update circle color
        scoreCircle.className = 'score-circle ' + assessment.grade;
        
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
            tab.classList.toggle('complete', section.score >= 70);
        }
    });
}

/**
 * Utility Functions
 */
function formatDateForInput(dateStr) {
    if (!dateStr) return '';
    // Handle ISO format or just date
    return dateStr.split('T')[0];
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
        'excellent': '🌟 Excellent',
        'good': '✅ Good',
        'fair': '⚠️ Fair',
        'needs_work': '🔧 Needs Work',
        'incomplete': '📝 Incomplete',
    };
    return grades[grade] || grade;
}

function showToast(message, type = 'info') {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
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
    summary.addEventListener('input', updateWordCount);
}

function updateWordCount() {
    const summary = document.getElementById('summary');
    const count = summary.value.trim().split(/\s+/).filter(w => w).length;
    document.getElementById('summary-count').textContent = count;
}

// Debounce completeness updates
let completenessTimeout;
document.getElementById('profile-form').addEventListener('input', () => {
    clearTimeout(completenessTimeout);
    completenessTimeout = setTimeout(updateCompleteness, 1000);
});
```

### 4. Add API Endpoints

**File:** `src/web/routes/profile.py` (extend from Task C)

Add these endpoints to the profile router:

```python
"""Profile API endpoints including editor support."""

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from src.modules.collector import get_collector
from src.modules.collector.models import UserProfile
from src.modules.collector.assessment import ProfileAssessment, assess_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/data")
async def get_profile_data():
    """Get current profile data for editor."""
    try:
        collector = await get_collector()
        profile = collector.get_profile()
        return profile.model_dump(mode='json')
    except Exception as e:
        raise HTTPException(status_code=404, detail="No profile loaded")


@router.post("/save")
async def save_profile(profile_data: dict):
    """Save profile from editor form."""
    try:
        # Validate profile data
        profile = UserProfile(**profile_data)
        
        # Save to YAML file
        profile_path = Path("data/profile.yaml")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(profile_path, 'w') as f:
            yaml.dump(
                profile.model_dump(mode='json'),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        
        # Reload in collector
        collector = await get_collector()
        await collector.load_profile(profile_path)
        await collector.index_profile()
        
        return {"status": "saved", "message": "Profile saved successfully"}
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess")
async def assess_profile_data(profile_data: dict) -> ProfileAssessment:
    """Assess profile completeness without saving."""
    try:
        profile = UserProfile(**profile_data)
        return assess_profile(profile)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/export-yaml")
async def export_profile_yaml(profile_data: dict):
    """Export profile as YAML file download."""
    try:
        profile = UserProfile(**profile_data)
        
        yaml_content = yaml.dump(
            profile.model_dump(mode='json'),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": "attachment; filename=profile.yaml"
            }
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

### 5. Add Route to Web App

**File:** `src/web/routes/pages.py`

Add the profile editor page route:

```python
@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_editor(request: Request):
    """Profile editor page."""
    return templates.TemplateResponse(
        "profile_editor.html",
        {"request": request}
    )
```

### 6. Add Navigation Link

**File:** `src/web/templates/base.html` (or navigation component)

Add a link to the profile editor in the navigation:

```html
<a href="/profile/edit" class="nav-link">Edit Profile</a>
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/web/templates/profile_editor.html` | Create | Main editor template |
| `src/web/static/css/profile-editor.css` | Create | Editor styles |
| `src/web/static/js/profile-editor.js` | Create | Editor JavaScript |
| `src/web/routes/profile.py` | Modify | Add save/export endpoints |
| `src/web/routes/pages.py` | Modify | Add editor page route |
| `src/web/templates/base.html` | Modify | Add nav link |

---

## Testing Instructions

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# Start the web server
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# In browser, navigate to:
# http://192.168.1.21:8000/profile/edit

# Test the following:
# 1. Form navigation (tabs and prev/next buttons)
# 2. Add/remove skills, experiences, education, certifications
# 3. Save profile and verify data persists
# 4. Export YAML and verify file downloads
# 5. Completeness score updates as you type
# 6. Load existing profile if one exists
```

---

## Success Criteria

1. ✅ Profile editor page loads at `/profile/edit`
2. ✅ All 6 sections are navigable
3. ✅ Can add/remove dynamic list items (skills, etc.)
4. ✅ Save button persists profile to `data/profile.yaml`
5. ✅ Export YAML downloads valid file
6. ✅ Completeness score updates live
7. ✅ Existing profile loads into form
8. ✅ Form validation prevents invalid saves
9. ✅ UI is responsive on mobile
10. ✅ No JavaScript errors in console

---

## Constraints

- Use existing Scout UI styling (CSS variables)
- No external JS frameworks (vanilla JS only)
- Profile must validate against `UserProfile` schema
- YAML export must be importable back
- Support existing profile.yaml format

---

## Environment

- SSH access: `ssh cally@192.168.1.21`
- Project path: `/home/cally/projects/scout-code`
- Virtual env: `source venv/bin/activate`
- Python: 3.11+
- Web server: `uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000`
- Browser testing: `http://192.168.1.21:8000/profile/edit`
