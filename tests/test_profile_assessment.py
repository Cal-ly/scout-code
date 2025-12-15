"""
Tests for profile completeness assessment.

Tests cover:
- Section assessments (basic_info, summary, skills, experience, education, certifications)
- Overall profile assessment
- Grade calculation
- Suggestions prioritization
"""

from datetime import datetime

import pytest

from src.modules.collector.assessment import (
    ProfileGrade,
    assess_basic_info,
    assess_certifications,
    assess_education,
    assess_experience,
    assess_profile,
    assess_skills,
    assess_summary,
    calculate_grade,
)
from src.modules.collector.models import (
    Certification,
    Education,
    Experience,
    Skill,
    SkillLevel,
    UserProfile,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def minimal_profile() -> UserProfile:
    """Profile with minimal information."""
    return UserProfile(
        full_name="Test User",
        email="test@example.com",
    )


@pytest.fixture
def complete_profile() -> UserProfile:
    """Well-completed profile."""
    return UserProfile(
        full_name="Alex Developer",
        email="alex@example.com",
        phone="+45 12345678",
        location="Copenhagen, Denmark",
        linkedin_url="https://linkedin.com/in/alex",
        github_url="https://github.com/alex",
        title="Senior Software Engineer",
        years_experience=7.0,
        summary="Experienced software engineer with expertise in Python, cloud technologies, "
        "and distributed systems. Led multiple successful projects and mentored junior developers. "
        "Passionate about clean code and test-driven development.",
        skills=[
            Skill(name="Python", level=SkillLevel.EXPERT, years=7, keywords=["python3", "asyncio"]),
            Skill(name="FastAPI", level=SkillLevel.EXPERT, years=3, keywords=["REST", "async"]),
            Skill(
                name="PostgreSQL", level=SkillLevel.ADVANCED, years=5, keywords=["SQL", "database"]
            ),
            Skill(name="Docker", level=SkillLevel.ADVANCED, years=4, keywords=["containers"]),
            Skill(name="AWS", level=SkillLevel.ADVANCED, years=4, keywords=["cloud"]),
            Skill(name="Kubernetes", level=SkillLevel.INTERMEDIATE, years=2, keywords=["k8s"]),
            Skill(name="React", level=SkillLevel.INTERMEDIATE, years=2, keywords=["frontend"]),
            Skill(name="TypeScript", level=SkillLevel.INTERMEDIATE, years=2, keywords=["ts"]),
            Skill(name="Redis", level=SkillLevel.INTERMEDIATE, years=3, keywords=["cache"]),
            Skill(name="Git", level=SkillLevel.EXPERT, years=7, keywords=["version control"]),
        ],
        experiences=[
            Experience(
                company="TechCorp",
                role="Senior Software Engineer",
                start_date=datetime(2021, 1, 1),
                current=True,
                description="Leading backend development for fintech platform. "
                "Designing microservices and mentoring team members.",
                achievements=[
                    "Reduced API latency by 50%",
                    "Led migration to Kubernetes",
                    "Mentored 3 junior developers",
                ],
                technologies=["Python", "FastAPI", "PostgreSQL", "AWS", "Kubernetes"],
            ),
            Experience(
                company="StartupCo",
                role="Software Engineer",
                start_date=datetime(2018, 6, 1),
                end_date=datetime(2020, 12, 31),
                description="Full-stack development for e-commerce platform.",
                achievements=["Built payment integration", "Improved test coverage to 80%"],
                technologies=["Python", "Django", "React", "PostgreSQL"],
            ),
        ],
        education=[
            Education(
                institution="University of Copenhagen",
                degree="M.Sc.",
                field="Computer Science",
                start_date=datetime(2014, 9, 1),
                end_date=datetime(2016, 6, 30),
                relevant_courses=["Distributed Systems", "Machine Learning"],
            ),
        ],
        certifications=[
            Certification(
                name="AWS Solutions Architect",
                issuer="Amazon Web Services",
                date_obtained=datetime(2023, 1, 15),
                expiry_date=datetime(2026, 1, 15),
            ),
        ],
    )


# =============================================================================
# OVERALL ASSESSMENT TESTS
# =============================================================================


class TestProfileAssessment:
    """Tests for overall profile assessment."""

    def test_minimal_profile_low_score(self, minimal_profile):
        """Minimal profile should have low score."""
        assessment = assess_profile(minimal_profile)
        assert assessment.overall_score < 50
        assert assessment.grade in [ProfileGrade.INCOMPLETE, ProfileGrade.NEEDS_WORK]
        assert len(assessment.top_suggestions) > 0

    def test_complete_profile_high_score(self, complete_profile):
        """Complete profile should have high score."""
        assessment = assess_profile(complete_profile)
        assert assessment.overall_score >= 75
        assert assessment.grade in [ProfileGrade.GOOD, ProfileGrade.EXCELLENT]
        assert assessment.is_job_ready is True

    def test_assessment_has_all_sections(self, complete_profile):
        """Assessment should include all section scores."""
        assessment = assess_profile(complete_profile)
        section_names = {s.section for s in assessment.section_scores}
        expected = {"basic_info", "summary", "skills", "experience", "education", "certifications"}
        assert section_names == expected

    def test_suggestions_prioritized(self, minimal_profile):
        """Top suggestions should come from weakest sections."""
        assessment = assess_profile(minimal_profile)
        assert len(assessment.top_suggestions) <= 5
        # Should have suggestions since profile is incomplete
        assert len(assessment.top_suggestions) > 0

    def test_is_job_ready_property(self, minimal_profile, complete_profile):
        """is_job_ready should return True for scores >= 60."""
        minimal_assessment = assess_profile(minimal_profile)
        complete_assessment = assess_profile(complete_profile)

        assert minimal_assessment.is_job_ready is False
        assert complete_assessment.is_job_ready is True


# =============================================================================
# BASIC INFO ASSESSMENT TESTS
# =============================================================================


class TestBasicInfoAssessment:
    """Tests for basic info section."""

    def test_full_basic_info(self, complete_profile):
        """Complete basic info should score high."""
        score = assess_basic_info(complete_profile)
        assert score.score >= 80
        assert len(score.issues) == 0

    def test_minimal_basic_info(self, minimal_profile):
        """Minimal basic info should have suggestions."""
        score = assess_basic_info(minimal_profile)
        assert score.score < 80
        assert len(score.suggestions) > 0

    def test_missing_required_fields(self):
        """Missing required fields should add issues."""
        profile = UserProfile(
            full_name="",
            email="invalid-email",
            location="",
        )
        score = assess_basic_info(profile)
        assert score.score < 50
        assert len(score.issues) > 0

    def test_optional_fields_add_points(self, minimal_profile):
        """Optional fields like phone, linkedin add to score."""
        minimal_score = assess_basic_info(minimal_profile)

        profile_with_extras = UserProfile(
            full_name="Test User",
            email="test@example.com",
            phone="+45 12345678",
            linkedin_url="https://linkedin.com/in/test",
            github_url="https://github.com/test",
            location="Copenhagen",
        )
        full_score = assess_basic_info(profile_with_extras)

        assert full_score.score > minimal_score.score


# =============================================================================
# SUMMARY ASSESSMENT TESTS
# =============================================================================


class TestSummaryAssessment:
    """Tests for summary section."""

    def test_good_summary(self, complete_profile):
        """Good summary with action words should score high."""
        score = assess_summary(complete_profile)
        assert score.score >= 60

    def test_no_summary(self):
        """No summary should score very low."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            summary="",
        )
        score = assess_summary(profile)
        assert score.score < 30
        assert any("summary" in s.lower() for s in score.suggestions)

    def test_short_summary(self):
        """Short summary should have suggestions to expand."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            title="Developer",
            summary="I am a developer.",
        )
        score = assess_summary(profile)
        assert score.score < 60
        # Should have at least one suggestion related to summary improvement
        assert len(score.suggestions) > 0

    def test_missing_title_adds_suggestion(self):
        """Missing title should add suggestion."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            title="",
            summary="Experienced developer with many years of experience.",
        )
        score = assess_summary(profile)
        assert any("title" in s.lower() for s in score.suggestions)


# =============================================================================
# SKILLS ASSESSMENT TESTS
# =============================================================================


class TestSkillsAssessment:
    """Tests for skills section."""

    def test_many_skills_high_score(self, complete_profile):
        """Profile with 10+ skills should score high."""
        score = assess_skills(complete_profile)
        assert score.score >= 70

    def test_no_skills_low_score(self, minimal_profile):
        """Profile with no skills should score low."""
        score = assess_skills(minimal_profile)
        assert score.score < 30
        assert any("skill" in s.lower() for s in score.suggestions)

    def test_few_skills_suggests_more(self):
        """Few skills should suggest adding more."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[
                Skill(name="Python", level=SkillLevel.INTERMEDIATE),
                Skill(name="JavaScript", level=SkillLevel.INTERMEDIATE),
            ],
        )
        score = assess_skills(profile)
        assert score.score < 50
        assert any("more" in s.lower() or "add" in s.lower() for s in score.suggestions)

    def test_skill_level_diversity_bonus(self):
        """Diverse skill levels should add to score."""
        # All same level
        same_level_profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[
                Skill(name="Python", level=SkillLevel.INTERMEDIATE, years=3),
                Skill(name="JavaScript", level=SkillLevel.INTERMEDIATE, years=3),
                Skill(name="Java", level=SkillLevel.INTERMEDIATE, years=3),
                Skill(name="Go", level=SkillLevel.INTERMEDIATE, years=3),
                Skill(name="Rust", level=SkillLevel.INTERMEDIATE, years=3),
            ],
        )

        # Mixed levels
        mixed_level_profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[
                Skill(name="Python", level=SkillLevel.EXPERT, years=7),
                Skill(name="JavaScript", level=SkillLevel.ADVANCED, years=4),
                Skill(name="Java", level=SkillLevel.INTERMEDIATE, years=2),
                Skill(name="Go", level=SkillLevel.BEGINNER, years=1),
                Skill(name="Rust", level=SkillLevel.INTERMEDIATE, years=2),
            ],
        )

        same_score = assess_skills(same_level_profile)
        mixed_score = assess_skills(mixed_level_profile)

        assert mixed_score.score > same_score.score

    def test_keywords_add_to_score(self):
        """Skills with keywords should score higher."""
        no_keywords = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[
                Skill(name="Python", level=SkillLevel.EXPERT, years=5),
                Skill(name="Java", level=SkillLevel.ADVANCED, years=3),
                Skill(name="Docker", level=SkillLevel.INTERMEDIATE, years=2),
                Skill(name="AWS", level=SkillLevel.ADVANCED, years=3),
                Skill(name="Git", level=SkillLevel.EXPERT, years=5),
            ],
        )

        with_keywords = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[
                Skill(
                    name="Python", level=SkillLevel.EXPERT, years=5, keywords=["Django", "FastAPI"]
                ),
                Skill(name="Java", level=SkillLevel.ADVANCED, years=3, keywords=["Spring"]),
                Skill(name="Docker", level=SkillLevel.INTERMEDIATE, years=2, keywords=["k8s"]),
                Skill(name="AWS", level=SkillLevel.ADVANCED, years=3, keywords=["EC2", "S3"]),
                Skill(name="Git", level=SkillLevel.EXPERT, years=5, keywords=["GitHub"]),
            ],
        )

        no_kw_score = assess_skills(no_keywords)
        with_kw_score = assess_skills(with_keywords)

        assert with_kw_score.score > no_kw_score.score


