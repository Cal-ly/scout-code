# Scout User Guide

**Version:** 1.0
**Date:** December 14, 2025
**For:** Scout PoC Web Interface

---

## Overview

Scout is an intelligent job application system that automates the creation of tailored CVs and cover letters. This guide walks you through using the Scout web interface to generate professional application materials.

### What Scout Does

1. **Analyzes Job Postings** - Extracts requirements, qualifications, and key information
2. **Matches Your Profile** - Compares your skills and experience to job requirements
3. **Generates Tailored Documents** - Creates customized CV and cover letter
4. **Outputs Professional PDFs** - Ready-to-submit application materials

### Processing Time

Scout uses local AI inference, which means processing takes longer than cloud-based alternatives but keeps your data completely private.

| Environment | Expected Time |
|-------------|---------------|
| Development Machine (GPU) | 1-3 minutes |
| Raspberry Pi 5 (CPU) | 15-30 minutes |

---

## Getting Started

### Prerequisites

Before using Scout, ensure:

1. **Scout is running** - Check by accessing `http://<scout-ip>:8000`
2. **Profile is configured** - Your professional profile must be set up (see Profile Setup)
3. **Job posting ready** - Have the full job posting text available to paste

### Accessing Scout

Open a web browser and navigate to:

```
http://<scout-ip>:8000
```

For example:
- **Raspberry Pi:** `http://192.168.1.21:8000`
- **Local development:** `http://localhost:8000`

You'll see the main Scout interface with the "Paste Job Posting" input area.

---

## Profile Setup

Scout requires a user profile to generate tailored applications. The profile is stored as a YAML file at `data/profile.yaml`.

### Profile Location

```
scout-code/
  data/
    profile.yaml  <-- Your profile goes here
```

### Creating Your Profile

Create `data/profile.yaml` with the following structure:

```yaml
# Scout User Profile
# Edit this file with your professional information

# Basic Information
full_name: "Your Full Name"
email: "your.email@example.com"
phone: "+45 12 34 56 78"  # Optional
location: "Copenhagen, Denmark"
linkedin_url: "https://linkedin.com/in/yourprofile"  # Optional
github_url: "https://github.com/yourusername"  # Optional

# Professional Summary
title: "Senior Software Engineer"
years_experience: 5.0
summary: |
  Experienced software engineer with expertise in Python, FastAPI, and
  machine learning. Passionate about building scalable applications and
  exploring edge computing solutions.

# Skills
skills:
  - name: "Python"
    level: "expert"  # beginner, intermediate, advanced, expert
    years: 5.0
    keywords: ["FastAPI", "Django", "Flask", "asyncio"]

  - name: "Machine Learning"
    level: "advanced"
    years: 3.0
    keywords: ["PyTorch", "TensorFlow", "NLP", "Computer Vision"]

  - name: "Docker"
    level: "advanced"
    years: 4.0
    keywords: ["Containerization", "Docker Compose", "Kubernetes"]

  - name: "Project Management"
    level: "intermediate"
    years: 2.0
    keywords: ["Agile", "Scrum", "JIRA"]

# Work Experience
experiences:
  - company: "Tech Company A"
    role: "Senior Software Engineer"
    start_date: "2022-01-01"
    end_date: null  # null means current position
    description: |
      Lead developer for AI-powered applications. Designed and implemented
      microservices architecture. Mentored junior developers.
    achievements:
      - "Reduced API response time by 60% through optimization"
      - "Led team of 4 developers on greenfield project"
      - "Implemented CI/CD pipeline reducing deployment time by 80%"
    technologies:
      - "Python"
      - "FastAPI"
      - "PostgreSQL"
      - "Docker"
      - "Kubernetes"

  - company: "Startup B"
    role: "Software Developer"
    start_date: "2019-06-01"
    end_date: "2021-12-31"
    description: |
      Full-stack development for e-commerce platform. Built features from
      design to deployment.
    achievements:
      - "Developed payment integration handling $1M+ monthly transactions"
      - "Improved search functionality increasing conversion by 25%"
    technologies:
      - "Python"
      - "Django"
      - "React"
      - "AWS"

# Education
education:
  - institution: "Technical University of Denmark"
    degree: "Master's"
    field: "Computer Science"
    start_date: "2017-09-01"
    end_date: "2019-06-01"
    gpa: 10.5  # Optional, Danish scale
    relevant_courses:
      - "Machine Learning"
      - "Distributed Systems"
      - "Advanced Algorithms"

  - institution: "University of Copenhagen"
    degree: "Bachelor's"
    field: "Software Development"
    start_date: "2014-09-01"
    end_date: "2017-06-01"

# Certifications (Optional)
certifications:
  - name: "AWS Solutions Architect"
    issuer: "Amazon Web Services"
    date_obtained: "2023-03-15"
    expiry_date: "2026-03-15"
    credential_id: "ABC123XYZ"

# Profile Metadata (auto-updated)
profile_version: "1.0"
```

