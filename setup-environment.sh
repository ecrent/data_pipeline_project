#!/bin/bash

# =============================================================================
# ENVIRONMENT DETECTION AND URL GENERATION SCRIPT
# =============================================================================
# This script detects whether we're running in GitHub Codespaces or locally
# and generates the appropriate URLs for accessing services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to detect environment
detect_environment() {
    if [[ -n "${CODESPACE_NAME}" ]]; then
        echo "codespaces"
    else
        echo "local"
    fi
}

# Function to generate service URLs
generate_urls() {
    local environment=$1
    local base_domain=""
    
    if [[ "$environment" == "codespaces" ]]; then
        base_domain="${CODESPACE_NAME}-{port}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
        protocol="https"
    else
        base_domain="localhost:{port}"
        protocol="http"
    fi
    
    # Service URLs
    declare -A services=(
        ["Kibana Dashboard"]="5601"
        ["Spark Master UI"]="8080"
        ["Spark Worker UI"]="8081"
        ["MinIO Console"]="9001"
        ["MinIO API"]="9000"
        ["Elasticsearch"]="9200"
        ["Kafka (external)"]="9092"
        ["Zookeeper"]="2181"
    )
    
    print_color "$GREEN" "\n=== DATA PIPELINE SERVICES - $environment ENVIRONMENT ==="
    print_color "$BLUE" "Environment detected: $(echo $environment | tr '[:lower:]' '[:upper:]')"
    
    if [[ "$environment" == "codespaces" ]]; then
        print_color "$YELLOW" "Codespace: ${CODESPACE_NAME}"
        print_color "$YELLOW" "Domain: ${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    fi
    
    echo ""
    
    for service in "${!services[@]}"; do
        local port=${services[$service]}
        local url
        
        if [[ "$environment" == "codespaces" ]]; then
            url="https://${CODESPACE_NAME}-${port}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"
        else
            url="http://localhost:${port}/"
        fi
        
        printf "%-20s %s\n" "$service:" "$url"
    done
    
    echo ""
    print_color "$GREEN" "=== CONNECTION STRINGS ==="
    
    # Kafka connection strings
    if [[ "$environment" == "codespaces" ]]; then
        kafka_external="$CODESPACE_NAME-9092.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:443"
        elasticsearch_url="https://$CODESPACE_NAME-9200.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
        minio_endpoint="$CODESPACE_NAME-9000.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:443"
    else
        kafka_external="localhost:9092"
        elasticsearch_url="http://localhost:9200"
        minio_endpoint="localhost:9000"
    fi
    
    echo "Kafka (external):     $kafka_external"
    echo "Kafka (internal):     kafka:29092"
    echo "Elasticsearch:        $elasticsearch_url"
    echo "MinIO Endpoint:       $minio_endpoint"
    echo ""
}

# Function to update docker-compose with environment-specific settings
update_docker_compose() {
    local environment=$1
    
    print_color "$YELLOW" "Updating docker-compose.yml for $environment environment..."
    
    # Create a backup
    cp docker-compose.yml docker-compose.yml.backup
    
    if [[ "$environment" == "codespaces" ]]; then
        # Update Kafka advertised listeners for Codespaces
        # This is more complex and might require template substitution
        print_color "$GREEN" "Docker Compose updated for Codespaces"
        print_color "$YELLOW" "Note: You may need to configure port forwarding visibility in Codespaces"
    else
        print_color "$GREEN" "Docker Compose is already configured for local development"
    fi
}

# Function to create environment-specific override file
create_override() {
    local environment=$1
    
    if [[ "$environment" == "codespaces" ]]; then
        print_color "$YELLOW" "Creating docker-compose.codespaces.yml override..."
        
        cat > docker-compose.codespaces.yml << 'EOF'
version: '3.8'

# GitHub Codespaces Override Configuration
# This file provides Codespaces-specific settings

services:
  kafka:
    environment:
      # Override Kafka listeners for Codespaces
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://kafka:9092
      # Additional Codespaces-specific config can go here
      
  kibana:
    environment:
      # Ensure Kibana works behind Codespaces proxy
      - SERVER_BASEPATH=/
      - SERVER_REWRITEBASEPATH=false
      
  minio:
    environment:
      # MinIO console should work with Codespaces forwarding
      - MINIO_BROWSER_REDIRECT_URL=off
EOF
        
        print_color "$GREEN" "Codespaces override file created!"
        print_color "$BLUE" "Use: docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml up"
    fi
}

# Function to show commands for starting services
show_commands() {
    local environment=$1
    
    print_color "$GREEN" "\n=== QUICK START COMMANDS ==="
    
    if [[ "$environment" == "codespaces" ]]; then
        echo "# Start all services (Codespaces):"
        echo "docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d"
        echo ""
        echo "# Start specific services:"
        echo "docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d zookeeper kafka minio elasticsearch kibana"
        echo ""
        echo "# Run ingestion (when ready):"
        echo "docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml --profile ingestion up ingestion-service"
        echo ""
        echo "# Run processing (when ready):"
        echo "docker-compose -f docker-compose.yml -f docker-compose.codespaces.yml --profile processing up spark-processor"
    else
        echo "# Start all services (Local):"
        echo "docker-compose up -d"
        echo ""
        echo "# Start specific services:"
        echo "docker-compose up -d zookeeper kafka minio elasticsearch kibana"
        echo ""
        echo "# Run ingestion (when ready):"
        echo "docker-compose --profile ingestion up ingestion-service"
        echo ""
        echo "# Run processing (when ready):"
        echo "docker-compose --profile processing up spark-processor"
    fi
    
    echo ""
    echo "# View logs:"
    echo "docker-compose logs -f [service-name]"
    echo ""
    echo "# Stop all services:"
    echo "docker-compose down"
    echo ""
}

# Main execution
main() {
    print_color "$BLUE" "🚀 Data Pipeline Environment Setup"
    print_color "$BLUE" "================================="
    
    # Detect environment
    local environment=$(detect_environment)
    
    # Generate URLs and connection info
    generate_urls "$environment"
    
    # Create override files if needed
    create_override "$environment"
    
    # Show quick start commands
    show_commands "$environment"
    
    # Update .env file with detected environment
    if [[ -f .env ]]; then
        # Update the ENVIRONMENT variable in .env
        if grep -q "^ENVIRONMENT=" .env; then
            sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=$environment/" .env
        else
            echo "ENVIRONMENT=$environment" >> .env
        fi
        print_color "$GREEN" "Updated .env with detected environment: $environment"
    fi
    
    print_color "$GREEN" "\n✅ Environment setup complete!"
    
    if [[ "$environment" == "codespaces" ]]; then
        print_color "$YELLOW" "\n📝 Codespaces Notes:"
        echo "• Make sure to set port visibility to 'Public' for web UIs"
        echo "• Some services may take longer to start in Codespaces"
        echo "• Use the generated URLs above to access services"
    fi
}

# Run main function
main "$@"
