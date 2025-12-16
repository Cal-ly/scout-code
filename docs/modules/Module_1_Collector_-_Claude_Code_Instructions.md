---
updated: 2025-10-04, 18:19
---

## Module 1: Collector - Claude Code Instructions

### Context & Objective

You're building the **Collector module** for Scout, an intelligent job application system. This module manages the user's professional profile data, making it searchable and accessible for tailored application generation.

### Module Specifications

**Purpose**: Store, index, and retrieve user profile information for semantic matching against job requirements.

**Key Responsibilities**:
1. Load and validate user profile data from YAML/JSON
2. Create vector embeddings for experiences and skills
3. Provide semantic search for relevant experiences
4. Maintain profile versioning and updates

### Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- ChromaDB for vector storage
- PyYAML for profile loading
- Claude 3.5 Haiku API for intelligent extraction

**File Structure**:
```
scout/
├── app/
│   ├── core/
│   │   └── collector.py
│   ├── models/
│   │   └── profile.py
│   └── config/
│       └── settings.py
├── data/
│   ├── profile.yaml (user-editable)
│   └── vectors/ (ChromaDB storage)
└── tests/
    └── test_collector.py
```

### Data Models to Implement

Create these models in `app/models/profile.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class Skill(BaseModel):
    name: str
    level: SkillLevel
    years: Optional[float] = None
    keywords: List[str] = []  # Related terms for matching

class Experience(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    company: str
    role: str
    start_date: datetime
    end_date: Optional[datetime] = None
    current: bool = False
    description: str
    achievements: List[str] = []
    technologies: List[str] = []
    
    @validator('current', always=True)
    def set_current(cls, v, values):
        return values.get('end_date') is None

class Education(BaseModel):
    institution: str
    degree: str
    field: str
    start_date: datetime
    end_date: Optional[datetime]
    gpa: Optional[float] = None
    relevant_courses: List[str] = []

class Certification(BaseModel):
    name: str
    issuer: str
    date_obtained: datetime
    expiry_date: Optional[datetime] = None
    credential_id: Optional[str] = None

class UserProfile(BaseModel):
    # Basic Info
    full_name: str
    email: str
    phone: Optional[str] = None
    location: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    
    # Professional Summary
    title: str
    years_experience: float
    summary: str
    
    # Detailed Sections
    skills: List[Skill] = []
    experiences: List[Experience] = []
    education: List[Education] = []
    certifications: List[Certification] = []
    
    # Metadata
    profile_version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.now)
```

### Collector Implementation

Create the main module in `app/core/collector.py`:

```python
import chromadb
from chromadb.utils import embedding_functions
import yaml
import json
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
from datetime import datetime

class Collector:
    def __init__(
        self, 
        profile_path: str = "data/profile.yaml",
        vector_db_path: str = "data/vectors",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.profile_path = Path(profile_path)
        self.vector_db_path = Path(vector_db_path)
        
        # Initialize profile
        self.profile: Optional[UserProfile] = None
        self.profile_hash: Optional[str] = None
        
        # Initialize vector store
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_db_path)
        )
        
        # Use sentence transformers for embeddings
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Create or get collections
        self.experiences_collection = self.chroma_client.get_or_create_collection(
            name="experiences",
            embedding_function=self.embedding_function
        )
        
        self.skills_collection = self.chroma_client.get_or_create_collection(
            name="skills",
            embedding_function=self.embedding_function
        )
    
    async def initialize(self) -> None:
        """Load profile and build vector indices"""
        await self.load_profile()
        await self.index_profile()
    
    async def load_profile(self) -> UserProfile:
        """Load and validate user profile from YAML"""
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile not found at {self.profile_path}")
        
        # Load YAML
        with open(self.profile_path, 'r') as f:
            profile_data = yaml.safe_load(f)
        
        # Validate with Pydantic
        self.profile = UserProfile(**profile_data)
        
        # Calculate hash for change detection
        profile_str = json.dumps(profile_data, sort_keys=True, default=str)
        self.profile_hash = hashlib.md5(profile_str.encode()).hexdigest()
        
        return self.profile
    
    async def index_profile(self) -> None:
        """Create vector embeddings for profile components"""
        if not self.profile:
            await self.load_profile()
        
        # Clear existing indices
        self.experiences_collection.delete(
            where={"profile_hash": {"$ne": self.profile_hash}}
        )
        
        # Index experiences
        for exp in self.profile.experiences:
            # Create rich text for embedding
            exp_text = f"{exp.role} at {exp.company}. {exp.description} "
            exp_text += f"Technologies: {', '.join(exp.technologies)}. "
            exp_text += f"Achievements: {' '.join(exp.achievements)}"
            
            self.experiences_collection.add(
                documents=[exp_text],
                metadatas=[{
                    "company": exp.company,
                    "role": exp.role,
                    "start_date": exp.start_date.isoformat(),
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "current": exp.current,
                    "technologies": json.dumps(exp.technologies),
                    "profile_hash": self.profile_hash
                }],
                ids=[exp.id]
            )
        
        # Index skills with context
        for skill in self.profile.skills:
            skill_text = f"{skill.name} - {skill.level} level"
            if skill.years:
                skill_text += f", {skill.years} years experience"
            if skill.keywords:
                skill_text += f". Related: {', '.join(skill.keywords)}"
            
            self.skills_collection.add(
                documents=[skill_text],
                metadatas=[{
                    "name": skill.name,
                    "level": skill.level,
                    "years": skill.years,
                    "keywords": json.dumps(skill.keywords),
                    "profile_hash": self.profile_hash
                }],
                ids=[f"skill_{skill.name.lower().replace(' ', '_')}"]
            )
    
    def search_experiences(
        self, 
        query: str, 
        n_results: int = 5
    ) -> List[Dict]:
        """Semantic search for relevant experiences"""
        results = self.experiences_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            formatted_results.append({
                'id': doc_id,
                'company': metadata['company'],
                'role': metadata['role'],
                'relevance_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                'content': results['documents'][0][i],
                'technologies': json.loads(metadata['technologies'])
            })
        
        return formatted_results
    
    def search_skills(
        self, 
        requirements: List[str], 
        threshold: float = 0.7
    ) -> Dict[str, List[Dict]]:
        """Match requirements against user skills"""
        matches = {}
        
        for req in requirements:
            results = self.skills_collection.query(
                query_texts=[req],
                n_results=3
            )
            
            # Filter by threshold
            relevant_skills = []
            for i, doc_id in enumerate(results['ids'][0]):
                if results['distances'][0][i] < (1 - threshold):
                    metadata = results['metadatas'][0][i]
                    relevant_skills.append({
                        'skill': metadata['name'],
                        'level': metadata['level'],
                        'match_score': 1 - results['distances'][0][i]
                    })
            
            if relevant_skills:
                matches[req] = relevant_skills
        
        return matches
    
    def get_profile_summary(self) -> Dict:
        """Get a summary of the loaded profile"""
        if not self.profile:
            return {"error": "No profile loaded"}
        
        return {
            "name": self.profile.full_name,
            "title": self.profile.title,
            "years_experience": self.profile.years_experience,
            "skill_count": len(self.profile.skills),
            "experience_count": len(self.profile.experiences),
            "last_updated": self.profile.last_updated.isoformat()
        }
    
    async def update_profile_field(self, field: str, value: any) -> bool:
        """Update a specific field in the profile"""
        # Reload profile
        await self.load_profile()
        
        # Update field
        if hasattr(self.profile, field):
            setattr(self.profile, field, value)
            self.profile.last_updated = datetime.now()
            
            # Save back to YAML
            profile_dict = self.profile.dict()
            with open(self.profile_path, 'w') as f:
                yaml.dump(profile_dict, f, default_flow_style=False)
            
            # Re-index
            await self.index_profile()
            return True
        
        return False
```

### Test Implementation Requirements

Create `tests/test_collector.py`:

1. Test profile loading from YAML
2. Test vector indexing completion
3. Test experience search with sample queries
4. Test skill matching against requirements
5. Test profile updates and re-indexing

### Sample Profile YAML

Create `data/profile.yaml` with this structure:

```yaml
full_name: "John Doe"
email: "john.doe@example.com"
location: "Copenhagen, Denmark"
title: "Senior Software Engineer"
years_experience: 8.5
summary: "Experienced full-stack developer with focus on Python and cloud technologies"

skills:
  - name: "Python"
    level: "expert"
    years: 8
    keywords: ["Django", "FastAPI", "Flask", "async"]
  - name: "Machine Learning"
    level: "advanced"
    years: 3
    keywords: ["PyTorch", "scikit-learn", "NLP", "computer vision"]

experiences:
  - company: "TechCorp"
    role: "Senior Software Engineer"
    start_date: 2021-03-01
    description: "Lead developer for cloud-native applications"
    achievements:
      - "Reduced API response time by 60%"
      - "Implemented ML pipeline serving 1M requests/day"
    technologies: ["Python", "AWS", "Docker", "Kubernetes"]
```

### Configuration Settings

Create `app/config/settings.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Profile settings
    profile_path: str = "data/profile.yaml"
    vector_db_path: str = "data/vectors"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # ChromaDB settings
    chroma_persist: bool = True
    chroma_anonymized_telemetry: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Success Criteria

1. Profile loads successfully from YAML with full validation
2. All experiences and skills are indexed in ChromaDB
3. Semantic search returns relevant experiences for job requirements
4. Skills matching identifies gaps and strengths
5. Profile updates trigger re-indexing automatically
6. Tests pass with >90% coverage

### Edge Cases to Handle

- Missing or malformed YAML file
- Empty profile sections
- Duplicate experience IDs
- Vector DB persistence between restarts
- Large profiles (>100 experiences)
- Non-English content in profiles

Build this module with comprehensive error handling, logging, and make it production-ready. Focus on clean interfaces that other modules can easily use.