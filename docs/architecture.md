# DHRUVION Architecture

- Backend: FastAPI + SQLAlchemy + SQLite for persistent mission management.
- Data services: Rasterio/NumPy over the NASA DHRUVION_DATA package.
- AI: deterministic allowlisted tools plus optional Ollama phrasing.
- Frontend: React/Vite/TypeScript with shared mission state in sessionStorage.
- Mission management: persistent `missions` table; route planning and reports delegate to existing deterministic services.