# =============================================================================
# EXPERIENCE ASSESSMENT TESTS
# =============================================================================


class TestExperienceAssessment:
    """Tests for experience section."""

    def test_good_experience_high_score(self, complete_profile):
        """Well-documented experience should score high."""
        score = assess_experience(complete_profile)
        # Complete profile has good structure but descriptions are moderate length
        assert score.score >= 60

    def test_no_experience_low_score(self, minimal_profile):
        """No experience should score low."""
        score = assess_experience(minimal_profile)
        assert score.score < 30
        assert any("experience" in s.lower() for s in score.suggestions)

    def test_current_role_adds_points(self):
        """Having a current role should add points."""
        no_current = UserProfile(
            full_name="Test",
            email="test@test.com",
            experiences=[
                Experience(
                    company="OldCo",
                    role="Developer",
                    start_date=datetime(2018, 1, 1),
                    end_date=datetime(2020, 12, 31),
                    description="Some work description here for testing purposes.",
                ),
            ],
        )

        with_current = UserProfile(
            full_name="Test",
            email="test@test.com",
            experiences=[
                Experience(
                    company="CurrentCo",
                    role="Developer",
                    start_date=datetime(2021, 1, 1),
                    current=True,
                    description="Some work description here for testing purposes.",
                ),
            ],
        )

        no_current_score = assess_experience(no_current)
        with_current_score = assess_experience(with_current)

        assert with_current_score.score > no_current_score.score

    def test_achievements_add_points(self):
        """Experiences with achievements should score higher."""
        without_achievements = UserProfile(
            full_name="Test",
            email="test@test.com",
            experiences=[
                Experience(
                    company="TechCo",
                    role="Developer",
                    start_date=datetime(2020, 1, 1),
                    current=True,
                    description="Working on various projects and tasks for the company.",
                    technologies=["Python", "JavaScript", "Docker"],
                ),
            ],
        )

        with_achievements = UserProfile(
            full_name="Test",
            email="test@test.com",
            experiences=[
                Experience(
                    company="TechCo",
                    role="Developer",
                    start_date=datetime(2020, 1, 1),
                    current=True,
                    description="Working on various projects and tasks for the company.",
                    achievements=["Improved performance by 50%", "Led team of 3 developers"],
                    technologies=["Python", "JavaScript", "Docker"],
                ),
            ],
        )

        without_score = assess_experience(without_achievements)
        with_score = assess_experience(with_achievements)

        assert with_score.score > without_score.score


