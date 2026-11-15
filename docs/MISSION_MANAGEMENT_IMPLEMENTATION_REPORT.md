# Mission Management Implementation Report

## Implemented features
- Persistent mission CRUD backed by SQLite/SQLAlchemy.
- Mission Management page with search, filtering, sorting, add/edit modal.
- Overview "+ Add mission" entry point.
- Mission detail, status updates, route planning, and report generation.
- Coordinate and coverage validation.
- Deletion rules for active/completed missions.

## Files changed
- `backend/app/core/models.py`
- `backend/app/schemas/models.py`
- `backend/app/services/mission_management_service.py`
- `backend/app/api/routes_missions.py`
- `backend/app/main.py`
- `backend/tests/test_missions.py`
- `frontend/src/types/index.ts`
- `frontend/src/services/api/endpoints.ts`
- `frontend/src/features/missions/MissionsPage.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/features/overview/OverviewPage.tsx`
- `frontend/src/features/auth/AuthLayout.tsx`

## API endpoints
- `GET /api/missions`
- `POST /api/missions`
- `GET /api/missions/{mission_id}`
- `PATCH /api/missions/{mission_id}`
- `DELETE /api/missions/{mission_id}`
- `POST /api/missions/{mission_id}/plan`
- `POST /api/missions/{mission_id}/report`

## Test results
- `cd backend; python -m pytest tests -q` -> `63 passed`.
- `cd frontend; npm run build` -> passed.

## Limitations
- Missions are global, not user-scoped.
- Route and mission feasibility remain in-memory after planning; restart clears planned route state but persistent mission records remain.
- Coordinates must be inside MOLA coverage.
- MOLA is ~463 m/px regional data, not rover-scale.

## Startup
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000

cd frontend
npm run dev
```
