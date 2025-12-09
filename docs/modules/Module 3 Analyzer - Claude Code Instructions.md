---
updated: 2025-10-04, 18:35
---

## Module 3 Analyzer - Claude Code Instructions

## Context & Objective

You're building the **Analyzer module** for Scout, an intelligent job application system. This module performs semantic matching between user profiles and job requirements, producing detailed compatibility analysis and application strategy recommendations.

## Module Specifications

**Purpose**: Analyze the semantic similarity between user profile (from Collector) and job requirements (from Rinser), generating match scores, gap analysis, and strategic recommendations.

**Key Responsibilities**:
1. Calculate semantic similarity between experiences and job requirements
2. Score technical skill matches with weighted importance
3. Identify qualification gaps and strengths
4. Generate application strategy recommendations
5. Produce detailed match reports for user review

## Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- NumPy for mathematical operations
- Sentence-transformers for embeddings
- ChromaDB for vector similarity
- Anthropic Claude for strategic analysis

**File Structure**:
```
scout/
├── app/
│   ├── core/
│   │   └── analyzer.py
│   ├── models/
│   │   └── analysis.py
│   ├── services/
│   │   ├── vector_store.py
│   │   └── llm.py
│   └── algorithms/
│       ├── __init__.py
│       ├── scoring.py
│       └── matching.py
├── prompts/
│   └── analysis/
│       ├── gap_analysis.txt
│       ├── strategy_recommendation.txt
│       └── keyword_optimization.txt
├── data/
│   └── cache/
└── tests/
    └── test_analyzer.py
```

## Data Models to Implement

Create these models in `app/models/analysis.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
import uuid

class MatchLevel(str, Enum):
    EXCELLENT = "excellent"      # 85-100%
    STRONG = "strong"            # 70-84%
    MODERATE = "moderate"        # 55-69%
    WEAK = "weak"               # 40-54%
    POOR = "poor"               # Below 40%

class SkillMatch(BaseModel):
    """Individual skill matching result"""
    requirement: str
    requirement_priority: str  # 'must_have' or 'nice_to_have'
    matched_skills: List[Dict[str, float]]  # skill_name: confidence
    best_match_score: float = Field(ge=0, le=1)
    user_skill_level: Optional[str] = None
    years_required: Optional[float] = None
    years_possessed: Optional[float] = None
    is_met: bool = False
    
    @validator('is_met', always=True)
    def determine_if_met(cls, v, values):
        # Must-have requires >0.7 match, nice-to-have >0.5
        threshold = 0.7 if values.get('requirement_priority') == 'must_have' else 0.5
        return values.get('best_match_score', 0) >= threshold

class ExperienceMatch(BaseModel):
    """Experience relevance to job"""
    experience_id: str
    company: str
    role: str
    relevance_score: float = Field(ge=0, le=1)
    matching_keywords: List[str]
    relevant_achievements: List[str]
    applicable_technologies: List[str]
    years_in_role: float
    recency_bonus: float = Field(ge=0, le=0.2)  # Bonus for recent experience

class QualificationGap(BaseModel):
    """Missing qualification analysis"""
    requirement: str
    importance: str  # 'critical', 'important', 'beneficial'
    gap_type: str  # 'skill', 'experience', 'education', 'certification'
    current_state: Optional[str] = None
    required_state: str
    improvement_difficulty: str  # 'easy', 'moderate', 'difficult'
    suggested_action: str
    estimated_time_to_acquire: Optional[str] = None  # e.g., "2-3 months"

class ApplicationStrategy(BaseModel):
    """Strategic recommendations for application"""
    positioning_statement: str  # How to position yourself
    key_strengths: List[str]  # Top 3-5 strengths to emphasize
    experiences_to_highlight: List[str]  # Which experiences to feature
    skills_to_emphasize: List[str]  # Skills to prominently display
    keywords_to_include: List[str]  # ATS optimization keywords
    gaps_to_address: List[str]  # How to address gaps in cover letter
    tone_recommendation: str  # 'formal', 'casual', 'technical', etc.
    customization_priority: str  # 'high', 'medium', 'low'
    estimated_success_rate: float = Field(ge=0, le=1)

class CompatibilityScore(BaseModel):
    """Overall compatibility scoring"""
    overall_score: float = Field(ge=0, le=100)
    match_level: MatchLevel
    
    # Component scores (all 0-100)
    technical_skills_score: float = Field(ge=0, le=100)
    experience_relevance_score: float = Field(ge=0, le=100)
    requirements_met_score: float = Field(ge=0, le=100)
    soft_skills_score: float = Field(ge=0, le=100)
    education_match_score: float = Field(ge=0, le=100)
    
    # Detailed breakdowns
    must_have_requirements_met: int
    must_have_requirements_total: int
    nice_to_have_requirements_met: int
    nice_to_have_requirements_total: int
    
    @validator('match_level', always=True)
    def determine_match_level(cls, v, values):
        score = values.get('overall_score', 0)
        if score >= 85:
            return MatchLevel.EXCELLENT
        elif score >= 70:
            return MatchLevel.STRONG
        elif score >= 55:
            return MatchLevel.MODERATE
        elif score >= 40:
            return MatchLevel.WEAK
        else:
            return MatchLevel.POOR

class AnalysisResult(BaseModel):
    """Complete analysis output"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    profile_hash: str
    
    # Core results
    compatibility: CompatibilityScore
    skill_matches: List[SkillMatch]
    experience_matches: List[ExperienceMatch]
    qualification_gaps: List[QualificationGap]
    strategy: ApplicationStrategy
    
    # Metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    analysis_duration: float  # seconds
    confidence_score: float = Field(ge=0, le=1)
    
    # Detailed insights
    strengths_summary: str
    weaknesses_summary: str
    overall_recommendation: str  # 'strongly_recommend', 'recommend', 'consider', 'not_recommended'
    
    # ATS optimization
    ats_keyword_match_rate: float = Field(ge=0, le=1)
    missing_keywords: List[str]
    keyword_suggestions: Dict[str, List[str]]  # section: keywords to add

class MatchMatrix(BaseModel):
    """Detailed matching matrix for debugging"""
    requirement_to_skill_scores: Dict[str, Dict[str, float]]
    requirement_to_experience_scores: Dict[str, List[Tuple[str, float]]]
    skill_coverage_map: Dict[str, bool]
    experience_relevance_map: Dict[str, float]
```

