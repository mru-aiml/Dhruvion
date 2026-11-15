# DHRUVION API Reference

Base URL: `http://127.0.0.1:8000/api`

## Mission management
- `GET /api/missions` - list missions. Query: `status`, `mission_type`, `search`, `sort_by`, `descending`.
- `POST /api/missions` - create a persistent mission.
- `GET /api/missions/{mission_id}` - retrieve one mission.
- `PATCH /api/missions/{mission_id}` - update fields.
- `DELETE /api/missions/{mission_id}` - delete draft/planned/archived missions only.
- `POST /api/missions/{mission_id}/plan` - calculate a real MOLA route and mission feasibility.
- `POST /api/missions/{mission_id}/report` - generate a mission report.
- `GET /api/missions/{mission_id}/report/pdf` - server-generated mission report PDF.

## Existing endpoints
See `docs/DHRUVION_INTEGRATION_REPORT.md` for the full endpoint list and scientific limitations.
