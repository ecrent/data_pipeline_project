# 🏗️ Infrastructure as Code (IaC) - Deployment Guide

## 📋 **Overview**
This data pipeline project is designed with Infrastructure as Code principles for easy deployment, scaling, and maintenance across different environments.

---

## 🚀 **Deployment Options**

### **🎯 Option 1: Zero-Experience Installation (WSL/Ubuntu)**

**Perfect for:** New users, Windows developers, local development

```bash
# One command installs everything
curl -L https://raw.githubusercontent.com/ecrent/data_pipeline_project/main/install-wsl.sh -o install-wsl.sh && chmod +x install-wsl.sh && ./install-wsl.sh
```

**What it does:**
- ✅ Installs Docker + Docker Compose
- ✅ Sets up Python environment  
- ✅ Configures system limits
- ✅ Starts all services
- ✅ Verifies installation

---

### **🔧 Option 2: Quick Setup (Existing Environment)**

**Perfect for:** Users with Docker already installed

```bash
# Clone and setup
git clone https://github.com/ecrent/data_pipeline_project.git
cd data_pipeline_project
chmod +x setup.sh && ./setup.sh
```

---

### **⚙️ Option 3: Manual Docker Compose**

**Perfect for:** Advanced users, production deployments

```bash
git clone https://github.com/ecrent/data_pipeline_project.git
cd data_pipeline_project

# Configure environment
cp .env.example .env  # Edit as needed

# Start services
docker compose up -d

# Verify
docker compose ps
```

---

## 🏗️ **Infrastructure Components**

### **Container Orchestration**
- **Docker Compose**: Multi-service orchestration
- **Health Checks**: Automatic service dependency management  
- **Environment Detection**: Codespaces vs Local vs Production
- **Port Configuration**: Flexible port mapping

### **Service Architecture**
```yaml
# docker-compose.yml structure:
services:
  zookeeper:      # Kafka coordination
  kafka:          # Event streaming (3 partitions)
  spark-master:   # Distributed processing coordinator
  spark-worker:   # Processing worker nodes (scalable)
  elasticsearch:  # Real-time analytics database
  kibana:         # Data visualization
  minio:          # S3-compatible data lake
```

### **Network & Storage**
- **Custom Network**: Isolated service communication
- **Persistent Volumes**: Data persistence across restarts
- **Health Monitoring**: Comprehensive service health checks

---

## 🔧 **Configuration Management**

### **Environment Variables**
```bash
# .env file structure:
ENVIRONMENT=local                    # codespaces|local|production
KAFKA_PARTITIONS=3                  # Scaling parameter
SPARK_WORKER_MEMORY=2G              # Resource allocation
ES_JAVA_OPTS=-Xms2g -Xmx2g         # Memory tuning
```

### **Service Configuration**
- **Kafka**: Auto-topic creation, 3-partition setup
- **Spark**: Cluster mode with scalable workers
- **Elasticsearch**: Single-node development, cluster-ready
- **MinIO**: S3-compatible with console access

---

## 📊 **Scaling Configuration**

### **Horizontal Scaling**
```bash
# Scale Spark workers
docker compose up -d --scale spark-worker=5

# Scale Kafka (requires configuration changes)
# Edit docker-compose.yml to add kafka-2, kafka-3, etc.
```

### **Resource Allocation**
```yaml
# In docker-compose.yml:
services:
  elasticsearch:
    deploy:
      resources:
        limits:
          memory: 4g
        reservations:
          memory: 2g
```

### **Performance Tuning**
```bash
# System limits (automated in install scripts)
vm.max_map_count=262144              # Elasticsearch requirement
fs.file-max=65536                    # File descriptor limits
net.core.somaxconn=1024              # Network connections
```

---

## 🌍 **Multi-Environment Support**

### **Development (Local/WSL)**
```bash
ENVIRONMENT=local
# Uses localhost URLs
# Single-node services
# Development-friendly settings
```

### **GitHub Codespaces**
```bash
ENVIRONMENT=codespaces
# Auto-detects Codespace URLs
# Port forwarding support
# Cloud-optimized configuration
```

