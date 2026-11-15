"""Persistent mission management endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.models import MissionCreate, MissionResponse, MissionRouteCreate, MissionRouteResponse, MissionUpdate
from app.services.mission_management_service import MissionManagementService
from app.services.mission_service import get_mission_service
from app.services.report_pdf import generate_mission_report_pdf

router = APIRouter(tags=["missions"])


def get_service(db: Session = Depends(get_db)) -> MissionManagementService:
    return MissionManagementService(db)


@router.get("/missions", response_model=List[MissionResponse])
def list_missions(
    status: Optional[str] = Query(None),
    mission_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    descending: bool = Query(True),
    service: MissionManagementService = Depends(get_service),
):
    return service.list_missions(
        status_filter=status,
        mission_type=mission_type,
        search=search,
        sort_by=sort_by,
        descending=descending,
    )


@router.post("/missions", response_model=MissionResponse, status_code=201)
def create_mission(payload: MissionCreate, service: MissionManagementService = Depends(get_service)):
    return service.create(payload)


@router.get("/missions/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: str, service: MissionManagementService = Depends(get_service)):
    return service.get(mission_id)


@router.patch("/missions/{mission_id}", response_model=MissionResponse)
def update_mission(
    mission_id: str, payload: MissionUpdate, service: MissionManagementService = Depends(get_service)
):
    return service.update(mission_id, payload)


@router.delete("/missions/{mission_id}", status_code=204)
def delete_mission(mission_id: str, service: MissionManagementService = Depends(get_service)):
    service.delete(mission_id)
    return None


@router.post("/missions/{mission_id}/plan")
def plan_persistent_mission(
    mission_id: str,
    body: dict = None,
    service: MissionManagementService = Depends(get_service),
):
    mission = service.get(mission_id)
    payload = {
        "mission_id": mission.id,
        "region_id": mission.region_id,
        "start": {"x": mission.start.x, "y": mission.start.y},
        "destination": {"x": mission.destination.x, "y": mission.destination.y},
        "time_limit_min": mission.time_budget_min,
        "name": mission.name,
    }
    if body:
        payload.update(body)
    return get_mission_service().plan(payload)


@router.post("/missions/{mission_id}/report")
def report_persistent_mission(
    mission_id: str,
    body: dict = None,
    service: MissionManagementService = Depends(get_service),
):
    mission = service.get(mission_id)
    # Ensure an in-memory mission exists for report generation.
    try:
        get_mission_service().evaluate(mission_id)
    except Exception:
        payload = {
            "mission_id": mission.id,
            "region_id": mission.region_id,
            "start": {"x": mission.start.x, "y": mission.start.y},
            "destination": {"x": mission.destination.x, "y": mission.destination.y},
            "time_limit_min": mission.time_budget_min,
            "name": mission.name,
        }
        get_mission_service().plan(payload)
    report_body = {"mission_id": mission_id}
    if body:
        report_body.update(body)
    return get_mission_service().report(report_body.get("mission_id"), report_format=report_body.get("format", "json"))


@router.get("/missions/{mission_id}/routes", response_model=List[MissionRouteResponse])
def list_mission_routes(mission_id: str, service: MissionManagementService = Depends(get_service)):
    return service.list_routes(mission_id)


@router.post("/missions/{mission_id}/routes", response_model=MissionRouteResponse, status_code=201)
def create_mission_route(
    mission_id: str, payload: MissionRouteCreate, service: MissionManagementService = Depends(get_service)
):
    return service.create_route(mission_id, payload)


@router.get("/missions/{mission_id}/report/pdf")
def mission_report_pdf(mission_id: str, service: MissionManagementService = Depends(get_service)):
    report = get_mission_service().report(mission_id, report_format="json")
    pdf_bytes = generate_mission_report_pdf(report)
    return Response(content=pdf_bytes, media_type="application/pdf")