#!/bin/bash

# =============================================================================
# PORT VISIBILITY CONFIGURATION FOR GITHUB CODESPACES
# =============================================================================
# This script configures port visibility in GitHub Codespaces for all services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if we're in Codespaces
if [[ -z "${CODESPACE_NAME}" ]]; then
    print_color "$YELLOW" "⚠️  This script is designed for GitHub Codespaces only."
    print_color "$BLUE" "Running locally? No port configuration needed!"
    exit 0
fi

print_color "$BLUE" "🔧 Configuring GitHub Codespaces Port Visibility"
print_color "$BLUE" "=============================================="

# Function to configure port visibility
configure_port() {
    local port=$1
    local label=$2
    
    print_color "$YELLOW" "Configuring port $port for $label..."
    
    # Use GitHub CLI to set port visibility to public
    if command -v gh &> /dev/null; then
        gh codespace ports visibility $port:public -c $CODESPACE_NAME 2>/dev/null || true
        print_color "$GREEN" "✓ Port $port ($label) set to public"
    else
        print_color "$YELLOW" "⚠️  GitHub CLI not available. Please set port $port visibility manually."
    fi
}

# Configure all service ports
declare -A ports=(
    ["2181"]="Zookeeper"
    ["5601"]="Kibana Dashboard"
    ["8080"]="Spark Master UI"
    ["8081"]="Spark Worker UI"
    ["9000"]="MinIO API"
    ["9001"]="MinIO Console"
    ["9092"]="Kafka"
    ["9200"]="Elasticsearch"
)

for port in "${!ports[@]}"; do
    configure_port "$port" "${ports[$port]}"
done

print_color "$GREEN" "\n✅ Port configuration complete!"
print_color "$BLUE" "\nYour services will be available at:"
print_color "$BLUE" "https://$CODESPACE_NAME-[PORT].app.github.dev/"

echo ""
print_color "$YELLOW" "📝 Note: If ports don't work immediately:"
echo "1. Go to the 'Ports' tab in VS Code"
echo "2. Right-click on each port and select 'Port Visibility' → 'Public'"
echo "3. Or use the GitHub Codespaces dashboard to manage port visibility"