# =============================================================================
# EDUCATION ASSESSMENT TESTS
# =============================================================================


class TestEducationAssessment:
    """Tests for education section."""

    def test_good_education_high_score(self, complete_profile):
        """Complete education should score high."""
        score = assess_education(complete_profile)
        assert score.score >= 60

    def test_no_education_low_score(self, minimal_profile):
        """No education should score low."""
        score = assess_education(minimal_profile)
        assert score.score < 30
        assert any("education" in s.lower() for s in score.suggestions)

    def test_relevant_courses_add_points(self):
        """Relevant courses should add to score."""
        without_courses = UserProfile(
            full_name="Test",
            email="test@test.com",
            education=[
                Education(
                    institution="University",
                    degree="B.Sc.",
                    field="Computer Science",
                    start_date=datetime(2015, 9, 1),
                    end_date=datetime(2019, 6, 30),
                ),
            ],
        )

        with_courses = UserProfile(
            full_name="Test",
            email="test@test.com",
            education=[
                Education(
                    institution="University",
                    degree="B.Sc.",
                    field="Computer Science",
                    start_date=datetime(2015, 9, 1),
                    end_date=datetime(2019, 6, 30),
                    relevant_courses=["Data Structures", "Algorithms", "Machine Learning"],
                ),
            ],
        )

        without_score = assess_education(without_courses)
        with_score = assess_education(with_courses)

        assert with_score.score > without_score.score


