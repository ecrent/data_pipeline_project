# =============================================================================
# DATA PIPELINE PROJECT - MAKEFILE
# =============================================================================
# Simplified commands for managing the data pipeline across environments

.PHONY: help setup start stop logs clean status test-services

# Default target
help: ## Show this help message
	@echo "🚀 Data Pipeline Management Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Environment setup
setup: ## Detect environment and configure services
	@echo "🔧 Setting up environment..."
	@./setup-environment.sh
	@if [ "$$ENVIRONMENT" = "codespaces" ]; then ./configure-ports.sh; fi

# Service management
start: ## Start all core services
	@echo "🚀 Starting data pipeline services..."
	@if [ -f docker-compose.codespaces.yml ]; then \
		docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d; \
	else \
		docker-compose up -d; \
	fi
	@echo "✅ Services started!"
	@$(MAKE) status

start-minimal: ## Start only essential services (zookeeper, kafka, minio, elasticsearch, kibana)
	@echo "🚀 Starting minimal service set..."
	@if [ -f docker-compose.codespaces.yml ]; then \
		docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d zookeeper kafka minio elasticsearch kibana; \
	else \
		docker-compose up -d zookeeper kafka minio elasticsearch kibana; \
	fi

stop: ## Stop all services
	@echo "🛑 Stopping data pipeline services..."
	@docker-compose down
	@echo "✅ Services stopped!"

restart: ## Restart all services
	@$(MAKE) stop
	@$(MAKE) start

# Service monitoring
status: ## Show status of all services
	@echo "📊 Service Status:"
	@echo "=================="
	@docker-compose ps

logs: ## Show logs for all services (use 'make logs SERVICE=kafka' for specific service)
	@if [ -n "$(SERVICE)" ]; then \
		echo "📋 Showing logs for $(SERVICE)..."; \
		docker-compose logs -f $(SERVICE); \
	else \
		echo "📋 Showing logs for all services..."; \
		docker-compose logs -f; \
	fi

health: ## Check health status of all services
	@echo "🏥 Health Check Status:"
	@echo "======================"
	@for service in zookeeper kafka minio elasticsearch kibana spark-master spark-worker; do \
		echo -n "$$service: "; \
		docker-compose ps $$service --format "table {{.Status}}" | tail -n 1 | grep -q "healthy" && echo "✅ Healthy" || echo "❌ Unhealthy"; \
	done

# Data operations
check-data: ## Check if dataset is available and show info
	@echo "📊 Checking dataset status..."
	@if [ -f "./data/electronics.csv" ]; then \
		echo "✅ Dataset found: ./data/electronics.csv"; \
		echo "📏 File size: $$(du -h ./data/electronics.csv | cut -f1)"; \
		echo "📋 Line count: $$(wc -l < ./data/electronics.csv) rows"; \
		echo "🔍 First few lines:"; \
		head -3 ./data/electronics.csv; \
	else \
		echo "❌ Dataset not found."; \
		echo "📥 Please download manually:"; \
		echo "   1. Visit: https://www.kaggle.com/mkechinov/ecommerce-events-history-in-electronics-store"; \
		echo "   2. Download the CSV file"; \
		echo "   3. Save as ./data/electronics.csv"; \
	fi

ingest: ## Run the data ingestion service
	@echo "📥 Starting data ingestion..."
	@if [ ! -f "./data/electronics.csv" ]; then \
		echo "❌ Dataset not found. Please download it manually:"; \
		echo "   1. Visit: https://www.kaggle.com/mkechinov/ecommerce-events-history-in-electronics-store"; \
		echo "   2. Download the CSV file"; \
		echo "   3. Save as ./data/electronics.csv"; \
		exit 1; \
	fi
	@if [ -f docker-compose.codespaces.yml ]; then \
		docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml --profile ingestion up ingestion-service; \
	else \
		docker-compose --profile ingestion up ingestion-service; \
	fi

