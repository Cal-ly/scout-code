"""
Skills API Routes

Skill alias and normalization endpoints.

Endpoints:
    GET /api/v1/skills/aliases - Get all skill aliases
    GET /api/v1/skills/normalize - Normalize a skill name
    GET /api/v1/skills/expand - Expand skill to include aliases
    GET /api/v1/skills/search - Search skills (semantic)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.modules.collector import (
    SKILL_ALIASES,
    expand_skill_query,
    get_all_canonical_skills,
    get_collector,
    is_known_skill,
    normalize_skill_name,
)
from src.modules.collector.collector import Collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


async def get_collector_dep() -> Collector:
    """Get collector dependency."""
    return await get_collector()


@router.get(
    "/aliases",
    summary="Get all skill aliases",
    description="Returns the complete skill alias mapping.",
)
async def get_aliases() -> dict:
    """Get all skill aliases."""
    return {
        "aliases": SKILL_ALIASES,
        "canonical_skills": get_all_canonical_skills(),
        "total_canonical": len(SKILL_ALIASES),
    }


@router.get(
    "/normalize",
    summary="Normalize skill name",
    description="Convert a skill name or alias to its canonical form.",
)
async def normalize(
    skill: str = Query(..., description="Skill name to normalize"),
) -> dict:
    """Normalize a skill name to canonical form."""
    canonical = normalize_skill_name(skill)
    return {
        "input": skill,
        "canonical": canonical,
        "is_known": is_known_skill(skill),
    }


@router.get(
    "/expand",
    summary="Expand skill to aliases",
    description="Get all known aliases for a skill.",
)
async def expand(
    skill: str = Query(..., description="Skill to expand"),
) -> dict:
    """Expand skill name to include all aliases."""
    expanded = expand_skill_query(skill)
    return {
        "input": skill,
        "canonical": normalize_skill_name(skill),
        "expanded": expanded,
        "count": len(expanded),
    }


@router.get(
    "/search",
    summary="Search skills semantically",
    description="Search for skills matching a query using semantic similarity.",
)
async def search_skills(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    min_score: float = Query(default=0.3, ge=0, le=1, description="Minimum similarity score"),
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """Search for matching skills."""
    try:
        # Ensure profile is loaded
        try:
            collector.get_profile()
        except Exception:
            await collector.load_profile()

        matches = await collector.search_skills(query, n_results=top_k)

        # Filter by minimum score
        filtered = [m for m in matches if m.score >= min_score]

        return {
            "query": query,
            "expanded_query": expand_skill_query(query),
            "matches": [
                {
                    "skill": m.metadata.get("name", ""),
                    "canonical": m.metadata.get("canonical_name", ""),
                    "level": m.metadata.get("level", ""),
                    "years": m.metadata.get("years", 0),
                    "score": round(m.score, 3),
                }
                for m in filtered
            ],
            "count": len(filtered),
        }

    except Exception as e:
        logger.error(f"Skill search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
