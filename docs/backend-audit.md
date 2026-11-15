# DHRUVION Backend Audit

**Date:** 2026-11-15
**Scope:** `backend/` (FastAPI service in the repository root), its data pipeline, processed
data handover package, API contract, and frontend integration points.
**Mode:** Read-only audit first, then incremental integration. Existing endpoints and
response fields are preserved and extended additively.

---

## 1. Method

1. Read `README.md`, `prd.md`, `architecture.md`, `design.md`, `api.md`, `testing.md`,
   `backend/README.md`, and the NASA package handover documentation
   (`DHRUVION_DATA/documentation/*`, `processed/*/README.md`, provenance JSONs).
2. Enumerated every FastAPI route and traced it: route handler → service / data access →
   tests.
3. Inspected every raster, summary JSON, and metadata file that the backend is expected to
   serve, including CRS, transform, bounds, NoData, class codes, units, and row counts.
4. Ran the existing backend test suite and recorded the actual result:
   `cd backend; python -m pytest tests -q` → **11 passed** (4 API, 7 auth).
5. Verified runtime environment: Python 3.13.7, FastAPI 0.116.1, Pydantic 2.11.7,
   rasterio 1.5.2, NumPy 2.2.6. `pyproj` is **not installed**; `httpx` and network access
   are available. Ollama is reachable at `http://127.0.0.1:11434` with
   `qwen2.5-coder:3b` (capabilities include `tools`).

A feature is only marked **Working** when an endpoint, its service logic, and a test all
support the behaviour with the real dataset. Code presence alone is **Partial** or
**Broken**.

---

## 2. Feature audit

