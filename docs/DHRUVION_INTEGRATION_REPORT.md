# DHRUVION Integration Report

## 1. Backend audit results

The full audit is in `docs/backend-audit.md`. Summary of the defects found and
fixed:

- D1: legacy terrain service returned placeholder values instead of raster samples.
- D2: route planner used synthetic grid/costs rather than the MOLA coverage grid.
- D3: mission feasibility, return feasibility, reroute, and reports were stubbed.
- D4: REMS/RAD were not connected to the supplied JSON files.
- D5: CTX imagery bounds and DN labelling were missing.
- D6: dataset catalog and layer catalog were not package-aware.
- D7: assistant was not allowlisted against real services and could not report tool failures.
- D8: frontend contracts did not cover dataset, terrain, REMS, RAD, mission, or structured assistant responses.
- D9: map bounds and tile proxy assumptions were not metadata-derived.
- D10: reports and emergency workflows used static scenario data.
- D11-D16: missing tests, missing provenance propagation, missing NoData handling, missing class-2 handling, missing model fallback, missing frontend mission sharing.

## 2. Existing implementations reused

- FastAPI app skeleton and router registration in `backend/app/main.py`.
- Authentication and database models/tests in `backend/tests/test_auth.py`.
- Core exception handling and response conventions in `backend/app/core/exceptions.py`.
- Existing terrain/raster compatibility routes in `backend/app/api/routes_v2.py`.
- Existing frontend visual design, components, pages, and styling.
- Existing Ollama client pattern from `Dhruvion-main/backend/app/services/assistant_service.py`, reimplemented in `backend/app/ai/llm_client.py`.
- Existing API contracts were preserved and extended additively.

## 3. New and modified files

### Backend added
- `backend/app/ai/agent.py`
- `backend/app/ai/llm_client.py`
- `backend/app/ai/schemas.py`
- `backend/app/ai/tools.py`
- `backend/app/api/routes_assistant.py`
- `backend/app/api/routes_environment.py`
- `backend/app/api/routes_planning.py`
- `backend/app/data_pipeline/dataset_paths.py`
- `backend/app/services/dataset_catalog_service.py`
- `backend/app/services/hazard_service.py`
- `backend/app/services/layer_catalog.py`
- `backend/app/services/mission_service.py`
- `backend/app/services/rad_service.py`
- `backend/app/services/rems_service.py`
- `backend/app/services/route_planner.py`
- `backend/app/services/terrain_service.py`
- `backend/tests/test_ai.py`
- `backend/tests/test_dataset_integration.py`
- `backend/tests/test_planning.py`

### Backend modified
- `backend/app/api/routes.py`
- `backend/app/api/routes_v2.py`
- `backend/app/core/config.py`
- `backend/app/data_pipeline/ingestion.py` (pre-existing change preserved, not discarded)
- `backend/app/main.py`
- `backend/app/schemas/models.py`
- `backend/app/services/imagery_service.py`
- `backend/tests/test_api.py`

### Frontend modified
- `frontend/src/components/map/mars.ts`
- `frontend/src/features/assistant/AssistantPage.tsx`
- `frontend/src/features/emergency/EmergencyPage.tsx`
- `frontend/src/features/martian-map/MartianMapPage.tsx`
- `frontend/src/features/overview/OverviewPage.tsx`
- `frontend/src/features/reports/ReportsPage.tsx`
- `frontend/src/features/route-planner/RoutePlannerPage.tsx`
- `frontend/src/services/api/endpoints.ts`
- `frontend/src/types/index.ts`
- `frontend/src/services/missionStore.ts` (added)

## 4. Dataset integration status

Data root resolves through `DHRUVION_DATA_DIR`, then `DHRUVION_DATA`, then
`data/source_packages/...`, then `Dhruvion-main/data/source_packages/...`.

### MOLA terrain
- Connected `elevation_m.tif`, `slope_deg.tif`, `roughness_tri_riley_m.tif`, `coverage_mask.tif`.
- Rasterio + NumPy sampling with CRS/transform/NoData/bounds handling.
- Coverage classes preserved: 0 = no data, 1 = usable, 2 = elevation only.
- Class 2 never supplies slope or roughness.
- Unknown cells are never zero-cost terrain.
- Resolution is approximately 463 m/px and is reported as regional, not rover-scale.

### CTX imagery
- Connected processed CTX PNG and overlay metadata.
- Partial coverage preserved: lat -6.9187..-4.0, lon 136.1999..139.4.
- Mars equirectangular/plate carrée used; Web Mercator is not used.
- Pixel values labelled as DN, not reflectance.
- Imagery is not stretched into uncovered areas.

### REMS
- Connected `rems_sol_summary.json`, `rems_session_summary.json`,
  `rems_observations_clean.json`, `rems_trends.json`.
