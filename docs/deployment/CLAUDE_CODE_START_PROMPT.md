# Claude Code Start Prompt - Pre-Flight Verification

---

## Mission

Execute comprehensive pre-flight verification for Scout PoC deployment to Raspberry Pi 5. Your goal is to systematically validate that the codebase aligns with deployment requirements, create all necessary test scripts, execute verification phases, and document results.

## Context

Scout is a job application automation system using local Ollama LLM inference (no cloud APIs). We've completed quick wins:
- Removed Redis from configuration
- Cleaned up .env.example (Ollama only)
- Created verification documentation
- Aligned deployment guide with PoC scope

## SSH Access to Raspberry Pi 5

**IMPORTANT: You have passwordless SSH access to the target deployment machine.**

**Connection Details:**
- Host: `192.168.1.21`
- User: `cally`
- Authentication: SSH key (passwordless)
- OS: Ubuntu Server 24.04 LTS (ARM64)

**SSH Commands:**
```bash
# Connect to Pi 5
ssh cally@192.168.1.21

# Execute remote command
ssh cally@192.168.1.21 "command here"

# Copy files to Pi 5
scp local_file cally@192.168.1.21:/path/on/pi/
```

**When to Use SSH:**
- You do NOT need SSH for pre-flight verification (Phases 1-8)
- Pre-flight tests run on LOCAL development machine (Windows 11)
- SSH will be needed for actual deployment (after verification completes)
- The deployment guide references SSH extensively

**For This Session:**
You are performing PRE-FLIGHT verification on the local Windows machine. Do NOT connect to the Pi 5 yet. All test scripts run locally to validate the codebase before deployment.

## Your Task

Work through the comprehensive verification document systematically, creating test scripts and validating each aspect of the codebase before Pi 5 deployment.

## Essential Reading (In Order)

1. **`docs/deployment/PreFlight_QuickWins_Status.md`**
   - What's already done
   - Current state summary
   - Files modified/created

2. **`docs/deployment/Deployment_PreFlight_Verification.md`**
   - Your primary work guide
   - 8 verification phases with detailed instructions
   - Test scripts to create and execute
   - Success criteria for each check

3. **`docs/deployment/Deployment_PreFlight_Checklist.md`**
   - Quick reference
   - Go/No-Go decision matrix
   - Use for tracking progress

## Working Methodology

Follow the **RAVE approach** in ~15-minute increments:

### Session 1: Environment Configuration Verification
**Objective:** Validate .env.example and configuration files
**Deliverables:**
- Verification of .env.example (Section 1.1)
- Confirmation Redis is removed (Section 1.2)
- Data directory structure validation (Section 1.3)
- Document findings in verification notes

**Commands to run:**
```bash
cat .env.example | grep -E "(LLM_|OLLAMA_|ANTHROPIC|OPENAI)"
cat .env.example | grep -i redis
cat .env.example | grep -E "(DIR|PATH)" | grep -v "^#"
```

### Session 2: Dependency Validation
**Objective:** Check requirements.txt for ARM64 compatibility
**Deliverables:**
- requirements.txt ARM64 check (Section 2.1)
- Redis dependency verification (Section 2.2)
- ChromaDB version check (Section 2.3)
- Document package versions

**Commands to run:**
```bash
grep -E "(ollama|chromadb|sentence-transformers|fastapi)" requirements.txt
grep -i redis requirements.txt
```

### Session 3: Service Integration Tests (Part 1)
**Objective:** Create and run cost tracker tests
**Deliverables:**
- `test_cost_tracker_local.py` created (Section 3.1)
- `test_cost_tracker_zero_budget.py` created (Section 5.1)
- `test_cost_tracker_metrics.py` created (Section 5.2)
- Execute tests, document results

**Test creation:** Follow exact scripts from Verification document Section 3.1, 5.1, 5.2

### Session 4: Service Integration Tests (Part 2)
**Objective:** Create and run cache service tests
**Deliverables:**
- `test_cache_service.py` created (Section 3.2)
- `test_cache_lru.py` created (Section 6.1)
- Execute tests, document results

**Test creation:** Follow exact scripts from Verification document Section 3.2, 6.1

### Session 5: LLM Service Validation
**Objective:** Validate Ollama provider integration
**Deliverables:**
- `test_llm_service_init.py` created (Section 3.3)
- `test_ollama_response_parsing.py` created (Section 4.1)
- `scripts/check_ollama.py` utility created (Section 4.2)
- Execute tests, document results

