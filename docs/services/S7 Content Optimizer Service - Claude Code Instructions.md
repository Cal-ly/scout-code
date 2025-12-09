---
updated: 2025-10-04, 20:12
---

## Content Optimizer Service - Claude Code Instructions

### Context & Objective

You're building the **Content Optimizer Service** for Scout, an advanced post-processing layer that enhances generated application materials by improving readability, ensuring ATS compatibility, validating terminology, and optimizing content for maximum impact.

### Module Specifications

**Purpose**: Refine and optimize generated CV and cover letter content through multiple optimization passes, ensuring professional quality, ATS parseability, appropriate keyword density, and industry-standard formatting while maintaining authentic voice.

**Key Responsibilities**:
1. Optimize keyword placement and density for ATS
2. Improve readability scores and sentence structure
3. Validate industry-specific terminology
4. Check grammar, spelling, and punctuation
5. Ensure tone consistency across documents
6. Optimize content length for standards
7. Enhance action verbs and achievement metrics

### Technical Requirements

**Dependencies**:
- spaCy for NLP analysis
- Language-tool-python for grammar checking
- Textstat for readability metrics
- NLTK for text processing
- Pyspellchecker for spell checking
- Joblib for model caching
- Beautiful Soup for HTML content
- Rake-NLTK for keyword extraction

**File Structure**:
```
scout/
├── app/
│   ├── services/
│   │   ├── content_optimizer.py
│   │   ├── optimization/
│   │   │   ├── __init__.py
│   │   │   ├── ats_optimizer.py
│   │   │   ├── readability_optimizer.py
│   │   │   ├── keyword_optimizer.py
│   │   │   ├── grammar_checker.py
│   │   │   ├── tone_analyzer.py
│   │   │   └── length_optimizer.py
│   │   ├── validators/
│   │   │   ├── __init__.py
│   │   │   ├── terminology_validator.py
│   │   │   ├── metric_validator.py
│   │   │   └── format_validator.py
│   │   └── analyzers/
│   │       ├── __init__.py
│   │       ├── content_analyzer.py
│   │       ├── impact_scorer.py
│   │       └── industry_matcher.py
│   ├── models/
│   │   └── optimization.py
│   └── data/
│       ├── dictionaries/
│       │   ├── industry_terms.json
│       │   ├── action_verbs.json
│       │   └── power_words.json
│       └── rules/
│           ├── ats_rules.yaml
│           └── style_guides.yaml
├── tests/
│   └── test_content_optimizer.py
└── resources/
    └── optimization/
        ├── templates/
        └── examples/
```

### Data Models Implementation

