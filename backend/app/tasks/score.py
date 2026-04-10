import asyncio

from app.celery_app import celery_app
from app.scoring.engine import compute_scores_all_cities, compute_scores_for_city


@celery_app.task(name="score.run_all")
def run_all_scoring() -> dict:
    """Compute trending scores for all cities. Runs at 3am UTC after collection."""
    return asyncio.run(compute_scores_all_cities())


@celery_app.task(name="score.run_city")
def run_scoring_for_city(city: str) -> dict:
    """Compute trending scores for a single city."""
    count = asyncio.run(compute_scores_for_city(city))
    return {city: count}
