# Scout Documentation Index

This directory contains comprehensive specifications for all Scout modules and services.

## Directory Structure

- **modules/** - Core processing modules (M1-M5)
- **services/** - Supporting services (S1-S8)
- **architecture/** - System design and configuration docs
- **guides/** - Development guides and checklists

## Module Specifications

### Core Modules
- [Module 1: Collector](modules/M1_Collector.md) - Profile management and indexing
- [Module 2: Rinser](modules/M2_Rinser.md) - Job text sanitization and extraction
- [Module 3: Analyzer](modules/M3_Analyzer.md) - Semantic matching and scoring
- [Module 4: Creator](modules/M4_Creator.md) - Tailored content generation
- [Module 5: Formatter](modules/M5_Formatter.md) - Document formatting and PDF generation

### Services
- [S1: LLM Service](services/S1_LLM_Service.md) - Claude API integration
- [S2: Cost Tracker](services/S2_Cost_Tracker.md) - Budget management
- [S3: Cache Service](services/S3_Cache_Service.md) - Multi-tier caching
- [S4: Vector Store](services/S4_Vector_Store.md) - ChromaDB integration
- [S6: Pipeline Orchestrator](services/S6_Pipeline_Orchestrator.md) - Module coordination
- [S7: Content Optimizer](services/S7_Content_Optimizer.md) - Output quality enhancement
- [S8: Notification Service](services/S8_Notification_Service.md) - User notifications
- [Web Interface](services/Web_Interface.md) - User interface specification

### Architecture & Guides
- [Scout PoC Scope](architecture/Scout_PoC_Scope.md) - Project scope and boundaries
- [Project Structure](architecture/Project_Structure.md) - Complete system architecture
- [Implementation Checklist](guides/Implementation_Checklist.md) - Step-by-step development guide
- [Development Guide](guides/Development_Guide.md) - Code patterns and standards
- [CLAUDE.md](guides/CLAUDE.md) - Claude Code interaction guide

## Implementation Order

1. **Phase 1: Foundation Services** (S2 → S3 → S4 → S1)
2. **Phase 2: Core Modules** (M1 → M2 → M3 → M4 → M5)
3. **Phase 3: Integration** (S6 → API → S8 → Web)

See [Implementation Checklist](guides/Implementation_Checklist.md) for detailed steps.

## Using These Specifications

Each specification document contains:
- **Context & Objective** - What the component does
- **Technical Requirements** - Dependencies and file structure
- **Data Models** - Pydantic models to implement
- **Implementation** - Core logic and patterns
- **Testing** - Test requirements and examples
- **Success Criteria** - Acceptance criteria

Follow the implementation checklist for systematic development with Claude Code.