Create comprehensive models in `app/models/optimization.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import re

class OptimizationType(str, Enum):
    ATS = "ats"
    READABILITY = "readability"
    KEYWORDS = "keywords"
    GRAMMAR = "grammar"
    TONE = "tone"
    LENGTH = "length"
    TERMINOLOGY = "terminology"
    METRICS = "metrics"

class ContentType(str, Enum):
    CV = "cv"
    COVER_LETTER = "cover_letter"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    ACHIEVEMENT = "achievement"

class ToneType(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    CREATIVE = "creative"
    ACADEMIC = "academic"

class ReadabilityLevel(str, Enum):
    VERY_EASY = "very_easy"  # Grade 5-6
    EASY = "easy"  # Grade 7-9
    STANDARD = "standard"  # Grade 10-12
    DIFFICULT = "difficult"  # College
    VERY_DIFFICULT = "very_difficult"  # Graduate

class OptimizationRequest(BaseModel):
    """Request for content optimization"""
    content: str
    content_type: ContentType
    
    # Target parameters
    target_keywords: List[str] = []
    target_tone: ToneType = ToneType.PROFESSIONAL
    target_readability: ReadabilityLevel = ReadabilityLevel.STANDARD
    target_length: Optional[int] = None  # Word count
    
    # Optimization options
    optimization_types: List[OptimizationType] = [
        OptimizationType.ATS,
        OptimizationType.READABILITY,
        OptimizationType.GRAMMAR
    ]
    
    # Context
    industry: Optional[str] = None
    job_level: Optional[str] = None  # entry, mid, senior, executive
    company_culture: Optional[str] = None  # startup, corporate, etc.
    
    # Constraints
    preserve_technical_terms: bool = True
    maintain_personal_voice: bool = True
    strict_length_limit: bool = False
    
    # Quality thresholds
    min_readability_score: float = 60.0
    max_keyword_density: float = 0.05  # 5%
    min_keyword_density: float = 0.02  # 2%

class ContentAnalysis(BaseModel):
    """Analysis of content before optimization"""
    # Basic metrics
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    
    # Readability scores
    flesch_reading_ease: float  # 0-100
    flesch_kincaid_grade: float
    gunning_fog_index: float
    coleman_liau_index: float
    automated_readability_index: float
    overall_readability: ReadabilityLevel
    
    # Keyword analysis
    keyword_count: Dict[str, int]
    keyword_density: Dict[str, float]
    missing_keywords: List[str]
    keyword_placement: Dict[str, List[int]]  # keyword: [positions]
    
    # Grammar analysis
    grammar_errors: List[Dict[str, Any]]
    spelling_errors: List[str]
    punctuation_issues: List[str]
    
    # Tone analysis
    detected_tone: ToneType
    tone_consistency: float  # 0-1
    formality_score: float  # 0-1
    
    # Structure analysis
    has_action_verbs: bool
    action_verb_ratio: float
    has_metrics: bool
    metric_count: int
    
    # ATS analysis
    ats_score: float  # 0-100
    ats_issues: List[str]
    problematic_formatting: List[str]

class OptimizationSuggestion(BaseModel):
    """Individual optimization suggestion"""
    type: OptimizationType
    severity: str  # "low", "medium", "high"
    location: Optional[Tuple[int, int]] = None  # (start, end) character positions
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None
    reason: str
    impact_score: float  # 0-1, how much this improves the content
    auto_applicable: bool = True
    
    @validator('severity')
    def validate_severity(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError("Severity must be low, medium, or high")
        return v

class OptimizationResult(BaseModel):
    """Result of content optimization"""
    # Optimized content
    optimized_content: str
    
    # Changes made
    changes_applied: List[OptimizationSuggestion]
    changes_pending: List[OptimizationSuggestion]  # Require manual review
    
    # Before/after analysis
    original_analysis: ContentAnalysis
    optimized_analysis: ContentAnalysis
    
    # Improvement metrics
    readability_improvement: float
    ats_score_improvement: float
    keyword_optimization_score: float
    
    # Quality scores
    overall_quality_score: float  # 0-100
    confidence_score: float  # 0-1
    
    # Warnings
    warnings: List[str]
    
    # Processing details
    optimization_time: float  # seconds
    optimizations_applied: List[OptimizationType]

class ATSOptimizationConfig(BaseModel):
    """ATS-specific optimization configuration"""
    # Formatting rules
    use_standard_headings: bool = True
    avoid_tables: bool = True
    avoid_columns: bool = True
    avoid_headers_footers: bool = True
    avoid_graphics: bool = True
    
    # Text rules
    use_standard_bullets: bool = True
    avoid_special_characters: bool = True
    spell_out_acronyms: bool = True
    
    # Keyword rules
    exact_match_keywords: List[str] = []
    synonym_keywords: Dict[str, List[str]] = {}
    
    # Section requirements
    required_sections: List[str] = [
        "experience", "education", "skills"
    ]
    section_order: List[str] = []

class ReadabilityOptimizationConfig(BaseModel):
    """Readability optimization configuration"""
    target_flesch_score: float = 60.0  # 60-70 is ideal
    max_sentence_length: int = 25
    max_syllables_per_word: float = 2.0
    
    # Simplification rules
    replace_complex_words: bool = True
    split_long_sentences: bool = True
    use_active_voice: bool = True
    
    # Preserve list
    preserve_technical_terms: List[str] = []
    preserve_brand_names: List[str] = []

class KeywordOptimizationConfig(BaseModel):
    """Keyword optimization configuration"""
    primary_keywords: List[str]
    secondary_keywords: List[str]
    
    # Placement strategy
    keywords_in_summary: int = 3
    keywords_per_experience: int = 2
    keywords_in_skills: int = 5
    
    # Density targets
    min_density: float = 0.02
    max_density: float = 0.05
    
    # Distribution
    even_distribution: bool = True
    prioritize_early_placement: bool = True

class IndustryTerminology(BaseModel):
    """Industry-specific terminology validation"""
    industry: str
    
    # Terms database
    standard_terms: List[str]
    avoid_terms: List[str]
    preferred_synonyms: Dict[str, str]
    
    # Acronyms
    common_acronyms: Dict[str, str]  # acronym: full_form
    
    # Job levels
    level_appropriate_terms: Dict[str, List[str]]  # level: terms

class ContentMetrics(BaseModel):
    """Metrics and achievements validation"""
    # Detected metrics
    numerical_metrics: List[str]
    percentage_metrics: List[str]
    financial_metrics: List[str]
    time_metrics: List[str]
    
    # Validation
    metrics_validated: bool
    metrics_credibility_score: float  # 0-1
    
    # Improvements
    vague_statements: List[str]
    quantification_opportunities: List[str]

class ToneAnalysis(BaseModel):
    """Detailed tone analysis"""
    primary_tone: ToneType
    secondary_tones: List[ToneType]
    
    # Detailed scores
    formality_score: float  # 0-1
    confidence_score: float
    enthusiasm_score: float
    professionalism_score: float
    
    # Consistency
    tone_variations: List[Dict[str, Any]]  # Location and deviation
    consistency_score: float  # 0-1
    
    # Recommendations
    tone_adjustments: List[str]

class OptimizationProfile(BaseModel):
    """User's optimization preferences"""
    user_id: str
    
    # Preferences
    preferred_tone: ToneType
    preferred_readability: ReadabilityLevel
    preferred_length: Dict[ContentType, int]  # content_type: word_count
    
    # Industry settings
    industry: str
    specialization: Optional[str]
    
    # Custom dictionaries
    custom_keywords: List[str]
    avoided_phrases: List[str]
    preferred_phrases: List[str]
    
    # Historical performance
    avg_ats_score: float
    successful_applications: List[str]  # Job IDs that led to interviews
```

