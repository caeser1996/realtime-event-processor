.PHONY: help up down logs build test clean generate-events

# Default target
help:
	@echo "Real-Time Event Processor - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make up              - Start all services with Docker Compose"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs from all services"
	@echo "  make build           - Build all Docker images"
	@echo "  make rebuild         - Rebuild and restart all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make test-backend    - Run backend tests"
	@echo "  make test-frontend   - Run frontend tests"
	@echo "  make lint            - Run linters"
	@echo ""
	@echo "Data:"
	@echo "  make generate-events - Generate sample events"
	@echo "  make seed-data       - Seed database with sample data"
	@echo ""
	@echo "Kubernetes:"
	@echo "  make k8s-deploy      - Deploy to Kubernetes"
	@echo "  make k8s-delete      - Delete Kubernetes resources"
	@echo "  make k8s-status      - Check Kubernetes status"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           - Remove all containers and volumes"
	@echo "  make clean-all       - Remove everything including images"

# Docker Compose commands
up:
	docker-compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "Frontend:    http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs:    http://localhost:8000/docs"
	@echo "Kafka UI:    http://localhost:8080"
	@echo "Grafana:     http://localhost:3001"
	@echo "Prometheus:  http://localhost:9090"

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-kafka:
	docker-compose logs -f kafka

build:
	docker-compose build

rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && npm test -- --coverage --watchAll=false

lint:
	cd backend && python -m flake8 app/ && python -m mypy app/
	cd frontend && npm run lint

format:
	cd backend && python -m black app/ tests/
	cd frontend && npm run format

# Data generation
generate-events:
	@echo "Generating sample events..."
	curl -X POST http://localhost:8000/api/v1/events/generate \
		-H "Content-Type: application/json" \
		-d '{"count": 1000, "event_type": "user_action"}'

seed-data:
	@echo "Seeding database with sample data..."
	docker-compose exec backend python -m app.scripts.seed_data

# Kubernetes
k8s-deploy:
	kubectl create namespace event-processor --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -k infrastructure/kubernetes/

k8s-delete:
	kubectl delete -k infrastructure/kubernetes/
	kubectl delete namespace event-processor --ignore-not-found

k8s-status:
	kubectl get all -n event-processor

k8s-logs:
	kubectl logs -f -n event-processor -l app=backend

# Port forwarding for local access to K8s services
k8s-forward:
	@echo "Starting port forwarding..."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	kubectl port-forward -n event-processor svc/frontend 3000:80 &
	kubectl port-forward -n event-processor svc/backend 8000:8000 &

# Cleanup
clean:
	docker-compose down -v
	rm -rf backend/__pycache__ backend/.pytest_cache
	rm -rf frontend/node_modules frontend/build

clean-all: clean
	docker-compose down -v --rmi all
	docker system prune -f

# Development helpers
shell-backend:
	docker-compose exec backend /bin/bash

shell-clickhouse:
	docker-compose exec clickhouse clickhouse-client

shell-kafka:
	docker-compose exec kafka /bin/bash

# Health checks
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: Not responding"
	@docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo "Kafka: OK" || echo "Kafka: Not responding"

# Monitoring
metrics:
	@curl -s http://localhost:8000/metrics

grafana-import:
	@echo "Importing Grafana dashboards..."
	./infrastructure/monitoring/import-dashboards.sh