## Analyzer Implementation

Create the main module in `app/core/analyzer.py`:

```python
import numpy as np
from typing import List, Dict, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import json
from collections import defaultdict

from app.core.collector import Collector
from app.models.job import ProcessedJob, Requirement
from app.models.profile import UserProfile, Experience, Skill
from app.models.analysis import (
    AnalysisResult, CompatibilityScore, SkillMatch,
    ExperienceMatch, QualificationGap, ApplicationStrategy,
    MatchLevel, MatchMatrix
)
from app.services.llm import LLMService
from app.algorithms.scoring import ScoringAlgorithm
from app.config.settings import settings

class Analyzer:
    def __init__(
        self,
        collector: Collector,
        llm_service: Optional[LLMService] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.collector = collector
        self.llm = llm_service or LLMService()
        self.embedding_model = SentenceTransformer(embedding_model)
        self.scoring = ScoringAlgorithm()
        
        # Load analysis prompts
        self.prompts = self._load_prompts()
        
        # Weights for overall scoring
        self.score_weights = {
            'technical_skills': 0.35,
            'experience_relevance': 0.25,
            'requirements_met': 0.20,
            'soft_skills': 0.10,
            'education_match': 0.10
        }
        
        # Cache for embeddings
        self.embedding_cache = {}
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load analysis prompt templates"""
        prompts = {}
        prompt_files = ['gap_analysis.txt', 'strategy_recommendation.txt', 'keyword_optimization.txt']
        
        for file in prompt_files:
            with open(f'prompts/analysis/{file}', 'r') as f:
                prompts[file.replace('.txt', '')] = f.read()
        
        return prompts
    
    async def analyze(
        self,
        job: ProcessedJob,
        profile: Optional[UserProfile] = None
    ) -> AnalysisResult:
        """Main analysis pipeline"""
        start_time = datetime.now()
        
        # Load profile if not provided
        if not profile:
            profile = self.collector.profile
            if not profile:
                await self.collector.load_profile()
                profile = self.collector.profile
        
        # Step 1: Analyze skill matches
        skill_matches = await self.match_skills(job, profile)
        
        # Step 2: Analyze experience relevance
        experience_matches = await self.match_experiences(job, profile)
        
        # Step 3: Calculate compatibility scores
        compatibility = self.calculate_compatibility(
            job, profile, skill_matches, experience_matches
        )
        
        # Step 4: Identify gaps
        gaps = await self.identify_gaps(job, profile, skill_matches)
        
        # Step 5: Generate strategy
        strategy = await self.generate_strategy(
            job, profile, compatibility, skill_matches, experience_matches, gaps
        )
        
        # Step 6: ATS optimization
        ats_analysis = self.analyze_ats_compatibility(job, profile)
        
        # Step 7: Generate summaries
        strengths_summary = self.summarize_strengths(skill_matches, experience_matches)
        weaknesses_summary = self.summarize_weaknesses(gaps)
        overall_recommendation = self.determine_recommendation(compatibility)
        
        # Calculate analysis metadata
        analysis_duration = (datetime.now() - start_time).total_seconds()
        confidence_score = self.calculate_confidence(skill_matches, experience_matches)
        
        return AnalysisResult(
            job_id=job.id,
            profile_hash=self.collector.profile_hash,
            compatibility=compatibility,
            skill_matches=skill_matches,
            experience_matches=experience_matches,
            qualification_gaps=gaps,
            strategy=strategy,
            analysis_duration=analysis_duration,
            confidence_score=confidence_score,
            strengths_summary=strengths_summary,
            weaknesses_summary=weaknesses_summary,
            overall_recommendation=overall_recommendation,
            ats_keyword_match_rate=ats_analysis['match_rate'],
            missing_keywords=ats_analysis['missing_keywords'],
            keyword_suggestions=ats_analysis['suggestions']
        )
    
    async def match_skills(
        self,
        job: ProcessedJob,
        profile: UserProfile
    ) -> List[SkillMatch]:
        """Match job requirements against user skills"""
        skill_matches = []
        
        # Get embeddings for all requirements and skills
        req_embeddings = await self._get_embeddings(
            [r.text for r in job.requirements]
        )
        skill_embeddings = await self._get_embeddings(
            [f"{s.name} {' '.join(s.keywords)}" for s in profile.skills]
        )
        
        # Match each requirement
        for i, requirement in enumerate(job.requirements):
            req_embedding = req_embeddings[i]
            
            # Calculate similarity with all user skills
            similarities = []
            for j, skill in enumerate(profile.skills):
                skill_embedding = skill_embeddings[j]
                similarity = self._cosine_similarity(req_embedding, skill_embedding)
                similarities.append({
                    'skill': skill.name,
                    'score': similarity,
                    'level': skill.level,
                    'years': skill.years
                })
            
            # Sort by similarity and take top matches
            similarities.sort(key=lambda x: x['score'], reverse=True)
            top_matches = similarities[:3]  # Top 3 matches
            
            best_match = top_matches[0] if top_matches else {'score': 0}
            
            skill_match = SkillMatch(
                requirement=requirement.text,
                requirement_priority=requirement.priority,
                matched_skills=[{m['skill']: m['score']} for m in top_matches],
                best_match_score=best_match['score'],
                user_skill_level=best_match.get('level'),
                years_required=requirement.years_needed,
                years_possessed=best_match.get('years')
            )
            
            skill_matches.append(skill_match)
        
        return skill_matches
    
    async def match_experiences(
        self,
        job: ProcessedJob,
        profile: UserProfile
    ) -> List[ExperienceMatch]:
        """Match user experiences against job requirements"""
        experience_matches = []
        
        # Create job context embedding
        job_context = f"{job.title} {job.description} {' '.join(job.responsibilities)}"
        job_embedding = (await self._get_embeddings([job_context]))[0]
        
        for experience in profile.experiences:
            # Create experience context
            exp_context = f"{experience.role} at {experience.company}. "
            exp_context += f"{experience.description} "
            exp_context += f"Technologies: {', '.join(experience.technologies)}. "
            exp_context += f"Achievements: {' '.join(experience.achievements)}"
            
            # Calculate relevance
            exp_embedding = (await self._get_embeddings([exp_context]))[0]
            relevance_score = self._cosine_similarity(job_embedding, exp_embedding)
            
            # Find matching keywords
            job_keywords = set(job.technical_skills + job.tools_technologies)
            exp_keywords = set(experience.technologies)
            matching_keywords = list(job_keywords & exp_keywords)
            
            # Find relevant achievements
            relevant_achievements = []
            for achievement in experience.achievements:
                ach_embedding = (await self._get_embeddings([achievement]))[0]
                if self._cosine_similarity(job_embedding, ach_embedding) > 0.6:
                    relevant_achievements.append(achievement)
            
            # Calculate recency bonus (more recent = higher bonus)
            if experience.current:
                recency_bonus = 0.2
            else:
                years_ago = (datetime.now() - experience.end_date).days / 365
                recency_bonus = max(0, 0.2 - (years_ago * 0.04))  # -0.04 per year, max 0.2
            
            # Calculate years in role
            if experience.current:
                years_in_role = (datetime.now() - experience.start_date).days / 365
            else:
                years_in_role = (experience.end_date - experience.start_date).days / 365
            
            match = ExperienceMatch(
                experience_id=experience.id,
                company=experience.company,
                role=experience.role,
                relevance_score=min(relevance_score + recency_bonus, 1.0),
                matching_keywords=matching_keywords,
                relevant_achievements=relevant_achievements,
                applicable_technologies=list(exp_keywords),
                years_in_role=round(years_in_role, 1),
                recency_bonus=recency_bonus
            )
            
            experience_matches.append(match)
        
        # Sort by relevance
        experience_matches.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return experience_matches
    
    def calculate_compatibility(
        self,
        job: ProcessedJob,
        profile: UserProfile,
        skill_matches: List[SkillMatch],
        experience_matches: List[ExperienceMatch]
    ) -> CompatibilityScore:
        """Calculate overall compatibility scores"""
        
        # Technical skills score
        tech_scores = [m.best_match_score for m in skill_matches 
                      if any(keyword in m.requirement.lower() 
                      for keyword in ['technical', 'programming', 'software', 'tool'])]
        technical_skills_score = np.mean(tech_scores) * 100 if tech_scores else 50
        
        # Experience relevance score
        exp_scores = [m.relevance_score for m in experience_matches[:5]]  # Top 5 experiences
        experience_relevance_score = np.mean(exp_scores) * 100 if exp_scores else 40
        
        # Requirements met score
        must_have_matches = [m for m in skill_matches if m.requirement_priority == 'must_have']
        nice_to_have_matches = [m for m in skill_matches if m.requirement_priority == 'nice_to_have']
        
        must_have_met = sum(1 for m in must_have_matches if m.is_met)
        nice_to_have_met = sum(1 for m in nice_to_have_matches if m.is_met)
        
        if must_have_matches:
            must_have_rate = must_have_met / len(must_have_matches)
        else:
            must_have_rate = 1.0  # No must-haves means all are met
        
        if nice_to_have_matches:
            nice_to_have_rate = nice_to_have_met / len(nice_to_have_matches)
        else:
            nice_to_have_rate = 0.5  # Neutral if no nice-to-haves
        
        requirements_met_score = (must_have_rate * 70 + nice_to_have_rate * 30)
        
        # Soft skills score (simplified for now)
        soft_skill_matches = [m for m in skill_matches 
                             if any(keyword in m.requirement.lower() 
                             for keyword in ['communication', 'leadership', 'team', 'collaboration'])]
        soft_skills_score = np.mean([m.best_match_score for m in soft_skill_matches]) * 100 if soft_skill_matches else 60
        
        # Education match score (simplified)
        education_keywords = ['degree', 'bachelor', 'master', 'phd', 'education']
        education_requirements = [r for r in job.requirements 
                                 if any(k in r.text.lower() for k in education_keywords)]
        
        if education_requirements and profile.education:
            education_match_score = 80  # Has education when required
        elif not education_requirements:
            education_match_score = 100  # Not required
        else:
            education_match_score = 40  # Required but missing
        
        # Calculate overall score using weights
        overall_score = (
            technical_skills_score * self.score_weights['technical_skills'] +
            experience_relevance_score * self.score_weights['experience_relevance'] +
            requirements_met_score * self.score_weights['requirements_met'] +
            soft_skills_score * self.score_weights['soft_skills'] +
            education_match_score * self.score_weights['education_match']
        )
        
        return CompatibilityScore(
            overall_score=round(overall_score, 1),
            technical_skills_score=round(technical_skills_score, 1),
            experience_relevance_score=round(experience_relevance_score, 1),
            requirements_met_score=round(requirements_met_score, 1),
            soft_skills_score=round(soft_skills_score, 1),
            education_match_score=round(education_match_score, 1),
            must_have_requirements_met=must_have_met,
            must_have_requirements_total=len(must_have_matches),
            nice_to_have_requirements_met=nice_to_have_met,
            nice_to_have_requirements_total=len(nice_to_have_matches)
        )
    
    async def identify_gaps(
        self,
        job: ProcessedJob,
        profile: UserProfile,
        skill_matches: List[SkillMatch]
    ) -> List[QualificationGap]:
        """Identify and analyze qualification gaps"""
        gaps = []
        
        # Analyze unmet requirements
        unmet_requirements = [m for m in skill_matches if not m.is_met]
        
        for match in unmet_requirements:
            # Determine gap type
            gap_type = self._determine_gap_type(match.requirement)
            
            # Determine importance
            if match.requirement_priority == 'must_have':
                importance = 'critical'
            elif match.best_match_score < 0.3:
                importance = 'important'
            else:
                importance = 'beneficial'
            
            # Generate improvement suggestion using LLM
            suggestion = await self._generate_gap_suggestion(
                match.requirement,
                gap_type,
                match.best_match_score
            )
            
            gap = QualificationGap(
                requirement=match.requirement,
                importance=importance,
                gap_type=gap_type,
                current_state=f"Match score: {match.best_match_score:.1%}",
                required_state="Full proficiency",
                improvement_difficulty=self._assess_difficulty(gap_type, match),
                suggested_action=suggestion['action'],
                estimated_time_to_acquire=suggestion['timeframe']
            )
            
            gaps.append(gap)
        
        return gaps
    
    async def generate_strategy(
        self,
        job: ProcessedJob,
        profile: UserProfile,
        compatibility: CompatibilityScore,
        skill_matches: List[SkillMatch],
        experience_matches: List[ExperienceMatch],
        gaps: List[QualificationGap]
    ) -> ApplicationStrategy:
        """Generate strategic application recommendations"""
        
        # Identify key strengths
        key_strengths = []
        
        # Add strong skill matches
        strong_skills = [m for m in skill_matches if m.best_match_score > 0.8]
        for skill in strong_skills[:3]:
            key_strengths.append(f"Strong match in {skill.requirement}")
        
        # Add relevant experiences
        top_experiences = experience_matches[:2]
        for exp in top_experiences:
            if exp.relevance_score > 0.7:
                key_strengths.append(f"{exp.role} experience at {exp.company}")
        
        # Determine which experiences to highlight
        experiences_to_highlight = [
            f"{exp.role} at {exp.company}" 
            for exp in experience_matches[:3]
            if exp.relevance_score > 0.6
        ]
        
        # Extract keywords for ATS optimization
        keywords_to_include = list(set(
            job.technical_skills[:10] + 
            job.tools_technologies[:5] +
            [req.text.split()[0] for req in job.requirements[:5] if len(req.text.split()) > 0]
        ))
        
        # Determine skills to emphasize
        skills_to_emphasize = []
        for skill_match in skill_matches:
            if skill_match.is_met and skill_match.requirement_priority == 'must_have':
                if skill_match.matched_skills:
                    skills_to_emphasize.append(list(skill_match.matched_skills[0].keys())[0])
        
        # Generate positioning statement
        positioning_statement = await self._generate_positioning_statement(
            job, profile, compatibility, key_strengths
        )
        
        # Determine how to address gaps
        gaps_to_address = []
        for gap in gaps[:3]:  # Top 3 gaps
            if gap.importance == 'critical':
                gaps_to_address.append(f"Demonstrate transferable skills for {gap.requirement}")
            elif gap.importance == 'important':
                gaps_to_address.append(f"Show willingness to quickly learn {gap.requirement}")
        
        # Determine tone based on job and company
        tone = self._determine_tone(job)
        
        # Estimate success rate
        success_rate = self._estimate_success_rate(compatibility, gaps)
        
        return ApplicationStrategy(
            positioning_statement=positioning_statement,
            key_strengths=key_strengths[:5],
            experiences_to_highlight=experiences_to_highlight[:4],
            skills_to_emphasize=skills_to_emphasize[:6],
            keywords_to_include=keywords_to_include[:15],
            gaps_to_address=gaps_to_address,
            tone_recommendation=tone,
            customization_priority=self._determine_priority(compatibility),
            estimated_success_rate=success_rate
        )
    
    def analyze_ats_compatibility(
        self,
        job: ProcessedJob,
        profile: UserProfile
    ) -> Dict:
        """Analyze ATS keyword compatibility"""
        # Extract all keywords from job
        job_keywords = set()
        job_keywords.update(job.technical_skills)
        job_keywords.update(job.tools_technologies)
        job_keywords.update(job.soft_skills)
        
        # Extract keywords from profile
        profile_keywords = set()
        profile_keywords.update([s.name for s in profile.skills])
        for exp in profile.experiences:
            profile_keywords.update(exp.technologies)
        
        # Calculate match rate
        if job_keywords:
            matched_keywords = job_keywords & profile_keywords
            match_rate = len(matched_keywords) / len(job_keywords)
        else:
            match_rate = 0.5
        
        # Identify missing critical keywords
        missing_keywords = list(job_keywords - profile_keywords)[:10]
        
        # Suggest where to add keywords
        suggestions = {
            'summary': missing_keywords[:3],
            'skills': missing_keywords[3:6],
            'experience': missing_keywords[6:10]
        }
        
        return {
            'match_rate': match_rate,
            'missing_keywords': missing_keywords,
            'suggestions': suggestions
        }
    
    async def _get_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings with caching"""
        embeddings = []
        
        for text in texts:
            # Check cache
            if text in self.embedding_cache:
                embeddings.append(self.embedding_cache[text])
            else:
                # Generate embedding
                embedding = self.embedding_model.encode(text)
                self.embedding_cache[text] = embedding
                embeddings.append(embedding)
        
        return embeddings
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return dot_product / norm_product
    
    def _determine_gap_type(self, requirement: str) -> str:
        """Determine the type of gap from requirement text"""
        requirement_lower = requirement.lower()
        
        if any(word in requirement_lower for word in ['year', 'experience', 'senior', 'junior']):
            return 'experience'
        elif any(word in requirement_lower for word in ['degree', 'bachelor', 'master', 'phd']):
            return 'education'
        elif any(word in requirement_lower for word in ['certification', 'certified', 'license']):
            return 'certification'
        else:
            return 'skill'
    
    def _assess_difficulty(self, gap_type: str, match: SkillMatch) -> str:
        """Assess difficulty of closing a gap"""
        if gap_type == 'experience':
            return 'difficult'  # Can't quickly gain years of experience
        elif gap_type == 'education':
            return 'difficult'  # Degrees take time
        elif gap_type == 'certification':
            return 'moderate'  # Can be obtained in weeks/months
        elif match.best_match_score > 0.5:
            return 'easy'  # Already have some foundation
        else:
            return 'moderate'
    
    async def _generate_gap_suggestion(
        self,
        requirement: str,
        gap_type: str,
        current_score: float
    ) -> Dict[str, str]:
        """Generate suggestion for closing a gap"""
        # Simplified version - in production, would use LLM
        suggestions = {
            'skill': {
                'action': f"Take online course or tutorial on {requirement}",
                'timeframe': "2-4 weeks" if current_score > 0.3 else "1-3 months"
            },
            'experience': {
                'action': f"Highlight transferable experience related to {requirement}",
                'timeframe': "Immediate positioning"
            },
            'education': {
                'action': f"Consider relevant certifications as alternative to {requirement}",
                'timeframe': "2-6 months"
            },
            'certification': {
                'action': f"Obtain certification for {requirement}",
                'timeframe': "1-3 months"
            }
        }
        
        return suggestions.get(gap_type, suggestions['skill'])
    
    async def _generate_positioning_statement(
        self,
        job: ProcessedJob,
        profile: UserProfile,
        compatibility: CompatibilityScore,
        strengths: List[str]
    ) -> str:
        """Generate strategic positioning statement"""
        if compatibility.overall_score >= 80:
            return f"Position as ideal candidate with {profile.years_experience} years of directly relevant experience and proven expertise in key requirements"
        elif compatibility.overall_score >= 60:
            return f"Emphasize strong technical foundation and {len(strengths)} key matching qualifications, with enthusiasm to grow in specific areas"
        else:
            return f"Focus on transferable skills, learning agility, and unique perspective from {profile.title} background"
    
    def _determine_tone(self, job: ProcessedJob) -> str:
        """Determine appropriate tone for application"""
        company_size = job.company.size
        
        if company_size in ['startup', 'small']:
            return 'casual'
        elif any(word in job.title.lower() for word in ['senior', 'lead', 'principal', 'executive']):
            return 'professional'
        elif 'technical' in job.title.lower() or 'engineer' in job.title.lower():
            return 'technical'
        else:
            return 'balanced'
    
    def _determine_priority(self, compatibility: CompatibilityScore) -> str:
        """Determine customization priority"""
        if compatibility.overall_score >= 75:
            return 'high'
        elif compatibility.overall_score >= 55:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_success_rate(
        self,
        compatibility: CompatibilityScore,
        gaps: List[QualificationGap]
    ) -> float:
        """Estimate application success rate"""
        base_rate = compatibility.overall_score / 100
        
        # Penalize for critical gaps
        critical_gaps = sum(1 for g in gaps if g.importance == 'critical')
        gap_penalty = critical_gaps * 0.15
        
        # Bonus for meeting all must-haves
        if compatibility.must_have_requirements_total > 0:
            must_have_rate = compatibility.must_have_requirements_met / compatibility.must_have_requirements_total
            if must_have_rate == 1.0:
                base_rate += 0.1
        
        return max(0.05, min(0.95, base_rate - gap_penalty))
    
    def summarize_strengths(
        self,
        skill_matches: List[SkillMatch],
        experience_matches: List[ExperienceMatch]
    ) -> str:
        """Generate strengths summary"""
        strong_skills = sum(1 for m in skill_matches if m.best_match_score > 0.7)
        relevant_exp = sum(1 for e in experience_matches if e.relevance_score > 0.6)
        
        return f"Strong alignment in {strong_skills} key skills with {relevant_exp} highly relevant experiences"
    
    def summarize_weaknesses(self, gaps: List[QualificationGap]) -> str:
        """Generate weaknesses summary"""
        critical_gaps = sum(1 for g in gaps if g.importance == 'critical')
        total_gaps = len(gaps)
        
        if critical_gaps > 0:
            return f"{critical_gaps} critical gaps identified among {total_gaps} total improvement areas"
        elif total_gaps > 0:
            return f"{total_gaps} minor gaps identified, all addressable with targeted preparation"
        else:
            return "No significant gaps identified"
    
    def determine_recommendation(self, compatibility: CompatibilityScore) -> str:
        """Determine overall recommendation"""
        if compatibility.overall_score >= 75:
            return 'strongly_recommend'
        elif compatibility.overall_score >= 60:
            return 'recommend'
        elif compatibility.overall_score >= 45:
            return 'consider'
        else:
            return 'not_recommended'
    
    def calculate_confidence(
        self,
        skill_matches: List[SkillMatch],
        experience_matches: List[ExperienceMatch]
    ) -> float:
        """Calculate analysis confidence score"""
        # Based on amount and quality of data
        skill_data_points = len(skill_matches)
        exp_data_points = len(experience_matches)
        
        if skill_data_points >= 10 and exp_data_points >= 5:
            return 0.95
        elif skill_data_points >= 5 and exp_data_points >= 3:
            return 0.85
        elif skill_data_points >= 3 and exp_data_points >= 2:
            return 0.75
        else:
            return 0.65
```

