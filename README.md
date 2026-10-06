# OpenTrade Peer Node

Reference implementation of the OpenTrade Exchange Protocol (PEP) — a FastAPI service for publishing and searching P2P product listings.

## Features

- **FastAPI** backend with async support
- **SQLModel** ORM with PostgreSQL (asyncpg driver)
- **Meilisearch** integration for full-text search
- **OpenAPI-compliant** API matching the OpenTrade Protocol specification
- **Docker Compose** orchestration with PostgreSQL and Meilisearch
- **Health checks** for database and search engine monitoring

## Quick Start

### Docker Compose (Recommended)

```bash
cd ../infrastructure
docker compose up --build -d
```

Services start on:

| Service | Port | Description |
|---------|------|-------------|
| PEP Node | `8000` | FastAPI REST API |
| PostgreSQL | `5432` | Database |
| Meilisearch | `7700` | Full-text search |

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://opentrade:secret@localhost:5432/pepnode"
export MEILISEARCH_URL="http://localhost:7700"
export MEILISEARCH_MASTER_KEY="masterKey123"

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (DB + Meilisearch) |
| `GET` | `/v1/api/v1/listings` | List/search listings |
| `POST` | `/v1/api/v1/listings` | Create a new listing |
| `POST` | `/v1/api/v1/search` | Full-text search via Meilisearch |

### Examples

```bash
# Health check
curl http://localhost:8000/health

# List listings
curl http://localhost:8000/v1/api/v1/listings

# Create listing
curl -X POST http://localhost:8000/v1/api/v1/listings \
  -H "Content-Type: application/json" \
  -d '{"title":"Burton Custom X","price":45000,"currency":"RUB","category":"snowboards","condition":"new","seller_node_id":"node-test-01"}'

# Search
curl -X POST "http://localhost:8000/v1/api/v1/search?query=Burton&category=all"
```

## Swagger Documentation

Interactive API docs: **http://localhost:8000/docs**

## Project Structure

```
pep-node/
├── app/
│   ├── main.py              # FastAPI application + health check
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API routes
│   │       └── search_router.py  # Search endpoint
│   ├── models/
│   │   └── listing.py       # SQLModel DB model + Pydantic schemas
│   ├── core/
│   │   ├── config.py        # Pydantic Settings
│   │   └── logging.py       # Structured logging
│   ├── services/
│   │   └── search/
│   │       └── service.py   # Meilisearch + DB search logic
│   └── db/
│       └── __init__.py      # Async engine + session management
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── README.md
```

## Configuration

Environment variables (see [`app/core/config.py`](app/core/config.py)):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./pepnode.db` | PostgreSQL connection string |
| `MEILISEARCH_URL` | `http://localhost:7700` | Meilisearch API URL |
| `MEILISEARCH_MASTER_KEY` | `""` | Meilisearch master key |
| `NODE_ID` | auto-generated | Unique node identifier |

## Database Migrations

SQLModel auto-creates tables on startup. For production, use Alembic:

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

## Testing

```bash
# Run tests
cd ../infrastructure
# Seed test data
python3 scripts/seed-snowboards.py --base-url http://localhost:8000

# Verify
bash scripts/verify-system.sh
```

## Known Issues & Fixes

### Meilisearch Document ID Sanitization

Meilisearch rejects document IDs containing colons (`:`). The `index_listing()` method in [`service.py`](app/services/search/service.py:304) automatically sanitizes URN-format IDs:

```python
# Input:  "urn:opentrade:listing:abc-123"
# Output: "urn_opentrade_listing_abc-dash-123"
```

The original ID is preserved in the `_meilisearch_id` field.

### Async Engine Driver

The async engine uses `postgresql+asyncpg://` URL scheme. If `DATABASE_URL` is set without the `+asyncpg` suffix, it's automatically added in [`db/__init__.py`](app/db/__init__.py:41).

## Deployment

See the [Deployment Guide](https://opentradeprotocol.com/docs/node-operator/deployment/) for production setup instructions.

## Contributing

See [CONTRIBUTING.md](https://github.com/open-trade-protocol/.github/blob/main/CONTRIBUTING.md).

## License

Apache-2.0
