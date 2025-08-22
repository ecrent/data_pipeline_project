#!/bin/bash
# =============================================================================
# DATA PIPELINE PROJECT - WSL INSTALLATION SCRIPT
# =============================================================================
# This script installs all dependencies and sets up the data pipeline on WSL
# Tested on Ubuntu 22.04 LTS
#
# Usage: bash install-wsl.sh
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "=================================================================="
    echo "$1"
    echo "=================================================================="
    echo -e "${NC}"
}

# Check if running on WSL
check_wsl() {
    if grep -qi microsoft /proc/version 2>/dev/null || [[ "$WSL_DISTRO_NAME" ]]; then
        log_info "✅ WSL environment detected"
        IS_WSL=true
        
        # Check if Docker Desktop is accessible from WSL
        if command -v docker &> /dev/null && docker info &> /dev/null; then
            log_success "Docker Desktop integration is working"
            DOCKER_AVAILABLE=true
        else
            log_warning "Docker Desktop integration not available"
            log_warning "Please ensure Docker Desktop for Windows is:"
            log_warning "  1. Installed on your Windows host"
            log_warning "  2. Running with WSL2 integration enabled"
            log_warning "  3. Has your WSL distribution enabled in Settings"
            DOCKER_AVAILABLE=false
        fi
    else
        log_info "Native Linux environment detected"
        IS_WSL=false
        DOCKER_AVAILABLE=false
    fi
}

# Update system packages
update_system() {
    print_header "UPDATING SYSTEM PACKAGES"
    
    log_info "Updating package lists..."
    sudo apt update
    
    log_info "Upgrading existing packages..."
    sudo apt upgrade -y
    
    log_info "Installing essential packages..."
    sudo apt install -y \
        curl \
        wget \
        git \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential \
        python3 \
        python3-pip \
        python3-venv
    
    log_success "System packages updated"
}

# Install Docker
install_docker() {
    print_header "INSTALLING DOCKER"
    
    if command -v docker &> /dev/null; then
        log_info "Docker already installed: $(docker --version)"
        return
    fi
    
    log_info "Adding Docker's official GPG key..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    log_info "Adding Docker repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    log_info "Installing Docker..."
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    log_info "Adding user to docker group..."
    sudo usermod -aG docker $USER
    
    log_info "Starting Docker service..."
    sudo systemctl enable docker
    sudo systemctl start docker
    
    log_success "Docker installed successfully"
    log_warning "You may need to logout and login again for docker group membership to take effect"
}

# Install Docker Compose
install_docker_compose() {
    print_header "INSTALLING DOCKER COMPOSE"
    
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose already installed: $(docker-compose --version)"
        return
    fi
    
    log_info "Installing Docker Compose..."
    sudo apt install -y docker-compose-plugin
    
    # Create docker-compose symlink for compatibility
    if ! command -v docker-compose &> /dev/null; then
        log_info "Creating docker-compose symlink..."
        sudo ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
    fi
    
    log_success "Docker Compose installed successfully"
}

# Install Python dependencies
setup_python() {
    print_header "SETTING UP PYTHON ENVIRONMENT"
    
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    log_info "Installing Python dependencies..."
    pip install \
        kafka-python==2.2.15 \
        elasticsearch==8.19.0 \
        pandas==2.3.1 \
        numpy==2.3.1 \
        matplotlib==3.10.3 \
        seaborn==0.13.2 \
        requests==2.32.4 \
        pyarrow==16.1.0 \
        minio==7.2.7
    
    log_success "Python environment setup complete"
}

