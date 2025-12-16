"""Tests for skill alias functionality."""

import pytest

from src.modules.collector.skill_aliases import (
    SKILL_ALIASES,
    expand_skill_query,
    get_all_canonical_skills,
    get_canonical_name,
    is_known_skill,
    normalize_skill_name,
)


class TestNormalizeSkillName:
    """Tests for normalize_skill_name function."""

    def test_normalize_exact_match(self) -> None:
        """Canonical names return themselves."""
        assert normalize_skill_name("python") == "python"
        assert normalize_skill_name("kubernetes") == "kubernetes"
        assert normalize_skill_name("javascript") == "javascript"

    def test_normalize_alias(self) -> None:
        """Aliases normalize to canonical name."""
        assert normalize_skill_name("k8s") == "kubernetes"
        assert normalize_skill_name("py") == "python"
        assert normalize_skill_name("js") == "javascript"
        assert normalize_skill_name("postgres") == "postgresql"
        assert normalize_skill_name("ts") == "typescript"

    def test_normalize_case_insensitive(self) -> None:
        """Normalization is case-insensitive."""
        assert normalize_skill_name("Python") == "python"
        assert normalize_skill_name("KUBERNETES") == "kubernetes"
        assert normalize_skill_name("PostgreSQL") == "postgresql"
        assert normalize_skill_name("JavaScript") == "javascript"

    def test_normalize_with_version(self) -> None:
        """Version-specific names normalize correctly."""
        assert normalize_skill_name("Python 3.11") == "python"
        assert normalize_skill_name("python3") == "python"
        assert normalize_skill_name("Python 3.x") == "python"

    def test_normalize_unknown_skill(self) -> None:
        """Unknown skills return lowercase original."""
        assert normalize_skill_name("SomeObscureFramework") == "someobscureframework"
        assert normalize_skill_name("CustomTool") == "customtool"
        assert normalize_skill_name("MyLibrary") == "mylibrary"

    def test_normalize_strips_whitespace(self) -> None:
        """Whitespace is stripped."""
        assert normalize_skill_name("  python  ") == "python"
        assert normalize_skill_name("\tk8s\n") == "kubernetes"
        assert normalize_skill_name("  PostgreSQL  ") == "postgresql"


class TestExpandSkillQuery:
    """Tests for expand_skill_query function."""

    def test_expand_known_skill(self) -> None:
        """Known skills expand to include aliases."""
        expanded = expand_skill_query("kubernetes")
        assert "kubernetes" in expanded
        assert "k8s" in expanded
        assert "kube" in expanded

    def test_expand_from_alias(self) -> None:
        """Aliases expand to full set."""
        expanded = expand_skill_query("k8s")
        assert "kubernetes" in expanded
        assert "k8s" in expanded
        assert "kube" in expanded

    def test_expand_python(self) -> None:
        """Python expands to include common variants."""
        expanded = expand_skill_query("python")
        assert "python" in expanded
        assert "py" in expanded
        assert "python3" in expanded

    def test_expand_unknown_skill(self) -> None:
        """Unknown skills return single-item list."""
        expanded = expand_skill_query("unknownskill")
        assert expanded == ["unknownskill"]

    def test_expand_case_insensitive(self) -> None:
        """Expansion is case-insensitive."""
        expanded = expand_skill_query("PYTHON")
        assert "python" in expanded
        assert "py" in expanded

    def test_expand_no_duplicates(self) -> None:
        """Expanded list has no duplicates."""
        expanded = expand_skill_query("python")
        assert len(expanded) == len(set(expanded))

    def test_expand_javascript(self) -> None:
        """JavaScript expands correctly."""
        expanded = expand_skill_query("javascript")
        assert "javascript" in expanded
        assert "js" in expanded
        assert "es6" in expanded


class TestIsKnownSkill:
    """Tests for is_known_skill function."""

    def test_canonical_is_known(self) -> None:
        """Canonical names are known."""
        assert is_known_skill("python") is True
        assert is_known_skill("kubernetes") is True
        assert is_known_skill("javascript") is True

    def test_alias_is_known(self) -> None:
        """Aliases are known."""
        assert is_known_skill("k8s") is True
        assert is_known_skill("py") is True
        assert is_known_skill("js") is True

    def test_unknown_not_known(self) -> None:
        """Unknown skills are not known."""
        assert is_known_skill("randomthing") is False
        assert is_known_skill("notaskill") is False

    def test_case_insensitive(self) -> None:
        """Check is case-insensitive."""
        assert is_known_skill("PYTHON") is True
        assert is_known_skill("K8S") is True
        assert is_known_skill("JavaScript") is True

    def test_whitespace_handling(self) -> None:
        """Whitespace is handled correctly."""
        assert is_known_skill("  python  ") is True
        assert is_known_skill("\tk8s\n") is True