### Core Optimizer Implementation

Create the main optimizer in `app/services/content_optimizer.py`:

```python
import re
import spacy
import textstat
import language_tool_python
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter, defaultdict
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from spellchecker import SpellChecker
from bs4 import BeautifulSoup
import json
import logging
from pathlib import Path

from app.models.optimization import (
    OptimizationRequest, OptimizationResult, ContentAnalysis,
    OptimizationSuggestion, OptimizationType, ContentType,
    ToneType, ReadabilityLevel, ATSOptimizationConfig,
    ReadabilityOptimizationConfig, KeywordOptimizationConfig,
    IndustryTerminology, ContentMetrics, ToneAnalysis
)
from app.services.optimization.ats_optimizer import ATSOptimizer
from app.services.optimization.readability_optimizer import ReadabilityOptimizer
from app.services.optimization.keyword_optimizer import KeywordOptimizer
from app.services.optimization.grammar_checker import GrammarChecker
from app.services.optimization.tone_analyzer import ToneAnalyzer
from app.services.optimization.length_optimizer import LengthOptimizer
from app.services.validators.terminology_validator import TerminologyValidator
from app.services.validators.metric_validator import MetricValidator

logger = logging.getLogger(__name__)

class ContentOptimizer:
    def __init__(self):
        # Initialize NLP models
        self.nlp = spacy.load("en_core_web_sm")
        self.grammar_tool = language_tool_python.LanguageTool('en-US')
        self.spell_checker = SpellChecker()
        
        # Download NLTK data if needed
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        
        # Initialize optimizers
        self.ats_optimizer = ATSOptimizer()
        self.readability_optimizer = ReadabilityOptimizer(self.nlp)
        self.keyword_optimizer = KeywordOptimizer()
        self.grammar_checker = GrammarChecker(self.grammar_tool)
        self.tone_analyzer = ToneAnalyzer(self.nlp)
        self.length_optimizer = LengthOptimizer()
        
        # Initialize validators
        self.terminology_validator = TerminologyValidator()
        self.metric_validator = MetricValidator()
        
        # Load resources
        self.resources = self._load_resources()
        
        # Cache for optimization results
        self.cache = {}
    
    def _load_resources(self) -> Dict[str, Any]:
        """Load optimization resources"""
        resources = {}
        resource_dir = Path("app/data/dictionaries")
        
        # Load industry terms
        industry_terms_file = resource_dir / "industry_terms.json"
        if industry_terms_file.exists():
            with open(industry_terms_file, 'r') as f:
                resources['industry_terms'] = json.load(f)
        
        # Load action verbs
        action_verbs_file = resource_dir / "action_verbs.json"
        if action_verbs_file.exists():
            with open(action_verbs_file, 'r') as f:
                resources['action_verbs'] = json.load(f)
        
        # Load power words
        power_words_file = resource_dir / "power_words.json"
        if power_words_file.exists():
            with open(power_words_file, 'r') as f:
                resources['power_words'] = json.load(f)
        
        return resources
    
    async def optimize(
        self,
        request: OptimizationRequest
    ) -> OptimizationResult:
        """Main optimization pipeline"""
        import time
        start_time = time.time()
        
        # Analyze original content
        original_analysis = await self.analyze_content(
            request.content,
            request.content_type,
            request.target_keywords
        )
        
        # Initialize optimization tracking
        optimized_content = request.content
        changes_applied = []
        changes_pending = []
        warnings = []
        
        # Apply optimizations based on request
        for opt_type in request.optimization_types:
            try:
                if opt_type == OptimizationType.ATS:
                    result = await self._optimize_ats(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.READABILITY:
                    result = await self._optimize_readability(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.KEYWORDS:
                    result = await self._optimize_keywords(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.GRAMMAR:
                    result = await self._optimize_grammar(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.TONE:
                    result = await self._optimize_tone(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.LENGTH:
                    result = await self._optimize_length(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.TERMINOLOGY:
                    result = await self._validate_terminology(
                        optimized_content,
                        request
                    )
                elif opt_type == OptimizationType.METRICS:
                    result = await self._validate_metrics(
                        optimized_content,
                        request
                    )
                
                # Apply changes
                if result:
                    optimized_content = result['content']
                    changes_applied.extend(result.get('applied', []))
                    changes_pending.extend(result.get('pending', []))
                    warnings.extend(result.get('warnings', []))
            
            except Exception as e:
                logger.error(f"Optimization {opt_type} failed: {e}")
                warnings.append(f"{opt_type} optimization skipped due to error")
        
        # Analyze optimized content
        optimized_analysis = await self.analyze_content(
            optimized_content,
            request.content_type,
            request.target_keywords
        )
        
        # Calculate improvements
        improvements = self._calculate_improvements(
            original_analysis,
            optimized_analysis
        )
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            optimized_analysis,
            request
        )
        
        return OptimizationResult(
            optimized_content=optimized_content,
            changes_applied=changes_applied,
            changes_pending=changes_pending,
            original_analysis=original_analysis,
            optimized_analysis=optimized_analysis,
            readability_improvement=improvements['readability'],
            ats_score_improvement=improvements['ats'],
            keyword_optimization_score=improvements['keywords'],
            overall_quality_score=quality_score,
            confidence_score=self._calculate_confidence(changes_applied),
            warnings=warnings,
            optimization_time=time.time() - start_time,
            optimizations_applied=request.optimization_types
        )
    
    async def analyze_content(
        self,
        content: str,
        content_type: ContentType,
        target_keywords: List[str]
    ) -> ContentAnalysis:
        """Analyze content for optimization opportunities"""
        # Clean content for analysis
        clean_text = self._clean_text(content)
        
        # Basic metrics
        sentences = sent_tokenize(clean_text)
        words = word_tokenize(clean_text)
        words_no_stop = [w for w in words if w.lower() not in stopwords.words('english')]
        
        # Readability scores
        flesch_score = textstat.flesch_reading_ease(clean_text)
        flesch_kincaid = textstat.flesch_kincaid_grade(clean_text)
        gunning_fog = textstat.gunning_fog(clean_text)
        coleman_liau = textstat.coleman_liau_index(clean_text)
        ari = textstat.automated_readability_index(clean_text)
        
        # Keyword analysis
        keyword_analysis = self._analyze_keywords(
            clean_text,
            target_keywords
        )
        
        # Grammar analysis
        grammar_errors = self.grammar_checker.check(clean_text)
        spelling_errors = self._check_spelling(words)
        
        # Tone analysis
        tone_result = self.tone_analyzer.analyze(clean_text)
        
        # Structure analysis
        action_verbs = self._count_action_verbs(clean_text)
        metrics = self.metric_validator.extract_metrics(clean_text)
        
        # ATS analysis
        ats_score, ats_issues = self.ats_optimizer.analyze(clean_text)
        
        return ContentAnalysis(
            word_count=len(words),
            sentence_count=len(sentences),
            paragraph_count=clean_text.count('\n\n') + 1,
            avg_words_per_sentence=len(words) / len(sentences) if sentences else 0,
            avg_syllables_per_word=textstat.syllable_count(clean_text) / len(words) if words else 0,
            flesch_reading_ease=flesch_score,
            flesch_kincaid_grade=flesch_kincaid,
            gunning_fog_index=gunning_fog,
            coleman_liau_index=coleman_liau,
            automated_readability_index=ari,
            overall_readability=self._determine_readability_level(flesch_score),
            keyword_count=keyword_analysis['count'],
            keyword_density=keyword_analysis['density'],
            missing_keywords=keyword_analysis['missing'],
            keyword_placement=keyword_analysis['placement'],
            grammar_errors=[self._format_grammar_error(e) for e in grammar_errors],
            spelling_errors=spelling_errors,
            punctuation_issues=self._check_punctuation(clean_text),
            detected_tone=tone_result.primary_tone,
            tone_consistency=tone_result.consistency_score,
            formality_score=tone_result.formality_score,
            has_action_verbs=len(action_verbs) > 0,
            action_verb_ratio=len(action_verbs) / len(sentences) if sentences else 0,
            has_metrics=len(metrics.numerical_metrics) > 0,
            metric_count=len(metrics.numerical_metrics) + len(metrics.percentage_metrics),
            ats_score=ats_score,
            ats_issues=ats_issues,
            problematic_formatting=self._detect_problematic_formatting(content)
        )
    
    async def _optimize_ats(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Optimize content for ATS systems"""
        config = ATSOptimizationConfig(
            exact_match_keywords=request.target_keywords
        )
        
        optimized, suggestions = self.ats_optimizer.optimize(content, config)
        
        applied = []
        pending = []
        
        for suggestion in suggestions:
            if suggestion.auto_applicable:
                applied.append(suggestion)
            else:
                pending.append(suggestion)
        
        return {
            'content': optimized,
            'applied': applied,
            'pending': pending,
            'warnings': []
        }
    
    async def _optimize_readability(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Optimize content readability"""
        config = ReadabilityOptimizationConfig(
            target_flesch_score=self._get_target_flesch_score(request.target_readability),
            preserve_technical_terms=request.target_keywords if request.preserve_technical_terms else []
        )
        
        optimized, suggestions = self.readability_optimizer.optimize(content, config)
        
        # Check if readability improved
        original_score = textstat.flesch_reading_ease(content)
        new_score = textstat.flesch_reading_ease(optimized)
        
        warnings = []
        if new_score < original_score:
            warnings.append("Readability decreased after optimization")
        
        return {
            'content': optimized,
            'applied': suggestions,
            'pending': [],
            'warnings': warnings
        }
    
    async def _optimize_keywords(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Optimize keyword placement and density"""
        config = KeywordOptimizationConfig(
            primary_keywords=request.target_keywords[:5],
            secondary_keywords=request.target_keywords[5:],
            min_density=request.min_keyword_density,
            max_density=request.max_keyword_density
        )
        
        optimized, suggestions = self.keyword_optimizer.optimize(content, config)
        
        # Validate keyword density
        analysis = self._analyze_keywords(optimized, request.target_keywords)
        warnings = []
        
        for keyword, density in analysis['density'].items():
            if density > request.max_keyword_density:
                warnings.append(f"Keyword '{keyword}' density ({density:%}) exceeds maximum")
            elif density < request.min_keyword_density:
                warnings.append(f"Keyword '{keyword}' density ({density:%}) below minimum")
        
        return {
            'content': optimized,
            'applied': suggestions,
            'pending': [],
            'warnings': warnings
        }
    
    async def _optimize_grammar(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Fix grammar and spelling issues"""
        # Check grammar
        grammar_matches = self.grammar_tool.check(content)
        
        applied = []
        pending = []
        optimized = content
        
        # Apply corrections
        offset = 0
        for match in sorted(grammar_matches, key=lambda x: x.offset):
            if match.replacements:
                suggestion = OptimizationSuggestion(
                    type=OptimizationType.GRAMMAR,
                    severity="medium" if match.category == "GRAMMAR" else "low",
                    location=(match.offset + offset, match.offset + offset + match.errorLength),
                    original_text=content[match.offset:match.offset + match.errorLength],
                    suggested_text=match.replacements[0],
                    reason=match.message,
                    impact_score=0.3,
                    auto_applicable=match.category != "STYLE"
                )
                
                if suggestion.auto_applicable:
                    # Apply the correction
                    before = optimized[:match.offset + offset]
                    after = optimized[match.offset + offset + match.errorLength:]
                    optimized = before + match.replacements[0] + after
                    
                    # Update offset for subsequent corrections
                    offset += len(match.replacements[0]) - match.errorLength
                    applied.append(suggestion)
                else:
                    pending.append(suggestion)
        
        # Check spelling
        words = word_tokenize(optimized)
        misspelled = self.spell_checker.unknown(words)
        
        for word in misspelled:
            correction = self.spell_checker.correction(word)
            if correction and correction != word:
                # Find word position
                pattern = r'\b' + re.escape(word) + r'\b'
                for match in re.finditer(pattern, optimized):
                    suggestion = OptimizationSuggestion(
                        type=OptimizationType.GRAMMAR,
                        severity="low",
                        location=(match.start(), match.end()),
                        original_text=word,
                        suggested_text=correction,
                        reason=f"Possible spelling error: '{word}' -> '{correction}'",
                        impact_score=0.2,
                        auto_applicable=False  # Require review for spelling
                    )
                    pending.append(suggestion)
        
        return {
            'content': optimized,
            'applied': applied,
            'pending': pending,
            'warnings': []
        }
    
    async def _optimize_tone(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Optimize content tone"""
        current_tone = self.tone_analyzer.analyze(content)
        
        if current_tone.primary_tone == request.target_tone:
            return {
                'content': content,
                'applied': [],
                'pending': [],
                'warnings': ["Content already matches target tone"]
            }
        
        # Apply tone adjustments
        optimized, suggestions = self.tone_analyzer.adjust_tone(
            content,
            request.target_tone,
            maintain_voice=request.maintain_personal_voice
        )
        
        return {
            'content': optimized,
            'applied': suggestions,
            'pending': [],
            'warnings': []
        }
    
    async def _optimize_length(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Optimize content length"""
        if not request.target_length:
            return {
                'content': content,
                'applied': [],
                'pending': [],
                'warnings': ["No target length specified"]
            }
        
        current_length = len(content.split())
        
        if abs(current_length - request.target_length) < 10:
            return {
                'content': content,
                'applied': [],
                'pending': [],
                'warnings': ["Content already at target length"]
            }
        
        # Optimize length
        optimized, suggestions = self.length_optimizer.optimize(
            content,
            request.target_length,
            strict=request.strict_length_limit
        )
        
        warnings = []
        new_length = len(optimized.split())
        if request.strict_length_limit and new_length > request.target_length:
            warnings.append(f"Could not meet strict length limit. Current: {new_length}, Target: {request.target_length}")
        
        return {
            'content': optimized,
            'applied': suggestions,
            'pending': [],
            'warnings': warnings
        }
    
    async def _validate_terminology(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Validate industry terminology"""
        if not request.industry:
            return {
                'content': content,
                'applied': [],
                'pending': [],
                'warnings': ["No industry specified for terminology validation"]
            }
        
        # Get industry terminology
        terminology = self._get_industry_terminology(request.industry)
        
        # Validate and suggest corrections
        validated, suggestions = self.terminology_validator.validate(
            content,
            terminology
        )
        
        return {
            'content': validated,
            'applied': [s for s in suggestions if s.auto_applicable],
            'pending': [s for s in suggestions if not s.auto_applicable],
            'warnings': []
        }
    
    async def _validate_metrics(
        self,
        content: str,
        request: OptimizationRequest
    ) -> Dict[str, Any]:
        """Validate and enhance metrics"""
        metrics = self.metric_validator.extract_metrics(content)
        
        # Find vague statements that could be quantified
        suggestions = []
        for statement in metrics.vague_statements:
            suggestion = OptimizationSuggestion(
                type=OptimizationType.METRICS,
                severity="medium",
                original_text=statement,
                suggested_text=None,  # Manual quantification needed
                reason="This statement could be strengthened with specific metrics",
                impact_score=0.5,
                auto_applicable=False
            )
            suggestions.append(suggestion)
        
        # Validate existing metrics
        if not metrics.metrics_validated:
            warnings = ["Some metrics appear unrealistic and should be reviewed"]
        else:
            warnings = []
        
        return {
            'content': content,
            'applied': [],
            'pending': suggestions,
            'warnings': warnings
        }
    
    def _clean_text(self, content: str) -> str:
        """Clean text for analysis"""
        # Remove HTML if present
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _analyze_keywords(
        self,
        text: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """Analyze keyword usage in text"""
        text_lower = text.lower()
        words = word_tokenize(text_lower)
        total_words = len(words)
        
        keyword_count = {}
        keyword_density = {}
        keyword_placement = {}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = text_lower.count(keyword_lower)
            keyword_count[keyword] = count
            keyword_density[keyword] = count / total_words if total_words > 0 else 0
            
            # Find positions
            positions = []
            for match in re.finditer(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
                positions.append(match.start())
            keyword_placement[keyword] = positions
        
        # Find missing keywords
        missing = [k for k in keywords if keyword_count.get(k, 0) == 0]
        
        return {
            'count': keyword_count,
            'density': keyword_density,
            'placement': keyword_placement,
            'missing': missing
        }
    
    def _check_spelling(self, words: List[str]) -> List[str]:
        """Check for spelling errors"""
        # Filter out numbers, URLs, etc.
        filtered_words = [
            w for w in words 
            if w.isalpha() and len(w) > 2
        ]
        
        misspelled = self.spell_checker.unknown(filtered_words)
        return list(misspelled)
    
    def _check_punctuation(self, text: str) -> List[str]:
        """Check for punctuation issues"""
        issues = []
        
        # Check for double spaces
        if '  ' in text:
            issues.append("Double spaces detected")
        
        # Check for missing periods
        sentences = sent_tokenize(text)
        for sentence in sentences:
            if sentence and sentence[-1] not in '.!?':
                issues.append(f"Missing punctuation: '{sentence[:30]}...'")
        
        return issues
    
    def _count_action_verbs(self, text: str) -> List[str]:
        """Count action verbs in text"""
        action_verbs = self.resources.get('action_verbs', [])
        if not action_verbs:
            # Default action verbs
            action_verbs = [
                'achieved', 'managed', 'developed', 'created', 'led',
                'improved', 'increased', 'reduced', 'delivered', 'implemented'
            ]
        
        found_verbs = []
        text_lower = text.lower()
        
        for verb in action_verbs:
            if verb.lower() in text_lower:
                found_verbs.append(verb)
        
        return found_verbs
    
    def _determine_readability_level(self, flesch_score: float) -> ReadabilityLevel:
        """Determine readability level from Flesch score"""
        if flesch_score >= 90:
            return ReadabilityLevel.VERY_EASY
        elif flesch_score >= 70:
            return ReadabilityLevel.EASY
        elif flesch_score >= 50:
            return ReadabilityLevel.STANDARD
        elif flesch_score >= 30:
            return ReadabilityLevel.DIFFICULT
        else:
            return ReadabilityLevel.VERY_DIFFICULT
    
    def _detect_problematic_formatting(self, content: str) -> List[str]:
        """Detect formatting that might cause ATS issues"""
        issues = []
        
        # Check for tables
        if '<table' in content.lower() or '|---|' in content:
            issues.append("Tables detected - may cause ATS parsing issues")
        
        # Check for multiple columns
        if 'column' in content.lower() or 'flex' in content.lower():
            issues.append("Multi-column layout detected")
        
        # Check for special characters
        special_chars = set(re.findall(r'[^\w\s\.,;:\-\(\)\/]', content))
        if special_chars:
            issues.append(f"Special characters detected: {', '.join(special_chars)}")
        
        return issues
    
    def _format_grammar_error(self, error: Any) -> Dict[str, Any]:
        """Format grammar error for output"""
        return {
            'message': error.message,
            'category': error.category,
            'offset': error.offset,
            'length': error.errorLength,
            'replacements': error.replacements[:3] if error.replacements else []
        }
    
    def _get_target_flesch_score(self, level: ReadabilityLevel) -> float:
        """Get target Flesch score for readability level"""
        scores = {
            ReadabilityLevel.VERY_EASY: 90,
            ReadabilityLevel.EASY: 70,
            ReadabilityLevel.STANDARD: 60,
            ReadabilityLevel.DIFFICULT: 40,
            ReadabilityLevel.VERY_DIFFICULT: 20
        }
        return scores.get(level, 60)
    
    def _get_industry_terminology(self, industry: str) -> IndustryTerminology:
        """Get industry-specific terminology"""
        # Load from resources or use defaults
        terms = self.resources.get('industry_terms', {}).get(industry, {})
        
        return IndustryTerminology(
            industry=industry,
            standard_terms=terms.get('standard', []),
            avoid_terms=terms.get('avoid', []),
            preferred_synonyms=terms.get('synonyms', {}),
            common_acronyms=terms.get('acronyms', {}),
            level_appropriate_terms=terms.get('levels', {})
        )
    
    def _calculate_improvements(
        self,
        original: ContentAnalysis,
        optimized: ContentAnalysis
    ) -> Dict[str, float]:
        """Calculate improvement percentages"""
        improvements = {}
        
        # Readability improvement
        if original.flesch_reading_ease > 0:
            improvements['readability'] = (
                (optimized.flesch_reading_ease - original.flesch_reading_ease) / 
                original.flesch_reading_ease * 100
            )
        else:
            improvements['readability'] = 0
        
        # ATS score improvement
        if original.ats_score > 0:
            improvements['ats'] = (
                (optimized.ats_score - original.ats_score) / 
                original.ats_score * 100
            )
        else:
            improvements['ats'] = 0
        
        # Keyword optimization
        original_missing = len(original.missing_keywords)
        optimized_missing = len(optimized.missing_keywords)
        if original_missing > 0:
            improvements['keywords'] = (
                (original_missing - optimized_missing) / original_missing * 100
            )
        else:
            improvements['keywords'] = 100 if optimized_missing == 0 else 0
        
        return improvements
    
    def _calculate_quality_score(
        self,
        analysis: ContentAnalysis,
        request: OptimizationRequest
    ) -> float:
        """Calculate overall quality score"""
        score = 0
        weights = {
            'readability': 0.25,
            'ats': 0.25,
            'keywords': 0.20,
            'grammar': 0.15,
            'metrics': 0.15
        }
        
        # Readability score (0-100)
        readability_score = min(100, analysis.flesch_reading_ease)
        score += readability_score * weights['readability']
        
        # ATS score (0-100)
        score += analysis.ats_score * weights['ats']
        
        # Keyword score
        if request.target_keywords:
            keyword_coverage = 1 - (len(analysis.missing_keywords) / len(request.target_keywords))
            score += keyword_coverage * 100 * weights['keywords']
        else:
            score += 100 * weights['keywords']  # No keywords required
        
        # Grammar score
        grammar_score = max(0, 100 - len(analysis.grammar_errors) * 5)
        score += grammar_score * weights['grammar']
        
        # Metrics score
        metrics_score = 100 if analysis.has_metrics else 50
        score += metrics_score * weights['metrics']
        
        return min(100, score)
    
    def _calculate_confidence(self, changes: List[OptimizationSuggestion]) -> float:
        """Calculate confidence score for optimizations"""
        if not changes:
            return 1.0
        
        # Base confidence on impact scores and auto-applicability
        total_impact = sum(c.impact_score for c in changes)
        auto_applicable = sum(1 for c in changes if c.auto_applicable)
        
        confidence = 0.5  # Base confidence
        confidence += min(0.3, total_impact / 10)  # Impact contribution
        confidence += (auto_applicable / len(changes)) * 0.2  # Auto-applicable contribution
        
        return min(1.0, confidence)
    
    async def suggest_improvements(
        self,
        content: str,
        content_type: ContentType,
        target_role: Optional[str] = None
    ) -> List[str]:
        """Suggest high-level improvements for content"""
        analysis = await self.analyze_content(content, content_type, [])
        suggestions = []
        
        # Readability suggestions
        if analysis.flesch_reading_ease < 50:
            suggestions.append("Simplify sentence structure to improve readability")
        
        if analysis.avg_words_per_sentence > 20:
            suggestions.append("Break long sentences into shorter, clearer ones")
        
        # Action verb suggestions
        if not analysis.has_action_verbs:
            suggestions.append("Start bullet points with strong action verbs")
        
        # Metrics suggestions
        if not analysis.has_metrics:
            suggestions.append("Add quantifiable achievements and metrics")
        
        # ATS suggestions
        if analysis.ats_score < 70:
            suggestions.append("Remove complex formatting for better ATS compatibility")
        
        # Tone suggestions
        if analysis.formality_score < 0.6 and content_type == ContentType.COVER_LETTER:
            suggestions.append("Increase formality for professional tone")
        
        return suggestions
```

