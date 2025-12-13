"""
M4 Creator Prompts

LLM prompts used for CV and cover letter content generation.
"""

CV_SYSTEM_PROMPT = """You are an expert CV writer. Create compelling, ATS-friendly CV content.
Focus on quantifiable achievements and relevant experience.
Use action verbs and be concise. Tailor everything to the target job.
Always respond with valid JSON matching the requested format exactly."""

CV_SUMMARY_PROMPT = """Write a professional summary for this CV.

Target Job: {job_title} at {company_name}
Candidate: {full_name}
Current Title: {current_title}
Years Experience: {years_experience}

Key Strengths to Highlight:
{key_strengths}

Strategy:
{positioning}

Write 3-4 sentences that:
1. State their professional identity
2. Highlight most relevant experience
3. Mention key technical skills
4. Show alignment with target role

Return JSON:
{{
    "summary": "The professional summary text (3-4 sentences)"
}}"""

CV_EXPERIENCE_PROMPT = """Tailor this experience entry for the target job.

Target Job: {job_title}
Keywords to Include: {keywords}

Original Experience:
Company: {company}
Title: {title}
Duration: {duration}
Description: {description}
Achievements: {achievements}
Technologies: {technologies}

Rewrite to emphasize relevance to target job.
Return JSON:
{{
    "title": "possibly adjusted title",
    "company": "{company}",
    "duration": "{duration}",
    "bullet_points": [
        "Achievement-focused bullet 1",
        "Achievement-focused bullet 2",
        "Achievement-focused bullet 3"
    ]
}}

Guidelines:
- Start bullets with action verbs
- Include metrics where possible
- Incorporate target keywords naturally
- Keep 3-5 bullets per role"""

COVER_LETTER_SYSTEM_PROMPT = """You are an expert cover letter writer.
Write compelling, personalized cover letters that stand out.
Be authentic, enthusiastic, and specific. Avoid generic phrases.
Always respond with valid JSON matching the requested format exactly."""

COVER_LETTER_PROMPT = """Write a cover letter for this application.

Job: {job_title} at {company_name}
Applicant: {full_name}, {current_title}

Application Strategy:
{positioning}

Key Strengths:
{key_strengths}

How to Address Gaps:
{address_gaps}

Opening Hook Suggestion:
{opening_hook}

Relevant Experiences:
{relevant_experiences}

Return JSON:
{{
    "opening": "Opening paragraph (2-3 sentences with hook)",
    "body_paragraphs": [
        "Paragraph about relevant experience and skills",
        "Paragraph about specific achievements and value"
    ],
    "closing": "Closing paragraph with call to action"
}}

Guidelines:
- Opening should hook immediately (use the hook suggestion)
- Be specific about why THIS company
- Show don't tell - use examples
- Keep under 400 words total
- End with clear call to action"""
