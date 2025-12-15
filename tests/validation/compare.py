"""
Metrics Comparison Tool

Compare validation results across multiple runs to identify:
- Performance regressions
- Score consistency
- Extraction quality changes

Usage:
    python -m tests.validation.compare results/validation_20241215_*.json
    python -m tests.validation.compare --baseline results/baseline.json --current results/latest.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from datetime import datetime


def load_results(path: Path) -> dict[str, Any]:
    """Load results from JSON file."""
    with open(path) as f:
        return json.load(f)


def compare_runs(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare two validation runs."""
    baseline_summary = baseline["summary"]
    current_summary = current["summary"]

    # Calculate deltas
    duration_delta = current_summary["avg_duration_ms"] - baseline_summary["avg_duration_ms"]
    duration_pct = (duration_delta / baseline_summary["avg_duration_ms"] * 100) if baseline_summary["avg_duration_ms"] > 0 else 0

    score_delta = None
    if baseline_summary.get("avg_compatibility_score") and current_summary.get("avg_compatibility_score"):
        score_delta = current_summary["avg_compatibility_score"] - baseline_summary["avg_compatibility_score"]

    # Compare individual test cases
    baseline_results = {r["test_case_id"]: r for r in baseline["results"]}
    current_results = {r["test_case_id"]: r for r in current["results"]}

    test_comparisons = []
    for tc_id, current_result in current_results.items():
        baseline_result = baseline_results.get(tc_id)
        if baseline_result:
            comparison = {
                "test_case_id": tc_id,
                "test_case_name": current_result["test_case_name"],
                "baseline_success": baseline_result["success"],
                "current_success": current_result["success"],
                "baseline_duration_ms": baseline_result["duration_ms"],
                "current_duration_ms": current_result["duration_ms"],
                "duration_change_ms": current_result["duration_ms"] - baseline_result["duration_ms"],
            }

            # Score comparison
            baseline_score = baseline_result["analysis"].get("compatibility_score")
            current_score = current_result["analysis"].get("compatibility_score")
            if baseline_score is not None and current_score is not None:
                comparison["baseline_score"] = baseline_score
                comparison["current_score"] = current_score
                comparison["score_change"] = round(current_score - baseline_score, 1)

            # Regression detection
            comparison["is_regression"] = (
                (baseline_result["success"] and not current_result["success"]) or
                (comparison.get("score_change", 0) < -5) or
                (comparison["duration_change_ms"] > baseline_result["duration_ms"] * 0.5)  # 50% slower
            )

            test_comparisons.append(comparison)

    regressions = [tc for tc in test_comparisons if tc.get("is_regression")]

    return {
        "comparison_timestamp": datetime.now().isoformat(),
        "baseline": {
            "timestamp": baseline_summary["timestamp"],
            "total_tests": baseline_summary["total_tests"],
            "pass_rate": baseline_summary["pass_rate"],
            "avg_duration_ms": baseline_summary["avg_duration_ms"],
            "avg_score": baseline_summary.get("avg_compatibility_score"),
        },
        "current": {
            "timestamp": current_summary["timestamp"],
            "total_tests": current_summary["total_tests"],
            "pass_rate": current_summary["pass_rate"],
            "avg_duration_ms": current_summary["avg_duration_ms"],
            "avg_score": current_summary.get("avg_compatibility_score"),
        },
        "deltas": {
            "duration_ms": duration_delta,
            "duration_pct": round(duration_pct, 1),
            "score": score_delta,
        },
        "regressions": regressions,
        "test_comparisons": test_comparisons,
    }


