#!/usr/bin/env python3
"""
Scout Cross-Platform Benchmark

Runs standardized job postings through Scout pipeline and collects metrics
for thesis comparison across different hardware platforms.

Usage:
    python run_benchmark.py                    # Run with defaults
    python run_benchmark.py --runs 5           # 5 runs per job
    python run_benchmark.py --url http://pi:8000  # Custom Scout URL
    python run_benchmark.py --output results/  # Custom output directory
"""

import argparse
import asyncio
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing required package: httpx")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


# =============================================================================
# TEST JOB DEFINITIONS
# =============================================================================

TEST_JOBS = {
    "senior_python": {
        "name": "Senior Python Developer",
        "description": "Backend-focused Python role at a FinTech startup",
        "text": """
Senior Python Developer - FinTech Startup

Location: Remote (US/EU timezone overlap)
Salary: $150,000 - $180,000 + equity

About Us:
We're a fast-growing FinTech startup revolutionizing payment processing for
small businesses. Our platform handles millions of transactions daily.

The Role:
We're seeking an experienced Python developer to join our backend team. You'll
be working on our core payment processing engine and API infrastructure.

Requirements:
- 5+ years of professional Python development experience
- Strong experience with FastAPI or Django REST Framework
- PostgreSQL expertise including query optimization
- Redis for caching and message queuing
- Docker and Kubernetes in production environments
- AWS services (EC2, RDS, Lambda, SQS)
- Understanding of microservices architecture patterns
- Experience with async Python (asyncio, aiohttp)

Nice to Have:
- Financial services or payment processing background
- Real-time data processing with Kafka or similar
- Machine learning model deployment experience
- Contributions to open-source projects

What We Offer:
- Competitive salary and equity package
- Fully remote work environment
- Health, dental, and vision insurance
- Unlimited PTO policy
- Annual learning budget of $2,000
- Latest MacBook Pro and home office setup

Apply with your resume and a brief note about why you're interested.
"""
    },

    "fullstack_react": {
        "name": "Full Stack React Developer",
        "description": "Full stack role with React frontend focus",
        "text": """
Full Stack Developer - React & Node.js

Company: TechVentures Inc.
Location: San Francisco, CA (Hybrid - 2 days in office)
Compensation: $140,000 - $165,000

About TechVentures:
We build enterprise software solutions for Fortune 500 companies. Our
flagship product is a workflow automation platform used by over 200
organizations worldwide.

Role Overview:
Join our product team to build and enhance our web application. You'll work
across the full stack, with a focus on creating exceptional user experiences
with React while building robust Node.js backend services.

Technical Requirements:
- 4+ years of full stack development experience
- Expert-level React skills (hooks, context, Redux or Zustand)
- TypeScript proficiency (both frontend and backend)
- Node.js and Express.js backend development
- REST API design and GraphQL experience
- PostgreSQL and MongoDB database experience
- Git workflow and CI/CD pipelines
- Unit testing with Jest and React Testing Library

Bonus Points:
- Experience with Next.js or Remix
- Familiarity with AWS or GCP cloud services
- UI/UX design sensibility
- Experience with WebSocket real-time features
- Previous work on enterprise B2B products

Benefits:
- Competitive base salary plus annual bonus
- 401(k) with 4% company match
- Premium health insurance (medical, dental, vision)
- 3 weeks PTO plus holidays
- Commuter benefits for hybrid work
- Team events and professional development

To apply, send your resume and portfolio/GitHub profile.
"""
    },

    "devops_engineer": {
        "name": "DevOps Engineer",
        "description": "Infrastructure and automation focused role",
        "text": """
Senior DevOps Engineer

Organization: CloudScale Systems
Location: Austin, TX or Remote
Salary Range: $145,000 - $175,000

About CloudScale:
We provide cloud infrastructure management solutions to mid-size companies.
Our platform automates cloud resource provisioning, monitoring, and cost
optimization across AWS, Azure, and GCP.

Position Summary:
We're looking for a Senior DevOps Engineer to lead our infrastructure
automation initiatives. You'll design and implement CI/CD pipelines,
manage Kubernetes clusters, and ensure our platform maintains 99.99% uptime.

Required Skills:
- 5+ years in DevOps/SRE/Infrastructure roles
- Expert knowledge of Kubernetes (CKA certification preferred)
- Infrastructure as Code with Terraform or Pulumi
- CI/CD pipeline design (GitHub Actions, GitLab CI, or Jenkins)
- Strong Linux system administration skills
- AWS certification and hands-on experience
- Monitoring and observability (Prometheus, Grafana, DataDog)
- Python or Go scripting for automation

Desired Experience:
- Multi-cloud environment management
- Service mesh implementation (Istio or Linkerd)
- Database administration (PostgreSQL, Redis clusters)
- Security best practices and compliance (SOC2, HIPAA)
- On-call rotation and incident management experience

What We Provide:
- Competitive compensation with equity
- Full remote work option
- Health and wellness benefits
- $3,000 annual education budget
- Home office equipment allowance
- Flexible work schedule

Interview Process:
1. Initial phone screen (30 min)
2. Technical assessment (take-home, 2-3 hours)
3. System design interview (1 hour)
4. Team culture fit interview (45 min)
"""
    }
}


