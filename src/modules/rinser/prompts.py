"""
M2 Rinser Prompts

LLM prompts used for structured extraction from job postings.
"""

SYSTEM_PROMPT = """You are a job posting parser. Extract structured information from job postings.
Always respond with valid JSON matching the requested format exactly.
If information is not present, use null or empty arrays.
Be precise with requirement priorities: only mark as "must_have" if the posting
explicitly requires it."""

JOB_EXTRACTION_PROMPT = """Extract structured information from this job posting.

Job Posting:
---
{raw_text}
---

Return JSON with this exact structure:
{{
    "title": "Job title",
    "company": {{
        "name": "Company name",
        "industry": "Industry or null",
        "size": "Company size or null",
        "culture_notes": "Any culture/values mentioned or null"
    }},
    "location": "Location or null",
    "employment_type": "Full-time/Part-time/Contract or null",
    "salary_range": "Salary range if mentioned or null",
    "requirements": [
        {{
            "text": "Requirement text",
            "priority": "must_have|nice_to_have|preferred",
            "category": "technical|experience|education|certification|soft_skill|other",
            "years_required": number or null
        }}
    ],
    "responsibilities": [
        {{
            "text": "Responsibility text",
            "category": "technical|experience|soft_skill|other"
        }}
    ],
    "benefits": ["benefit1", "benefit2"],
    "summary": "1-2 sentence summary of the role"
}}

Guidelines:
- Mark as "must_have" only if words like "required", "must have", "essential" are used
- Default to "nice_to_have" for general requirements
- Extract years from phrases like "5+ years" -> years_required: 5
- Categorize technical skills (Python, AWS) as "technical"
- Categorize "X years experience" as "experience"
- Include all distinct requirements, don't merge similar ones"""