def print_comparison(comparison: dict[str, Any]) -> None:
    """Print comparison report to console."""
    print("\n" + "=" * 70)
    print("VALIDATION COMPARISON REPORT")
    print("=" * 70)

    baseline = comparison["baseline"]
    current = comparison["current"]
    deltas = comparison["deltas"]

    print(f"\nBaseline: {baseline['timestamp']}")
    print(f"Current:  {current['timestamp']}")

    print("\n" + "-" * 70)
    print("SUMMARY COMPARISON")
    print("-" * 70)
    print(f"{'Metric':<25} {'Baseline':<15} {'Current':<15} {'Delta':<15}")
    print("-" * 70)

    # Pass rate
    print(f"{'Pass Rate':<25} {baseline['pass_rate']:<15} {current['pass_rate']:<15}")

    # Duration
    duration_indicator = "⚠️" if deltas["duration_pct"] > 20 else "✅" if deltas["duration_pct"] < -10 else "➖"
    print(f"{'Avg Duration (ms)':<25} {baseline['avg_duration_ms']:<15} {current['avg_duration_ms']:<15} "
          f"{deltas['duration_ms']:+}ms ({deltas['duration_pct']:+.1f}%) {duration_indicator}")

    # Score
    if baseline["avg_score"] and current["avg_score"]:
        score_indicator = "⚠️" if deltas["score"] < -5 else "✅" if deltas["score"] > 5 else "➖"
        print(f"{'Avg Score':<25} {baseline['avg_score']:<15} {current['avg_score']:<15} "
              f"{deltas['score']:+.1f}% {score_indicator}")

    # Regressions
    regressions = comparison["regressions"]
    if regressions:
        print("\n" + "-" * 70)
        print(f"⚠️  REGRESSIONS DETECTED: {len(regressions)}")
        print("-" * 70)
        for reg in regressions:
            print(f"\n  {reg['test_case_id']}: {reg['test_case_name']}")
            if not reg["current_success"] and reg["baseline_success"]:
                print("    ❌ Test now failing (was passing)")
            if reg.get("score_change") and reg["score_change"] < -5:
                print(f"    📉 Score dropped: {reg['baseline_score']}% → {reg['current_score']}% ({reg['score_change']:+.1f}%)")
            if reg["duration_change_ms"] > reg["baseline_duration_ms"] * 0.5:
                print(f"    🐢 Slower: {reg['baseline_duration_ms']}ms → {reg['current_duration_ms']}ms "
                      f"({reg['duration_change_ms']:+}ms)")
    else:
        print("\n✅ No regressions detected!")

    # Individual test changes
    print("\n" + "-" * 70)
    print("TEST CASE DETAILS")
    print("-" * 70)
    print(f"{'ID':<8} {'Status':<12} {'Duration Change':<18} {'Score Change':<15}")
    print("-" * 70)

    for tc in comparison["test_comparisons"]:
        status = "✅→✅" if tc["current_success"] else "❌→❌"
        if tc["baseline_success"] != tc["current_success"]:
            status = "✅→❌" if tc["baseline_success"] else "❌→✅"

        duration_str = f"{tc['duration_change_ms']:+}ms"
        score_str = f"{tc.get('score_change', 0):+.1f}%" if tc.get("score_change") is not None else "N/A"

        print(f"{tc['test_case_id']:<8} {status:<12} {duration_str:<18} {score_str:<15}")

    print("=" * 70 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare Scout validation results across runs",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        help="Baseline results file",
    )
    parser.add_argument(
        "--current",
        type=str,
        help="Current results file to compare",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Result files to compare (first is baseline, last is current)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save comparison to JSON file",
    )

    args = parser.parse_args()

    # Determine baseline and current files
    if args.baseline and args.current:
        baseline_path = Path(args.baseline)
        current_path = Path(args.current)
    elif args.files and len(args.files) >= 2:
        baseline_path = Path(args.files[0])
        current_path = Path(args.files[-1])
    else:
        parser.error("Provide --baseline and --current, or at least 2 files")
        return 1

    # Load and compare
    print(f"Loading baseline: {baseline_path}")
    baseline = load_results(baseline_path)

    print(f"Loading current: {current_path}")
    current = load_results(current_path)

    comparison = compare_runs(baseline, current)

    # Output
    print_comparison(comparison)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"Comparison saved to {output_path}")

    # Return non-zero if regressions found
    return 1 if comparison["regressions"] else 0


if __name__ == "__main__":
    sys.exit(main())
