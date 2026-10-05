# OpenTrade Peer Node

Референсная реализация узла OpenTrade Protocol на FastAPI.

## Быстрый старт

### Через Docker Compose

```bash
cd ../infrastructure
docker compose up --build -d
```

Сервер будет доступен на `http://localhost:8000`.

Swagger-документация: `http://localhost:8000/docs`

### Локально

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Требования: Python 3.12+, PostgreSQL, Meilisearch.

## Структура

```
pep-node/
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── api/
│   │   └── v1/
│   │       └── router.py  # API routes (matches spec/openapi/openapi.yaml)
│   ├── models/
│   │   └── listing.py     # Pydantic models (strictly matches OpenAPI spec)
│   ├── core/
│   │   ├── config.py      # Settings (pydantic-settings)
│   │   └── logging.py
│   └── services/
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── README.md
```

## API

См. `spec/openapi/openapi.yaml` для полной спецификации.

## Лицензия

Apache-2.0
