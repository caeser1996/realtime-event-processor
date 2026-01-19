# Real-Time Event Processor

A production-ready event-driven architecture demo featuring Kafka, ClickHouse, FastAPI, React, and comprehensive monitoring.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Event Sources  │────▶│     Kafka       │────▶│   Consumers     │
│  (Producers)    │     │   (Message Bus) │     │   (FastAPI)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │   ClickHouse    │◀─────────────┘
                        │   (Analytics)   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  React Dashboard │
                        │   (Real-time)   │
                        └─────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Message Queue | Apache Kafka |
| Analytics DB | ClickHouse |
| Backend API | FastAPI (Python) |
| Frontend | React + TypeScript |
| Containerization | Docker |
| Orchestration | Kubernetes |
| Monitoring | Prometheus + Grafana |

## Features

- **Real-time Event Processing**: Kafka-based event streaming with exactly-once semantics
- **High-Performance Analytics**: ClickHouse for sub-second analytical queries on billions of events
- **Live Dashboard**: React frontend with WebSocket updates for real-time visualization
- **Scalable Architecture**: Kubernetes-ready with horizontal pod autoscaling
- **Full Observability**: Prometheus metrics, Grafana dashboards, and structured logging

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- kubectl (for Kubernetes deployment)

### Local Development with Docker Compose

```bash
# Clone the repository
git clone <repo-url>
cd realtime-event-processor

# Start all services
make up

# Or use docker-compose directly
docker-compose up -d

# View logs
make logs

# Stop services
make down
```

### Access Services

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Kafka UI | http://localhost:8080 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

### Generate Sample Events

```bash
# Generate test events
make generate-events

# Or use the API
curl -X POST http://localhost:8000/api/v1/events/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1000, "event_type": "user_action"}'
```

## Project Structure

```
realtime-event-processor/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── core/              # Configuration
│   │   ├── kafka/             # Kafka producer/consumer
│   │   ├── clickhouse/        # ClickHouse client
│   │   ├── models/            # Pydantic models
│   │   └── services/          # Business logic
│   ├── tests/                 # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React dashboard
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom hooks
│   │   ├── services/          # API services
│   │   └── types/             # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── infrastructure/
│   ├── docker/                # Docker configurations
│   ├── kubernetes/            # K8s manifests
│   └── monitoring/            # Prometheus/Grafana
├── docker-compose.yml
├── Makefile
└── README.md
```

## Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Running Tests

```bash
# Backend tests
make test-backend

# Frontend tests
make test-frontend

# All tests
make test
```

## Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace event-processor

# Apply configurations
kubectl apply -k infrastructure/kubernetes/

# Check status
kubectl get pods -n event-processor

# Port forward for local access
kubectl port-forward -n event-processor svc/frontend 3000:80
```

## Monitoring

### Prometheus Metrics

The backend exposes metrics at `/metrics`:
- `events_processed_total`: Total events processed
- `event_processing_duration_seconds`: Event processing latency
- `kafka_messages_produced_total`: Kafka messages produced
- `kafka_messages_consumed_total`: Kafka messages consumed
- `clickhouse_query_duration_seconds`: ClickHouse query latency

### Grafana Dashboards

Pre-configured dashboards:
1. **Event Processing Overview**: Real-time event throughput and latency
2. **Kafka Metrics**: Producer/consumer lag, partition distribution
3. **ClickHouse Performance**: Query performance, storage metrics
4. **System Resources**: CPU, memory, network usage

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | `kafka:9092` |
| `CLICKHOUSE_HOST` | ClickHouse server host | `clickhouse` |
| `CLICKHOUSE_PORT` | ClickHouse server port | `8123` |
| `CLICKHOUSE_DATABASE` | ClickHouse database name | `events` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Documentation

### Events API

```bash
# Create event
POST /api/v1/events
{
  "event_type": "user_action",
  "user_id": "user123",
  "payload": {"action": "click", "element": "button"}
}

# Query events
GET /api/v1/events?event_type=user_action&start_time=2024-01-01&limit=100

# Get event statistics
GET /api/v1/analytics/stats?interval=1h

# Get real-time metrics
GET /api/v1/analytics/realtime
```

### WebSocket

```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/events');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New event:', data);
};
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
