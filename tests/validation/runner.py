"""
Scout Validation Test Runner

Runs validation test cases through the pipeline and collects metrics.

Usage:
    # Run all test cases
    python -m tests.validation.runner --all

    # Run specific test case
    python -m tests.validation.runner --case TC001

    # Run category of tests
    python -m tests.validation.runner --category baseline

    # Dry run (show what would be executed)
    python -m tests.validation.runner --all --dry-run

    # Save results to specific file
    python -m tests.validation.runner --all --output results_2024_01_01.json
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
VALIDATION_DIR = Path(__file__).parent
TEST_CASES_FILE = VALIDATION_DIR / "test_cases.yaml"
TEST_PROFILE_FILE = VALIDATION_DIR / "test_profile.yaml"
RESULTS_DIR = VALIDATION_DIR / "results"

# Ollama configuration
OLLAMA_HOST = "http://localhost:11434"


async def check_ollama_available() -> tuple[bool, str]:
    """Check if Ollama server is running and has required models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check server is running
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code != 200:
                return False, "Ollama server not responding"
            
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            
            # Check for required models
            required = ["qwen2.5:3b", "gemma2:2b"]
            available = [m for m in required if any(m in model for model in models)]
            
            if not available:
                return False, f"No required models found. Available: {models}. Need one of: {required}"
            
            return True, f"Ollama ready with models: {available}"
            
    except httpx.ConnectError:
        return False, "Ollama server not running. Start with: ollama serve"
    except Exception as e:
        return False, f"Ollama check failed: {e}"


class ValidationResult:
    """Result of a single validation test case."""

    def __init__(self, test_case_id: str):
        self.test_case_id = test_case_id
        self.test_case_name: str = ""
        self.category: str = ""
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.success: bool = False
        self.error: str | None = None

        # Pipeline results
        self.pipeline_status: str | None = None
        self.total_duration_ms: int = 0
        self.step_durations: dict[str, int] = {}

        # Extraction results
        self.extracted_job_title: str | None = None
        self.extracted_company: str | None = None
        self.extracted_requirements: list[str] = []

        # Analysis results
        self.compatibility_score: float | None = None
        self.top_matches: list[str] = []
        self.key_gaps: list[str] = []

        # Output paths
        self.cv_path: str | None = None
        self.cover_letter_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case_name,
            "category": self.category,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.total_duration_ms,
            "success": self.success,
            "error": self.error,
            "pipeline_status": self.pipeline_status,
            "step_durations": self.step_durations,
            "extraction": {
                "job_title": self.extracted_job_title,
                "company": self.extracted_company,
                "requirements_count": len(self.extracted_requirements),
                "requirements": self.extracted_requirements[:10],  # Limit for readability
            },
            "analysis": {
                "compatibility_score": self.compatibility_score,
                "top_matches": self.top_matches[:5],
                "key_gaps": self.key_gaps[:5],
            },
            "outputs": {
                "cv_path": self.cv_path,
                "cover_letter_path": self.cover_letter_path,
            },
        }


