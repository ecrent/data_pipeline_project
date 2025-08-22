#!/bin/bash
# =============================================================================
# DATA PIPELINE PROJECT - QUICK SETUP SCRIPT  
# =============================================================================
# Simple script to set up the project in an existing environment
# Use this if Docker and Python are already installed
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Data Pipeline Project - Quick Setup${NC}"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker not found. Please install Docker first.${NC}"
    echo "Run: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Set up Python environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment ready${NC}"

# Configure for local environment
echo "⚙️  Configuring for local environment..."
sed -i 's/ENVIRONMENT=codespaces/ENVIRONMENT=local/' .env 2>/dev/null || echo "ENVIRONMENT=local" >> .env

# Set system limits
echo "🔧 Configuring system settings..."
if [ "$(id -u)" != "0" ]; then
    echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf > /dev/null
    sudo sysctl -p
else
    echo "vm.max_map_count=262144" | tee -a /etc/sysctl.conf > /dev/null
    sysctl -p
fi

echo -e "${GREEN}✅ System configured${NC}"

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d

echo "⏳ Waiting for services to initialize..."
sleep 30

echo "🔍 Checking service health..."
docker compose ps

echo -e "${GREEN}"
echo "🎉 Setup complete!"
echo ""
echo "🔗 Access your services:"
echo "  • Spark Master UI:  http://localhost:8080"
echo "  • Kibana Dashboard: http://localhost:5601"  
echo "  • MinIO Console:    http://localhost:9001"
echo ""
echo "🚀 Next steps:"
echo "  source venv/bin/activate"
echo "  python monitoring/pipeline_monitor.py"
echo "  python processing/run_complete_pipeline.py"
echo -e "${NC}"
