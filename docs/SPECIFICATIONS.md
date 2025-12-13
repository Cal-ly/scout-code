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
  - **Ollama local LLM integration** (Qwen 2.5 3B / Gemma 2 2B)
  - See also: `docs/guides/Local_LLM_Transition_Guide.md`
  
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

- **Local LLM Transition** - `docs/guides/Local_LLM_Transition_Guide.md`
  - **NEW**: Migration from Anthropic API to Ollama local inference

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

All phases complete. Track progress in `/mnt/project/Scout_Implementation_Checklist.md`:

### Phase 1: Foundation Services (COMPLETE)
- [x] S2 Cost Tracker (27 tests)
- [x] S3 Cache Service (46 tests)
- [x] S4 Vector Store (55 tests)
- [x] S1 LLM Service (52 tests) - **Refactored for Ollama**

### Phase 2: Core Modules (COMPLETE)
- [x] M1 Collector (49 tests)
- [x] M2 Rinser (71 tests)
- [x] M3 Analyzer (62 tests)
- [x] M4 Creator (48 tests)
- [x] M5 Formatter (38 tests)

### Phase 3: Integration (COMPLETE)
- [x] S6 Pipeline Orchestrator (52 tests)
- [x] API Routes (43 tests)
- [x] S8 Notification Service (40 tests)
- [x] Web Interface (26 tests)

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

## Completion Status

**All PoC phases complete (609+ tests passing)**

1. ✅ Project structure created
2. ✅ Specifications centralized
3. ✅ Phase 1: Foundation Services implemented
4. ✅ Phase 2: Core Modules implemented
5. ✅ Phase 3: Integration implemented
6. ✅ LLM Service refactored for local Ollama inference

**Architecture:** Local LLM via Ollama (Qwen 2.5 3B / Gemma 2 2B)

---

*Last updated: December 13, 2025*
