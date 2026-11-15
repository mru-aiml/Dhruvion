# DHRUVION --- API Contract

## 1. API conventions

**Base path:** `/api`\
**Transport:** HTTP(S), JSON; GeoJSON for spatial geometry.\
**Versioning:** add `/v1` before public release if breaking evolution is
expected.\
**Coordinate reference:** every spatial response must identify its CRS
and coordinate order. The selected Mars CRS must be agreed and verified
before implementation.

All numeric values must include documented units. Timestamps use ISO
8601 with timezone when known. Missing values are `null` or represented
through an explicit availability/status field; do not replace missing
data with zero.

## 2. Shared enums

``` json
{
  "provenance_status": ["observed", "derived", "simulated", "unavailable"],
  "availability": ["available", "partial", "unavailable", "stale"],
  "feasibility_status": ["feasible", "caution", "not_feasible", "unverified"],
  "route_strategy": ["shortest", "safest_estimated", "balanced"]
}
```

## 3. Shared response conventions

### Layer metadata

``` json
{
  "id": "mola_elevation",
  "name": "Elevation",
  "layer_type": "raster",
  "status": "observed",
  "availability": "available",
  "source": {
    "name": "Verified source product name",
    "provider": "NASA/PDS",
    "product_id": null,
    "source_uri": null
  },
  "crs": "Mars-specific CRS identifier",
  "resolution_m": null,
  "units": "m",
  "bounds": null,
  "acquired_at": null,
  "processed_at": null,
  "warnings": []
}
```

Use actual verified values. `null` above indicates a value that must be
populated only when verified, not a literal source claim.

### Standard error

``` json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The supplied coordinate is outside the supported region.",
    "details": {}
  },
  "request_id": "server-generated-id"
}
```

## 4. Endpoints

### `GET /api/health`

Returns service readiness.

**Response**

``` json
{
  "status": "ok",
  "service": "dhruvion-api",
  "version": "0.1.0"
}
```

Do not expose secrets, internal paths, or environment configuration.

### `GET /api/regions`

Returns supported regions.

**Response**

``` json
{
  "items": [
    {
      "id": "gale_crater",
      "name": "Gale Crater",
      "body": "Mars",
      "crs": "configured Mars CRS",
      "availability": "available"
    }
  ]
}
```

The region item must only be marked available when the required region
metadata/data exists.

### `GET /api/layers?region_id={region_id}`

Returns layer catalog and provenance.

**Response**

``` json
{
  "region_id": "gale_crater",
  "items": [
    {
      "id": "mola_elevation",
      "name": "Elevation / MOLA",
      "status": "observed",
      "availability": "available",
      "units": "m",
      "crs": "configured Mars CRS",
      "resolution_m": null,
      "source": {},
      "warnings": []
    }
  ]
}
```

### `GET /api/terrain`

Query terrain at a coordinate or within a bounded region.

**Query parameters** - `region_id` (required) - `x`, `y` or named
coordinate fields according to the declared convention (required for
point query) - `layer_ids` (optional comma-separated list)

**Response**

``` json
{
  "region_id": "gale_crater",
  "coordinate": {"x": 0, "y": 0, "crs": "configured Mars CRS"},
  "values": {
    "elevation_m": null,
    "slope_deg": null,
    "roughness": null
  },
  "provenance": [],
  "availability": "partial",
  "warnings": []
}
```

The example values are schema placeholders, not terrain measurements.

### `GET /api/hazards`

Returns hazard features or a hazard summary for a region/bounds.

**Query parameters** - `region_id` (required) - `bounds` (optional,
encoded according to API implementation)

**Response**

``` json
{
  "region_id": "gale_crater",
  "features": {
    "type": "FeatureCollection",
    "features": []
  },
  "summary": {
    "identified_count": 0,
    "unknown_coverage": true
  },
  "provenance": [],
  "warnings": []
}
```

An empty feature collection does not mean the area is hazard-free;
include coverage/unknown metadata.

### `GET /api/targets`

Returns science targets.

**Query parameters** - `region_id` (required) - `feature_type`
(optional) - `priority_min` (optional) - `max_distance_m` (optional, if
origin is supplied) - `visited` (optional)

**Response**

``` json
{
  "region_id": "gale_crater",
  "items": [
    {
      "id": "target-example",
      "name": "Example target",
      "feature_type": null,
      "geometry": {"type": "Point", "coordinates": [0, 0]},
      "coordinate_crs": "configured Mars CRS",
      "priority": null,
      "description": null,
      "interpretation": null,
      "provenance": [],
      "warnings": []
    }
  ]
}
```

Example target is a schema placeholder; do not seed it as a real target
without evidence.

### `POST /api/route/optimize`

Calculates candidate route strategies.

**Request**

``` json
{
  "region_id": "gale_crater",
  "start": {"x": 0, "y": 0, "crs": "configured Mars CRS"},
  "destination": {"x": 1, "y": 1, "crs": "configured Mars CRS"},
  "strategies": ["shortest", "safest_estimated", "balanced"],
  "max_difficulty": null,
  "risk_weight": 1.0,
  "travel_speed_m_per_min": null
}
```

