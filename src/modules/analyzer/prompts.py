"""
M3 Analyzer Prompts

LLM prompts used for application strategy generation.
"""

STRATEGY_SYSTEM_PROMPT = """You are a career advisor helping craft job application strategies.
You analyze job requirements against candidate qualifications to provide actionable advice.
Be specific, practical, and focus on what makes the candidate stand out.
Always respond with valid JSON matching the requested format exactly."""

STRATEGY_GENERATION_PROMPT = """Generate an application strategy based on this analysis.

Job Title: {job_title}
Company: {company_name}

Compatibility Score: {overall_score}%
Must-have requirements met: {must_haves_met}/{must_haves_total}

Key Skill Matches:
{skill_matches_text}

Experience Matches:
{experience_matches_text}

Gaps Identified:
{gaps_text}

Generate a JSON strategy:
{{
    "positioning": "2-3 sentence positioning statement for this application",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "address_gaps": ["how to address gap1", "how to address gap2"],
    "tone": "professional|enthusiastic|technical|creative",
    "keywords_to_use": ["keyword1", "keyword2", "keyword3"],
    "opening_hook": "Compelling opening sentence for cover letter"
}}

Guidelines:
- Position around strengths, not gaps
- Be specific about how to address gaps (not just "mention willingness to learn")
- Include keywords from the job posting for ATS optimization
- Match tone to company culture if apparent
- Keep positioning concise but impactful"""
