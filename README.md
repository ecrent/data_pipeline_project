# 🚀 Batch Processing Data Pipeline

## 📋 Overview
A scalable data pipeline that processes e-commerce events and generates customer insights. Built with Apache Kafka, Spark, Elasticsearch, and containerized with Docker.

**Architecture:** Kafka → Spark → MinIO (Data Lake) + Elasticsearch → Kibana

---

## 🖥️ System Requirements

- Ubuntu 22.04 LTS (or WSL2 with Ubuntu)
- At least 8GB RAM (16GB recommended)  
- 20GB free disk space
- Docker and Docker Compose

---

## 🖥️ Data Setup

- You can download the data from https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store

---

## 🛠️ Installation

### Step 1: Install Docker

**For WSL2/Ubuntu:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Logout and login again, then verify
docker --version && docker compose version
```

### Step 2: Configure System

```bash
# Set Elasticsearch memory limits (required)
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Step 3: Setup Project

```bash
# Install Python dependencies
sudo apt install python3 python3-pip python3-venv git curl -y

# Clone project
git clone https://github.com/ecrent/data_pipeline_project.git
cd data_pipeline_project

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install kafka-python==2.2.15 elasticsearch==8.19.0 pandas==2.3.1 numpy==2.3.1 requests==2.32.4 pyarrow==16.1.0 minio==7.2.7
```

### Step 4: Start Pipeline

```bash
# Start all services
docker compose up -d

# Wait for initialization (2-3 minutes)
sleep 120

# Check service status
docker compose ps
```

---

## 🎯 Usage

### Run Processing Pipeline
```bash
# Activate virtual environment
source venv/bin/activate

# Process data
python processing/run_complete_pipeline.py

# View analytics
python analytics/advanced_analytics.py

# Monitor system
python monitoring/pipeline_monitor.py
```

### Access Web Interfaces
- **Spark Master UI:** http://localhost:8080
- **Kibana Dashboard:** http://localhost:5601  
- **MinIO Console:** http://localhost:9001 (login: `minioadmin`/`minioadmin123`)

---

## 📊 Service Management

```bash
# Start/stop services
docker compose up -d
docker compose down

# View logs
docker compose logs -f [service-name]

# Scale workers
docker compose up -d --scale spark-worker=3
```

---

## 🔧 Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Kibana | 5601 | Analytics dashboard |
| Spark Master | 8080 | Cluster monitoring |
| MinIO Console | 9001 | Storage management |
| Elasticsearch | 9200 | Search API |
| Kafka | 9092 | Message streaming |

---
