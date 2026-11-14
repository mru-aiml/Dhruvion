# DHRUVION --- Code Style and Engineering Conventions

## 1. General rules

-   Prefer readable, explicit code over clever abstractions.
-   Keep functions small and focused on one responsibility.
-   Use strict typing at API and domain boundaries.
-   Keep deterministic calculations independent of UI and LLM code.
-   Do not commit secrets, local datasets, build artifacts, or
    machine-specific configuration.
-   Follow existing repository conventions if they are more specific
    than this document.

## 2. Repository and naming

  -----------------------------------------------------------------------------
  Item                    Convention              Example
  ----------------------- ----------------------- -----------------------------
  Python modules          `snake_case.py`         `route_planner.py`

  Python classes          `PascalCase`            `MissionFeasibilityService`

  Python                  `snake_case`            `calculate_return_time`
  functions/variables                             

  Constants               `UPPER_SNAKE_CASE`      `DEFAULT_RESERVE_MINUTES`

  React components        `PascalCase.tsx`        `RouteComparisonCard.tsx`

  React hooks             `use` + `camelCase`     `useMissionContext.ts`

  TypeScript              `camelCase`             `fetchRouteOptions`
  variables/functions                             

  Types/interfaces        `PascalCase`            `RouteOption`

  CSS classes             Tailwind utilities;     ---
                          extract repeated        
                          patterns                

  API paths               lowercase               `/api/routes`
                          plural/noun-oriented    
                          where practical         

  Environment variables   `UPPER_SNAKE_CASE`      `NASA_DATA_DIR`
  -----------------------------------------------------------------------------

Use descriptive names. Avoid ambiguous abbreviations except established
units and geospatial terms.

## 3. Python conventions

-   Target the Python version declared in `pyproject.toml`; use Python
    3.11+ if the environment permits.
-   Use type hints for public functions, service methods, and Pydantic
    schemas.
-   Use Pydantic models for external input/output contracts.
-   Use `pathlib.Path` rather than manual path concatenation.
-   Use `logging`; do not use `print()` for application diagnostics.
-   Raise domain-specific exceptions and translate them to HTTP
    responses at the API boundary.
-   Avoid broad `except Exception` unless the exception is logged and
    safely re-raised/translated.
-   Keep raster handles and file resources inside context-managed
    scopes.
-   Do not mutate source rasters; write derived outputs to a separate
    processed directory.
-   Document units and CRS in variable names, schema descriptions, or
    metadata.
-   Use `Decimal` only when exact decimal arithmetic is required;
    ordinary geospatial calculations should use appropriate
    floating-point types and explicit tolerances.

Suggested formatting/linting: - Ruff for linting and formatting. -
Pyright or mypy for static type checking. - Pytest for tests.

## 4. TypeScript and React conventions

-   Enable `strict: true` in TypeScript.
-   Avoid `any`; use `unknown` at untrusted boundaries and validate
    before use.
-   Define API response types in a shared `types` or generated schema
    layer.
-   Use function components and hooks.
-   Keep components presentational where possible; move data fetching
    and orchestration into feature hooks/services.
-   Avoid giant page components; split map controls, layer panels,
    inspectors, route cards, and status components.
-   Keep reusable components free of feature-specific API assumptions.
-   Use stable keys for rendered lists.
-   Handle loading, empty, unavailable, and error states explicitly.
-   Keep map state and route-selection state synchronized through a
    single owner/store.
-   Do not calculate backend risk or mission feasibility values in the
    browser.
-   Use semantic HTML and accessible labels; do not rely on color alone.

Suggested tools: - ESLint. - Prettier. - TypeScript compiler
(`tsc --noEmit`). - Vitest and React Testing Library.

## 5. API and schema conventions

-   Use Pydantic request/response models.
-   Use ISO 8601 timestamps with timezone information when a timestamp
    exists.
-   Include units in field names or schema descriptions,
    e.g. `distance_m`, `duration_min`, `elevation_m`.
-   Use a consistent coordinate representation and document the
    coordinate reference system.
-   Use enums for provenance and feasibility states.
-   Keep error response shapes consistent.
-   Version breaking API changes or coordinate them with frontend owners
    before merging.

## 6. Geospatial conventions

-   Never mix coordinate systems without an explicit transformation.
-   Document Mars body, datum, projection, axis order, units, and
    coordinate convention.
-   Keep raster CRS, bounds, transform, nodata, and resolution in
    metadata.
-   Validate alignment before cell-by-cell raster operations.
-   Preserve NoData masks through calculations.
-   Use metric units internally where source data supports conversion.
-   Do not assume pixel indices are geographic coordinates.
-   Use explicit suffixes such as `_m`, `_km`, `_deg`, `_min`, `_s`, and
    `_pct`.
-   Explain whether route distance is planar, geodesic, or grid-derived.

## 7. Data and provenance conventions

Every published layer or derived result should carry: - `status`:
`observed`, `derived`, `simulated`, or `unavailable`. - `source_name`
and dataset/instrument identifiers when verified. - `source_uri` where
available. - `acquired_at` / `processed_at` only when known. -
`resolution` and `crs` where applicable. - `method` and `parameters` for
derived products. - `warnings` for limitations or incomplete coverage.

Never fabricate provenance to make a UI card look complete.

## 8. Comments and documentation

-   Explain why, not what, when code is non-obvious.
-   Document formulas, thresholds, route cost weights, assumptions, and
    limitations.
-   Add docstrings to public service functions and complex algorithms.
-   Keep README setup commands synchronized with actual scripts and
    environment variables.
-   Update `api.md` whenever endpoint contracts change.
-   Update `database.md` whenever persisted entities or migrations
    change.

## 9. Git workflow

Suggested branch pattern: - `main`: stable demo branch. -
`feat/<short-name>`: feature work. - `fix/<short-name>`: bug fixes. -
`docs/<short-name>`: documentation.

Commit messages: - `feat: add route comparison endpoint` -
`fix: preserve nodata in slope calculation` -
`docs: define assistant tool contract` -
`test: cover return feasibility boundaries`

Before merging: 1. Run formatter and linter. 2. Run type checks. 3. Run
relevant unit and integration tests. 4. Verify API schema compatibility.
5. Review provenance and security implications. 6. Confirm the frontend
has no inert controls or fabricated values.

## 10. UI design implementation rules

Use `design.md` as the source of truth for the visual system. Core
palette: - Canvas `#101216` - Surface 1 `#191E25` - Surface 2
`#222832` - Surface 3 `#2B333E` - Mars orange `#E56A3A` - Amber
`#F4B544` - Cyan `#55C7D9` - Safe green `#65B88A` - Warning amber
`#EAB45B` - Critical red `#E45C5C` - Primary text `#F3F1ED` - Secondary
text `#9AA5B1` - Muted text `#687482` - Lines `#343C47`

Use Inter, IBM Plex Sans, or Manrope. Use tabular numerals for
coordinates, distances, durations, percentages, and telemetry. Prefer
borders over heavy shadows. Do not introduce neon/glassmorphism or
decorative HUD elements that reduce legibility.

## 11. Definition of done

A change is done when: - It satisfies the acceptance criteria in the
related issue/PRD requirement. - Types and validation are updated. -
Loading, empty, error, and unavailable states are considered. -
Provenance and units are preserved. - Tests pass. - No secrets or
unverified source claims are introduced. - Relevant docs and API
contracts are updated.
