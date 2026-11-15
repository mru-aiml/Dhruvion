# DHRUVION --- Data Model and Database Design

## 1. Purpose and persistence strategy

DHRUVION is primarily a geospatial data application. Large raster
datasets should remain in file/object storage rather than being inserted
into relational tables. The relational database, if enabled, stores
mission configuration, layer catalog metadata, science target metadata,
saved route plans, reroute events, and report records.

For a 24-hour prototype, SQLite is sufficient for lightweight
persistence. The application must also support a file-backed/demo mode
if database setup would threaten the core workflow. The schema below is
a proposed logical model; create only the tables needed by implemented
features.

## 2. Storage categories

  -----------------------------------------------------------------------
  Data                                Storage
  ----------------------------------- -----------------------------------
  Original NASA raster products       Immutable file/object storage

  Processed GeoTIFF layers            File/object storage

  Science target geometry             GeoJSON initially; relational table
                                      optional

  Layer and source manifests          JSON and/or relational metadata

  Mission plans and settings          SQLite

  Saved route results                 SQLite or generated JSON

  Emergency scenario history          SQLite or generated JSON

  Reports                             HTML/PDF files with database
                                      metadata
  -----------------------------------------------------------------------

## 3. Core entities

### 3.1 `regions`

Represents a supported Martian study region.

  Field                     Type            Notes
  ------------------------- --------------- -----------------------------------
  `id`                      TEXT PK         Stable slug, e.g. `gale_crater`
  `name`                    TEXT            Display name
  `body`                    TEXT            `Mars`
  `crs`                     TEXT            Full CRS identifier/description
  `coordinate_convention`   TEXT            Axis order and units
  `bounds_json`             TEXT            Serialized bounds in declared CRS
  `description`             TEXT nullable   Region notes
  `created_at`              TEXT            ISO 8601 UTC

### 3.2 `data_sources`

Represents a verified source product or dataset record.

  Field               Type            Notes
  ------------------- --------------- ---------------------------------------
  `id`                TEXT PK         Internal stable ID
  `name`              TEXT            Dataset/instrument display name
  `provider`          TEXT            NASA/PDS/USGS/etc. only when verified
  `product_id`        TEXT nullable   Actual source product ID
  `source_uri`        TEXT nullable   Source landing/download URL
  `acquired_at`       TEXT nullable   Only if known
  `published_at`      TEXT nullable   Only if known
  `license_notes`     TEXT nullable   Usage constraints
  `checksum_sha256`   TEXT nullable   File integrity
  `metadata_json`     TEXT            Additional verified metadata

### 3.3 `layers`

Represents a map/analysis layer backed by a raster, vector, or tile
source.

  -----------------------------------------------------------------------------
  Field                   Type                    Notes
  ----------------------- ----------------------- -----------------------------
  `id`                    TEXT PK                 Stable layer ID

  `region_id`             TEXT FK                 Region

  `source_id`             TEXT FK nullable        Source product

  `name`                  TEXT                    Display name

  `layer_type`            TEXT                    `raster`, `vector`, `tiles`,
                                                  `derived`

  `status`                TEXT                    `observed`, `derived`,
                                                  `simulated`, `unavailable`

  `availability`          TEXT                    `available`, `partial`,
                                                  `unavailable`, `stale`

  `file_path`             TEXT nullable           Server-side path/key, never
                                                  client-controlled

  `format`                TEXT nullable           GeoTIFF, GeoJSON, etc.

  `crs`                   TEXT nullable           Layer CRS

  `resolution_m`          REAL nullable           If known

  `units`                 TEXT nullable           Elevation m, slope degrees,
                                                  etc.

  `nodata_value`          REAL nullable           Preserve mask semantics

  `bounds_json`           TEXT nullable           Bounds in declared CRS

  `processing_method`     TEXT nullable           For derived products

  `parameters_json`       TEXT nullable           Weights/thresholds/settings

  `processed_at`          TEXT nullable           When known

  `warnings_json`         TEXT                    Limitations and gaps
  -----------------------------------------------------------------------------

### 3.4 `science_targets`

Represents a geological/scientific target.

  ----------------------------------------------------------------------------
  Field                   Type                    Notes
  ----------------------- ----------------------- ----------------------------
  `id`                    TEXT PK                 Stable target ID

  `region_id`             TEXT FK                 Region

  `name`                  TEXT                    Target label

  `feature_type`          TEXT nullable           Geological feature category

  `longitude`             REAL                    Coordinate value under
                                                  declared convention

  `latitude`              REAL                    Coordinate value under
                                                  declared convention

  `coordinate_crs`        TEXT                    CRS of stored coordinate

  `priority`              REAL nullable           Project-defined score;
                                                  document scale

  `description`           TEXT nullable           Evidence-based description

  `interpretation`        TEXT nullable           Clearly distinguished from
                                                  observation

  `source_id`             TEXT FK nullable        Supporting source

  `provenance_status`     TEXT                    observed/derived/simulated

  `evidence_json`         TEXT                    Evidence references and
                                                  notes
  ----------------------------------------------------------------------------