process: ## Run the Spark processing application
	@echo "⚡ Starting Spark processing..."
	@if [ -f docker-compose.codespaces.yml ]; then \
		docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml --profile processing up spark-processor; \
	else \
		docker-compose --profile processing up spark-processor; \
	fi

# Data management
clean: ## Remove all containers, volumes, and networks (DESTRUCTIVE)
	@echo "🧹 Cleaning up all data (this will DELETE all data)..."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans; \
		docker system prune -f; \
		echo "✅ Cleanup complete!"; \
	else \
		echo "❌ Cleanup cancelled."; \
	fi

reset: ## Stop services and remove volumes (keeps images)
	@echo "🔄 Resetting data pipeline..."
	@docker-compose down -v
	@echo "✅ Data pipeline reset!"

# Development helpers
shell: ## Get shell access to a service (use 'make shell SERVICE=kafka')
	@if [ -n "$(SERVICE)" ]; then \
		echo "🐚 Opening shell for $(SERVICE)..."; \
		docker-compose exec $(SERVICE) /bin/bash; \
	else \
		echo "❌ Please specify SERVICE. Example: make shell SERVICE=kafka"; \
	fi

urls: ## Show service URLs for current environment
	@./setup-environment.sh | grep -A 20 "DATA PIPELINE SERVICES"

test-services: ## Test connectivity to all services
	@echo "🧪 Testing service connectivity..."
	@echo "================================"
	@echo "Testing Kafka..."
	@docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list >/dev/null 2>&1 && echo "✅ Kafka: OK" || echo "❌ Kafka: Failed"
	@echo "Testing Elasticsearch..."
	@curl -s http://localhost:9200/_cluster/health >/dev/null 2>&1 && echo "✅ Elasticsearch: OK" || echo "❌ Elasticsearch: Failed"
	@echo "Testing MinIO..."
	@curl -s http://localhost:9000/minio/health/live >/dev/null 2>&1 && echo "✅ MinIO: OK" || echo "❌ MinIO: Failed"
	@echo "Testing Kibana..."
	@curl -s http://localhost:5601/api/status >/dev/null 2>&1 && echo "✅ Kibana: OK" || echo "❌ Kibana: Failed"

# Development workflow
dev: ## Start development environment (minimal services + watch logs)
	@$(MAKE) start-minimal
	@echo "🔍 Watching logs (Ctrl+C to exit)..."
	@docker-compose logs -f

# Quick access to web UIs
open-kibana: ## Open Kibana dashboard
	@echo "Opening Kibana dashboard..."
	@if [ -n "$(CODESPACE_NAME)" ]; then \
		echo "🌐 Kibana: https://$(CODESPACE_NAME)-5601.app.github.dev/"; \
	else \
		echo "🌐 Kibana: http://localhost:5601/"; \
	fi

open-spark: ## Open Spark Master UI
	@echo "Opening Spark Master UI..."
	@if [ -n "$(CODESPACE_NAME)" ]; then \
		echo "🌐 Spark: https://$(CODESPACE_NAME)-8080.app.github.dev/"; \
	else \
		echo "🌐 Spark: http://localhost:8080/"; \
	fi

open-minio: ## Open MinIO console
	@echo "Opening MinIO console..."
	@if [ -n "$(CODESPACE_NAME)" ]; then \
		echo "🌐 MinIO: https://$(CODESPACE_NAME)-9001.app.github.dev/"; \
	else \
		echo "🌐 MinIO: http://localhost:9001/"; \
	fi

# Environment info
env: ## Show current environment information
	@echo "🌍 Environment Information:"
	@echo "=========================="
	@echo "Environment: $$(grep ENVIRONMENT .env | cut -d= -f2)"
	@if [ -n "$(CODESPACE_NAME)" ]; then \
		echo "Codespace: $(CODESPACE_NAME)"; \
		echo "Domain: $(GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN)"; \
	else \
		echo "Running locally"; \
	fi
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version)"