class TestGetCanonicalName:
    """Tests for get_canonical_name function."""

    def test_known_skill_returns_canonical(self) -> None:
        """Known skills return their canonical name."""
        assert get_canonical_name("k8s") == "kubernetes"
        assert get_canonical_name("py") == "python"
        assert get_canonical_name("postgres") == "postgresql"

    def test_canonical_returns_self(self) -> None:
        """Canonical names return themselves."""
        assert get_canonical_name("python") == "python"
        assert get_canonical_name("kubernetes") == "kubernetes"

    def test_unknown_returns_none(self) -> None:
        """Unknown skills return None."""
        assert get_canonical_name("unknownthing") is None
        assert get_canonical_name("notaskill") is None

    def test_case_insensitive(self) -> None:
        """Check is case-insensitive."""
        assert get_canonical_name("PYTHON") == "python"
        assert get_canonical_name("K8s") == "kubernetes"


class TestGetAllCanonicalSkills:
    """Tests for get_all_canonical_skills function."""

    def test_returns_list(self) -> None:
        """Returns a list of skills."""
        skills = get_all_canonical_skills()
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_contains_common_skills(self) -> None:
        """Contains common programming skills."""
        skills = get_all_canonical_skills()
        assert "python" in skills
        assert "javascript" in skills
        assert "kubernetes" in skills

    def test_matches_aliases_keys(self) -> None:
        """Returns all keys from SKILL_ALIASES."""
        skills = get_all_canonical_skills()
        assert set(skills) == set(SKILL_ALIASES.keys())


class TestSkillAliasesCoverage:
    """Tests for alias dictionary coverage."""

    def test_common_languages_covered(self) -> None:
        """Common programming languages have aliases."""
        languages = ["python", "javascript", "typescript", "golang", "rust"]
        for lang in languages:
            assert lang in SKILL_ALIASES, f"{lang} should be in aliases"

    def test_common_databases_covered(self) -> None:
        """Common databases have aliases."""
        databases = ["postgresql", "mongodb", "redis", "mysql"]
        for db in databases:
            assert db in SKILL_ALIASES, f"{db} should be in aliases"

    def test_cloud_providers_covered(self) -> None:
        """Cloud providers have aliases."""
        clouds = ["aws", "gcp", "azure", "kubernetes", "docker"]
        for cloud in clouds:
            assert cloud in SKILL_ALIASES, f"{cloud} should be in aliases"

    def test_frameworks_covered(self) -> None:
        """Common frameworks have aliases."""
        frameworks = ["react", "vue", "angular", "django", "fastapi"]
        for fw in frameworks:
            assert fw in SKILL_ALIASES, f"{fw} should be in aliases"

    def test_ml_skills_covered(self) -> None:
        """Machine learning skills have aliases."""
        ml_skills = ["machine learning", "deep learning", "pytorch", "tensorflow"]
        for skill in ml_skills:
            assert skill in SKILL_ALIASES, f"{skill} should be in aliases"

    def test_aliases_are_lowercase(self) -> None:
        """All aliases should be lowercase."""
        for canonical, aliases in SKILL_ALIASES.items():
            for alias in aliases:
                assert alias == alias.lower(), f"Alias '{alias}' for '{canonical}' should be lowercase"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_string(self) -> None:
        """Empty string handled gracefully."""
        assert normalize_skill_name("") == ""
        assert expand_skill_query("") == [""]
        assert is_known_skill("") is False

    def test_whitespace_only(self) -> None:
        """Whitespace-only string handled gracefully."""
        assert normalize_skill_name("   ") == ""
        assert is_known_skill("   ") is False

    def test_special_characters_in_aliases(self) -> None:
        """Skills with special characters work correctly."""
        # C# has special character
        assert normalize_skill_name("c#") == "csharp"
        assert normalize_skill_name("C#") == "csharp"

        # C++ has special characters
        assert normalize_skill_name("c++") == "cplusplus"

    def test_dotnet_variations(self) -> None:
        """Various .NET spellings work."""
        assert normalize_skill_name(".net") == "csharp"
        assert normalize_skill_name("dotnet") == "csharp"

    def test_ci_cd_variations(self) -> None:
        """CI/CD variations work correctly."""
        expanded = expand_skill_query("ci/cd")
        assert "ci/cd" in expanded
        assert "cicd" in expanded
        assert "continuous integration" in expanded