### 3.5 `missions`

Represents a planned traverse/mission.

  Field                    Type            Notes
  ------------------------ --------------- ------------------------------------------
  `id`                     TEXT PK         UUID
  `name`                   TEXT            Mission name
  `region_id`              TEXT FK         Region
  `status`                 TEXT            draft/planned/active/completed/simulated
  `start_location_json`    TEXT            Coordinate and CRS
  `destination_json`       TEXT            Coordinate and CRS
  `time_limit_min`         REAL nullable   Mission time budget
  `exploration_time_min`   REAL nullable   Planned science stop time
  `reserve_time_min`       REAL nullable   Explicit reserve
  `objective`              TEXT nullable   Mission objective
  `created_at`             TEXT            ISO 8601 UTC
  `updated_at`             TEXT            ISO 8601 UTC

### 3.6 `route_plans`

Represents a computed candidate route.

  --------------------------------------------------------------------------------------------
  Field                     Type                    Notes
  ------------------------- ----------------------- ------------------------------------------
  `id`                      TEXT PK                 UUID

  `mission_id`              TEXT FK                 Parent mission

  `strategy`                TEXT                    shortest/safest_estimated/balanced

  `geometry_json`           TEXT                    GeoJSON geometry with CRS convention
                                                    documented

  `distance_m`              REAL                    Distance

  `outbound_duration_min`   REAL nullable           Estimated

  `return_duration_min`     REAL nullable           Estimated

  `terrain_difficulty`      REAL nullable           Project-defined scale

  `hazard_count`            INTEGER nullable        Only if computable

  `feasibility_status`      TEXT                    feasible/caution/not_feasible/unverified

  `cost_model_json`         TEXT                    Algorithm parameters

  `provenance_json`         TEXT                    Layers/sources used

  `warnings_json`           TEXT                    Limitations

  `created_at`              TEXT                    ISO 8601 UTC
  --------------------------------------------------------------------------------------------

### 3.7 `reroute_events`

Represents a route obstruction or alternative path event.

  Field                    Type               Notes
  ------------------------ ------------------ ---------------------------------
  `id`                     TEXT PK            UUID
  `mission_id`             TEXT FK            Mission
  `original_route_id`      TEXT FK nullable   Blocked route
  `alternative_route_id`   TEXT FK nullable   New route
  `event_type`             TEXT               obstacle/hazard/simulated_block
  `status`                 TEXT               observed/simulated
  `location_json`          TEXT               Obstruction location
  `reason`                 TEXT               Explanation
  `created_at`             TEXT               ISO 8601 UTC

### 3.8 `reports`

Stores report metadata; report content can remain in a file.

  Field               Type            Notes
  ------------------- --------------- ----------------------------
  `id`                TEXT PK         UUID
  `mission_id`        TEXT FK         Mission
  `format`            TEXT            html/pdf/json
  `file_path`         TEXT nullable   Server-side generated path
  `content_hash`      TEXT nullable   Integrity
  `provenance_json`   TEXT            Sources and status
  `created_at`        TEXT            ISO 8601 UTC

## 4. Relationships

``` text
regions 1 ─── * layers
regions 1 ─── * science_targets
regions 1 ─── * missions
data_sources 1 ─── * layers
data_sources 1 ─── * science_targets
missions 1 ─── * route_plans
missions 1 ─── * reroute_events
missions 1 ─── * reports
route_plans 1 ─── * reroute_events (as original/alternative references)
```

## 5. Data constraints

-   Use stable IDs; do not rely on display names as identifiers.
-   Enforce foreign keys.
-   Store timestamps as timezone-aware ISO 8601 strings or a consistent
    UTC representation.
-   Validate numeric fields for finite values and expected ranges.
-   Record coordinate CRS and axis order; never store ambiguous
    coordinates.
-   Use explicit units in column names.
-   Restrict status values to documented enums.
-   Preserve missing values as NULL/NoData, not zero.
-   Store provenance and algorithm parameters for derived results.
-   Keep absolute filesystem paths server-side; do not expose them in
    API responses.

## 6. Suggested indexes

-   `layers(region_id, status)`
-   `science_targets(region_id, feature_type)`
-   `missions(region_id, status)`
-   `route_plans(mission_id, strategy)`
-   `reroute_events(mission_id, created_at)`
-   `reports(mission_id, created_at)`

Add spatial indexes only if a real spatial database extension is
adopted. For the prototype, GeoJSON and raster file access may be
sufficient.

## 7. Migrations and seed data

-   Use Alembic if SQLAlchemy is adopted; otherwise maintain versioned
    SQL migration scripts.
-   Keep schema creation reproducible.
-   Seed only verified region/layer/source metadata.
-   Any demonstration mission, synthetic target, or simulated
    obstruction must be labelled as simulated.
-   Never seed fabricated NASA product IDs or dates.

## 8. Backup and retention

-   Back up the database and generated reports before demo milestones.
-   Keep source datasets reproducible through source URLs and checksums
    where possible.
-   Avoid storing unnecessary chat history.
-   Define retention before storing user/operator data beyond the
    hackathon.