**Response**

``` json
{
  "region_id": "gale_crater",
  "routes": [
    {
      "id": "route-id",
      "strategy": "shortest",
      "geometry": {"type": "LineString", "coordinates": []},
      "distance_m": 0,
      "estimated_duration_min": null,
      "terrain_difficulty": null,
      "hazard_count": null,
      "feasibility_status": "unverified",
      "rationale": "",
      "provenance": [],
      "warnings": []
    }
  ],
  "algorithm": {
    "name": "A*",
    "version": "implementation-version",
    "cost_model": {}
  }
}
```

Return only strategies actually calculated. If a strategy cannot be
computed, return an explicit per-strategy error/status rather than
inventing a route.

### `POST /api/mission/plan`

Creates or evaluates a mission plan.

**Request**

``` json
{
  "mission_id": null,
  "region_id": "gale_crater",
  "start": {"x": 0, "y": 0, "crs": "configured Mars CRS"},
  "destination": {"x": 1, "y": 1, "crs": "configured Mars CRS"},
  "time_limit_min": 240,
  "exploration_time_min": 30,
  "reserve_time_min": 30,
  "travel_speed_m_per_min": null,
  "route_strategy": "balanced"
}
```

**Response**

``` json
{
  "mission_id": "generated-id",
  "route": {},
  "time_budget": {
    "outbound_min": null,
    "exploration_min": 30,
    "return_min": null,
    "reserve_min": 30,
    "total_min": null,
    "limit_min": 240
  },
  "feasibility_status": "unverified",
  "reasons": [],
  "assumptions": [],
  "warnings": []
}
```

### `POST /api/mission/return`

Evaluates return-to-base feasibility for an existing mission/route.

**Request**

``` json
{
  "mission_id": "mission-id",
  "current_location": {"x": 1, "y": 1, "crs": "configured Mars CRS"},
  "remaining_time_min": 90,
  "reserve_time_min": 20
}
```

**Response**

``` json
{
  "return_route": {},
  "estimated_return_min": null,
  "remaining_time_min": 90,
  "reserve_time_min": 20,
  "feasibility_status": "unverified",
  "reasons": [],
  "warnings": []
}
```

### `POST /api/route/reroute`

Recalculates a route after a blocked segment or simulated obstruction.

**Request**

``` json
{
  "mission_id": "mission-id",
  "original_route_id": "route-id",
  "blocked_geometry": {"type": "Point", "coordinates": [0, 0]},
  "scenario_status": "simulated",
  "remaining_time_min": 90
}
```

**Response**

``` json
{
  "original_route_id": "route-id",
  "alternative_route": {},
  "distance_delta_m": null,
  "duration_delta_min": null,
  "feasibility_status": "unverified",
  "scenario_status": "simulated",
  "reason": "",
  "provenance": [],
  "warnings": []
}
```

The server must not treat a client-supplied `scenario_status` as proof
of an observed event. Validate allowed scenario types and preserve the
simulated label.

### `POST /api/assistant/ask`

Runs the mission-aware assistant.

**Request**

``` json
{
  "message": "Can I reach this target and return within the time limit?",
  "mission_id": "mission-id",
  "context": {
    "region_id": "gale_crater",
    "selected_route_id": null
  }
}
```

**Response**

``` json
{
  "message": "Structured, evidence-grounded explanation.",
  "intent": "mission_feasibility",
  "recommendation": {},
  "tool_activity": [
    {"tool": "check_mission_feasibility", "status": "completed"}
  ],
  "evidence": [],
  "warnings": [],
  "sources": [],
  "actions": []
}
```

Tool activity must reflect real calls only. Do not include
model-generated source references unless returned by trusted backend
data.

### `POST /api/mission/report`

Generates a mission report.

**Request**

``` json
{
  "mission_id": "mission-id",
  "format": "html"
}
```

**Response**

``` json
{
  "report_id": "generated-id",
  "format": "html",
  "status": "generated",
  "download_url": null,
  "provenance": [],
  "warnings": []
}
```

Only return a download URL if the report was actually generated and the
URL is accessible to the requester.

## 5. HTTP status codes

  Status   Meaning
  -------- --------------------------------------------------
  200      Successful read or calculation
  201      Resource created
  202      Accepted asynchronous processing, if implemented
  400      Invalid request semantics
  404      Unknown region/layer/mission/target
  413      Payload too large
  422      Schema or validation error
  429      Rate limit exceeded
  500      Unexpected server error
  503      Required data/model/service unavailable

## 6. API implementation rules

-   Publish OpenAPI from FastAPI and keep it aligned with this contract.
-   Use typed Pydantic schemas for all request and response bodies.
-   Keep CRS and coordinate order explicit.
-   Include provenance and warnings on data-dependent responses.
-   Return `UNVERIFIED` when required inputs are missing.
-   Never return placeholder example coordinates or values as real data.
-   Keep error responses consistent and avoid stack traces.
-   Add request IDs and log safe diagnostics.
-   Update this document whenever a contract changes.
