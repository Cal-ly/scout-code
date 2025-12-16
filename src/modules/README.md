# Scout Modules

Core processing modules that implement the job application pipeline.

## Module Overview

| Module | Purpose | Key Class | LLM? |
|--------|---------|-----------|------|
| **M1 Collector** | User profile management | `Collector` | No |
| **M2 Rinser** | Job posting extraction | `Rinser` | Yes |
| **M3 Analyzer** | Profile-job matching | `Analyzer` | Yes |
| **M4 Creator** | Content generation | `Creator` | Yes |
| **M5 Formatter** | PDF generation | `Formatter` | No |

## Pipeline Flow

```
                    ┌─────────────────────────────────────────┐
                    │         Pipeline Orchestrator           │
                    │   (src/services/pipeline/pipeline.py)   │
                    └─────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│    Rinser     │              │   Collector   │              │   Analyzer    │
│ ┌───────────┐ │              │ ┌───────────┐ │              │ ┌───────────┐ │
│ │process_job│─┼──────────────┼▶│get_profile│ │◀─────────────┼─│  analyze  │ │
│ └───────────┘ │              │ └───────────┘ │              │ └───────────┘ │
│               │              │               │              │               │
│ Input:        │              │ Input:        │              │ Input:        │
│  Raw job text │              │  YAML file    │              │  ProcessedJob │
│               │              │               │              │  UserProfile  │
│ Output:       │              │ Output:       │              │               │
│  ProcessedJob │              │  UserProfile  │              │ Output:       │
└───────────────┘              └───────────────┘              │  AnalysisResult│
        │                                                     └───────────────┘
        │                              ┌──────────────────────────────┘
        │                              │
        ▼                              ▼
┌───────────────┐              ┌───────────────┐
│    Creator    │              │   Formatter   │
│ ┌───────────┐ │              │ ┌───────────┐ │
│ │create_    │ │              │ │format_    │ │
│ │content    │─┼─────────────▶│ │documents  │ │
│ └───────────┘ │              │ └───────────┘ │
│               │              │               │
│ Input:        │              │ Input:        │
│  UserProfile  │              │  CVContent    │
│  AnalysisResult              │  CoverLetter  │
│               │              │               │
│ Output:       │              │ Output:       │
│  CreatedContent              │  PDF files    │
└───────────────┘              └───────────────┘
```

## Module Structure

Each module follows the same pattern:

```
module_name/
├── __init__.py       # Exports (get_module, Module, models)
├── models.py         # Pydantic data models
├── exceptions.py     # Module-specific exceptions
├── prompts.py        # LLM prompts (if applicable)
└── <module>.py       # Main implementation
```

## Usage Examples

### Get User Profile
```python
from src.modules.collector import get_collector

collector = await get_collector()
await collector.load_profile(Path("data/profile.yaml"))
profile = collector.get_profile()
```

### Process Job Posting
```python
from src.modules.rinser import get_rinser

rinser = await get_rinser()
processed_job = await rinser.process_job(raw_job_text)
print(f"Title: {processed_job.title}")
print(f"Company: {processed_job.company.name}")
```

### Analyze Compatibility
```python
from src.modules.analyzer import get_analyzer

analyzer = await get_analyzer()
result = await analyzer.analyze(processed_job)
print(f"Score: {result.compatibility.overall}%")
```

### Generate Content
```python
from src.modules.creator import get_creator

creator = await get_creator()
content = await creator.create_content(profile, analysis_result)
```

### Create PDFs
```python
from src.modules.formatter import get_formatter

formatter = await get_formatter()
docs = await formatter.format_documents(
    cv_content=content.cv,
    cover_letter=content.cover_letter,
    output_dir=Path("outputs/")
)
```

## Key Models

### UserProfile (M1)
```python
class UserProfile(BaseModel):
    full_name: str
    email: str
    title: str
    skills: list[Skill]
    experiences: list[Experience]
    education: list[Education]
    certifications: list[Certification]
```

### ProcessedJob (M2)
```python
class ProcessedJob(BaseModel):
    title: str
    company: Company
    requirements: list[Requirement]
    responsibilities: list[str]
    benefits: list[str]
```

### AnalysisResult (M3)
```python
class AnalysisResult(BaseModel):
    compatibility: CompatibilityScore
    skill_matches: list[SkillMatch]
    gaps: list[SkillGap]
    strategy: ApplicationStrategy
```

---

*For full model definitions, see each module's `models.py` file.*