- Default filter is `all_valid_values`.
- Wind uses circular statistics and reports insufficient data where sparse.
- Historical sols 9 and 11 at Curiosity location; not live/forecast/spatially distributed.

### RAD
- Connected `rad_sol_summary.json`, `rad_observations_clean.json`, `rad_trends.json`.
- Detectors B and E remain separate.
- Units are microGray / Hour.
- `qc_placeholder` is not treated as a quality flag.
- Historical sols 1-3; not route-specific radiation predictions.

## 5. AI agent implementation status

- Allowlisted tools call real backend services:
  `get_terrain_at_coordinate`, `get_terrain_profile`, `get_coverage_status`,
  `get_rems_summary`, `get_radiation_summary`, `calculate_route`,
  `compare_routes`, `evaluate_mission`, `evaluate_return_feasibility`,
  `generate_mission_report`.
- Terrain, hazard, and route calculations remain deterministic Python.
- The LLM only phrases evidence produced by tools.
- Model availability check, timeout handling, clear errors, and graceful fallback are implemented.
- Data APIs and mission calculations continue to work when the LLM is offline.
- Structured response includes answer, tools used, observations, sources/units,
  recommendations, warnings, limitations, confidence explanation, fallback flag,
  model, mission id, and grounding metadata.

## 6. Model provider and configuration

- Provider: Ollama.
- Base URL: `http://127.0.0.1:11434`.
- Model: `qwen2.5-coder:3b`.
- The model is installed and reachable; health endpoint reports `available: true`.
- On CPU the phrasing call usually exceeds the 30 s answer timeout, so the
  assistant returns the deterministic evidence-based answer and marks
  `fallback: true`. Tool execution and values remain real in both cases.

## 7. Working API endpoints

- `GET /api/health`
- `GET /api/datasets`
- `GET /api/regions`
- `GET /api/layers`
- `GET /api/terrain`
- `GET /api/terrain/elevation`
- `GET /api/terrain/slope`
- `GET /api/terrain/roughness`
- `GET /api/terrain/coverage`
- `GET /api/imagery`
- `GET /api/environment/rems`
- `GET /api/environment/radiation`
- `POST /api/route/optimize`
- `POST /api/mission/plan`
- `POST /api/mission/return`
- `POST /api/mission/report`
- `POST /api/route/reroute`
- `POST /api/assistant/ask`
- `GET /api/assistant/health`

## 8. Scientific limitations

- MOLA is approximately 463 m/px regional terrain data, not rover-scale obstacle detection.
- CTX imagery is partial coverage and DN, not reflectance.
- REMS and RAD are historical point measurements at Curiosity, not live weather, forecasts, or spatially distributed data.
- Slope and roughness are derived at the MOLA baseline.
- Class 2 cells have elevation only; slope and roughness are unavailable.
- Unknown cells are never treated as zero cost.
- Route travel speed of 60.0 m/min is a planning assumption, not rover-verified.
- Reports and emergency reroute are planning simulations based on user-supplied blockage geometry.
- No verified science-target dataset was supplied; UI science targets remain simulated and labelled.

## 9. Test results

- Backend: `cd backend; python -m pytest tests -q` -> `49 passed, 97 warnings`.
- Smoke test: `python C:\Users\Nilesh\AppData\Local\Temp\opencode\dhruvion_smoke.py` -> `33 checks, 0 failed`.
- Frontend: `cd frontend; npm run build` -> success, 2598 modules transformed, built in 23.63 s.
- Package self-tests: attempted with `cd Dhruvion-main/.../DHRUVION_DATA; python -m pytest scripts/tests -q`; blocked because `pyproj` is not installed in this environment (`ModuleNotFoundError: No module named 'pyproj'`). The backend terrain service does not depend on `pyproj` and uses a direct fallback. The package previously recorded 26 passed in `DHRUVION_DATA/reports/test_results.txt`.
- Real assistant call: `/api/assistant/ask` returned HTTP 200 with real MOLA values and `fallback: true` because the CPU model timed out after 30 s.

## 10. Remaining blockers

- `pyproj` is not installed, so the NASA package's own `scripts/tests/test_pipeline.py` cannot be collected in this environment.
- Ollama phrasing is slower than the configured 30 s answer timeout on CPU; deterministic fallback is used.
- No verified science-target dataset is included in the package.
- Mission and route registries are in-memory and reset on server restart.

## 11. Exact startup commands

Backend:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

Tests:
```bash
cd backend
python -m pytest tests -q
```

Frontend build:
```bash
cd frontend
npm run build
```

Optional dataset directory override:
```bash
set DHRUVION_DATA_DIR=D:\path\to\DHRUVION_DATA
```
