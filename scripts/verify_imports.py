"""
Import verification script for Scout project.

Run with: python -c "exec(open('scripts/verify_imports.py').read())"
Or: python scripts/verify_imports.py

Verifies all major imports resolve correctly.
"""

import sys
from typing import Any

def verify_imports() -> tuple[list[str], list[str]]:
    """Verify all major Scout imports."""
    success: list[str] = []
    failures: list[str] = []

    imports_to_check = [
        # Services
        ("src.services.llm_service", ["LLMService", "get_llm_service"]),
        ("src.services.cache_service", ["CacheService", "get_cache_service"]),
        ("src.services.vector_store", ["VectorStoreService", "get_vector_store_service"]),
        ("src.services.metrics_service", ["MetricsService", "get_metrics_service"]),
        ("src.services.pipeline", ["PipelineOrchestrator", "get_pipeline_orchestrator"]),
        ("src.services.notification", ["NotificationService", "get_notification_service"]),
        ("src.services.profile", ["ProfileService", "get_profile_service"]),
        
        # Modules
        ("src.modules.collector", ["Collector", "get_collector", "UserProfile"]),
        ("src.modules.rinser", ["Rinser", "get_rinser", "ProcessedJob"]),
        ("src.modules.analyzer", ["Analyzer", "get_analyzer", "AnalysisResult"]),
        ("src.modules.creator", ["Creator", "get_creator", "CreatedContent"]),
        ("src.modules.formatter", ["Formatter", "get_formatter", "FormattedApplication"]),
        
        # Web
        ("src.web", ["app"]),
        ("src.web.routes", ["api_router"]),
    ]

    for module_path, names in imports_to_check:
        try:
            module = __import__(module_path, fromlist=names)
            for name in names:
                if not hasattr(module, name):
                    failures.append(f"{module_path}.{name} - not found in module")
                else:
                    success.append(f"{module_path}.{name}")
        except ImportError as e:
            failures.append(f"{module_path} - {e}")
        except Exception as e:
            failures.append(f"{module_path} - unexpected error: {e}")

    return success, failures


def main() -> int:
    """Run import verification."""
    print("=" * 60)
    print("Scout Import Verification")
    print("=" * 60)
    print()

    success, failures = verify_imports()

    print(f"✅ Successful imports: {len(success)}")
    for item in success:
        print(f"   {item}")
    
    print()
    
    if failures:
        print(f"❌ Failed imports: {len(failures)}")
        for item in failures:
            print(f"   {item}")
        return 1
    else:
        print("All imports verified successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
