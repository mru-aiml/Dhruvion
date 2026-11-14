# DHRUVION --- System Architecture

## 1. Purpose

This document defines the proposed implementation architecture for the
DHRUVION hackathon prototype. It complements `prd.md` and the visual/UI
requirements in `design.md`. The architecture favors a small, testable
modular monolith over distributed services because the project has a
short build window and a four-person team.

## 2. Architectural principles

1.  **Map-first and geospatially correct:** all spatial layers and route
    geometries must share an explicitly defined spatial reference or be
    transformed before overlay.
2.  **Deterministic core:** raster processing, hazard scoring, route
    search, and feasibility calculations live in deterministic Python
    services.
3.  **LLM as interface, not authority:** the AI agent interprets
    requests, calls tools, and explains results; it does not calculate
    or fabricate geospatial facts.
4.  **Provenance by design:** source metadata and data status travel
    with every layer, feature, route, and report.
5.  **Missing data is unknown:** NoData is not a safe value and must not
    be coerced to zero.
6.  **One region first:** optimize for complete end-to-end coverage of a
    single selected demo region.
7.  **Replaceable adapters:** NASA source ingestion, map rendering, and
    LLM provider integrations should be replaceable without rewriting
    domain logic.

## 3. High-level topology

``` text
React + TypeScript UI
        |
        | HTTPS / JSON / GeoJSON
        v
FastAPI application
  ├── API routers + Pydantic schemas
  ├── Mission application services
  │    ├── Terrain service
  │    ├── Hazard/difficulty service
  │    ├── Science target service
  │    ├── Route planner
  │    ├── Mission feasibility service
  │    └── Report service
  ├── AI assistant orchestration
  │    └── allowlisted tools -> application services
  ├── Data access / repositories
  └── NASA data adapters + local dataset catalog
        |
        ├── Raster/vector files (GeoTIFF, GeoJSON)
        ├── Metadata manifests (JSON)
        └── SQLite (optional persistence)
```

The first release should run as one FastAPI process and one frontend
application. Raster files can remain on disk with a metadata catalog;
SQLite is optional for mission plans, saved routes, and report history.
Avoid introducing a message broker, microservices, Kubernetes, or a
separate vector database unless a concrete requirement appears.

## 4. Suggested repository structure

``` text
dhruvion/
├── README.md
├── prd.md
├── architecture.md
├── code_style.md
├── testing.md
├── agents.md
├── security.md
├── database.md
├── api.md
├── design.md
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── map/
│   │   │   ├── routes/
│   │   │   ├── science/
│   │   │   ├── mission/
│   │   │   └── common/
│   │   ├── features/
│   │   │   ├── overview/
│   │   │   ├── martian-map/
│   │   │   ├── route-planner/
│   │   │   ├── science-explorer/
│   │   │   ├── emergency/
│   │   │   ├── assistant/
│   │   │   └── reports/
│   │   ├── services/api/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── styles/
│   │   └── main.tsx
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── domain/
│   │   ├── repositories/
│   │   ├── data_adapters/
│   │   └── ai_agent/
│   ├── tests/
│   └── pyproject.toml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── vectors/
│   └── manifests/
├── scripts/
└── docs/
```

Keep raw source files immutable. Store processed outputs separately and
record their processing lineage.

## 5. Backend layers

### 5.1 API layer

FastAPI routers handle HTTP concerns only: - Parse and validate request
bodies/query parameters. - Apply request size and rate limits where
configured. - Call application services. - Return typed response schemas
and meaningful HTTP errors. - Avoid raster calculations or LLM prompts
inside route handlers.

### 5.2 Application services

Orchestrate use cases: - `TerrainService`: query raster values and layer
metadata. - `HazardService`: calculate documented derived
difficulty/hazard indicators. - `ScienceTargetService`: filter and
retrieve target records. - `RoutePlanningService`: construct
traversability costs and candidate paths. - `MissionFeasibilityService`:
calculate round-trip time budget. - `EmergencyService`: mark a segment
blocked and recalculate alternatives. - `ReportService`: assemble a
traceable mission summary. - `AssistantService`: orchestrate model
requests and allowlisted tools.

### 5.3 Domain logic

Pure functions and domain types should implement: - Coordinate
validation and conversion. - Distance and duration calculations. -
Terrain cost normalization. - Route cost and feasibility rules. -
Provenance/status transitions. - Mission-time calculations.

Domain logic should not depend on FastAPI, React, database drivers, or a
specific LLM provider.

### 5.4 Data adapters

Use adapters for: - NASA/PDS/USGS source discovery and downloads. -
Raster loading and reprojection. - GeoJSON target loading. - Local
filesystem or SQLite repositories. - LLM inference (e.g. local Ollama or
a configured hosted endpoint).

Each adapter must expose data availability and source metadata; failures
must not be hidden behind placeholder values.

## 6. Geospatial processing pipeline

1.  **Acquire:** download or obtain a source product from an
    authoritative source.