| # | Feature | Endpoint(s) | Implementation trace | Tests | Status | Concrete findings |
|---|---------|-------------|----------------------|-------|--------|-------------------|
| 1 | Service health | `GET /health`, `GET /api/health` | `app/main.py:78`, `app/api/routes.py:220` | `tests/test_api.py::test_health` | **Working** | Health is independent of NASA/external services. |
| 2 | Region catalog | `GET /api/regions` | `app/api/routes.py:225` | none | **Partial** | Returns a single hardcoded region with no bounds, resolution, CRS WKT, or dataset provenance. Frontend cannot derive map extent from it. |
| 3 | Layer catalog | `GET /api/layers` | Hardcoded `LAYERS` list in `app/api/routes.py:42-217` | none | **Partial / stale** | Describes the old 320×128 legacy crop (`/static/mola/gale/*.png`, lon 137–138, lat -6.5..-4.0). Does not expose the supplied NASA package (`processed/terrain`, `processed/ctx`), no `bounds` values, and no REMS/RAD dataset status. |
| 4 | Terrain point query | `GET /api/terrain` | `app/api/routes.py:243-286` (`_sample`), `app/api/services/terrain_data_service.py` is unused by this route | `test_terrain_available`, `test_terrain_outside_coverage` | **Partial** | Works only with legacy degrees-transform raster. `_sample` treats `0.0` as NoData, so a valid 0° slope is reported `null`. No coverage class, units, source, or limitation fields. No distinction between "elevation valid but derivative undefined" (class 2) and full validity. |
| 5 | Terrain sub-layer endpoints | `GET /api/terrain/elevation`, `/slope`, `/roughness`, `/coverage` | **missing** | none | **Missing** | Required by the integration brief. Nothing serves a single layer with value/unit/source/coverage/availability/provenance/limitations. |
| 6 | Hazard assessment | `GET /api/hazards` | `app/api/routes.py:289` | none | **Placeholder** | Always returns an empty FeatureCollection. The warning is honest, but no screening summary is computed from slope/roughness, and no hazard input raster exists. |
| 7 | Science targets | `GET /api/targets` | `app/api/routes.py:302`; `services/science_data_service.py` never loaded | none | **Unavailable (correctly)** | Package contains no verified target catalog, so empty results are acceptable, but `science_data_service` only loads `data/processed/science_targets.geojson` (absent). |
| 8 | Route optimization | `POST /api/route/optimize` | `app/api/routes.py:335-465` | none | **Broken for the real dataset** | `_latlon_to_rc` assumes 128 px/degree starting at lon 137 / lat -4. The real dataset has 410×410 cells over lon 136.1982–139.4014, lat -7.0002–-3.797 at ~463 m/px in metre coordinates. The grid mapping is wrong even for the legacy 320×128 crop (actual 100 px/degree). `_load_raster` returns a **closed** rasterio handle. No coverage-class handling; class-2 cells treated like fully usable cells. |
| 9 | Mission planning | `POST /api/mission/plan` | `app/api/routes.py:500-599` | none | **Partial / incorrect** | Reuses the broken grid. Return leg is assumed identical to outbound. No unknown-cell accounting, no coverage summary, and no link to a real mission registry. |
| 10 | Return feasibility | `POST /api/mission/return` | `app/api/routes.py:620-691` | none | **Broken** | Hardcodes base `(-5.45, 137.35)` and speed 60 m/min. Ignores the mission's actual start. `mission_id` is not used. |
| 11 | Emergency reroute | `POST /api/route/reroute` | `app/api/routes.py:715-725` | none | **Not implemented** | Always raises 503. Contract exists but no alternative route is produced. |
| 12 | AI assistant | `POST /api/assistant/ask` | `app/api/routes.py:751-764` | none | **Placeholder** | Returns a fixed message; no tools, no model, no evidence, no degraded-mode logic. Frontend copy even says "backend endpoint is not implemented". |
| 13 | Mission report | `POST /api/mission/report` | `app/api/routes.py:782-806` | none | **Placeholder** | Writes a stub JSON with `mission_id` only. No terrain/route/environment data, no provenance, no limitations. |
| 14 | Dataset catalog | `GET /api/datasets` | `app/api/routes_v2.py:54` | none | **Broken** | Route function is named `get_dataset_catalog`, shadowing the imported function of the same name, so the body calls itself recursively → `RecursionError`. In addition `DatasetCatalog` is never rebuilt by the getter (`data_pipeline/catalog.py:288`), so it would be empty even if reachable. Discovery targets legacy `data/`, not the NASA package. |
| 15 | Raster layer metadata | `GET /api/raster/layers`, `/metadata`, `/statistics`, `POST /validate-coordinate` | `app/api/routes_v2.py:133-170`, `services/terrain_data_service.py` | none | **Broken / stale** | All paths hardcoded to `data/processed/mola/gale/*.tif`. `validate_coordinate` depends on a catalog entry that does not exist. NaN-NoData statistics path is wrong (see defect D5). |
| 16 | Imagery layer catalog | `GET /api/imagery/layers` | `app/api/routes_v2.py:175-191`, `services/imagery_service.py:344` | none | **Broken (filtered) / stale** | `get_layer_catalog` dereferences nonexistent `layer.metadata` whenever `region_id` is supplied → `AttributeError`. Catalog contains only Mars Trek tiles + legacy PNGs; no CTX local overlay, projection note, or metadata-derived bounds. |
| 17 | Tile proxy | `GET /api/tiles/{layer}/{z}/{x}/{y}.png` | `app/api/routes.py:810-832` | `test_tile_proxy` | **Works but network-bound** | Proxies NASA Mars Trek with 15 s timeout. The existing test requires live internet, so the suite is not hermetic. No caching despite the README claim. |
| 18 | Science catalog API | `GET /api/science/catalogs*` | `app/api/routes_v2.py:196-297`, `services/science_data_service.py` | none | **Empty (correct)** | No verified catalog loaded; service returns empty lists. Distance approximation uses 59 km/degree and is not tied to Mars radius (59.27 km at equator), acceptable only as a rough demo. |
| 19 | Authentication | `/api/auth/*` | `app/api/auth.py`, `core/security.py`, `core/models.py` | `tests/test_auth.py` (7) | **Working** | Unrelated to scientific data; preserve as-is. |
| 20 | Static data mount | `/static/*` | `app/main.py:50-52` | none | **Stale** | Mounts only `data/processed`. The supplied NASA package is not web-accessible, so real overlay PNGs cannot be rendered. |

---

## 3. Data asset audit

### 3.1 Legacy local crop (`data/processed/mola/gale`)

- 320×128, float32, declared CRS `Mars_simpCyl_c180` but **transform is in degrees**
  (`0.01°/px`, origin 137.0, -4.0), bounds lon 137–138, lat -6.5..-4.0.
- NoData = 0.0. Slope can legitimately be 0°, which the route code
  (`routes.py:251`) rejects as missing.
- Resolution 0.01° ≈ 463 m at the equator but only ~460 m E–W at 5°S; not rover-scale.
- This crop is superseded by the supplied package and must not be the default source.

### 3.2 NASA handover package (`DHRUVION_DATA`)

Located in this repository at
`Dhruvion-main/data/source_packages/nasa_dataset_package_2026/DHRUVION_DATA`.
It must be resolved by configuration, never by a developer-specific absolute path.

**Terrain (`processed/terrain/`)**

- `..._elevation_m.tif`: 410×410 float32, NoData `NaN`, projected equirectangular
  (`R = 3 396 190 m`, central meridian 0), transform `463.0935 m/px`, bounds
  `x 8 073 109.71 … 8 262 978.06`, `y -414 931.81 … -225 063.46`
  → lon 136.1982–139.4014 E, lat -7.0002..-3.7970 (planetocentric, east-positive).