# =============================================================================
# SYSTEM INFORMATION
# =============================================================================

def get_system_info() -> dict:
    """Collect system information for benchmark context."""
    info = {
        "hostname": platform.node(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "timestamp": datetime.now().isoformat(),
    }

    # Try to get CPU info
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu_model"] = line.split(":")[1].strip()
                        break
            # Get CPU count
            import os
            info["cpu_count"] = os.cpu_count()
    except Exception:
        pass

    # Try to get memory info
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        info["memory_gb"] = round(mem_kb / 1024 / 1024, 1)
                        break
    except Exception:
        pass

    # Try to get GPU info
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info["gpu"] = result.stdout.strip()
        else:
            info["gpu"] = "None (CPU only)"
    except Exception:
        info["gpu"] = "None (CPU only)"

    # Try to get Raspberry Pi info
    try:
        if platform.system() == "Linux" and platform.machine() == "aarch64":
            result = subprocess.run(
                ["cat", "/proc/device-tree/model"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info["device_model"] = result.stdout.strip().replace('\x00', '')
    except Exception:
        pass

    return info


def get_ollama_info(base_url: str) -> dict:
    """Get Ollama model information."""
    try:
        # Extract Ollama URL from environment or derive from Scout
        ollama_url = "http://localhost:11434"

        response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"available_models": models}
    except Exception:
        pass
    return {"available_models": "unknown"}


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

async def run_single_job(
    client: httpx.AsyncClient,
    base_url: str,
    job_key: str,
    job_data: dict,
    run_number: int
) -> dict:
    """Run a single job through the pipeline and collect metrics."""

    result = {
        "job_key": job_key,
        "job_name": job_data["name"],
        "run_number": run_number,
        "status": "unknown",
        "error": None,
        "timings": {},
    }

    try:
        # Start the job
        start_time = time.time()
        response = await client.post(
            f"{base_url}/api/v1/jobs/apply",
            json={"job_text": job_data["text"], "source": "benchmark"}
        )

        if response.status_code != 200:
            result["status"] = "failed"
            result["error"] = f"Failed to start job: {response.status_code}"
            return result

        job_id = response.json()["job_id"]
        result["job_id"] = job_id
        submit_time = time.time()
        result["timings"]["submit_ms"] = int((submit_time - start_time) * 1000)

        # Poll until complete
        while True:
            await asyncio.sleep(2)

            status_response = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
            if status_response.status_code != 200:
                result["status"] = "failed"
                result["error"] = f"Failed to get status: {status_response.status_code}"
                return result

            status_data = status_response.json()

            if status_data["status"] in ("completed", "failed"):
                end_time = time.time()

                result["status"] = status_data["status"]
                result["timings"]["total_seconds"] = round(end_time - start_time, 2)
                result["compatibility_score"] = status_data.get("compatibility_score")

                # Extract step timings
                if "steps" in status_data:
                    for step in status_data["steps"]:
                        step_name = step.get("step", "unknown")
                        result["timings"][f"{step_name}_ms"] = step.get("duration_ms", 0)

                if status_data["status"] == "failed":
                    result["error"] = status_data.get("error", "Unknown error")

                return result

            # Timeout after 15 minutes
            if time.time() - start_time > 900:
                result["status"] = "timeout"
                result["error"] = "Pipeline timeout after 15 minutes"
                return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def run_benchmark(
    base_url: str,
    runs_per_job: int = 3,
    jobs_to_run: list[str] | None = None
) -> dict:
    """Run full benchmark suite."""

    results = {
        "system_info": get_system_info(),
        "ollama_info": get_ollama_info(base_url),
        "scout_url": base_url,
        "runs_per_job": runs_per_job,
        "started_at": datetime.now().isoformat(),
        "job_results": [],
    }

    # Filter jobs if specified
    jobs = {k: v for k, v in TEST_JOBS.items()
            if jobs_to_run is None or k in jobs_to_run}

    total_runs = len(jobs) * runs_per_job
    current_run = 0

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        # Verify Scout is accessible
        try:
            health = await client.get(f"{base_url}/api/v1/health")
            if health.status_code != 200:
                print(f"Error: Scout not accessible at {base_url}")
                return results
            results["scout_health"] = health.json()
        except Exception as e:
            print(f"Error: Cannot connect to Scout at {base_url}: {e}")
            return results

        # Run benchmarks
        for job_key, job_data in jobs.items():
            print(f"\n{'='*60}")
            print(f"Job: {job_data['name']}")
            print(f"{'='*60}")

            for run in range(1, runs_per_job + 1):
                current_run += 1
                print(f"\n  Run {run}/{runs_per_job} ({current_run}/{total_runs} total)...")

                result = await run_single_job(
                    client, base_url, job_key, job_data, run
                )
                results["job_results"].append(result)

                if result["status"] == "completed":
                    total_sec = result["timings"].get("total_seconds", 0)
                    score = result.get("compatibility_score", "N/A")
                    print(f"    ✓ Completed in {total_sec:.1f}s (score: {score})")
                else:
                    print(f"    ✗ {result['status']}: {result.get('error', 'Unknown')}")

    results["completed_at"] = datetime.now().isoformat()

    # Calculate summary statistics
    completed_runs = [r for r in results["job_results"] if r["status"] == "completed"]
    if completed_runs:
        total_times = [r["timings"]["total_seconds"] for r in completed_runs]
        results["summary"] = {
            "total_runs": len(results["job_results"]),
            "successful_runs": len(completed_runs),
            "success_rate": len(completed_runs) / len(results["job_results"]),
            "avg_total_seconds": sum(total_times) / len(total_times),
            "min_total_seconds": min(total_times),
            "max_total_seconds": max(total_times),
        }

        # Per-module averages
        for module in ["rinser", "analyzer", "creator", "formatter"]:
            times = [r["timings"].get(f"{module}_ms", 0) for r in completed_runs
                    if r["timings"].get(f"{module}_ms")]
            if times:
                results["summary"][f"avg_{module}_ms"] = sum(times) / len(times)

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Scout Cross-Platform Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmark.py
  python run_benchmark.py --runs 5 --url http://192.168.1.100:8000
  python run_benchmark.py --jobs senior_python devops_engineer
        """
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Scout URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per job (default: 3)"
    )
    parser.add_argument(
        "--output",
        default="results",
        help="Output directory for results (default: results)"
    )
    parser.add_argument(
        "--jobs",
        nargs="+",
        choices=list(TEST_JOBS.keys()),
        help="Specific jobs to run (default: all)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Scout Cross-Platform Benchmark")
    print("=" * 60)
    print(f"Scout URL: {args.url}")
    print(f"Runs per job: {args.runs}")
    print(f"Jobs: {args.jobs or 'all'}")
    print()

    # Run benchmark
    results = asyncio.run(run_benchmark(
        base_url=args.url,
        runs_per_job=args.runs,
        jobs_to_run=args.jobs
    ))

    # Save results
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    hostname = results["system_info"].get("hostname", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{hostname}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)

    if "summary" in results:
        s = results["summary"]
        print(f"Success rate: {s['success_rate']*100:.0f}% ({s['successful_runs']}/{s['total_runs']})")
        print(f"Average time: {s['avg_total_seconds']:.1f}s")
        print(f"Time range: {s['min_total_seconds']:.1f}s - {s['max_total_seconds']:.1f}s")

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