### Supporting Optimizer Modules

Create key supporting modules:

#### ATS Optimizer (`optimization/ats_optimizer.py`):
- Remove problematic formatting
- Standardize section headings
- Ensure keyword presence
- Optimize for parsing

#### Readability Optimizer (`optimization/readability_optimizer.py`):
- Simplify complex sentences
- Replace jargon with simpler terms
- Improve sentence variety
- Enhance flow and transitions

#### Keyword Optimizer (`optimization/keyword_optimizer.py`):
- Strategic keyword placement
- Natural integration
- Density optimization
- Synonym variation

### Testing Requirements

1. **Analysis Tests**: Content metrics accuracy
2. **Optimization Tests**: Each optimization type
3. **Quality Tests**: Score calculations, improvements
4. **Edge Case Tests**: Empty content, special formats
5. **Performance Tests**: Large documents, multiple passes
6. **Integration Tests**: With Creator and Formatter

### Success Criteria

- Analysis accuracy: >95% for metrics extraction
- Readability improvement: Average 10-20 point increase
- ATS score improvement: >15% average increase
- Grammar correction: >90% accuracy
- Keyword optimization: Natural placement in 100% of cases
- Processing speed: <2 seconds for standard CV
- Quality score accuracy: Correlates with human review

### Edge Cases to Handle