## Algorithm Implementation

Create `app/algorithms/scoring.py`:

```python
import numpy as np
from typing import List, Dict, Tuple

class ScoringAlgorithm:
    """Advanced scoring algorithms for matching"""
    
    def weighted_skill_match(
        self,
        requirements: List[Dict],
        skills: List[Dict],
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted skill match score"""
        total_weight = 0
        weighted_score = 0
        
        for req in requirements:
            priority = req.get('priority', 'nice_to_have')
            weight = weights.get(priority, 0.5)
            
            best_match = 0
            for skill in skills:
                match_score = self._calculate_match(req, skill)
                best_match = max(best_match, match_score)
            
            weighted_score += best_match * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0
    
    def _calculate_match(self, requirement: Dict, skill: Dict) -> float:
        """Calculate single requirement-skill match"""
        # Implement fuzzy matching logic
        pass
```

## Test Implementation Requirements

Create `tests/test_analyzer.py`:

1. **Skill Matching Tests**:
   - Test exact skill matches
   - Test partial/fuzzy skill matches
   - Test skill level consideration
   - Test years of experience matching

2. **Experience Matching Tests**:
   - Test role relevance scoring
   - Test technology overlap detection
   - Test recency bonus calculation
   - Test achievement relevance

3. **Compatibility Scoring Tests**:
   - Test overall score calculation
   - Test component score weights
   - Test match level determination
   - Test edge cases (no skills, no experience)

