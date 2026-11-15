"""REMS environment and RAD radiation endpoints.

Both endpoints return historical point measurements with explicit units,
coverage, provenance, and limitations. Neither is a live or forecast feed.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core.exceptions import NotFoundError
from app.services.rad_service import get_rad_service
from app.services.rems_service import get_rems_service
from app.services.terrain_service import REGION_ID

router = APIRouter(tags=["environment"])


def _assert_region(region_id: str) -> None:
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})


@router.get("/environment/rems")
def rems(
    region_id: str = Query(REGION_ID),
    sol: Optional[int] = Query(None, description="Optional sol filter (9 or 11)"),
    include_observations: bool = Query(False),
):
    _assert_region(region_id)
    return get_rems_service().environment(sol=sol, include_observations=include_observations)


@router.get("/environment/rems/observations")
def rems_observations(
    region_id: str = Query(REGION_ID),
    sol: Optional[int] = Query(None),
    measurement: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    _assert_region(region_id)
    return get_rems_service().observations(sol=sol, measurement=measurement, limit=limit)


@router.get("/environment/radiation")
def radiation(
    region_id: str = Query(REGION_ID),
    sol: Optional[int] = Query(None, description="Optional sol filter (1, 2, or 3)"),
    include_observations: bool = Query(False),
):
    _assert_region(region_id)
    return get_rad_service().radiation(sol=sol, include_observations=include_observations)


@router.get("/environment/radiation/observations")
def radiation_observations(
    region_id: str = Query(REGION_ID),
    detector: Optional[str] = Query(None, description="B or E"),
    sol: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=500),
):
    _assert_region(region_id)
    return get_rad_service().observations(detector=detector, sol=sol, limit=limit)