### **Production (Future)**
```bash
ENVIRONMENT=production
# Cluster configurations
# High availability settings
# Enhanced security
```

---

## 🔐 **Security & Best Practices**

### **Development Security**
- **Default Credentials**: Clearly documented (minioadmin/minioadmin123)
- **Network Isolation**: Custom Docker network
- **No External Exposure**: Services only accessible via localhost

### **Production Ready Features**
- **Environment Variable Management**: All secrets configurable
- **Health Check Integration**: Ready for load balancers
- **Logging Configuration**: Structured logging support
- **Monitoring Endpoints**: Health check APIs

---

## 📦 **Deployment Automation**

### **CI/CD Ready Structure**
```
.
├── docker-compose.yml           # Main orchestration
├── docker-compose.codespaces.yml  # Environment override
├── .env                        # Configuration
├── install-wsl.sh              # Full installation
├── setup.sh                    # Quick setup
├── requirements.txt            # Python dependencies
└── README.md                   # User documentation
```

### **Automated Testing**
```bash
# Health verification (built into install scripts)
python monitoring/pipeline_monitor.py
# Expected: All services "Healthy" ✅
```

### **Deployment Verification**
```bash
# End-to-end test
python processing/run_complete_pipeline.py --max-events 1000
# Expected: Customer profiles generated and stored
```

---

## 🔄 **Maintenance & Operations**

### **Service Management**
```bash
# Start/stop all services
docker compose up -d
docker compose down

# Individual service management
docker compose restart kafka
docker compose logs -f elasticsearch

# Scale specific services
docker compose up -d --scale spark-worker=3
```

### **Data Management**
```bash
# Backup data volumes
docker run --rm -v pipeline_elasticsearch_data:/data -v $(pwd):/backup alpine tar czf /backup/elasticsearch_backup.tar.gz /data

# Clear all data (reset)
docker compose down -v
```

### **Monitoring & Alerting**
```bash
# Real-time monitoring
python monitoring/pipeline_monitor.py  # Option 2: Continuous monitoring

# Health check endpoint (for external monitoring)
curl http://localhost:9200/_cluster/health
```

---

## 🎯 **Production Deployment Considerations**

### **Resource Requirements**
- **Minimum**: 8GB RAM, 4 CPU cores, 50GB disk
- **Recommended**: 16GB RAM, 8 CPU cores, 100GB disk
- **High Load**: 32GB RAM, 16 CPU cores, 500GB disk

### **High Availability Setup**
```yaml
# Future: Multi-node configuration
kafka:
  replicas: 3
elasticsearch:
  cluster.initial_master_nodes: ["es01", "es02", "es03"]
spark:
  master:
    replicas: 2  # Standby master
```

### **External Dependencies**
- **Load Balancer**: For web interface access
- **External Storage**: S3/GCS for production data lake
- **Monitoring**: Prometheus/Grafana integration
- **Secrets Management**: Vault/K8s secrets

---

## 📊 **Success Metrics**

### **Deployment Success Indicators**
✅ **All containers running**: `docker compose ps` shows "Up"  
✅ **Health checks passing**: All services report "Healthy"  
✅ **Data processing working**: Can process events end-to-end  
✅ **Web interfaces accessible**: All dashboards load correctly  
✅ **Performance metrics met**: >1000 events/second processing  

### **Infrastructure Health**
```bash
# Resource utilization
docker stats

# Service health
curl http://localhost:9200/_cluster/health | jq '.status'  # "green" or "yellow"
curl http://localhost:9000/minio/health/live              # HTTP 200
python monitoring/pipeline_monitor.py                      # All ✅
```

---

## 🎊 **Deployment Complete!**

Your Infrastructure as Code deployment provides:

🏗️ **Reproducible Infrastructure**: One-command deployment  
🔧 **Environment Flexibility**: Codespaces, WSL, Linux support  
📊 **Production Ready**: Scalable, monitorable, maintainable  
🚀 **Zero-Configuration**: Automatic setup with sensible defaults  

**Ready to process millions of events with enterprise-grade reliability!**

---

*💡 **Next**: Use `python analytics/advanced_analytics.py` to see your business intelligence in action!*