- Mixed languages in content
- Technical jargon preservation
- Creative formatting preservation
- Over-optimization prevention
- Conflicting optimization goals
- Content with tables/lists
- Very short/long content
- Industry-specific requirements
- Regional spelling variations
- Abbreviation handling

---

## Strategic Questions for Content Optimization

**91. Should optimization be reversible to allow users to undo changes?**
*Recommendation: Yes - Store original and track all changes with undo capability for user control.*

**92. Should we implement A/B testing to measure optimization effectiveness?**
*Recommendation: Not for PoC, but track which optimizations correlate with application success for future ML training.*

**93. Should optimization profiles be learned from successful applications?**
*Recommendation: Yes - Track which optimization settings lead to interviews and adapt defaults accordingly.*

**94. Should we support custom industry dictionaries?**
*Recommendation: Yes - Allow users to add industry-specific terms that should be preserved or preferred.*

**95. Should tone optimization consider company culture analysis?**
*Recommendation: Basic culture mapping for PoC (startup=casual, corporate=formal), expand with company research later.*

**96. Should we implement readability optimization for non-native speakers?**
*Recommendation: Not for PoC, but design optimizer to support different readability targets for future internationalization.*

**97. Should optimization suggestions explain why changes improve content?**
*Recommendation: Yes - Include brief explanations to educate users and build trust in the system.*

**98. Should we optimize for specific ATS systems (Taleo, Workday, etc.)?**
*Recommendation: Generic ATS optimization for PoC, add system-specific rules based on user feedback.*

**99. Should content optimization consider SEO for online profiles?**
*Recommendation: No for PoC - focus on ATS and human readability, add LinkedIn/online optimization in v2.*

**100. Should we implement sentiment analysis to ensure positive tone?**
*Recommendation: Basic positivity check for PoC - flag overly negative language but don't auto-correct tone beyond target formality.*

---

This completes the Content Optimizer Service implementation instructions, providing comprehensive content enhancement capabilities to ensure professional, ATS-compatible, and impactful application materials.