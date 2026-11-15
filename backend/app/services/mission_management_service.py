"""Persistent mission management backed by SQLite/SQLAlchemy."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.models import Mission, MissionRoute
from app.schemas.models import MissionCreate, MissionResponse, MissionUpdate
from app.services.terrain_service import get_terrain_service

SUPPORTED_REGIONS = {"gale_crater"}
VALID_MISSION_TYPES = {"traverse", "reconnaissance", "science_exploration", "return"}
VALID_STATUSES = {"draft", "planned", "active", "completed", "archived"}
DELETABLE_STATUSES = {"draft", "planned", "archived"}


def _validate_region(region_id: str) -> str:
    if region_id not in SUPPORTED_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported region '{region_id}'. Supported: {sorted(SUPPORTED_REGIONS)}",
        )
    return region_id


def _validate_mission_type(mission_type: str) -> str:
    if mission_type not in VALID_MISSION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported mission_type '{mission_type}'.",
        )
    return mission_type


def _validate_status(status_value: str) -> str:
    if status_value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported status '{status_value}'.",
        )
    return status_value


def _coverage_ok(lon: float, lat: float) -> bool:
    try:
        payload = get_terrain_service().coverage_at(lon, lat)
    except Exception:
        return False
    coverage = payload.get("coverage") or {}
    return payload.get("availability") == "available" and coverage.get("class") in (1, 2)


def _validate_coordinates(start_x, start_y, destination_x, destination_y) -> None:
    if not (_coverage_ok(start_x, start_y)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Start coordinate is outside available terrain coverage.",
        )
    if not (_coverage_ok(destination_x, destination_y)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Destination coordinate is outside available terrain coverage.",
        )


def _to_response(mission: Mission) -> MissionResponse:
    import json

    objectives: List[str] = []
    if mission.objectives:
        try:
            parsed = json.loads(mission.objectives)
            if isinstance(parsed, list):
                objectives = [str(item) for item in parsed]
            else:
                objectives = [str(mission.objectives)]
        except (ValueError, TypeError):
            objectives = [line for line in mission.objectives.splitlines() if line.strip()]
    return MissionResponse(
        id=mission.id,
        name=mission.name,
        description=mission.description,
        region_id=mission.region_id,
        mission_type=mission.mission_type,
        start={"x": mission.start_x, "y": mission.start_y},
        destination={"x": mission.destination_x, "y": mission.destination_y},
        time_budget_min=mission.time_budget_min,
        available_sols=mission.available_sols,
        objectives=objectives,
        notes=mission.notes,
        status=mission.status,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


class MissionManagementService:
    def __init__(self, db: Session):
        self.db = db

    def list_missions(
        self,
        status_filter: Optional[str] = None,
        mission_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        descending: bool = True,
    ) -> List[MissionResponse]:
        query = self.db.query(Mission)
        if status_filter:
            query = query.filter(Mission.status == status_filter)
        if mission_type:
            query = query.filter(Mission.mission_type == mission_type)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(Mission.name.ilike(like))
        sort_column = {
            "created_at": Mission.created_at,
            "name": Mission.name,
            "status": Mission.status,
            "mission_type": Mission.mission_type,
        }.get(sort_by, Mission.created_at)
        query = query.order_by(sort_column.desc() if descending else sort_column.asc())
        return [_to_response(m) for m in query.all()]

    def create(self, payload: MissionCreate) -> MissionResponse:
        _validate_region(payload.region_id)
        _validate_mission_type(payload.mission_type)
        _validate_status(payload.status)
        _validate_coordinates(
            payload.start.x, payload.start.y, payload.destination.x, payload.destination.y
        )
        mission = Mission(
            id=str(uuid.uuid4()),
            name=payload.name,
            description=payload.description,
            region_id=payload.region_id,
            mission_type=payload.mission_type,
            start_x=payload.start.x,
            start_y=payload.start.y,
            destination_x=payload.destination.x,
            destination_y=payload.destination.y,
            time_budget_min=payload.time_budget_min,
            available_sols=payload.available_sols,
            objectives=json.dumps(payload.objectives),
            notes=payload.notes,
            status=payload.status,
        )
        self.db.add(mission)
        self.db.commit()
        self.db.refresh(mission)
        return _to_response(mission)

    def get(self, mission_id: str) -> MissionResponse:
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
        return _to_response(mission)

    def update(self, mission_id: str, payload: MissionUpdate) -> MissionResponse:
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
        if payload.name is not None:
            mission.name = payload.name
        if payload.description is not None:
            mission.description = payload.description
        if payload.region_id is not None:
            mission.region_id = _validate_region(payload.region_id)
        if payload.mission_type is not None:
            mission.mission_type = _validate_mission_type(payload.mission_type)
        if payload.start is not None or payload.destination is not None:
            start_x = payload.start.x if payload.start else mission.start_x
            start_y = payload.start.y if payload.start else mission.start_y
            dest_x = payload.destination.x if payload.destination else mission.destination_x
            dest_y = payload.destination.y if payload.destination else mission.destination_y
            _validate_coordinates(start_x, start_y, dest_x, dest_y)
            mission.start_x = start_x
            mission.start_y = start_y
            mission.destination_x = dest_x
            mission.destination_y = dest_y
        if payload.time_budget_min is not None:
            mission.time_budget_min = payload.time_budget_min
        if payload.available_sols is not None:
            mission.available_sols = payload.available_sols
        if payload.objectives is not None:
            mission.objectives = json.dumps(payload.objectives)
        if payload.notes is not None:
            mission.notes = payload.notes
        if payload.status is not None:
            mission.status = _validate_status(payload.status)
        mission.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(mission)
        return _to_response(mission)

    def delete(self, mission_id: str) -> None:
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
        if mission.status not in DELETABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Mission with status '{mission.status}' cannot be deleted.",
            )
        self.db.delete(mission)
        self.db.commit()

    def list_routes(self, mission_id: str):
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise HTTPException(status_code=404, detail="Mission not found")
        rows = self.db.query(MissionRoute).filter(MissionRoute.mission_id == mission_id).order_by(MissionRoute.created_at.desc()).all()
        return [self._route_to_response(row) for row in rows]

    def create_route(self, mission_id: str, payload):
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise HTTPException(status_code=404, detail="Mission not found")
        row = MissionRoute(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            strategy=payload.strategy,
            geometry_json=json.dumps(payload.geometry),
            distance_m=payload.distance_m,
            estimated_duration_min=payload.estimated_duration_min,
            terrain_difficulty=payload.terrain_difficulty,
            max_slope_deg=payload.max_slope_deg,
            feasibility=payload.feasibility,
            parameters_json=json.dumps(payload.parameters or {}),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._route_to_response(row)

    @staticmethod
    def _route_to_response(row: MissionRoute):
        from app.schemas.models import MissionRouteResponse

        try:
            geometry = json.loads(row.geometry_json)
        except (ValueError, TypeError):
            geometry = []
        try:
            parameters = json.loads(row.parameters_json) if row.parameters_json else {}
        except (ValueError, TypeError):
            parameters = {}
        return MissionRouteResponse(
            id=row.id,
            mission_id=row.mission_id,
            strategy=row.strategy,
            geometry=geometry,
            distance_m=row.distance_m,
            estimated_duration_min=row.estimated_duration_min,
            terrain_difficulty=row.terrain_difficulty,
            max_slope_deg=row.max_slope_deg,
            feasibility=row.feasibility,
            parameters=parameters,
            created_at=row.created_at,
        )