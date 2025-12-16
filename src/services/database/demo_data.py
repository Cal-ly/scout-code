"""Demo data for Scout - Test User with 3 profile personas.

These profiles demonstrate different career positioning strategies:
1. Backend Focus - Emphasizes backend/infrastructure skills
2. Full Stack - Balanced frontend + backend
3. DevOps Specialist - Infrastructure and automation focus

All profiles share the same "Test User" owner, demonstrating
multi-profile capability for a single user.
"""

from src.services.database.models import (
    CertificationCreate,
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    LanguageProficiency,
    ProfileCreate,
    SkillCreate,
    SkillLevel,
    UserCreate,
)

# =============================================================================
# TEST USER
# =============================================================================

TEST_USER = UserCreate(
    username="test_user",
    email="test@scout.local",
    display_name="Test User",
)

# =============================================================================
# DEMO PROFILES
# =============================================================================

BACKEND_FOCUS_PROFILE = ProfileCreate(
    slug="backend-focus",
    name="Backend Focus",
    title="Senior Backend Engineer",
    email="backend.dev@example.com",
    phone="+1-555-0101",
    location="San Francisco, CA",
    summary=(
        "Backend engineer with 8+ years of experience building scalable "
        "distributed systems. Specialized in Python and Go, with deep expertise "
        "in API design, database optimization, and cloud infrastructure. Proven "
        "track record of improving system performance and reliability at scale. "
        "Passionate about clean architecture and mentoring junior engineers."
    ),
    skills=[
        SkillCreate(
            name="Python", level=SkillLevel.EXPERT,
            years=8, category="Programming", sort_order=0
        ),
        SkillCreate(
            name="Go", level=SkillLevel.ADVANCED,
            years=4, category="Programming", sort_order=1
        ),
        SkillCreate(
            name="PostgreSQL", level=SkillLevel.EXPERT,
            years=7, category="Database", sort_order=2
        ),
        SkillCreate(
            name="Redis", level=SkillLevel.ADVANCED,
            years=5, category="Database", sort_order=3
        ),
        SkillCreate(
            name="MongoDB", level=SkillLevel.INTERMEDIATE,
            years=3, category="Database", sort_order=4
        ),
        SkillCreate(
            name="Docker", level=SkillLevel.ADVANCED,
            years=5, category="DevOps", sort_order=5
        ),
        SkillCreate(
            name="Kubernetes", level=SkillLevel.INTERMEDIATE,
            years=2, category="DevOps", sort_order=6
        ),
        SkillCreate(
            name="AWS", level=SkillLevel.ADVANCED,
            years=5, category="Cloud", sort_order=7
        ),
        SkillCreate(
            name="REST API Design", level=SkillLevel.EXPERT,
            years=7, category="Architecture", sort_order=8
        ),
        SkillCreate(
            name="gRPC", level=SkillLevel.ADVANCED,
            years=3, category="Architecture", sort_order=9
        ),
        SkillCreate(
            name="Message Queues", level=SkillLevel.ADVANCED,
            years=4, category="Architecture", sort_order=10
        ),
        SkillCreate(
            name="System Design", level=SkillLevel.ADVANCED,
            years=5, category="Architecture", sort_order=11
        ),
    ],
    experiences=[
        ExperienceCreate(
            title="Senior Backend Engineer",
            company="TechScale Inc.",
            start_date="2021-03",
            end_date=None,  # Current position
            description=(
                "Lead backend engineer for core platform services handling "
                "10M+ daily requests. Architecting and implementing "
                "high-performance microservices in Python and Go."
            ),
            achievements=[
                "Reduced API latency by 60% through query optimization and caching",
                "Designed event-driven architecture processing 5M events/day",
                "Mentored team of 4 junior engineers on best practices",
                "Led migration from monolith to microservices, improving deploy 10x",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="Backend Engineer",
            company="DataFlow Systems",
            start_date="2018-06",
            end_date="2021-02",
            description=(
                "Built and maintained data pipeline infrastructure for analytics "
                "platform serving Fortune 500 clients."
            ),
            achievements=[
                "Developed real-time data ingestion system handling 100K events/sec",
                "Implemented automated testing pipeline reducing bug escape rate 40%",
                "Optimized database queries reducing response time from 2s to 200ms",
            ],
            sort_order=1,
        ),
        ExperienceCreate(
            title="Software Developer",
            company="StartupHub",
            start_date="2016-01",
            end_date="2018-05",
            description=(
                "Full-stack development for B2B SaaS platform with focus on "
                "backend services."
            ),
            achievements=[
                "Built RESTful API serving 50+ enterprise clients",
                "Implemented OAuth 2.0 authentication system",
                "Reduced deployment time from 2 hours to 15 minutes with CI/CD",
            ],
            sort_order=2,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of California, Berkeley",
            degree="B.S.",
            field="Computer Science",
            start_date="2012-08",
            end_date="2016-05",
            gpa="3.7",
            achievements=[
                "Dean's List - 6 semesters",
                "Senior thesis on distributed systems",
            ],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="AWS Solutions Architect - Associate",
            issuer="Amazon Web Services",
            date_obtained="2022-03",
            expiry_date="2025-03",
            sort_order=0,
        ),
        CertificationCreate(
            name="Certified Kubernetes Administrator (CKA)",
            issuer="Cloud Native Computing Foundation",
            date_obtained="2023-01",
            expiry_date="2026-01",
            sort_order=1,
        ),
    ],
    languages=[
        LanguageCreate(
            language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0
        ),
        LanguageCreate(
            language="Spanish",
            proficiency=LanguageProficiency.CONVERSATIONAL,
            sort_order=1,
        ),
    ],
)

FULLSTACK_FOCUS_PROFILE = ProfileCreate(
    slug="fullstack-focus",
    name="Full Stack",
    title="Full Stack Developer",
    email="fullstack.dev@example.com",
    phone="+1-555-0102",
    location="Austin, TX",
    summary=(
        "Versatile full-stack developer with 6 years of experience building "
        "end-to-end web applications. Strong expertise in React/TypeScript "
        "frontend and Python/Node.js backend. Passionate about creating "
        "intuitive user experiences backed by robust, scalable systems. "
        "Experience leading small teams and delivering projects from concept "
        "to production."
    ),
    skills=[
        SkillCreate(
            name="TypeScript", level=SkillLevel.EXPERT,
            years=5, category="Programming", sort_order=0
        ),
        SkillCreate(
            name="JavaScript", level=SkillLevel.EXPERT,
            years=6, category="Programming", sort_order=1
        ),
        SkillCreate(
            name="Python", level=SkillLevel.ADVANCED,
            years=4, category="Programming", sort_order=2
        ),
        SkillCreate(
            name="React", level=SkillLevel.EXPERT,
            years=5, category="Frontend", sort_order=3
        ),
        SkillCreate(
            name="Next.js", level=SkillLevel.ADVANCED,
            years=3, category="Frontend", sort_order=4
        ),
        SkillCreate(
            name="Vue.js", level=SkillLevel.INTERMEDIATE,
            years=2, category="Frontend", sort_order=5
        ),
        SkillCreate(
            name="Node.js", level=SkillLevel.ADVANCED,
            years=4, category="Backend", sort_order=6
        ),
        SkillCreate(
            name="FastAPI", level=SkillLevel.ADVANCED,
            years=2, category="Backend", sort_order=7
        ),
        SkillCreate(
            name="PostgreSQL", level=SkillLevel.ADVANCED,
            years=4, category="Database", sort_order=8
        ),
        SkillCreate(
            name="GraphQL", level=SkillLevel.ADVANCED,
            years=3, category="API", sort_order=9
        ),
        SkillCreate(
            name="Tailwind CSS", level=SkillLevel.EXPERT,
            years=3, category="Frontend", sort_order=10
        ),
        SkillCreate(
            name="Testing (Jest/Pytest)", level=SkillLevel.ADVANCED,
            years=4, category="Quality", sort_order=11
        ),
    ],
    experiences=[
        ExperienceCreate(
            title="Full Stack Developer",
            company="WebCraft Studios",
            start_date="2020-08",
            end_date=None,
            description=(
                "Lead developer for client projects ranging from e-commerce "
                "platforms to SaaS applications. Responsible for full project "
                "lifecycle from requirements to deployment."
            ),
            achievements=[
                "Delivered 15+ production applications for various industries",
                "Implemented reusable component library reducing dev time by 30%",
                "Built real-time collaboration features using WebSockets and Redis",
                "Achieved 95+ Lighthouse performance scores on all projects",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="Frontend Developer",
            company="DigitalFirst Agency",
            start_date="2018-03",
            end_date="2020-07",
            description=(
                "Frontend specialist building responsive, accessible web "
                "applications for agency clients."
            ),
            achievements=[
                "Migrated legacy jQuery codebase to React, improving perf 3x",
                "Introduced TypeScript adoption across team of 8 developers",
                "Created accessibility-first patterns meeting WCAG 2.1 AA",
            ],
            sort_order=1,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of Texas at Austin",
            degree="B.S.",
            field="Computer Science",
            start_date="2014-08",
            end_date="2018-05",
            gpa="3.5",
            achievements=["Undergraduate Teaching Assistant - Web Development"],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="Meta Frontend Developer Professional Certificate",
            issuer="Meta",
            date_obtained="2022-06",
            sort_order=0,
        ),
    ],
    languages=[
        LanguageCreate(
            language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0
        ),
    ],
)

DEVOPS_FOCUS_PROFILE = ProfileCreate(
    slug="devops-focus",
    name="DevOps Specialist",
    title="DevOps Engineer",
    email="devops.eng@example.com",
    phone="+1-555-0103",
    location="Seattle, WA",
    summary=(
        "DevOps engineer with 5 years of experience building and maintaining "
        "cloud infrastructure. Expert in Kubernetes, Terraform, and CI/CD "
        "pipelines. Focused on reliability, automation, and enabling development "
        "teams to ship faster with confidence. Strong background in security "
        "best practices and cost optimization."
    ),
    skills=[
        SkillCreate(
            name="Kubernetes", level=SkillLevel.EXPERT,
            years=4, category="Orchestration", sort_order=0
        ),
        SkillCreate(
            name="Terraform", level=SkillLevel.EXPERT,
            years=4, category="IaC", sort_order=1
        ),
        SkillCreate(
            name="AWS", level=SkillLevel.EXPERT,
            years=5, category="Cloud", sort_order=2
        ),
        SkillCreate(
            name="GCP", level=SkillLevel.ADVANCED,
            years=3, category="Cloud", sort_order=3
        ),
        SkillCreate(
            name="Docker", level=SkillLevel.EXPERT,
            years=5, category="Containers", sort_order=4
        ),
        SkillCreate(
            name="Python", level=SkillLevel.ADVANCED,
            years=4, category="Programming", sort_order=5
        ),
        SkillCreate(
            name="Bash/Shell", level=SkillLevel.EXPERT,
            years=6, category="Programming", sort_order=6
        ),
        SkillCreate(
            name="GitHub Actions", level=SkillLevel.EXPERT,
            years=3, category="CI/CD", sort_order=7
        ),
        SkillCreate(
            name="ArgoCD", level=SkillLevel.ADVANCED,
            years=2, category="CI/CD", sort_order=8
        ),
        SkillCreate(
            name="Prometheus/Grafana", level=SkillLevel.ADVANCED,
            years=3, category="Monitoring", sort_order=9
        ),
        SkillCreate(
            name="Helm", level=SkillLevel.ADVANCED,
            years=3, category="Orchestration", sort_order=10
        ),
        SkillCreate(
            name="Linux Administration", level=SkillLevel.EXPERT,
            years=6, category="Systems", sort_order=11
        ),
    ],
    experiences=[
        ExperienceCreate(
            title="Senior DevOps Engineer",
            company="CloudNative Corp",
            start_date="2022-01",
            end_date=None,
            description=(
                "Lead infrastructure engineer for multi-region Kubernetes "
                "platform serving 200+ microservices and 50+ development teams."
            ),
            achievements=[
                "Designed multi-region K8s platform with 99.99% uptime SLA",
                "Reduced infrastructure costs by 40% through right-sizing",
                "Implemented GitOps workflow with ArgoCD reducing errors by 80%",
                "Built self-service platform for teams to deploy independently",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="DevOps Engineer",
            company="ScaleUp Technologies",
            start_date="2019-06",
            end_date="2021-12",
            description=(
                "Built and maintained CI/CD infrastructure and cloud platform "
                "for rapidly growing SaaS company."
            ),
            achievements=[
                "Migrated on-premise infrastructure to AWS, reducing ops 60%",
                "Implemented infrastructure-as-code with Terraform for all envs",
                "Built automated security scanning catching 95% of vulnerabilities",
                "Reduced deployment time from 45 minutes to 5 minutes",
            ],
            sort_order=1,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of Washington",
            degree="B.S.",
            field="Information Systems",
            start_date="2015-09",
            end_date="2019-06",
            gpa="3.6",
            achievements=["Capstone: Automated Cloud Deployment System"],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="AWS Solutions Architect - Professional",
            issuer="Amazon Web Services",
            date_obtained="2022-08",
            expiry_date="2025-08",
            sort_order=0,
        ),
        CertificationCreate(
            name="Certified Kubernetes Administrator (CKA)",
            issuer="Cloud Native Computing Foundation",
            date_obtained="2021-03",
            expiry_date="2024-03",
            sort_order=1,
        ),
        CertificationCreate(
            name="HashiCorp Certified: Terraform Associate",
            issuer="HashiCorp",
            date_obtained="2021-09",
            expiry_date="2024-09",
            sort_order=2,
        ),
    ],
    languages=[
        LanguageCreate(
            language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0
        ),
        LanguageCreate(
            language="Mandarin",
            proficiency=LanguageProficiency.CONVERSATIONAL,
            sort_order=1,
        ),
    ],
)

# List of all demo profiles for iteration
DEMO_PROFILES: list[ProfileCreate] = [
    BACKEND_FOCUS_PROFILE,
    FULLSTACK_FOCUS_PROFILE,
    DEVOPS_FOCUS_PROFILE,
]

# The first profile should be active by default
DEFAULT_ACTIVE_PROFILE_SLUG = "backend-focus"
