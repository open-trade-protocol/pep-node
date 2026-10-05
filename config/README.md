# OpenTrade Peer Node — Configuration

See `settings.example.yaml` for all available settings.

## Environment Variables

All settings can be configured via environment variables with `OT_` prefix:

```bash
export OT_NODE_ID="snow.opentradeprotocol.com"
export OT_NODE_SECRET_KEY="<base64-encoded private key>"
export OT_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/opentrade"
export OT_MEILISEARCH_URL="http://localhost:7700"
export OT_QDRANT_URL="http://localhost:6333"
export OT_FEDERATION_INDEX_URL="https://api.opentradeprotocol.com/v1"
```

## Settings Reference

| Setting | Default | Description |
|---|---|---|
| `node_id` | `snow.opentradeprotocol.com` | Unique node identifier |
| `node_name` | `Snowboard Reference Node` | Human-readable node name |
| `node_secret_key` | `None` | Ed25519 private key for signing |
| `category` | `winter_sports/snowboard` | Product category |
| `host` | `0.0.0.0` | Bind address |
| `port` | `8000` | HTTP port |
| `debug` | `False` | Debug mode |
| `database_url` | `postgresql://...` | PostgreSQL connection |
| `meilisearch_url` | `http://localhost:7700` | Meilisearch endpoint |
| `qdrant_url` | `http://localhost:6333` | Qdrant endpoint |
| `federation_index_url` | `https://api.opentradeprotocol.com/v1` | PEP Index endpoint |
| `federation_heartbeat_interval` | `300` | Heartbeat interval (seconds) |
| `federation_sync_interval` | `60` | Sync interval (seconds) |
| `ai_service_url` | `None` | AI/ML service endpoint |
| `log_level` | `INFO` | Logging level |
| `cors_origins` | `["*"]` | CORS allowed origins |
