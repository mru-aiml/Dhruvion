#!/usr/bin/env python
"""Seed script for demo missions.

Creates a small set of clearly labelled demonstration missions for the Mission Management page.
This script is idempotent - it can be run multiple times without creating duplicates.
"""

import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import engine, Base
from app.core.models import Mission
from app.services.terrain_service import get_terrain_service

# Demo mission definitions - clearly marked as simulated
DEMO_MISSIONS = [
    {
        "id": "demo-gale-crater-survey",
        "name": "Gale Crater Survey",
        "description": "DEMO: Short terrain survey traverse in Gale Crater. Simulated mission for demonstration purposes only.",
        "region_id": "gale_crater",
        "mission_type": "traverse",
        "start_x": 137.2,
        "start_y": -4.5,
        "destination_x": 137.3,
        "destination_y": -4.55,
        "time_budget_min": 600,
        "available_sols": 10.0,
        "objectives": json.dumps([
            "Survey terrain between landing site and Aeolis Mons foothills",
            "Collect MOLA elevation profile data",
            "Identify potential science targets of opportunity"
        ]),
        "notes": "DEMO / SIMULATED - Not a real NASA mission. For UI demonstration only.",
        "status": "draft",
        "created_at": datetime(2024, 1, 15, 10, 30, 0),
        "updated_at": datetime(2024, 1, 15, 10, 30, 0),
    },
    {
        "id": "demo-jezero-terrain-recon",
        "name": "Jezero Terrain Recon",
        "description": "DEMO: Reconnaissance mission in Jezero Crater region. Simulated mission for demonstration purposes only.",
        "region_id": "gale_crater",  # Using gale_crater since it's the only supported region
        "mission_type": "reconnaissance",
        "start_x": 137.4,
        "start_y": -5.0,
        "destination_x": 137.6,
        "destination_y": -5.2,
        "time_budget_min": 720,
        "available_sols": 15.0,
        "objectives": json.dumps([
            "Reconnoiter delta-like terrain features",
            "Assess traverseability of crater floor units",
            "Document sedimentary layer exposures"
        ]),
        "notes": "DEMO / SIMULATED - Jezero region mapped onto Gale Crater coordinates for demo. Not a real NASA mission.",
        "status": "planned",
        "created_at": datetime(2024, 2, 20, 14, 0, 0),
        "updated_at": datetime(2024, 2, 20, 14, 0, 0),
    },
    {
        "id": "demo-elysium-logistics-test",
        "name": "Elysium Logistics Test",
        "description": "DEMO: Logistics and resource planning demonstration mission. Simulated mission for demonstration purposes only.",
        "region_id": "gale_crater",  # Using gale_crater since it's the only supported region
        "mission_type": "logistics",
        "start_x": 137.0,
        "start_y": -5.8,
        "destination_x": 137.1,
        "destination_y": -6.0,
        "time_budget_min": 480,
        "available_sols": 8.0,
        "objectives": json.dumps([
            "Test mission scheduling and resource allocation workflows",
            "Validate time budget calculations for short traverses",
            "Demonstrate mission reporting pipeline"
        ]),
        "notes": "DEMO / SIMULATED - Elysium Planitia region mapped onto Gale Crater coordinates for demo. Not a real NASA mission.",
        "status": "draft",
        "created_at": datetime(2024, 3, 10, 9, 15, 0),
        "updated_at": datetime(2024, 3, 10, 9, 15, 0),
    },
]


def _coverage_ok(lon: float, lat: float) -> bool:
    """Check if coordinates are within available terrain coverage."""
    try:
        payload = get_terrain_service().coverage_at(lon, lat)
    except Exception:
        return False
    coverage = payload.get("coverage") or {}
    return payload.get("availability") == "available" and coverage.get("class") in (1, 2)


def seed_demo_missions(db: Session) -> int:
    """Seed demo missions idempotently. Returns number of missions created."""
    created_count = 0
    
    for demo in DEMO_MISSIONS:
        # Check if mission already exists by ID
        existing = db.query(Mission).filter(Mission.id == demo["id"]).first()
        if existing:
            print(f"Demo mission already exists: {demo['name']} ({demo['id']})")
            continue
        
        # Validate coordinates are in coverage
        if not _coverage_ok(demo["start_x"], demo["start_y"]):
            print(f"WARNING: Start coordinates for {demo['name']} outside coverage, adjusting...")
            demo["start_x"], demo["start_y"] = 137.2, -4.5
        if not _coverage_ok(demo["destination_x"], demo["destination_y"]):
            print(f"WARNING: Destination coordinates for {demo['name']} outside coverage, adjusting...")
            demo["destination_x"], demo["destination_y"] = 137.3, -4.55
        
        mission = Mission(**demo)
        db.add(mission)
        created_count += 1
        print(f"Created demo mission: {demo['name']} ({demo['id']})")
    
    if created_count > 0:
        db.commit()
        print(f"Successfully created {created_count} demo mission(s)")
    else:
        print("No new demo missions created (all already exist)")
    
    return created_count


def main():
    """Main entry point for script execution."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as db:
        seed_demo_missions(db)


if __name__ == "__main__":
    main()