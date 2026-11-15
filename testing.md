# DHRUVION --- Testing Strategy

## 1. Purpose

Testing must protect the reliability of the geospatial pipeline, route
calculations, mission-time assessment, API contracts, and UI
synchronization. Because this is a hackathon prototype, prioritize
high-value tests around the core demonstration rather than broad but
shallow coverage.

## 2. Test levels

### Unit tests

Test pure functions and isolated components: - Coordinate validation and
conversion. - Raster nodata handling and alignment checks. -
Slope/roughness derivation on small known arrays. - Risk normalization
and weighted scoring. - Route edge costs and path reconstruction. -
Distance and duration calculations. - Mission feasibility boundaries. -
Provenance/status serialization. - API schema validation. - UI
components for status badges, route cards, and layer controls.

### Integration tests

Test services and API boundaries together: - Load a known test raster
and query terrain at known cells. - Verify layer metadata and
provenance. - Generate a route through a small synthetic cost grid. -
Ensure blocked cells are avoided. - Ensure unknown cells are not treated
as safe. - Calculate outbound + exploration + return + reserve
feasibility. - Simulate an obstruction and verify an alternate path is
returned or a clear no-route result is produced. - Verify AI tool
orchestration calls only the expected backend services. - Verify reports
include the exact source and simulation labels returned by services.

### End-to-end tests

Test the primary user journey: 1. Open Mission Overview. 2. Navigate to
Martian Map. 3. Toggle a supported terrain layer and inspect a feature.
4. Select start and target. 5. Compare route options. 6. Select a route
and review return feasibility. 7. Trigger the simulated blocked-route
scenario. 8. Generate an alternative route. 9. Ask the AI assistant to
explain the reroute. 10. Open and export the mission report.

### Manual acceptance tests

Run the full demo on the actual presentation machine and browser. Verify
map rendering, font loading, API connectivity, responsiveness, and
failure states with the network disconnected.

## 3. Critical geospatial test cases

-   CRS mismatch is rejected or explicitly transformed; it is never
    silently ignored.
-   Raster bounds, affine transform, resolution, and dimensions are
    validated.
-   Nodata masks survive reprojection and derived calculations.
-   Slope values are within expected mathematical bounds for the chosen
    method.
-   Roughness calculation is deterministic for a fixed input window.
-   A raster with all nodata returns unavailable/unknown, not zero risk.
-   Route geometry remains inside allowed bounds.
-   Route coordinates are serialized in the documented order and CRS.
-   Route distance is consistent with the selected distance method
    within a documented tolerance.
-   A blocked cell is never included in a returned route.
-   A missing layer is reported as unavailable and does not produce a
    falsely favorable route score.

Use small synthetic fixtures with known expected results. Avoid making
every test depend on downloading NASA data.

## 4. Route-planning tests

Test: - Start equals destination. - Valid direct path. - Obstacle forces
a detour. - No possible path. - Boundary start/destination. - Invalid
coordinates. - All cells blocked. - Unknown cells intersect a candidate
path. - Different lambda/risk weights produce expected trade-offs. -
Shortest route minimizes distance under constraints. - Safest-estimated
route minimizes the configured risk cost. - Balanced route uses the
documented combined cost. - A\* heuristic is admissible if optimality is
claimed. - Tie-breaking is deterministic.

Do not assert a route is absolutely safe. Assert only the behavior of
the documented cost model.

## 5. Mission feasibility tests

Given: `T_total = T_outbound + T_exploration + T_return + T_reserve`

Test: - Total less than time limit -\> `FEASIBLE`. - Total equals time
limit -\> expected boundary policy, documented explicitly. - Total
exceeds time limit -\> `NOT_FEASIBLE`. - Near-limit buffer -\> `CAUTION`
according to configured threshold. - Missing return route -\>
`UNVERIFIED`. - Missing required speed/duration input -\>
`UNVERIFIED`. - Negative, zero, NaN, or infinite durations are
rejected. - Reserve is always included and is visible in the response. -
Unit conversion does not change feasibility unexpectedly.

## 6. AI assistant tests

-   A question requiring terrain information triggers the terrain tool.
-   A question requiring a route triggers route calculation.
-   A return question triggers feasibility calculation with return and
    reserve.
-   An emergency question does not claim rerouting before the reroute
    tool succeeds.
-   Tool arguments are schema-validated.
-   Unknown tools are rejected.
-   Prompt injection in user text or retrieved data cannot grant new
    tools or permissions.
-   Model output is validated against a structured response schema.
-   Unsupported claims are removed or returned as unknown with a
    warning.
-   If the model is offline, deterministic UI workflows still work.
-   Tool activity shown in the UI matches actual tool calls.
-   Model responses never fabricate dataset identifiers, source
    citations, or telemetry.

Mock the LLM for deterministic tests; use a small number of manual
integration checks with the configured model.

## 7. API tests

-   Valid request and response schema.
-   Invalid field types and missing required fields.
-   Invalid coordinate ranges for the declared coordinate convention.
-   Unknown region/layer/target IDs.
-   Missing files and unavailable data.
-   Large request body rejection.
-   Consistent error codes and request IDs.
-   CORS behavior for approved frontend origins.
-   No internal stack traces or secrets in client-visible errors.
-   OpenAPI schema matches `api.md`.

## 8. Frontend tests

-   Sidebar routes navigate to the correct screen.
-   Layer toggle changes map visibility and legend together.
-   Selecting a target opens the matching inspector.
-   Selecting a route card highlights the matching route geometry.
-   Route summary and map use the same route ID.
-   Feasibility states show text/icon as well as color.
-   Simulated scenarios show a visible simulation label.
-   Loading, empty, unavailable, error, and unverified states render
    correctly.
-   Keyboard navigation and visible focus work for core controls.
-   Map controls have accessible names.
-   Layout remains usable at desktop, tablet, and mobile breakpoints.
-   Reduced-motion preference is respected.

## 9. Suggested tooling

Backend: - `pytest` - `pytest-cov` - `httpx` / FastAPI `TestClient` -
Small in-memory NumPy arrays and temporary GeoTIFF fixtures - Ruff and
Pyright/mypy

Frontend: - Vitest - React Testing Library - Playwright for a short
critical-path E2E suite - ESLint and TypeScript compiler

## 10. Test data policy

-   Keep small synthetic fixtures in `tests/fixtures`.
-   Do not commit large NASA source files to the test suite.
-   For each external sample, record source and usage constraints.
-   Tests must not require network access by default.
-   Provide a separate optional integration command for external data
    checks.
-   Never use simulated data in tests without naming it as simulated.

## 11. Release gate

Before the demo: - Backend unit and integration tests pass. - Frontend
type check and tests pass. - The end-to-end demo path has been completed
at least once. - The selected map region, projection, units, and data
sources are verified. - All simulated values and events are visibly
labelled. - No known route or feasibility bug remains in the demo
scenario. - Application still opens if the LLM provider is unavailable.
