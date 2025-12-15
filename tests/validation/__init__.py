"""
Scout Validation Test Framework

Provides structured test cases and metrics collection for pipeline validation.

Usage:
    # List available test cases
    python -m tests.validation.runner --list

    # Run all test cases
    python -m tests.validation.runner --all

    # Run specific test case
    python -m tests.validation.runner --case TC001
"""

from pathlib import Path

VALIDATION_DIR = Path(__file__).parent
TEST_CASES_FILE = VALIDATION_DIR / "test_cases.yaml"
TEST_PROFILE_FILE = VALIDATION_DIR / "test_profile.yaml"
RESULTS_DIR = VALIDATION_DIR / "results"
