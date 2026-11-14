# DHRUVION --- Team Roles and AI Coding-Agent Instructions

## 1. Project context

DHRUVION is a map-first AI-powered Martian mission-planning prototype
for the NASA Space Apps Challenge. The team has four primary
workstreams: data science/geospatial data, backend, frontend, and AI
agent orchestration. The build window is approximately 24 hours, so work
must be parallelized around stable contracts.

**Product tagline:** Navigate Mars. Understand the Terrain. Protect
Every Mission.

## 2. Team ownership

### Agent / Member 1 --- Data Scientist and Geospatial Data Lead

**Owns:** NASA data discovery, download, preprocessing, raster
alignment, terrain derivation, hazard inputs, science target dataset,
and provenance manifests.

Deliverables: - Verified source data for the selected region. -
Elevation raster (e.g. `elevation.tif`) where available. - Derived slope
and roughness rasters where valid. - Hazard/difficulty layer with
documented method and limitations. - Science target GeoJSON. -
`metadata.json` / layer manifest. - Sample values and validation notes.

Rules: - Verify source product, coverage, resolution, units, CRS,
nodata, and usage conditions. - Keep raw data immutable. - Never fill
missing values with zero risk. - Do not claim a layer is NASA-provided
if it is derived by the team. - Communicate exact CRS, bounds,
resolution, units, and filenames to backend early.

### Agent / Member 2 --- Backend Developer

**Owns:** FastAPI service, data access, route planner, mission
feasibility, emergency reroute, report API, validation, and integration.

Deliverables: - Health, region, layer, terrain, hazard, target, route,
feasibility, reroute, report, and assistant endpoints. - Pydantic
request/response models. - Deterministic domain services. - API tests
and OpenAPI contract. - Data loading and provenance propagation.

Rules: - Keep route/feasibility calculations deterministic. - Preserve
NoData and source metadata. - Do not place business logic in FastAPI
route handlers. - Publish API schemas early; notify frontend of breaking
changes.

### Agent / Member 3 --- Frontend Developer

**Owns:** React/Vite/TypeScript interface, design system, map workspace,
seven screens, API integration, responsive behavior, and accessibility.

Deliverables: - Mission Overview, Martian Map, Route Planner, Science
Explorer, Emergency Navigation, AI Mission Assistant, Mission Reports,
and Settings shell. - Shared layout, badges, cards, layer controls,
route comparison, inspector, and error states. - Typed API client. -
Working navigation and core demo flow.

Rules: - Use `design.md` as the UI source of truth. - Do not invent
terrain values, route geometry, feasibility, or NASA provenance. - Keep
map and route card selection synchronized. - Use explicit
unavailable/simulated states. - Do not leave decorative controls
pretending to work.

### Agent / Member 4 --- AI Agent Developer

**Owns:** mission-aware assistant, tool schemas, intent routing,
structured responses, prompt design, tool activity transparency, and
assistant integration.

Deliverables: - Assistant service and structured response schema. -
Allowlisted tools wired to backend services. - Evidence bundle and
source propagation. - Failure handling when model/tool is unavailable. -
Tests for tool selection and unsupported claims.

Rules: - LLM interprets and explains; backend computes. - No arbitrary
shell, SQL, filesystem, or unrestricted URL tools. - Tool calls must be
real and visible activity must reflect actual calls. - Never fabricate
data, citations, telemetry, confidence, or tool results. - Keep model
context bounded and avoid sending unnecessary data.

## 3. Shared ownership and integration

The backend owns canonical API contracts. The data lead owns the dataset
manifest and spatial metadata. The frontend owns UI state and rendering.
The AI developer owns assistant orchestration but calls the same backend
services as the UI.

Agree early on: - Region identifier. - Coordinate convention and CRS. -
Raster bounds, resolution, and nodata policy. - Units. - Layer IDs and
provenance schema. - Route and feasibility response schemas. - Simulated
emergency scenario identifier. - Demo mission parameters.

Do not let each workstream invent its own coordinate order, units, IDs,
or status labels.

## 4. Suggested 24-hour execution plan

### Phase A --- First 2 hours: contract and skeleton

-   Confirm demo region and source coverage.
-   Create repository and app skeleton.
-   Agree on CRS, layer manifest, API types, and naming.
-   Frontend builds shell and map placeholder with explicit prototype
    label.
-   Backend returns health and static region/layer metadata.
-   AI developer defines tool interfaces and structured response schema.

### Phase B --- Hours 2--8: core data and route workflow

-   Data lead prepares one usable elevation/terrain source and metadata.
-   Backend implements terrain access, route search, and feasibility.
-   Frontend connects map/layer controls and route planner.
-   AI developer connects route and terrain tools.
-   Integrate continuously; do not wait for all work to finish.

### Phase C --- Hours 8--14: complete mission journey

-   Add science targets where verified.
-   Add hazard/difficulty derivation.
-   Implement emergency rerouting simulation.
-   Implement AI evidence-based explanation.
-   Build report summary.

### Phase D --- Hours 14--19: validation

-   Run route and feasibility edge tests.
-   Verify projection and layer alignment.
-   Check missing-data behavior and provenance.
-   Complete primary E2E flow.
-   Fix cross-team contract mismatches.

### Phase E --- Hours 19--24: demo hardening

-   Freeze features.
-   Prepare one rehearsed scenario and fallback.
-   Verify deployment, API URLs, and local backup.
-   Remove unsupported claims and fake telemetry.
-   Rehearse concise explanation of data, method, limitations, and
    impact.

## 5. AI coding-agent operating rules

Any coding agent (Codex, OpenCode, Cline, Antigravity, or similar)
must: 1. Read `README.md`, `prd.md`, `architecture.md`, `design.md`, and
the relevant specialized docs before changing code. 2. Inspect the
existing repository before creating or overwriting files. 3. State the
intended files and plan briefly before large changes. 4. Work only
within the assigned ownership area unless asked to integrate. 5.
Preserve existing working behavior. 6. Avoid replacing real data with
hardcoded mock data. 7. Label unavoidable demo data as simulated. 8. Add
or update tests for changed behavior. 9. Update API/database/docs when
contracts change. 10. Run the relevant tests, type checks, and lint
commands. 11. Report exact changed files, commands run, results, known
gaps, and manual steps. 12. Never claim tests passed unless they were
actually run.

## 6. Parallel work and merge discipline

-   Create a shared API contract before parallel implementation.
-   Assign clear file ownership to avoid simultaneous edits to the same
    files.
-   Merge small changes frequently.
-   Keep `main` runnable.
-   Integrate against mocks only until real service contracts are
    available; remove or clearly isolate mocks before final demo.
-   Use feature branches and descriptive commits.
-   Freeze API changes during final demo rehearsal unless a critical bug
    requires a coordinated change.

## 7. Demo fallback rules

If an optional dataset is unavailable, disable that layer and show
`UNAVAILABLE`; do not invent it. If live NASA access fails, use a
previously downloaded and verified dataset with its source metadata. If
the LLM fails, demonstrate the deterministic route and feasibility
workflow without pretending the assistant succeeded. If a map layer is
illustrative, label it `PROTOTYPE VISUALIZATION`.
