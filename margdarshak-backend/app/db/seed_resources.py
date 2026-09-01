"""Seed the resource catalog used by the Resource Diagnostic flow.

Run from the backend directory after applying migrations:

    python -m app.db.seed_resources
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session_factory import get_session_factory
from app.models.resource import (
    Resource,
    ResourceFormat,
    ResourcePacing,
    ResourcePriceTier,
)


RESOURCE_CATALOG: tuple[dict[str, object], ...] = (
    {"skill_tag": "dsa", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://www.youtube.com/watch?v=6iCHf7OZn6c", "title": "Data Structures and Algorithms with Visualizations"},
    {"skill_tag": "dsa", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://dsa.handbook.academy/", "title": "The Open-source DSA Handbook"},
    {"skill_tag": "dsa", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.SHORT, "price_tier": ResourcePriceTier.PAID, "url": "https://leetcode.com/explore/", "title": "LeetCode Interview Study Plans"},
    {"skill_tag": "dbms", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://dsl.cds.iisc.ac.in/~course/DBMS/class/class.html", "title": "IISc Database Management Systems Lectures"},
    {"skill_tag": "dbms", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.SHORT, "price_tier": ResourcePriceTier.FREE, "url": "https://www.postgresql.org/docs/current/tutorial.html", "title": "PostgreSQL Tutorial"},
    {"skill_tag": "dbms", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.PAID, "url": "https://www.coursera.org/specializations/learn-sql-basics-data-science", "title": "Learn SQL Basics for Data Science"},
    {"skill_tag": "os", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/", "title": "Operating Systems: Three Easy Pieces"},
    {"skill_tag": "os", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://www.udacity.com/course/introduction-to-operating-systems--ud923", "title": "Introduction to Operating Systems"},
    {"skill_tag": "os", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.SHORT, "price_tier": ResourcePriceTier.PAID, "url": "https://www.educative.io/courses/operating-systems-virtualization-concurrency-persistence", "title": "Operating Systems: Virtualization, Concurrency, and Persistence"},
    {"skill_tag": "system_design", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.SHORT, "price_tier": ResourcePriceTier.FREE, "url": "https://www.grokkingsystemdesign.com/", "title": "System Design Concepts and Cheat Sheet"},
    {"skill_tag": "system_design", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://vibeengines.com/", "title": "Interactive System Design Practice"},
    {"skill_tag": "system_design", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.PAID, "url": "https://www.systemdesign.academy/", "title": "System Design Masterclass"},
    {"skill_tag": "web_dev", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.SHORT, "price_tier": ResourcePriceTier.FREE, "url": "https://developer.mozilla.org/en-US/docs/MDN/Tutorials", "title": "MDN Web Development Tutorials"},
    {"skill_tag": "web_dev", "format": ResourceFormat.SHEET, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.FREE, "url": "https://web.dev/learn/", "title": "Learn Web Development by web.dev"},
    {"skill_tag": "web_dev", "format": ResourceFormat.VIDEO, "pacing": ResourcePacing.LONG, "price_tier": ResourcePriceTier.PAID, "url": "https://frontendmasters.com/learn/", "title": "Frontend Masters Learning Paths"},
)


async def seed_resources(session: AsyncSession) -> dict[str, int]:
    """Insert resources whose URLs are not already in the catalog."""

    urls = [str(item["url"]) for item in RESOURCE_CATALOG]
    existing_urls = set(
        (await session.scalars(select(Resource.url).where(Resource.url.in_(urls)))).all()
    )
    new_resources = [
        Resource(**item) for item in RESOURCE_CATALOG if item["url"] not in existing_urls
    ]
    session.add_all(new_resources)
    await session.commit()
    return {
        "inserted": len(new_resources),
        "existing": len(RESOURCE_CATALOG) - len(new_resources),
    }


async def main() -> None:
    async with get_session_factory()() as session:
        result = await seed_resources(session)
    print(
        f"Resource catalog ready: {result['inserted']} inserted, "
        f"{result['existing']} already present."
    )


if __name__ == "__main__":
    asyncio.run(main())
