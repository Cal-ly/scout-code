# Scout Specification Reference Guide

## Overview

All detailed specifications are available in this Claude AI project's knowledge base at `/mnt/project/`. This document provides quick access paths for Claude Code development.

## Quick Reference - Module Specifications

When implementing with Claude Code, reference these specifications from project knowledge:

### Core Modules (Implementation Order: M1 → M2 → M3 → M4 → M5)

- **M1 Collector** - `/mnt/project/Module_1_Collector_-_Claude_Code_Instructions.md`
  - Profile management, YAML loading, vector indexing
  - **Start here**: Profile data models and ChromaDB integration

- **M2 Rinser** - `/mnt/project/Module_2_Rinser_-_Claude_Code_Instructions.md`
  - Job text sanitization, LLM-powered extraction
  - **Key**: HTML cleaning, structured data extraction

- **M3 Analyzer** - `/mnt/project/Module_3_Analyzer_-_Claude_Code_Instructions.md`
  - Semantic matching, compatibility scoring
  - **Key**: Vector similarity, gap analysis

- **M4 Creator** - `/mnt/project/Module_4_Creator_-_Claude_Code_Instructions.md`
  - Tailored CV and cover letter generation
  - **Key**: LLM prompting, content adaptation

- **M5 Formatter** - `/mnt/project/Module_5_Formatter_-_Claude_Code_Instructions.md`
  - PDF generation, document formatting
  - **Key**: WeasyPrint, template rendering

### Services (Implementation Order: S2 → S3 → S4 → S1 → S6 → S7 → S8)

- **S1 LLM Service** - `/mnt/project/S1_LLM_Service_-_Claude_Code_Instructions.md`
  - Claude API integration, retry logic, token management
  
- **S2 Cost Tracker** - `/mnt/project/S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md`
  - Budget enforcement, cost tracking
  
- **S3 Cache Service** - `/mnt/project/S3_Cache_Service_-_Claude_Code_Instructions.md`
  - Multi-tier caching (memory + file)
  
- **S4 Vector Store** - `/mnt/project/S4_Vector_Store_Service_-_Claude_Code_Instructions.md`
  - ChromaDB wrapper, embedding management
  
- **S6 Pipeline Orchestrator** - `/mnt/project/S6_Pipeline_Orchestrator_-_Claude_Code_Instructions.md`
  - Module coordination, error handling
  
- **S7 Content Optimizer** - `/mnt/project/S7_Content_Optimizer_Service_-_Claude_Code_Instructions.md`
  - Output quality enhancement (deferred in PoC)
  
- **S8 Notification Service** - `/mnt/project/S8_Notification_Service_-_Claude_Code_Instructions.md`
  - In-app notifications

- **Web Interface** - `/mnt/project/Web_Interface_-_Claude_Code_Instructions.md`
  - FastAPI routes, UI components

### Architecture & Planning Documents

- **PoC Scope** - `/mnt/project/Scout_PoC_Scope_Document.md`
  - **CRITICAL**: What's in/out of scope, boundaries, constraints
  
- **Project Structure** - `/mnt/project/Scout_PoC_-_Complete_Project_Structure___Configuration.md`
  - Complete directory layout, Docker setup
  
- **Implementation Checklist** - `/mnt/project/Scout_Implementation_Checklist.md`
  - **Step-by-step guide** with checkboxes for each component
  
- **Development Guide** - `/mnt/project/Scout_Claude_Code_Development_Guide.md`
  - Code patterns, best practices, standards
  
- **CLAUDE.md** - `/mnt/project/CLAUDE.md`
  - How to interact with Claude Code effectively

- **Initial Concept** - `/mnt/project/Scout_Initial_Concept`
  - Original project vision and requirements

## Usage with Claude Code

### Starting a New Module

1. Open Claude Code in the terminal
2. Reference the specific specification: 
   ```
   "I'm implementing Module X. Please read /mnt/project/Module_X_..._Instructions.md"
   ```
3. Claude Code will read the spec and implement following the detailed requirements

### Implementation Pattern

For each component:
1. **Read Spec** → Claude Code reads from `/mnt/project/`
2. **Create Models** → Pydantic data models first
3. **Implement Core** → Main service/module logic
4. **Write Tests** → Unit tests with fixtures
5. **Verify** → Run tests, check coverage

### Key Files to Reference

**Before any implementation:**
- Read `/mnt/project/Scout_PoC_Scope_Document.md` for boundaries
- Read `/mnt/project/Scout_Implementation_Checklist.md` for order

**During implementation:**
- Reference specific module/service specification
- Follow patterns in `/mnt/project/CLAUDE.md`

## Project Checklist Status

Track progress in `/mnt/project/Scout_Implementation_Checklist.md`:

### Phase 1: Foundation Services
- [ ] S2 Cost Tracker
- [ ] S3 Cache Service  
- [ ] S4 Vector Store
- [ ] S1 LLM Service

### Phase 2: Core Modules
- [ ] M1 Collector
- [ ] M2 Rinser
- [ ] M3 Analyzer
- [ ] M4 Creator
- [ ] M5 Formatter

### Phase 3: Integration
- [ ] S6 Pipeline Orchestrator
- [ ] API Routes
- [ ] S8 Notification Service
- [ ] Web Interface

## Claude Code Commands

```bash
# Start implementation session
claude "Let's implement S2 Cost Tracker. Read /mnt/project/S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md and create the implementation"

# Continue existing work
claude "Continue implementing the Cost Tracker tests"

# Review and verify
claude "Review the implementation against the specification in /mnt/project/"
```

## Important Notes

- **All specifications are in project knowledge** - No need to manually copy files
- **Specifications are comprehensive** - Include data models, tests, edge cases
- **Follow implementation order** - Dependencies matter (services before modules)
- **Check PoC scope** - Many features are explicitly deferred
- **Use checklist** - Track progress systematically

## Next Steps

1. ✅ Project structure created
2. ✅ Specifications centralized  
3. → Start Phase 1: Implement S2 Cost Tracker Service
4. → Follow implementation checklist step-by-step

---

**Ready to start implementation with Claude Code!**