- `..._slope_deg.tif`: Horn (1981) slope in degrees, same grid; undefined at border cells.
- `..._roughness_tri_riley_m.tif`: Riley (1999) TRI in **metres**, same grid.
- `..._coverage_mask.tif`: uint8 classes `0 = no elevation`, `1 = elevation + derivatives
  valid`, `2 = elevation valid, derivatives undefined`. Package counts:
  class 1 = 166 464, class 2 = 1 636, class 0 = 0.
- Ground spacing dx 459.6–462.1 m, dy 463.1 m. Derivatives are at the ~463 m DEM
  baseline, **not rover-scale**.
- Overlay metadata gives Leaflet bounds and display ranges; PNGs are display products
  (values clipped for display only), not analysis inputs.

**CTX imagery (`processed/ctx/`)**

- `..._GaleAOI.png` and clipped GeoTIFF: 3460×3794, uint8, NoData 0, pixel ~50 m,
  bounds lon 136.1999–139.4, lat -6.9187..-4.0000 — **partial** coverage relative to the
  terrain AOI (no stretching into uncovered areas allowed).
- Metadata: projection `Mars_2015_Ocentric_Equirectangular_clon_0`, stretch
  `none (8-bit DN as stored)`, `nodata_handling: declared NoData -> transparent`,
  alignment with DEM `NEAR_EQUIVALENT_CRS_DIFFERENT_GRID`
  (max offset 12.078 m > 5 m tolerance).

**REMS (`processed/rems/`)**

- Historical sols **9 and 11** at the Curiosity rover location, 1 Hz tables.
- Summary rows are keyed by `measurement` + `filter`; default is `all_valid_values`.
- 72 sol-summary rows, 1332 session-summary rows, 18 480 clean observations.
- Wind speed/direction are mostly invalid: only a handful of valid samples (sol 9 has
  1 valid wind speed; sol 11 session S9 has 1). Circular statistics are provided for
  direction (`circular_mean_deg`, `resultant_length`); no reliable wind conclusion is
  possible. Trends: "Fewer than 5 sols - trend not computed".
- Not live, not a forecast, not spatially distributed.

**RAD (`processed/rad/`)**

- Historical sols **1–3**, detectors **B** (silicon) and **E** kept separate.
- Unit `microGray / Hour`; 6 sol-summary rows, 94 clean observations.
- `qc_placeholder` is a placeholder field (`00000000`), **not** a validated quality flag.
- Per-sol means are unweighted means of observation dose rates.
- Trends: "Fewer than 5 sols - trend not computed".
- Never a route-specific radiation prediction.

**Catalog metadata (`metadata/`)**

- `FINAL_DATASET_CATALOG.json`: 20 datasets, classification vocabulary
  `OBSERVED/DERIVED/SIMULATED/UNAVAILABLE`.
- `validated_dataset_catalog.json`: 16 datasets, statuses include
  `VALIDATED`, `VALIDATED WITH LIMITATIONS`, `NOT AVAILABLE`.
- These should drive `/api/datasets`, filtered to the products actually present on disk.

---

## 4. Defect register

| ID | Defect | Location | Impact |
|----|--------|----------|--------|
| D1 | Coordinate→pixel mapping hardcoded as `128 px/deg` from `(137, -4)` | `app/api/routes.py:342` | Wrong cells for legacy 320×128 raster (100 px/deg) and completely wrong for the NASA 463 m projected grid. |
| D2 | `/api/terrain` samples projected-lon/lat as if they were CRS coordinates of the new raster | `app/api/routes.py:264` with dataset rasters | Would return `null` everywhere once the dataset is wired without a coordinate transform. |
| D3 | `0.0` treated as missing | `app/api/routes.py:251` | Valid zero slope reported as `null`. |
| D4 | `_load_raster` returns a closed handle | `app/api/routes.py:335-339` | Misleading API; reinforces the pattern of keeping file handles in response paths. |
| D5 | NaN NoData masked with `masked_equal` and `np.isnan` on a value only when `nodata is not None` | `app/data_pipeline/raster_loader.py:209,229` | NaN cells leak into statistics; `data.mask` is scalar `False` for NaN masks. |
| D6 | Route and mission handlers never consult the coverage mask | `app/api/routes.py:355-404`, `500-599` | Class-2 / unknown cells are treated as fully usable and safe (violates "unknown is never zero-cost"). |
| D7 | `/api/datasets` route shadows the imported catalog getter | `app/api/routes_v2.py:55` | Infinite recursion. |
| D8 | Catalog getter never rebuilds | `app/data_pipeline/catalog.py:288` | Empty catalog. |
| D9 | Discovery scans legacy `data/`, not the handover package | `app/data_pipeline/catalog.py:88`, `ingestion.py` | Dataset status endpoint cannot see the real products. |
| D10 | `imagery_service.get_layer_catalog` uses nonexistent `layer.metadata` | `app/services/imagery_service.py:348` | `AttributeError` when filtering by region. |
| D11 | Static mount covers only `data/processed` | `app/main.py:50` | Real overlay PNGs are unreachable. |
| D12 | `/mission/return` hardcodes a base | `app/api/routes.py:624` | Feasibility is not tied to the planned mission. |
| D13 | `/route/reroute` always returns 503 | `app/api/routes.py:722` | Emergency workflow cannot be demonstrated. |
| D14 | Assistant returns a constant string | `app/api/routes.py:751` | No tool use, no evidence, no model fallback. |
| D15 | Report contains no mission data | `app/api/routes.py:789` | Report is not evidence-based. |
| D16 | Tile proxy test requires live internet | `tests/test_api.py:24` | Test suite not hermetic. |

