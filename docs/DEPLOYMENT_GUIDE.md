# DHRUVION Deployment Guide

## Overview

This guide covers deploying DHRUVION (Martian Mission Planning System) to a production environment using Docker Compose. The application consists of:

- **Backend**: FastAPI service with SQLite/PostgreSQL, NASA data processing, and AI assistant
- **Frontend**: React 19 + Vite + TypeScript SPA served by nginx
- **Data**: NASA MOLA/CTX/REMS/RAD datasets (mounted as read-only volume)

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- 4GB+ RAM (8GB+ recommended for NASA data processing)
- 10GB+ disk space for datasets
- Groq API key (for AI assistant) or Ollama instance

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository>
cd DHRUVION

# Copy environment template
cp .env.example .env

# Edit .env with your values (see Configuration section)
nano .env
```

### 2. Prepare NASA Data

Mount your NASA dataset directory as a read-only volume:

```bash
# Option A: Use existing processed data
# Place data in ./data/processed/ relative to project root

# Option B: Mount external directory
# docker compose up -d
# The DHRUVION_DATA_DIR environment variable controls the path
```

Required dataset structure:
```
data/
├── processed/
│   ├── elevation.tif          # MOLA elevation raster
│   ├── slope.tif              # Derived slope
│   ├── roughness.tif          # Derived roughness
│   ├── ctx_mosaic.tif         # CTX imagery mosaic
│   ├── coverage_class.tif     # Coverage classification
│   ├── rems/                  # REMS environment data
│   ├── rad/                   # RAD radiation data
│   └── reports/               # Generated mission reports
└── catalog.json               # Dataset catalog manifest
```

### 3. Deploy

```bash
# Build and start services
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

Services will be available at:
- Frontend: http://localhost
- Backend API: http://localhost/api
- API Docs: http://localhost/docs

## Configuration

### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | **REQUIRED** Strong random secret for JWT tokens | `change-me-in-production` |
| `GROQ_API_KEY` | Groq API key for AI assistant | (empty) |
| `FRONTEND_ORIGIN` | Frontend URL for CORS | `http://localhost` |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/dhruvion.db` |

### Generate Secure Secrets

```bash
# JWT secret (32 bytes = 64 hex chars)
openssl rand -hex 32

# Add to .env
JWT_SECRET_KEY=<generated-secret>
```

### Optional: PostgreSQL Database

For production workloads, replace SQLite with PostgreSQL:

```yaml
# docker-compose.yml additions
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: dhruvion
      POSTGRES_USER: dhruvion
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - dhruvion-network

  backend:
    environment:
      DATABASE_URL: postgresql://dhruvion:${DB_PASSWORD}@db:5432/dhruvion
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres-data:
```

### AI Assistant Configuration

| Provider | Configuration |
|----------|---------------|
| **Groq** (recommended) | Set `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL=llama-3.3-70b-versatile` |
| **Ollama** (local) | Set `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`, `LLM_MODEL=qwen2.5-coder:3b` |

Add Ollama service to docker-compose.yml:
```yaml
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - dhruvion-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Production Hardening

### 1. Reverse Proxy with SSL

Use Traefik or nginx for SSL termination:

```yaml
# traefik.yml
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "letsencrypt:/letsencrypt"
    networks:
      - dhruvion-network
```

### 2. Resource Limits

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  frontend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### 3. Security Checklist

- [ ] Strong `JWT_SECRET_KEY` generated
- [ ] `GROQ_API_KEY` configured (not committed to git)
- [ ] `FRONTEND_ORIGIN` set to production domain
- [ ] Database credentials rotated
- [ ] Non-root containers (already configured)
- [ ] Read-only NASA data mount
- [ ] Rate limiting configured on reverse proxy
- [ ] TLS certificates valid
- [ ] Health checks passing
- [ ] Log aggregation configured

## Data Persistence

### SQLite (Default)
Data stored in `backend-data` Docker volume:
```bash
# Backup
docker run --rm -v nasachallenge_backend-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data

# Restore
docker run --rm -v nasachallenge_backend-data:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /
```

### PostgreSQL
```bash
# Backup
docker exec nasachallenge-db pg_dump -U dhruvion dhruvion > backup.sql

# Restore
docker exec -i nasachallenge-db psql -U dhruvion dhruvion < backup.sql
```

## NASA Data Management

### Mounting Data
```yaml
volumes:
  - /path/to/nasa/data:/app/data:ro  # Read-only mount
```

### Dataset Requirements
- `elevation.tif`: MOLA elevation (463m/px, GeoTIFF)
- `slope.tif`: Derived slope (degrees)
- `roughness.tif`: Derived roughness (meters)
- `coverage_class.tif`: Coverage classification (0=uncovered, 1=usable, 2=elevation-only)
- `ctx_mosaic.tif`: CTX imagery mosaic (partial coverage)
- `rems/`, `rad/`: Environment data (CSV/Parquet)
- `catalog.json`: Dataset manifest with provenance

### Health Check
Backend `/health` endpoint verifies:
- Database connectivity
- Dataset availability
- Tile service reachability

## Monitoring

### Health Endpoints
- Frontend: `GET /` (serves index.html)
- Backend: `GET /api/health` (JSON status)

### Logging
Structured JSON logs to stdout:
```json
{
  "timestamp": "2026-01-15T10:30:00Z",
  "level": "INFO",
  "service": "dhruvion-api",
  "request_id": "uuid",
  "message": "Route calculated",
  "region": "gale_crater",
  "strategy": "balanced"
}
```

### Metrics (Optional)
Add Prometheus exporter:
```python
# backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Backend health check fails | Check logs: `docker compose logs backend`; verify database and data mount |
| Frontend shows blank page | Check browser console; verify `VITE_API_BASE_URL` matches backend |
| AI assistant unavailable | Verify `GROQ_API_KEY` or Ollama connectivity; check `/api/assistant/health` |
| Tiles not loading | Check network tab for 404s; NASA Trek may be rate-limiting |
| Database locked | Ensure single backend instance; check SQLite WAL mode |

### Debug Commands
```bash
# Backend shell
docker compose exec backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# Check data mount
docker compose exec backend ls -la /app/data/

# Test API
curl http://localhost/api/health
curl http://localhost/api/regions

# Frontend nginx config
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

## Rollback Procedure

```bash
# 1. Tag current deployment
docker tag nasachallenge-backend:latest nasachallenge-backend:rollback-$(date +%s)

# 2. Deploy previous version
docker compose pull  # if using registry
docker compose up -d --no-deps backend frontend

# 3. Verify health
docker compose ps
curl -f http://localhost/api/health

# 4. Restore database if needed (see Data Persistence)
```

## Scaling Considerations

- **Backend**: Stateless, can run multiple replicas behind load balancer
- **Frontend**: Static files, scale nginx replicas
- **Database**: SQLite single-writer; migrate to PostgreSQL for horizontal scaling
- **NASA Data**: Read-only, shared volume works for multiple replicas
- **AI Assistant**: Groq handles concurrency; Ollama needs GPU per replica

## Support

- Check logs: `docker compose logs -f`
- API docs: http://localhost/docs
- Health: http://localhost/api/health
- GitHub Issues: [Repository Issues]