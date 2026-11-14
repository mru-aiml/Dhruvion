# DHRUVION

**Navigate Mars. Understand the Terrain. Protect Every Mission.**

DHRUVION is an AI-powered Martian Mission Intelligence Platform
prototype created for the NASA Space Apps Challenge --- **Interplanetary
Survival Guide: Martian Map**.

It combines a Mars map workspace, terrain intelligence, science target
discovery, route comparison, round-trip mission feasibility, emergency
rerouting simulation, and a tool-using AI mission assistant.

> **Important:** DHRUVION is a hackathon prototype and decision-support
> demonstration. It is not a certified astronaut safety system, a
> flight-qualified navigation tool, or a guarantee that any route is
> safe. Observed, derived, simulated, and unavailable data must remain
> clearly distinguished.

## Product capabilities

-   **Mission Overview:** mission status, terrain summary, alerts, and
    next actions.
-   **Martian Map:** region map, data layers, feature inspector, route
    and hazard overlays.
-   **Route Planner:** shortest, lowest-estimated-risk, and balanced
    route candidates.
-   **Science Explorer:** geological target discovery and evidence
    inspection.
-   **Emergency Navigation:** simulated obstruction and
    alternative-route calculation.
-   **AI Mission Assistant:** natural-language interface to
    deterministic mission tools.
-   **Mission Reports:** traceable summary of objectives, route,
    terrain, science, hazards, and sources.

## Technology direction

The proposed stack is: - Frontend: React, Vite, TypeScript, Tailwind
CSS. - Mapping: a geospatial map renderer verified against the chosen
Mars CRS and data format. - Backend: Python, FastAPI, Pydantic. -
Geospatial processing: NumPy, Rasterio/GDAL, GeoPandas, SciPy as
needed. - Route planning: A\* or another documented graph-search
implementation. - Optional persistence: SQLite. - AI assistant: local
Ollama or configured model endpoint, with application-controlled tools.

The exact package versions and run commands should be recorded in the
frontend and backend package manifests as the implementation is
finalized.

## Repository layout

``` text
dhruvion/
├── frontend/              # React application
├── backend/               # FastAPI application
├── data/
│   ├── raw/                # Immutable downloaded source products
│   ├── processed/          # Derived rasters and outputs
│   ├── vectors/            # GeoJSON and vector products
│   └── manifests/          # Layer/source metadata
├── scripts/                # Data preparation and utility scripts
├── tests/                  # Shared or project-level tests
├── prd.md
├── architecture.md
├── code_style.md
├── testing.md
├── agents.md
├── security.md
├── database.md
├── api.md
└── design.md
```

## Quick start

The commands below are a template. Confirm the actual entry points and
package scripts in the checked-out repository before using them.

### Prerequisites

-   Python 3.11 or later (or the version pinned by the backend project).
-   Node.js LTS and npm.
-   Git.
-   Optional: QGIS for inspecting planetary geospatial products.
-   Optional: Ollama or a configured hosted LLM endpoint for the
    assistant.

### Backend

``` bash
cd backend
python -m venv .venv
```

Activate the environment:

Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

``` bash
source .venv/bin/activate
```

Install dependencies using the project's declared dependency file. If
`requirements.txt` exists:

``` bash
pip install -r requirements.txt
```

Start the API using the actual FastAPI module path. Example only:

``` bash
uvicorn app.main:app --reload
```

The API health endpoint should be available at
`http://localhost:8000/api/health` if the configured route prefix
matches this documentation. FastAPI's OpenAPI UI is typically at
`http://localhost:8000/docs`.

### Frontend

``` bash
cd frontend
npm install
npm run dev
```

Configure the frontend API base URL using the environment variable
defined by the frontend implementation. Do not put private backend
credentials in frontend environment variables.

## Environment configuration

Create local environment files from the checked-in example when
available. Typical backend settings may include:

``` env
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
NASA_DATA_DIR=../data
DATABASE_URL=sqlite:///./dhruvion.db
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=
```

These are suggested names, not guaranteed implemented settings. Keep
`.env` out of Git. Never commit API keys or secrets.

## NASA data and provenance

Potential source discovery starting points: - NASA Mars Trek:
https://trek.nasa.gov/mars/ - NASA Planetary Data System:
https://pds.nasa.gov/ - PDS Geosciences Node:
https://pds-geosciences.wustl.edu/ - USGS Astrogeology:
https://astrogeology.usgs.gov/ - PDS Orbital Data Explorer:
https://ode.rsl.wustl.edu/

Prioritize one region with verified coverage. MOLA elevation is a
practical starting layer; slope and roughness may be derived if the data
and processing method support them. HiRISE/CTX imagery, THEMIS thermal,
and CRISM spectral products are optional extensions.

For every dataset, record source product, instrument/provider, source
URI, CRS, bounds, resolution, units, nodata, acquisition/processing date
when known, and any transformations. Never invent missing metadata. Keep
raw data immutable and place processed products in a separate directory.

## Core mission calculation

Mission feasibility uses:

``` text
T_total = T_outbound + T_exploration + T_return + T_reserve
```

The result must be `UNVERIFIED` when required information such as a
return route or travel assumption is missing. A route described as
"safest" means lowest estimated cost under the documented model; it is
not a guarantee of safety.

## Development workflow

1.  Read `prd.md`, `architecture.md`, `design.md`, and the relevant
    specialized docs.
2.  Agree on the selected region, Mars CRS, coordinate order, units, and
    layer manifest.
3.  Implement backend schemas before parallel frontend integration.
4.  Keep geospatial and feasibility logic deterministic.
5.  Add tests for nodata, route constraints, return-time calculations,
    and failure states.
6.  Keep observed, derived, simulated, unavailable, and prototype
    information distinct.
7.  Update `api.md` and `database.md` when contracts or persistence
    change.
8.  Run tests and rehearse the complete demo path before release.

## Documentation

  -----------------------------------------------------------------------
  File                                Purpose
  ----------------------------------- -----------------------------------
  `prd.md`                            Product scope, requirements, use
                                      cases, acceptance criteria

  `architecture.md`                   System components, data flow,
                                      geospatial and AI design

  `code_style.md`                     Coding and repository conventions

  `testing.md`                        Unit, integration, E2E, and release
                                      tests

  `agents.md`                         Team ownership and coding-agent
                                      rules

  `security.md`                       API, file, LLM, and mission-safety
                                      controls

  `database.md`                       Logical data model and persistence
                                      strategy

  `api.md`                            HTTP API contract

  `design.md`                         Visual system and screen-level UI
                                      specification
  -----------------------------------------------------------------------

## License and attribution

Add the project's chosen license before public release. Follow the
source dataset's own attribution, citation, redistribution, and usage
requirements. Do not imply NASA endorsement or certification.