class ValidationRunner:
    """Runs validation test cases and collects metrics."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.test_cases: list[dict[str, Any]] = []
        self.results: list[ValidationResult] = []
        self.profile_loaded = False

    def load_test_cases(self) -> None:
        """Load test cases from YAML file."""
        logger.info(f"Loading test cases from {TEST_CASES_FILE}")

        with open(TEST_CASES_FILE) as f:
            data = yaml.safe_load(f)

        self.test_cases = data.get("test_cases", [])
        logger.info(f"Loaded {len(self.test_cases)} test cases")

    def get_test_case(self, case_id: str) -> dict[str, Any] | None:
        """Get a specific test case by ID."""
        for tc in self.test_cases:
            if tc["id"] == case_id:
                return tc
        return None

    def get_test_cases_by_category(self, category: str) -> list[dict[str, Any]]:
        """Get all test cases in a category."""
        return [tc for tc in self.test_cases if tc.get("category") == category]

    async def setup_profile(self) -> None:
        """Load the test profile into the system."""
        if self.profile_loaded:
            return

        if self.dry_run:
            logger.info("[DRY RUN] Would load test profile")
            self.profile_loaded = True
            return

        logger.info("Setting up test profile...")

        try:
            from src.modules.collector import get_collector

            collector = await get_collector()

            # Copy test profile to data directory
            import shutil
            data_profile = PROJECT_ROOT / "data" / "profile.yaml"
            data_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(TEST_PROFILE_FILE, data_profile)

            # Load profile - pass Path object, not string
            await collector.load_profile(data_profile)
            self.profile_loaded = True
            logger.info("Test profile loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load test profile: {e}")
            raise

    async def run_test_case(self, test_case: dict[str, Any]) -> ValidationResult:
        """Run a single test case through the pipeline."""
        result = ValidationResult(test_case["id"])
        result.test_case_name = test_case["name"]
        result.category = test_case.get("category", "unknown")
        result.started_at = datetime.now()

        logger.info(f"Running test case: {test_case['id']} - {test_case['name']}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process: {test_case['input']['job_text'][:100]}...")
            result.success = True
            result.completed_at = datetime.now()
            result.total_duration_ms = 0
            return result

        try:
            from src.services.pipeline import (
                PipelineInput,
                PipelineProgress,
                get_pipeline_orchestrator,
            )

            orchestrator = await get_pipeline_orchestrator()

            # Prepare input
            job_text = test_case["input"]["job_text"]
            source = test_case["input"].get("source", "validation_test")

            pipeline_input = PipelineInput(
                raw_job_text=job_text,
                source=source,
            )

            # Progress callback to capture step timings
            step_timings: dict[str, int] = {}

            async def progress_callback(progress: PipelineProgress) -> None:
                if progress.current_step:
                    step_name = progress.current_step.value
                    logger.debug(f"  Step: {step_name} - {progress.message}")

            # Execute pipeline
            pipeline_result = await orchestrator.execute(
                pipeline_input,
                progress_callback=progress_callback,
            )

            # Capture results
            result.pipeline_status = pipeline_result.status.value
            result.total_duration_ms = pipeline_result.total_duration_ms
            result.success = pipeline_result.is_success

            # Extract step durations
            for step_result in pipeline_result.steps:
                result.step_durations[step_result.step.value] = step_result.duration_ms

            # Extraction results
            result.extracted_job_title = pipeline_result.job_title
            result.extracted_company = pipeline_result.company_name

            # Analysis results
            result.compatibility_score = pipeline_result.compatibility_score

            # Output paths
            result.cv_path = pipeline_result.cv_path
            result.cover_letter_path = pipeline_result.cover_letter_path

            if not result.success:
                result.error = pipeline_result.error

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Test case {test_case['id']} failed: {e}")

        result.completed_at = datetime.now()
        return result

    async def run_all(self, case_ids: list[str] | None = None) -> None:
        """Run all (or specified) test cases."""
        # Check Ollama availability first
        if not self.dry_run:
            ollama_ok, ollama_msg = await check_ollama_available()
            if not ollama_ok:
                logger.error(f"Ollama not available: {ollama_msg}")
                raise RuntimeError(f"Ollama required for validation: {ollama_msg}")
            logger.info(f"✓ {ollama_msg}")
        
        await self.setup_profile()

        cases_to_run = self.test_cases
        if case_ids:
            cases_to_run = [tc for tc in self.test_cases if tc["id"] in case_ids]

        logger.info(f"Running {len(cases_to_run)} test cases...")

        for test_case in cases_to_run:
            result = await self.run_test_case(test_case)
            self.results.append(result)

            # Log result summary
            status = "✅ PASS" if result.success else "❌ FAIL"
            score = f"{result.compatibility_score:.1f}%" if result.compatibility_score else "N/A"
            logger.info(
                f"  {status} | {result.test_case_id} | "
                f"Score: {score} | Duration: {result.total_duration_ms}ms"
            )

    def generate_report(self) -> dict[str, Any]:
        """Generate a summary report of all results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed

        total_duration = sum(r.total_duration_ms for r in self.results)
        avg_duration = total_duration / total if total > 0 else 0

        scores = [r.compatibility_score for r in self.results if r.compatibility_score is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        # Group by category
        by_category: dict[str, dict[str, int]] = {}
        for r in self.results:
            cat = r.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if r.success:
                by_category[cat]["passed"] += 1

        return {
            "summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
                "total_duration_ms": total_duration,
                "avg_duration_ms": int(avg_duration),
                "avg_compatibility_score": round(avg_score, 1) if avg_score else None,
            },
            "by_category": by_category,
            "results": [r.to_dict() for r in self.results],
        }

    def save_results(self, output_path: Path | None = None) -> Path:
        """Save results to JSON file."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = RESULTS_DIR / f"validation_{timestamp}.json"

        report = self.generate_report()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Results saved to {output_path}")
        return output_path

    def print_summary(self) -> None:
        """Print a human-readable summary to console."""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("VALIDATION TEST RESULTS")
        print("=" * 60)
        print(f"Timestamp:    {summary['timestamp']}")
        print(f"Total Tests:  {summary['total_tests']}")
        print(f"Passed:       {summary['passed']}")
        print(f"Failed:       {summary['failed']}")
        print(f"Pass Rate:    {summary['pass_rate']}")
        print(f"Total Time:   {summary['total_duration_ms']}ms")
        print(f"Avg Time:     {summary['avg_duration_ms']}ms")
        if summary['avg_compatibility_score']:
            print(f"Avg Score:    {summary['avg_compatibility_score']}%")
        print("-" * 60)

        print("\nBy Category:")
        for cat, stats in report["by_category"].items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

        print("\nDetailed Results:")
        for r in self.results:
            status = "✅" if r.success else "❌"
            score = f"{r.compatibility_score:.1f}%" if r.compatibility_score else "N/A"
            print(f"  {status} {r.test_case_id}: {r.test_case_name}")
            print(f"      Score: {score} | Duration: {r.total_duration_ms}ms")
            if r.error:
                print(f"      Error: {r.error[:80]}...")

        print("=" * 60 + "\n")


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scout Validation Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test cases",
    )
    parser.add_argument(
        "--case",
        type=str,
        help="Run specific test case by ID (e.g., TC001)",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Run all test cases in category (e.g., baseline, edge_case)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for results (default: auto-generated)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test cases and exit",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment readiness (Ollama, profile) and exit",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = ValidationRunner(dry_run=args.dry_run)
    runner.load_test_cases()

    # List mode
    if args.list:
        print("\nAvailable Test Cases:")
        print("-" * 60)
        for tc in runner.test_cases:
            print(f"  {tc['id']}: {tc['name']}")
            print(f"      Category: {tc.get('category', 'N/A')} | "
                  f"Complexity: {tc.get('complexity', 'N/A')}")
        return 0

    # Check mode
    if args.check:
        print("\nEnvironment Check:")
        print("-" * 60)
        
        # Check Ollama
        ollama_ok, ollama_msg = await check_ollama_available()
        status = "✓" if ollama_ok else "✗"
        print(f"  {status} Ollama: {ollama_msg}")
        
        # Check test profile exists
        profile_ok = TEST_PROFILE_FILE.exists()
        status = "✓" if profile_ok else "✗"
        print(f"  {status} Test Profile: {'Found' if profile_ok else 'Missing'} at {TEST_PROFILE_FILE}")
        
        # Check data directory
        data_dir = PROJECT_ROOT / "data"
        data_ok = data_dir.exists() or True  # Will be created
        status = "✓" if data_ok else "✗"
        print(f"  {status} Data Directory: {data_dir}")
        
        print("-" * 60)
        if ollama_ok and profile_ok:
            print("✓ Environment ready for validation testing")
            return 0
        else:
            print("✗ Environment not ready")
            if not ollama_ok:
                print("\n  To start Ollama:")
                print("    1. Install from https://ollama.ai")
                print("    2. Run: ollama serve")
                print("    3. Pull models: ollama pull qwen2.5:3b && ollama pull gemma2:2b")
            return 1

    # Determine which cases to run
    case_ids: list[str] | None = None

    if args.case:
        case_ids = [args.case]
        if not runner.get_test_case(args.case):
            logger.error(f"Test case not found: {args.case}")
            return 1

    elif args.category:
        cases = runner.get_test_cases_by_category(args.category)
        if not cases:
            logger.error(f"No test cases found in category: {args.category}")
            return 1
        case_ids = [tc["id"] for tc in cases]

    elif not args.all:
        parser.print_help()
        return 1

    # Run tests
    try:
        await runner.run_all(case_ids)
    except Exception as e:
        logger.error(f"Validation run failed: {e}")
        return 1

    # Output results
    runner.print_summary()

    output_path = Path(args.output) if args.output else None
    runner.save_results(output_path)

    # Return exit code based on results
    failed = sum(1 for r in runner.results if not r.success)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