### Profile Tips

1. **Be Specific**: Include concrete achievements with numbers (e.g., "reduced costs by 30%")
2. **Use Keywords**: Include relevant technical terms that appear in job postings
3. **Keep Updated**: Update your profile when you learn new skills or change roles
4. **Include All Experience**: Even older experience can be relevant for some jobs

### Verifying Your Profile

After creating your profile, restart Scout to load the new profile:

```bash
# If running manually, stop and restart
# If using systemd:
sudo systemctl restart scout
```

Check the logs to confirm profile loaded successfully:

```bash
# Look for "Collector module initialized" message
sudo journalctl -u scout | grep -i profile
```

---

## Using the Web Interface

### Step 1: Paste Job Posting

1. Copy the full job posting text from the job listing
2. Paste it into the large text area labeled "Paste Job Posting"
3. Include all relevant sections:
   - Job title and company
   - Requirements and qualifications
   - Responsibilities
   - Nice-to-have skills

**Minimum Length:** 100 characters (the submit button activates after this threshold)

**Character Counter:** Shows current length and warns if below minimum

### Step 2: Submit for Processing

1. Click the **"Generate Application"** button
2. The interface switches to the progress view

### Step 3: Monitor Progress

The progress view shows four steps:

| Step | Description | Estimated Time (Pi 5) |
|------|-------------|----------------------|
| 1. Processing | Parsing job requirements | 2-4 minutes |
| 2. Analyzing | Matching your profile | 4-8 minutes |
| 3. Generating | Creating CV and cover letter | 8-15 minutes |
| 4. Formatting | Converting to PDF | 10-30 seconds |

**Progress Indicators:**
- Gray circle with number = Pending
- Blue spinning circle = In Progress
- Green checkmark = Completed
- Red X = Failed

The progress bar fills as steps complete.

### Step 4: View Results

When processing completes, you'll see:

1. **Job Title and Company** - Extracted from the posting
2. **Compatibility Score** - Percentage match to job requirements
3. **Match Message** - Recommendation based on score

**Score Interpretation:**

| Score | Color | Meaning |
|-------|-------|---------|
| 85%+ | Green | Excellent match - strongly recommended |
| 70-84% | Blue | Strong match - good candidate |
| 50-69% | Yellow | Moderate match - consider highlighting transferable skills |
| <50% | Red | Weak match - may want to focus on other opportunities |

### Step 5: Download Documents

Two download buttons appear:

- **Download CV** (Blue) - Your tailored CV in PDF format
- **Download Cover Letter** (Green) - Personalized cover letter in PDF format

Click each button to download the respective document.

### Step 6: Process Another Job

Click **"Process Another Job"** to return to the input screen and process a different job posting.

---

## Understanding Results

### Compatibility Score

The score represents how well your profile matches the job requirements:

- **Must-have requirements matched**: Major impact on score
- **Nice-to-have requirements matched**: Moderate impact
- **Soft skills alignment**: Minor impact
- **Experience level match**: Considered in overall score

### Generated CV

The CV is tailored to emphasize:
- Skills relevant to this specific job
- Experiences with matching technologies
- Achievements aligned with job requirements