4. **Gap Analysis Tests**:
   - Test gap identification accuracy
   - Test gap type classification
   - Test improvement difficulty assessment
   - Test suggestion generation

5. **Strategy Generation Tests**:
   - Test positioning statement generation
   - Test keyword extraction
   - Test tone determination
   - Test success rate estimation

## Success Criteria

1. **Matching Accuracy**: >85% correlation with human evaluation
2. **Performance**: Complete analysis in <5 seconds for typical profile
3. **Skill Coverage**: Identify 90% of relevant skills from job posting
4. **Gap Detection**: Zero false negatives for must-have requirements
5. **Strategy Quality**: Actionable recommendations in 100% of cases
6. **ATS Optimization**: Identify 95% of critical keywords
7. **Confidence Calibration**: Confidence scores correlate with actual success

## Edge Cases to Handle

1. **Minimal job descriptions**: Jobs with very little detail
2. **Overqualified candidates**: Scoring when user exceeds requirements
3. **Career changers**: Limited direct experience but transferable skills
4. **Ambiguous requirements**: Vague or unclear job requirements
5. **Multiple interpretations**: Skills with different meanings in contexts
6. **Missing profile sections**: Incomplete user profiles
7. **Non-standard job titles**: Creative or unusual position names
8. **Language variations**: British vs American English in requirements
9. **Certification equivalence**: Different names for same qualification
10. **Remote vs onsite**: Location requirement matching

## Integration Notes

The Analyzer module integrates with:
- **Collector**: Retrieves user profile and searches experiences
- **Rinser**: Receives structured job data
- **Creator**: Provides analysis for content generation
- **LLM Service**: Strategic analysis and recommendations
- **Vector Store**: Semantic similarity calculations

---

**38. Should we implement a feedback loop to improve matching accuracy over time?**
*Recommendation: Yes - Track actual application outcomes (interviews, offers) to refine scoring weights and improve the matching algorithm's accuracy.*

This completes the Analyzer module specifications. The module provides comprehensive matching analysis with actionable insights for application strategy.