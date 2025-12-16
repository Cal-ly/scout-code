"""Demo data for initial database population."""

import logging
from datetime import datetime

from src.services.database.models import ProfileCreate
from src.services.database.service import DatabaseService

logger = logging.getLogger(__name__)


# =============================================================================
# DEMO PROFILES
# =============================================================================

DEMO_PROFILES = [
    {
        "name": "Emma Chen - Full-Stack Developer",
        "full_name": "Emma Chen",
        "email": "emma.chen@example.com",
        "title": "Full-Stack Developer",
        "profile_data": {
            "full_name": "Emma Chen",
            "email": "emma.chen@example.com",
            "phone": "+45 12 34 56 78",
            "location": "Copenhagen, Denmark",
            "linkedin_url": "https://linkedin.com/in/emmachen",
            "github_url": "https://github.com/emmachen",
            "title": "Full-Stack Developer",
            "years_experience": 4.0,
            "summary": "Passionate full-stack developer with 4 years of experience building scalable web applications. Strong background in Python and React, with a focus on clean architecture and user experience. Previously worked at a Danish fintech startup where I led the development of their customer-facing platform. I thrive in collaborative environments and enjoy mentoring junior developers.",
            "skills": [
                {"name": "Python", "level": "advanced", "years": 4, "keywords": ["FastAPI", "Django", "Flask"]},
                {"name": "JavaScript", "level": "advanced", "years": 4, "keywords": ["ES6+", "Node.js"]},
                {"name": "TypeScript", "level": "intermediate", "years": 2, "keywords": []},
                {"name": "React", "level": "advanced", "years": 3, "keywords": ["Redux", "Next.js", "Hooks"]},
                {"name": "PostgreSQL", "level": "intermediate", "years": 3, "keywords": ["SQL", "Database Design"]},
                {"name": "Docker", "level": "intermediate", "years": 2, "keywords": ["Docker Compose", "Containerization"]},
                {"name": "AWS", "level": "intermediate", "years": 2, "keywords": ["EC2", "S3", "Lambda", "RDS"]},
                {"name": "Git", "level": "advanced", "years": 4, "keywords": ["GitHub", "GitLab", "CI/CD"]},
                {"name": "REST APIs", "level": "advanced", "years": 4, "keywords": ["OpenAPI", "API Design"]},
                {"name": "Agile", "level": "intermediate", "years": 3, "keywords": ["Scrum", "Kanban"]}
            ],
            "experiences": [
                {
                    "company": "PayFlow ApS",
                    "role": "Full-Stack Developer",
                    "start_date": "2022-03-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Lead developer for customer-facing payment platform serving 50,000+ users. Architected and implemented new features using Python/FastAPI backend and React frontend.",
                    "achievements": [
                        "Reduced page load time by 40% through code optimization and caching strategies",
                        "Implemented real-time transaction monitoring dashboard used by operations team",
                        "Mentored 2 junior developers, conducting code reviews and pair programming sessions",
                        "Led migration from monolith to microservices architecture"
                    ],
                    "technologies": ["Python", "FastAPI", "React", "PostgreSQL", "Redis", "AWS"]
                },
                {
                    "company": "TechStart Copenhagen",
                    "role": "Junior Developer",
                    "start_date": "2020-08-01T00:00:00",
                    "end_date": "2022-02-28T00:00:00",
                    "current": False,
                    "description": "Full-stack development for various client projects in an agency setting. Gained experience across multiple tech stacks and industries.",
                    "achievements": [
                        "Delivered 8 client projects on time and within budget",
                        "Built e-commerce platform that processed 2M EUR in first year",
                        "Introduced automated testing practices to the team"
                    ],
                    "technologies": ["Python", "Django", "JavaScript", "React", "MySQL"]
                }
            ],
            "education": [
                {
                    "institution": "IT University of Copenhagen",
                    "degree": "Bachelor of Science",
                    "field": "Software Development",
                    "start_date": "2017-09-01T00:00:00",
                    "end_date": "2020-06-30T00:00:00",
                    "gpa": 10.2,
                    "relevant_courses": ["Web Development", "Database Systems", "Software Architecture", "Algorithms"]
                }
            ],
            "certifications": [
                {
                    "name": "AWS Certified Developer - Associate",
                    "issuer": "Amazon Web Services",
                    "date_obtained": "2023-05-15T00:00:00",
                    "expiry_date": "2026-05-15T00:00:00",
                    "credential_id": "AWS-DEV-12345"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    },
    {
        "name": "Marcus Andersen - Senior Backend Engineer",
        "full_name": "Marcus Andersen",
        "email": "marcus.andersen@example.com",
        "title": "Senior Backend Engineer",
        "profile_data": {
            "full_name": "Marcus Andersen",
            "email": "marcus.andersen@example.com",
            "phone": "+45 87 65 43 21",
            "location": "Aarhus, Denmark",
            "linkedin_url": "https://linkedin.com/in/marcusandersen",
            "github_url": "https://github.com/marcusandersen",
            "title": "Senior Backend Engineer",
            "years_experience": 8.0,
            "summary": "Senior backend engineer with 8 years of experience designing and building high-performance distributed systems. Expert in Python and Go, with deep knowledge of cloud infrastructure and DevOps practices. Passionate about system design, performance optimization, and building reliable software at scale. Currently focused on event-driven architectures and real-time data processing.",
            "skills": [
                {"name": "Python", "level": "expert", "years": 8, "keywords": ["FastAPI", "asyncio", "Celery"]},
                {"name": "Go", "level": "advanced", "years": 4, "keywords": ["Gin", "gRPC", "Concurrency"]},
                {"name": "PostgreSQL", "level": "expert", "years": 7, "keywords": ["Performance Tuning", "Replication"]},
                {"name": "Redis", "level": "advanced", "years": 5, "keywords": ["Caching", "Pub/Sub", "Streams"]},
                {"name": "Kubernetes", "level": "advanced", "years": 4, "keywords": ["Helm", "Operators", "Service Mesh"]},
                {"name": "AWS", "level": "expert", "years": 6, "keywords": ["EKS", "RDS", "SQS", "Lambda", "DynamoDB"]},
                {"name": "Kafka", "level": "advanced", "years": 3, "keywords": ["Event Streaming", "KSQL"]},
                {"name": "System Design", "level": "expert", "years": 6, "keywords": ["Microservices", "DDD", "CQRS"]},
                {"name": "CI/CD", "level": "advanced", "years": 5, "keywords": ["GitHub Actions", "ArgoCD", "Terraform"]},
                {"name": "Monitoring", "level": "advanced", "years": 5, "keywords": ["Prometheus", "Grafana", "Datadog"]}
            ],
            "experiences": [
                {
                    "company": "Danske Bank",
                    "role": "Senior Backend Engineer",
                    "start_date": "2021-01-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Tech lead for core banking platform modernization initiative. Leading a team of 5 engineers building next-generation transaction processing system.",
                    "achievements": [
                        "Designed event-driven architecture handling 1M+ transactions daily",
                        "Reduced system latency by 60% through optimization and caching",
                        "Led successful migration from on-premise to AWS with zero downtime",
                        "Established engineering best practices and code review standards"
                    ],
                    "technologies": ["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes", "AWS"]
                },
                {
                    "company": "Netcompany",
                    "role": "Backend Developer",
                    "start_date": "2018-03-01T00:00:00",
                    "end_date": "2020-12-31T00:00:00",
                    "current": False,
                    "description": "Backend development for enterprise clients in healthcare and public sector. Built scalable APIs and data pipelines.",
                    "achievements": [
                        "Developed national health registry integration serving 5M+ citizens",
                        "Built real-time analytics platform for public transportation",
                        "Promoted from mid-level to senior developer within 2 years"
                    ],
                    "technologies": ["Python", "Java", "PostgreSQL", "RabbitMQ", "Docker"]
                },
                {
                    "company": "Startup Hub Aarhus",
                    "role": "Software Developer",
                    "start_date": "2016-06-01T00:00:00",
                    "end_date": "2018-02-28T00:00:00",
                    "current": False,
                    "description": "Early-stage startup building IoT platform for smart buildings. Full ownership of backend services.",
                    "achievements": [
                        "Built RESTful API serving 10,000+ IoT devices",
                        "Implemented real-time alerting system for building managers",
                        "Reduced cloud costs by 35% through architecture optimization"
                    ],
                    "technologies": ["Python", "Node.js", "MongoDB", "MQTT", "AWS"]
                }
            ],
            "education": [
                {
                    "institution": "Aarhus University",
                    "degree": "Master of Science",
                    "field": "Computer Science",
                    "start_date": "2014-09-01T00:00:00",
                    "end_date": "2016-06-30T00:00:00",
                    "gpa": 11.0,
                    "relevant_courses": ["Distributed Systems", "Advanced Algorithms", "Database Implementation"]
                },
                {
                    "institution": "Aarhus University",
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "start_date": "2011-09-01T00:00:00",
                    "end_date": "2014-06-30T00:00:00",
                    "gpa": 10.5,
                    "relevant_courses": []
                }
            ],
            "certifications": [
                {
                    "name": "AWS Solutions Architect - Professional",
                    "issuer": "Amazon Web Services",
                    "date_obtained": "2022-08-20T00:00:00",
                    "expiry_date": "2025-08-20T00:00:00",
                    "credential_id": "AWS-SAP-67890"
                },
                {
                    "name": "Certified Kubernetes Administrator",
                    "issuer": "CNCF",
                    "date_obtained": "2023-02-10T00:00:00",
                    "expiry_date": "2026-02-10T00:00:00",
                    "credential_id": "CKA-2023-12345"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    },
    {
        "name": "Sofia Martinez - Data Engineer",
        "full_name": "Sofia Martinez",
        "email": "sofia.martinez@example.com",
        "title": "Data Engineer",
        "profile_data": {
            "full_name": "Sofia Martinez",
            "email": "sofia.martinez@example.com",
            "phone": "+45 55 66 77 88",
            "location": "Copenhagen, Denmark",
            "linkedin_url": "https://linkedin.com/in/sofiamartinez",
            "github_url": "https://github.com/sofiamartinez",
            "title": "Data Engineer",
            "years_experience": 5.0,
            "summary": "Data engineer with 5 years of experience building data pipelines and analytics platforms. Transitioning towards machine learning engineering with recent focus on MLOps and model deployment. Strong Python skills combined with cloud infrastructure expertise. Bilingual in Spanish and English, with professional proficiency in Danish.",
            "skills": [
                {"name": "Python", "level": "expert", "years": 5, "keywords": ["Pandas", "PySpark", "Airflow"]},
                {"name": "SQL", "level": "expert", "years": 5, "keywords": ["PostgreSQL", "BigQuery", "Snowflake"]},
                {"name": "Apache Spark", "level": "advanced", "years": 3, "keywords": ["PySpark", "Spark SQL"]},
                {"name": "Airflow", "level": "advanced", "years": 3, "keywords": ["DAGs", "Operators", "Scheduling"]},
                {"name": "AWS", "level": "intermediate", "years": 3, "keywords": ["S3", "Glue", "Athena", "SageMaker"]},
                {"name": "Machine Learning", "level": "intermediate", "years": 2, "keywords": ["scikit-learn", "XGBoost"]},
                {"name": "MLOps", "level": "beginner", "years": 1, "keywords": ["MLflow", "Model Serving"]},
                {"name": "dbt", "level": "intermediate", "years": 2, "keywords": ["Data Modeling", "Testing"]},
                {"name": "Docker", "level": "intermediate", "years": 3, "keywords": ["Containerization"]},
                {"name": "Git", "level": "advanced", "years": 5, "keywords": ["Version Control", "CI/CD"]}
            ],
            "experiences": [
                {
                    "company": "Vestas Wind Systems",
                    "role": "Senior Data Engineer",
                    "start_date": "2022-06-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Building data infrastructure for wind turbine analytics. Processing terabytes of sensor data daily to enable predictive maintenance and performance optimization.",
                    "achievements": [
                        "Designed data lake architecture processing 5TB+ daily sensor data",
                        "Built ML feature store enabling data scientists to deploy models 3x faster",
                        "Reduced data pipeline failures by 80% through improved monitoring",
                        "Led initiative to implement data quality framework across organization"
                    ],
                    "technologies": ["Python", "Spark", "Airflow", "AWS", "dbt", "Snowflake"]
                },
                {
                    "company": "Maersk",
                    "role": "Data Engineer",
                    "start_date": "2020-01-01T00:00:00",
                    "end_date": "2022-05-31T00:00:00",
                    "current": False,
                    "description": "Developed ETL pipelines and analytics solutions for global shipping operations. Worked with large-scale logistics data.",
                    "achievements": [
                        "Built real-time container tracking data pipeline",
                        "Automated reporting saving 20 hours per week of manual work",
                        "Migrated legacy data warehouse to cloud-native solution"
                    ],
                    "technologies": ["Python", "SQL", "Azure", "Databricks", "Power BI"]
                },
                {
                    "company": "Analytics Startup (Madrid)",
                    "role": "Junior Data Analyst",
                    "start_date": "2019-02-01T00:00:00",
                    "end_date": "2019-12-31T00:00:00",
                    "current": False,
                    "description": "Data analysis and visualization for marketing analytics platform. First role after completing master's degree.",
                    "achievements": [
                        "Developed customer segmentation model improving campaign ROI by 25%",
                        "Created automated dashboards for 15 enterprise clients"
                    ],
                    "technologies": ["Python", "SQL", "Tableau", "Google Analytics"]
                }
            ],
            "education": [
                {
                    "institution": "Technical University of Denmark",
                    "degree": "Master of Science",
                    "field": "Data Science",
                    "start_date": "2017-09-01T00:00:00",
                    "end_date": "2019-01-31T00:00:00",
                    "gpa": 10.8,
                    "relevant_courses": ["Machine Learning", "Big Data Systems", "Statistical Modeling", "Deep Learning"]
                },
                {
                    "institution": "Universidad Politecnica de Madrid",
                    "degree": "Bachelor of Science",
                    "field": "Computer Engineering",
                    "start_date": "2013-09-01T00:00:00",
                    "end_date": "2017-06-30T00:00:00",
                    "gpa": None,
                    "relevant_courses": []
                }
            ],
            "certifications": [
                {
                    "name": "Google Cloud Professional Data Engineer",
                    "issuer": "Google Cloud",
                    "date_obtained": "2023-09-01T00:00:00",
                    "expiry_date": "2025-09-01T00:00:00",
                    "credential_id": "GCP-DE-54321"
                },
                {
                    "name": "Databricks Certified Data Engineer Associate",
                    "issuer": "Databricks",
                    "date_obtained": "2022-11-15T00:00:00",
                    "expiry_date": None,
                    "credential_id": "DBX-DE-98765"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    }
]


async def load_demo_profiles(db: DatabaseService) -> list[int]:
    """
    Load demo profiles into database.

    Returns:
        List of created profile IDs.
    """
    created_ids = []

    for profile_dict in DEMO_PROFILES:
        try:
            profile_create = ProfileCreate(
                name=profile_dict["name"],
                full_name=profile_dict["full_name"],
                email=profile_dict["email"],
                title=profile_dict["title"],
                profile_data=profile_dict["profile_data"],
                is_active=False,
                is_demo=True,
            )

            profile = await db.create_profile(profile_create)
            created_ids.append(profile.id)
            logger.info(f"Created demo profile: {profile.name} (ID: {profile.id})")

        except Exception as e:
            logger.warning(f"Failed to create demo profile {profile_dict['name']}: {e}")

    # Activate the first demo profile if no active profile exists
    if created_ids:
        active = await db.get_active_profile()
        if active is None:
            await db.activate_profile(created_ids[0])
            logger.info(f"Activated demo profile ID: {created_ids[0]}")

    # Mark demo data as loaded
    await db.set_setting("demo_data_loaded", True)

    return created_ids


async def ensure_demo_data(db: DatabaseService) -> None:
    """
    Ensure demo data is loaded (idempotent).

    Called on application startup.
    """
    settings = await db.get_settings()

    if not settings.demo_data_loaded:
        logger.info("Loading demo profiles...")
        await load_demo_profiles(db)
        logger.info("Demo profiles loaded")
    else:
        logger.debug("Demo data already loaded")