# =============================================================================
# CERTIFICATIONS ASSESSMENT TESTS
# =============================================================================


class TestCertificationsAssessment:
    """Tests for certifications section."""

    def test_no_certs_still_acceptable(self, minimal_profile):
        """No certifications should still have acceptable base score."""
        score = assess_certifications(minimal_profile)
        # Should be 40 (baseline for no certs)
        assert score.score >= 30

    def test_multiple_certs_high_score(self, complete_profile):
        """Multiple valid certifications should score high."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            certifications=[
                Certification(
                    name="AWS Solutions Architect",
                    issuer="AWS",
                    date_obtained=datetime(2023, 1, 1),
                    expiry_date=datetime(2026, 1, 1),
                ),
                Certification(
                    name="Kubernetes Administrator",
                    issuer="CNCF",
                    date_obtained=datetime(2023, 3, 1),
                    expiry_date=datetime(2026, 3, 1),
                ),
                Certification(
                    name="Google Cloud Professional",
                    issuer="Google",
                    date_obtained=datetime(2023, 6, 1),
                    expiry_date=datetime(2026, 6, 1),
                ),
            ],
        )
        score = assess_certifications(profile)
        assert score.score >= 90

    def test_expired_cert_reduces_score(self):
        """Expired certifications should reduce score."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            certifications=[
                Certification(
                    name="Old Cert",
                    issuer="SomeOrg",
                    date_obtained=datetime(2020, 1, 1),
                    expiry_date=datetime(2022, 1, 1),  # Expired
                ),
            ],
        )
        score = assess_certifications(profile)
        assert len(score.issues) > 0
        assert any("expired" in i.lower() for i in score.issues)


