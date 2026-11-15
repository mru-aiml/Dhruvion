# DHRUVION

Map-first AI-powered Martian mission-planning prototype.

## Startup

Backend:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

## Tests
```bash
cd backend && python -m pytest tests -q
cd frontend && npm run build
```
