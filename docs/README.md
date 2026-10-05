# OpenTrade Peer Node — Reference Implementation

Reference implementation of an OpenTrade Protocol node. This node publishes listings
to the OpenTrade Index and serves as a marketplace for a specific category.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/open-trade-protocol/peer-node
cd peer-node
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp config/settings.example.yaml config/settings.yaml
# Edit config/settings.yaml with your node credentials

# Run migrations
python scripts/migrate.py up

# Start the node
python -m app.main
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Peer Node                         │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │  API     │  │  AI      │  │  Federation       │ │
│  │  Server  │  │  Assistant│  │  Sync             │ │
│  │          │  │          │  │                   │ │
│  │  • Search│  │  • Photo │  │  • Listing Announce│ │
│  │  • Escrow│  │    Verify│  │  • Heartbeat      │ │
│  │  • Offers│  │  • Price │  │  • Incremental    │ │
│  └────┬─────┘  │  Suggest │  │    Sync           │ │
│       │        │  • Defect│  └───────────────────┘ │
│       │        └──────────┘                         │
│       │                                             │
│  ┌────┴──────────────────────────────────────────┐ │
│  │              Core Services                     │ │
│  │                                                │ │
│  │  • Trust Service (scores, DID)                │ │
│  │  • Escrow Service (state machine)             │ │
│  │  • Search Service (Meilisearch + Qdrant)      │ │
│  │  • Product Service (PostgreSQL + JSONB)       │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Configuration

See `config/settings.example.yaml` for all available settings:

- `node_id`: Unique identifier for this node
- `node_key`: Ed25519 private key for signing listings
- `database_url`: PostgreSQL connection string
- `meilisearch_url`: Meilisearch endpoint
- `qdrant_url`: Qdrant vector store endpoint
- `federation.index_url`: OpenTrade Index endpoint
- `federation.heartbeat_interval`: Heartbeat interval in seconds
- `ai.service_url`: AI/ML service endpoint

## API Endpoints

### Node Registration

```bash
curl -X POST https://api.opentradeprotocol.com/v1/federation/register \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "snow.opentradeprotocol.com",
    "nodePublicKey": "...",
    "capabilities": ["search", "escrow", "logistics"]
  }'
```

### Announce Listings

```bash
curl -X POST https://api.opentradeprotocol.com/v1/federation/announce \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <node_secret_key>" \
  -d '{
    "nodeId": "snow.opentradeprotocol.com",
    "listings": [{"listingId": "lst_123", "signature": "...", "data": {...}}]
  }'
```

### Send Heartbeat

```bash
curl -X POST https://api.opentradeprotocol.com/v1/federation/heartbeat \
  -H "Authorization: Bearer <node_secret_key>" \
  -d '{
    "nodeId": "snow.opentradeprotocol.com",
    "status": "healthy",
    "listingsCount": 1247,
    "lastSyncAt": "2026-10-05T12:00:00Z"
  }'
```

## Testing

```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# Run all tests
python -m pytest
```

## Deployment

### Docker

```bash
docker build -t opentrade-peer-node .
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  opentrade-peer-node
```

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/
```
