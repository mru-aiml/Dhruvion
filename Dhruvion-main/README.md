# DHRUVION

**Navigate Mars. Understand the Terrain. Protect Every Mission.**

DHRUVION is an AI-powered Martian Mission Intelligence Platform
prototype created for the NASA Space Apps Challenge — **Interplanetary
Survival Guide: Martian Map**.

It combines a Mars map workspace, terrain intelligence, science target
discovery, route comparison, round-trip mission feasibility, emergency
rerouting simulation, and a tool-using AI mission assistant.

> **Important:** DHRUVION is a hackathon prototype and decision-support
> demonstration. It is not a certified astronaut safety system, a
> flight-qualified navigation tool, or a guarantee that any route is
> safe. Observed, derived, simulated, and unavailable data must remain
> clearly distinguished.

## Screenshots

### Landing Page
![Landing Page](docs/landing-verification/desktop-1920x1080.png)

### Mission Overview Dashboard
![Mission Overview](docs/landing-verification/hero-1917x901-mars-globe.png)

### Martian Map with Layer Controls
![Martian Map](docs/landing-verification/view-terrain.png)

### Route Planner
![Route Planner](docs/landing-verification/hero-1440x900-mission-data.png)

### Mobile Responsive
![Mobile](docs/landing-verification/mobile-390x844.png)

## Features

| Module | Status | Description |
|--------|--------|-------------|
| **Mission Overview** | ✅ Implemented | Mission status, terrain summary, alerts, next actions |
| **Martian Map** | ✅ Implemented | Region map, data layers, feature inspector, route overlays |
| **Route Planner** | ✅ Implemented | Shortest, safest-estimated, balanced route candidates |
| **Science Explorer** | ✅ Implemented | Geological target discovery and evidence inspection |
| **Emergency Navigation** | ✅ Implemented | Simulated obstruction and alternative-route calculation |
| **AI Mission Assistant** | ⚠️ Simulated | Natural-language interface to deterministic mission tools |
| **Mission Reports** | ⚠️ Simulated | Traceable summary of objectives, route, terrain, science |
| **Settings** | ✅ Implemented | Units, coordinate format, simulated labels, reduced motion |

### Feature Status Key
- ✅ **Implemented** — Fully functional with backend integration
- ⚠️ **Simulated** — UI complete, backend returns fallback/mock data
- 🚫 **Unavailable** — Not connected or outside coverage

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript 7, Vite 8, Tailwind CSS 3 |
| **Routing** | React Router DOM 7 |
| **Maps** | Leaflet 1.9, React-Leaflet 5, Custom Mars CRS |
| **Charts** | Recharts 3 |
| **Icons** | Lucide React |
| **State** | React Context, localStorage, Zustand |
| **Backend** | FastAPI, SQLAlchemy, Pydantic, SQLite |
| **Auth** | JWT (HttpOnly cookies), bcrypt |
| **Geospatial** | NumPy, Rasterio, custom Mars CRS (IAU 2000:104905) |
| **Testing** | pytest (backend), TypeScript strict mode |

## Architecture Overview

```
React + TypeScript UI
        |
        | HTTPS / JSON / GeoJSON
        v
FastAPI Application
  ├── API Routers + Pydantic Schemas
  ├── Mission Application Services
  │    ├── Terrain Service
  │    ├── Hazard/Difficulty Service
  │    ├── Science Target Service
  │    ├── Route Planner (A*)
  │    ├── Mission Feasibility
  │    └── Report Service
  ├── AI Assistant Orchestration
  │    └── Allowlisted Tools → Application Services
  ├── Data Access / Repositories
  └── NASA Data Adapters + Local Dataset Catalog
        |
        ├── Raster/Vector Files (GeoTIFF, GeoJSON)
        ├── Metadata Manifests (JSON)
        └── SQLite (Optional Persistence)
```

**Key Principles:**
- **Deterministic core** — Raster processing, hazard scoring, route search in Python
- **LLM as interface** — AI assistant calls tools, explains results; does not calculate
- **Provenance by design** — Source metadata travels with every layer, route, report
- **Missing data is unknown** — NoData never coerced to zero

## Installation

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 20+** and **npm** (frontend)
- **Git**
- Optional: **QGIS** for inspecting planetary geospatial products
- Optional: **Ollama** or configured LLM endpoint for AI assistant

### Backend Setup

```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings (see Environment Configuration below)
```

Start the API server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
- Health check: `http://localhost:8000/api/health`
- OpenAPI docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
```

Configure environment:
```bash
cp .env.example .env
# Edit .env if needed (default points to localhost:8000/api)
```

Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Environment Configuration

### Backend (`backend/.env`)

```env
# Database
DATABASE_URL=sqlite:///./dhruvion.db