---

## 5. Integration plan (applied after this audit)

1. **Config & path resolution** – add `DHRUVION_DATA_DIR` plus a candidate list
   (`DHRUVION_DATA_DIR` → repo `DHRUVION_DATA` → `data/source_packages/nasa_dataset_package_2026/DHRUVION_DATA`
   → `Dhruvion-main/...`). Add LLM settings (`OLLAMA_BASE_URL`, `LLM_MODEL`, timeouts,
   feature flag). No absolute paths in code.
2. **Terrain service** – cache raster arrays; transform planetocentric lon/lat to the
   raster CRS with `rasterio.warp.transform` (source `+proj=longlat +R=3396190`), inverse
   affine sampling; enforce coverage classes 0/1/2; NaN-safe; expose unit, source,
   coverage class, availability, `OBSERVED`/`DERIVED`, limitations.
3. **Hazard, routing, missions** – deterministic A* on the real grid, coverage-aware
   costs (unknown is expensive, never free), real start/base registry, reroute with a
   simulated blockage buffer, time-budget feasibility with explicit assumptions.
4. **Environment services** – REMS and RAD loaders from the supplied JSON; `all_valid_values`
   default; circular wind statistics; wind marked `insufficient_data`; detectors B/E
   separate; `qc_placeholder` explicitly not a quality flag.
5. **Catalog & layers** – dataset catalog built from present files and package metadata;
   layer catalog driven by the same service; CTX overlay with metadata bounds and DN note;
   static mount for the package `processed/` directory.
6. **AI agent** – Ollama provider (tools) with availability check, timeout, bounded
   context, real tool registry backed by the deterministic services, grounding check, and
   a deterministic degraded mode when the model is unavailable. Structured response
   (answer, tools used, observations, sources, units, recommendations, warnings,
   limitations, confidence explanation).
7. **Frontend** – metadata-driven map bounds, CTX/terrain overlays, dataset and
   environment/radiation panels, assistant structured rendering, typed API client.
8. **Verification** – dataset integration tests, AI tool/endpoint tests, mission tests,
   hermetic tile-proxy test, production frontend build.

---

## 6. Verification baseline (recorded before changes)

```powershell
cd backend
python -m pytest tests -q
# 11 passed
```

Environment checks:

```text
Python 3.13.7
fastapi 0.116.1 | pydantic 2.11.7 | rasterio 1.5.2 | numpy 2.2.6
pyproj: not installed
Ollama GET http://127.0.0.1:11434/api/tags -> 200, model qwen2.5-coder:3b (tools supported)
```

Package self-test report (`DHRUVION_DATA/reports/test_results.txt`): 26 passed.

---

## 7. Known limitations carried into the integration

- MOLA derivatives are ~463 m baseline products; they must never be presented as
  rover-scale slope or trafficability.
- Terrain and CTX grids are near-equivalent but not identical (max offset 12.078 m);
  overlays are displayed on their own metadata bounds.
- CTX PNG values are 8-bit DN, not reflectance, and cover a smaller AOI than the DEM.
- REMS/RAD are two/three historical sols at one location. No trend, forecast, live
  telemetry, spatial interpolation, or route-specific radiation prediction is supported.
- No verified science-target catalog or hazard raster is present. Those layers stay
  `UNAVAILABLE`; they are never filled with demo values.
- Travel speed remains an explicit planning assumption (default 60 m/min), not a
  rover-verified value.

## Mission management update
Persistent mission CRUD, coordinate validation, and mission-to-route/report integration were added. See docs/MISSION_MANAGEMENT_IMPLEMENTATION_REPORT.md.