# Clone or update project
setup_project() {
    print_header "SETTING UP PROJECT"
    
    PROJECT_DIR="$HOME/data_pipeline_project"
    
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Project directory exists. Updating..."
        cd "$PROJECT_DIR"
        git pull origin main || log_warning "Could not update git repository"
    else
        log_info "Cloning project repository..."
        git clone https://github.com/ecrent/data_pipeline_project.git "$PROJECT_DIR" || {
            log_warning "Could not clone from GitHub. Creating project structure manually..."
            mkdir -p "$PROJECT_DIR"
            cd "$PROJECT_DIR"
            
            # If this script is being run from the project directory, copy files
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
                log_info "Copying project files from current directory..."
                cp -r "$SCRIPT_DIR/"* "$PROJECT_DIR/" 2>/dev/null || true
            fi
        }
    fi
    
    cd "$PROJECT_DIR"
    
    # Set environment to local for WSL
    log_info "Configuring environment for WSL..."
    sed -i 's/ENVIRONMENT=codespaces/ENVIRONMENT=local/' .env 2>/dev/null || log_warning "Could not update .env file"
    
    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p data logs
    
    # Set permissions
    chmod +x scripts/*.py 2>/dev/null || true
    chmod +x processing/*.py 2>/dev/null || true
    chmod +x ingestion/src/*.py 2>/dev/null || true
    chmod +x analytics/*.py 2>/dev/null || true
    chmod +x monitoring/*.py 2>/dev/null || true
    
    log_success "Project setup complete in $PROJECT_DIR"
}

# Configure system limits for containers
configure_system() {
    print_header "CONFIGURING SYSTEM SETTINGS"
    
    log_info "Setting up system limits for containers..."
    
    # Increase vm.max_map_count for Elasticsearch
    echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf > /dev/null
    sudo sysctl -p
    
    # Increase file descriptor limits
    echo "*               soft    nofile          65536" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "*               hard    nofile          65536" | sudo tee -a /etc/security/limits.conf > /dev/null
    
    log_success "System configuration complete"
}

# Start services
start_services() {
    print_header "STARTING SERVICES"
    
    log_info "Building and starting Docker containers..."
    
    # Pull images first to show progress
    log_info "Pulling Docker images (this may take a while)..."
    docker-compose pull
    
    log_info "Starting services..."
    docker-compose up -d
    
    log_info "Waiting for services to be ready..."
    sleep 30
    
    log_success "Services started successfully"
}

# Verify installation
verify_installation() {
    print_header "VERIFYING INSTALLATION"
    
    log_info "Checking service health..."
    
    # Check if containers are running
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Some containers are not running!"
        docker-compose ps
        return 1
    fi
    
    # Wait a bit more for services to fully initialize
    log_info "Waiting for services to fully initialize..."
    sleep 60
    
    # Test basic connectivity
    log_info "Testing Kafka connectivity..."
    timeout 10 docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092 > /dev/null || log_warning "Kafka connectivity test failed"
    
    log_info "Testing Elasticsearch connectivity..."
    timeout 10 curl -s http://localhost:9200/_cluster/health > /dev/null || log_warning "Elasticsearch connectivity test failed"
    
    log_info "Testing MinIO connectivity..."
    timeout 10 curl -s http://localhost:9000/minio/health/live > /dev/null || log_warning "MinIO connectivity test failed"
    
    log_success "Installation verification complete"
}

# Main installation function
main() {
    print_header "DATA PIPELINE PROJECT - WSL INSTALLATION"
    
    log_info "Starting installation process..."
    log_info "This will install: Docker, Docker Compose, Python dependencies, and the data pipeline"
    
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
    
    # Run installation steps
    check_wsl
    update_system
    install_docker
    install_docker_compose
    configure_system
    setup_project
    setup_python
    start_services
    verify_installation
    
    # Final success message
    print_header "INSTALLATION COMPLETE!"
    
    echo -e "${GREEN}"
    echo "🎉 Data Pipeline Project is now installed and running!"
    echo ""
    echo "📊 Access your services:"
    echo "  • Spark Master UI:    http://localhost:8080"
    echo "  • Spark Worker UI:    http://localhost:8081" 
    echo "  • Kibana Dashboard:   http://localhost:5601"
    echo "  • MinIO Console:      http://localhost:9001 (minioadmin/minioadmin123)"
    echo ""
    echo "🚀 Quick start commands:"
    echo "  cd ~/data_pipeline_project"
    echo "  source venv/bin/activate"
    echo "  python monitoring/pipeline_monitor.py  # Check system health"
    echo "  python processing/run_complete_pipeline.py  # Process your data"
    echo ""
    echo "📚 Documentation:"
    echo "  • README.md - Complete setup guide"
    echo "  • QUICK_START.md - Command reference" 
    echo "  • ARCHITECTURE_OVERVIEW.md - Technical details"
    echo -e "${NC}"
    
    if groups $USER | grep -q docker; then
        log_success "Docker group membership is active"
    else
        log_warning "Please logout and login again to activate Docker group membership"
        log_warning "Then run: cd ~/data_pipeline_project && docker-compose up -d"
    fi
}

# Run main installation
main "$@"