# JWT Authentication (REQUIRED for production)
JWT_SECRET_KEY=your-secure-random-string-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
COOKIE_NAME=dhruvion_access_token

# CORS
FRONTEND_ORIGIN=http://localhost:5173
```

**Generate a secure JWT secret:**
```bash
# Linux/macOS
openssl rand -hex 32

# PowerShell
[System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

### Frontend (`frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Data Sources and Attribution

DHRUVION uses NASA public domain datasets with proper attribution:

| Dataset | Source | Status | Attribution |
|---------|--------|--------|-------------|
| MOLA Elevation (MEGDR) | NASA PDS Geosciences | OBSERVED / DERIVED | MGS MOLA MEGDR · NASA PDS |
| CTX Imagery Mosaic | NASA Mars Trek / JPL | OBSERVED | NASA Mars Trek · Gale_CTX_BlockAdj_dd |
| Mars Rotation Video | NASA SVS 30338 | OBSERVED | NASA SVS / JPL · not live footage |
| Slope/Roughness | Derived from MOLA | DERIVED | Computed by DHRUVION |
| Science Targets | Demo catalogue | SIMULATED | Not verified observations |
| Hazards | None connected | UNAVAILABLE | No observed dataset |

See `docs/data-sources.md` for complete documentation.

**Key Principle:** Never present simulated data as verified observations. All UI elements display explicit status badges.

## Running the Application

### Development Mode

```bash
# Terminal 1 - Backend
cd backend
.venv\Scripts\Activate.ps1  # Windows
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit `http://localhost:5173` — you should see the landing page with rotating Mars globe.

### Demo Credentials

| Email | Password |
|-------|----------|
| `demo@dhruvion.io` | `Mission2026!` |

### Production Build

```bash
# Frontend
cd frontend
npm run build
# Output in frontend/dist/

# Backend
cd backend
# Use a production ASGI server like Gunicorn/Uvicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Checks

```bash
cd frontend
npx tsc --noEmit      # TypeScript compilation
npm run lint          # oxlint
npm run build         # Production build verification
```

## Project Structure

```
dhruvion/
├── frontend/                 # React + Vite application
│   ├── src/
│   │   ├── features/         # Page components (10 pages)
│   │   ├── components/       # Shared UI (common, layout, map)
│   │   ├── context/          # AuthContext
│   │   ├── services/         # API client + endpoints
│   │   ├── data/             # Demo data
│   │   └── types/            # TypeScript types
│   ├── public/               # NASA assets (videos, images)
│   └── package.json
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # Routes + auth
│   │   ├── core/             # Config, security, database, models
│   │   └── schemas/          # Pydantic models
│   └── tests/                # pytest tests
├── scripts/                  # Data processing (MOLA, landing assets)
├── data/                     # Excluded from Git (downloaded/generated)
│   ├── raw/                  # Immutable source products
│   ├── processed/            # Derived rasters and outputs
│   └── vectors/              # GeoJSON and vector products
├── docs/
│   ├── landing-verification/ # Responsive design screenshots
│   └── data-sources.md       # Data catalog and attribution
├── CONTRIBUTING.md
├── .gitignore
└── README.md
```

## Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| AI Assistant backend | Terrain lookup connected; other tools pending | Expand the allowlisted `AssistantService` tools |
| Reports export | Simulated data only | Connect to real mission data |
| Hazard catalogue | No observed dataset | Mark UNAVAILABLE; never fabricate |
| Science targets | Demo catalogue only | Mark SIMULATED; no verified API |
| Large data files | Not in repo | Download via scripts at build time |
| Prototype CRS | Approximate projection | Document IAU 2000:104905 limitations |

## License

**Apache License 2.0** — See [LICENSE](LICENSE) file.

This license was chosen because:
- Permits commercial and non-commercial use
- Requires attribution (critical for NASA data provenance)
- Provides patent grant
- Compatible with NASA public domain data usage
- Industry standard for open-source geospatial tools

## NASA Data Usage Compliance

- All NASA datasets used are public domain
- Attribution provided per NASA Media Guidelines
- No NASA endorsement implied
- Simulated features clearly labeled
- Raw data kept immutable; processed outputs separate

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development workflow
- Code style guidelines
- Pull request process
- Architecture guidelines
- Security requirements

## Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Security**: GitHub Security Advisories for vulnerabilities
- **Questions**: GitHub Discussions

---

**Built for the NASA Space Apps Challenge 2026**  
*Interplanetary Survival Guide: Martian Map*
