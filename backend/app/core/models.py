from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class MissionRoute(Base):
    __tablename__ = "mission_routes"

    id = Column(String(36), primary_key=True, index=True)
    mission_id = Column(String(36), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy = Column(String(64), nullable=False, default="balanced")
    geometry_json = Column(Text, nullable=False)
    distance_m = Column(Float, nullable=True)
    estimated_duration_min = Column(Float, nullable=True)
    terrain_difficulty = Column(Float, nullable=True)
    max_slope_deg = Column(Float, nullable=True)
    feasibility = Column(String(32), nullable=True)
    parameters_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Mission(Base):
    __tablename__ = "missions"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    region_id = Column(String(64), nullable=False, default="gale_crater")
    mission_type = Column(String(64), nullable=False, default="traverse")
    start_x = Column(Float, nullable=False)
    start_y = Column(Float, nullable=False)
    destination_x = Column(Float, nullable=False)
    destination_y = Column(Float, nullable=False)
    time_budget_min = Column(Float, nullable=False)
    available_sols = Column(Float, nullable=True)
    objectives = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)