**Note:** Ollama connection will fail (expected on dev machine)

### Session 6: Integration & ARM64 Tests
**Objective:** Create end-to-end validation tests
**Deliverables:**
- `test_sentence_transformers_arm64.py` created (Section 7.1)
- `test_pipeline_integration.py` created (Section 8.1)
- Execute tests, document results

### Session 7: Final Verification & Report
**Objective:** Complete verification checklist and generate report
**Deliverables:**
- Fill out `Deployment_PreFlight_Checklist.md`
- Generate `verification_report.txt` with all test outputs
- Create summary of findings
- Identify any blockers or issues

## Critical Instructions

### Test Script Creation
- Copy test scripts EXACTLY from Verification document
- Save all test_*.py files in repository root (NOT in tests/ directory)
- Ensure each script is executable: `python test_*.py`

### Expected Test Results
- **PASS:** Configuration checks, dependency checks
- **PASS:** Cost tracker handles $0.00 costs
- **PASS:** Cache service file persistence
- **EXPECTED FAIL:** LLM service Ollama connection (Ollama not installed on dev machine)
- **PASS:** Mock response parsing (no Ollama needed)
- **PASS:** Service integration (with Ollama unavailable warning)

### Issue Documentation
For any failed check:
1. Document exact error in verification notes
2. Reference Verification document "IF FAILED" section
3. Attempt resolution if straightforward
4. Flag for human review if complex

### Git Hygiene
- Do NOT commit test_*.py files (already in .gitignore)
- Do NOT commit verification_report.txt
- Do NOT commit test_cache_temp/

## Success Criteria

### Minimum Success (Go for Deployment)
- [ ] All configuration checks pass (Section 1)
- [ ] All dependency checks pass (Section 2)
- [ ] Cost tracker handles zero costs without error (Section 3.1, 5.1)
- [ ] Cache service works with file persistence (Section 3.2, 6.1)
- [ ] LLM service initializes OllamaProvider (graceful fail OK) (Section 3.3)
- [ ] All test scripts created (9 scripts total)
- [ ] Verification checklist completed

### Ideal Success (All Tests Pass)
- [ ] sentence-transformers loads successfully (Section 7.1)
- [ ] Integration test passes (Section 8.1)
- [ ] No import errors in any service
- [ ] Go/No-Go matrix shows all GO criteria

## Deliverables

### Files to Create
1. test_cost_tracker_local.py
2. test_cost_tracker_zero_budget.py
3. test_cost_tracker_metrics.py
4. test_cache_service.py
5. test_cache_lru.py
6. test_llm_service_init.py
7. test_ollama_response_parsing.py
8. test_sentence_transformers_arm64.py
9. test_pipeline_integration.py
10. scripts/check_ollama.py

### Reports to Generate
1. `verification_report.txt` - All test outputs concatenated
2. Updated `Deployment_PreFlight_Checklist.md` with checkboxes filled

### Summary Document
Create `docs/deployment/Verification_Results_Summary.md` containing:
- Overall status (GO / NO-GO / CONDITIONAL)
- Issues found and resolutions
- Checklist completion status
- Recommendations for deployment

## Repository Location

```
C:\Users\Cal-l\Documents\GitHub\Scout\scout-code
```

## Working Directory

Stay in repository root for all operations.

## Final Notes

### What Makes This Different
This isn't a code review - it's **functional verification** that the code matches deployment requirements. Focus on:
- Does it align with PoC scope? (no Redis, no cloud APIs)
- Will it work on ARM64? (dependency compatibility)
- Does it handle local LLM? (zero costs, Ollama provider)

### Communication Style
- Document findings factually
- Use verification document's success criteria as binary pass/fail
- Flag ambiguities or unexpected results
- No need to explain every passing test - focus on failures and edge cases

### Time Boxing
- Spend ~10-15 minutes per session
- If a test script creation takes >5 minutes, flag for review
- Don't debug code issues - document and move on
- Complete all verification phases even if some tests fail

---

## Ready to Start?

Begin with Session 1: Environment Configuration Verification.

Read `docs/deployment/PreFlight_QuickWins_Status.md` to understand what's already done, then proceed through `Deployment_PreFlight_Verification.md` Section 1.

Your first command:
```bash
cat .env.example | grep -E "(LLM_|OLLAMA_|ANTHROPIC|OPENAI)"
```

Good luck! 🚀