2.  **Register:** record dataset/instrument, product identifier, source
    URL, acquisition/processing dates if available, license/usage notes,
    resolution, coordinate reference system, and checksum.
3.  **Inspect:** verify bounds, nodata values, units, raster dimensions,
    and projection.
4.  **Normalize:** reproject/resample to a common analysis grid only
    when justified; record the transformation.
5.  **Derive:** calculate slope/roughness or other indicators from
    documented inputs.
6.  **Classify:** generate hazard/difficulty outputs with explicit
    formula and thresholds.
7.  **Publish:** expose layer metadata and renderable map data.
8.  **Validate:** compare extents, nodata masks, units, and sample
    values before the UI treats the layer as available.

Mars coordinate reference systems are not interchangeable with Earth CRS
assumptions. Choose a Mars-appropriate projection/datum for the region
and record it in the dataset manifest. Do not assume that Leaflet
defaults, Web Mercator, or terrestrial basemaps are correct for Mars.

## 7. Route-planning design

Represent the traversable analysis area as a grid or graph. Each
traversable cell/node has a cost derived from distance and documented
terrain difficulty. For adjacent cells:

`edge_cost = distance_m * (1 + lambda * normalized_risk)`

where `lambda` controls the penalty for terrain difficulty. Exclude
cells explicitly classified as impassable. Cells with missing required
data should be marked unknown and handled by a conservative,
configurable policy; never silently treat them as safe.

Use A\* for route search where the heuristic is compatible with the cost
model. Use a distance lower bound as the heuristic when it remains
admissible. If the implementation uses a non-admissible heuristic or
heuristic weights, do not claim guaranteed optimality.

Return three strategies: - **Shortest:** minimize geometric distance
subject to hard constraints. - **Safest-estimated:** minimize the
documented terrain-risk cost subject to hard constraints. -
**Balanced:** combine distance and terrain penalty with a documented
weight.

The route API should return geometry, distance, estimated duration,
terrain summary, hazard count, provenance, warnings, and
algorithm/configuration metadata.

## 8. Mission feasibility

Use:

`T_total = T_outbound + T_exploration + T_return + T_reserve`

The feasibility service must: - Calculate outbound and return durations
using documented assumptions. - Include exploration duration. - Include
an explicit reserve. - Compare total time with the mission limit. -
Return `FEASIBLE`, `CAUTION`, `NOT_FEASIBLE`, or `UNVERIFIED`. - Explain
which component or missing input determines the status.

A missing return route or unknown travel assumption must not produce a
positive feasibility status.

## 9. AI assistant architecture

The LLM is an orchestration and explanation layer: 1. Receive user
question and a bounded mission context. 2. Classify intent and identify
required information. 3. Select only allowlisted application tools. 4.
Validate tool arguments. 5. Execute tools through application services.
6. Build a compact evidence bundle from actual tool responses. 7. Ask
the model to explain the bundle in structured form. 8. Validate the
response and return it with tool activity, sources, warnings, and
permitted UI actions.

Initial tools: - `get_terrain_info` - `get_hazards` -
`find_science_targets` - `calculate_routes` -
`check_mission_feasibility` - `request_emergency_reroute` -
`generate_mission_report`

Do not allow arbitrary code execution, shell access, unrestricted SQL,
arbitrary URL fetching, or direct file-system access from the model. If
the model is unavailable, the rest of the application must remain
usable.

## 10. Frontend architecture

Use React, Vite, TypeScript, and Tailwind CSS. Use a Mars-capable map
rendering strategy that supports the selected projection and layer
format; validate the chosen map library against the actual coordinate
system before committing. Use a typed API client and keep server state
separate from local UI state.

Primary routes: - `/overview` - `/map` - `/routes` - `/science` -
`/emergency` - `/assistant` - `/reports` - `/settings`

The map, selected route card, route detail panel, and feature inspector
must share consistent identifiers and state. The frontend displays
backend calculations; it must not independently invent risk or
feasibility values.

## 11. Observability and errors

-   Assign a request ID to each API request.
-   Log service errors with request ID and relevant safe metadata.
-   Do not log secrets, access tokens, or full sensitive prompts.
-   Return structured errors with stable error codes.
-   Distinguish `unavailable`, `no_data`, `invalid_input`,
    `processing_error`, and `internal_error`.
-   Expose a health endpoint that checks application readiness without
    leaking environment details.

## 12. Deployment

For the hackathon, deploy frontend and backend separately or serve the
built frontend through a static host. Configure the backend base URL
through environment variables. Keep NASA source files and generated
raster artifacts in a storage location accessible to the backend. Do not
commit large source datasets, credentials, or generated secrets to Git.

## 13. Architecture decisions to confirm during implementation

-   Exact Mars projection/datum and coordinate convention for the
    selected region.
-   Raster analysis grid resolution and resampling method.
-   Which source layers have verified coverage.
-   Whether SQLite persistence is needed for the demo.
-   Exact map renderer and tile/raster serving strategy.
-   LLM provider/model and whether tool calling is native or
    orchestrated by application code.
-   Whether reports are generated as HTML/print view or PDF.