# =============================================================================
# GRADE CALCULATION TESTS
# =============================================================================


class TestGradeCalculation:
    """Tests for grade calculation."""

    def test_grade_thresholds(self, complete_profile, minimal_profile):
        """Test grade thresholds are applied correctly."""
        complete_assessment = assess_profile(complete_profile)
        minimal_assessment = assess_profile(minimal_profile)

        # Complete should be Good or better
        assert complete_assessment.grade in [ProfileGrade.GOOD, ProfileGrade.EXCELLENT]

        # Minimal should be Needs Work or Incomplete
        assert minimal_assessment.grade in [ProfileGrade.NEEDS_WORK, ProfileGrade.INCOMPLETE]

    def test_calculate_grade_boundaries(self):
        """Test grade boundary values."""
        assert calculate_grade(100) == ProfileGrade.EXCELLENT
        assert calculate_grade(90) == ProfileGrade.EXCELLENT
        assert calculate_grade(89) == ProfileGrade.GOOD
        assert calculate_grade(75) == ProfileGrade.GOOD
        assert calculate_grade(74) == ProfileGrade.FAIR
        assert calculate_grade(60) == ProfileGrade.FAIR
        assert calculate_grade(59) == ProfileGrade.NEEDS_WORK
        assert calculate_grade(40) == ProfileGrade.NEEDS_WORK
        assert calculate_grade(39) == ProfileGrade.INCOMPLETE
        assert calculate_grade(0) == ProfileGrade.INCOMPLETE


# =============================================================================
# STRENGTHS IDENTIFICATION TESTS
# =============================================================================


class TestStrengthsIdentification:
    """Tests for strengths identification."""

    def test_strengths_from_high_sections(self, complete_profile):
        """Strengths should come from high-scoring sections."""
        assessment = assess_profile(complete_profile)

        # Complete profile should have at least some strengths
        assert len(assessment.strengths) > 0

        # Strengths should be limited to 3
        assert len(assessment.strengths) <= 3

    def test_no_strengths_for_minimal_profile(self, minimal_profile):
        """Minimal profile should have few or no strengths."""
        assessment = assess_profile(minimal_profile)

        # Minimal profile might have one strength (basic info partially complete)
        # but generally should have very few
        assert len(assessment.strengths) <= 1