### Generated Cover Letter

The cover letter includes:
- Why you're interested in the role
- How your experience matches requirements
- Specific achievements relevant to the job
- Call to action

---

## Troubleshooting

### Issue: "Generate Application" Button Disabled

**Cause:** Job posting text is too short (< 100 characters)

**Solution:** Paste more of the job posting text, including requirements and description

### Issue: Processing Takes Very Long

**Cause:** Local LLM inference is computationally intensive

**Solutions:**
- This is expected on Raspberry Pi (15-30 minutes)
- Don't refresh the page - progress is tracked in background
- Check system resources aren't exhausted (memory/CPU)

### Issue: Processing Fails

**Possible Causes:**
1. Ollama service not running
2. Profile not configured
3. System out of memory

**Check:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check Scout health
curl http://localhost:8000/health

# View error logs
sudo journalctl -u scout | tail -50
```

### Issue: Poor Compatibility Score

**Causes:**
- Profile doesn't match job requirements well
- Profile missing relevant skills/experience
- Job posting requires skills you don't have

**Solutions:**
- Update profile with additional relevant skills
- Add keywords to skill definitions
- Consider if this job is a good fit

### Issue: PDFs Won't Download

**Cause:** Files weren't generated or path issues

**Check:**
- Verify pipeline completed successfully
- Check `data/outputs/` directory for PDF files
- View Scout logs for file generation errors

---

## Tips for Best Results

### Preparing Job Postings

1. **Copy the full posting** - More text = better analysis
2. **Include requirements section** - Essential for matching
3. **Include company name and title** - Used in cover letter
4. **Remove unnecessary content** - Job board headers, application instructions

### Maintaining Your Profile

1. **Regular updates** - Add new skills as you learn them
2. **Quantify achievements** - Use numbers and metrics
3. **Use industry keywords** - Match terminology in job postings
4. **Include soft skills** - Leadership, communication, teamwork

### After Generation

1. **Review the CV** - Make minor adjustments if needed
2. **Personalize the cover letter** - Add specific company knowledge
3. **Check formatting** - Ensure PDF displays correctly
4. **Proofread** - LLM output may need minor corrections

---

## API Endpoints (Advanced)

For programmatic access, Scout provides these REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check status |
| `/api/apply` | POST | Submit job for processing |
| `/api/status/{job_id}` | GET | Get processing status |
| `/api/download/{job_id}/cv` | GET | Download CV PDF |
| `/api/download/{job_id}/cover_letter` | GET | Download cover letter PDF |
| `/api/jobs` | GET | List all processed jobs |

### Example: Submit via API

```bash
curl -X POST http://localhost:8000/api/apply \
  -H "Content-Type: application/json" \
  -d '{"job_text": "Your job posting text here..."}'
```

### Example: Check Status

```bash
curl http://localhost:8000/api/status/<job_id>
```

---

## Notifications

Scout shows toast notifications for important events:

| Type | Color | Meaning |
|------|-------|---------|
| Info | Blue | Informational message |
| Success | Green | Operation completed successfully |
| Warning | Yellow | Something needs attention |
| Error | Red | An error occurred |

Notifications auto-dismiss after 5 seconds (except warnings and errors).

Click the X to manually dismiss a notification.

---

## Privacy and Data

### Local Processing

Scout processes everything locally:
- Your profile stays on your device
- Job postings are not sent to external services
- Generated documents remain local

### Data Storage

| Data | Location | Persistence |
|------|----------|-------------|
| Profile | `data/profile.yaml` | Until you delete |
| Job history | In-memory | Until restart |
| Generated PDFs | `data/outputs/` | Until you delete |
| Vector embeddings | `data/chroma_data/` | Until you delete |

### Cleaning Up

To remove generated files:
```bash
rm -rf data/outputs/*
```

To reset vector database:
```bash
rm -rf data/chroma_data/*
# Then restart Scout to reinitialize
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-14 | Initial user guide |

---

*This guide is part of the Scout PoC documentation.*
*For technical deployment, see the Raspberry Pi 5 Deployment Guide.*
