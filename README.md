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

1. **Download the dataset:**
   - Visit: https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store  
   - Download the CSV file
   - Place it in the `data/` folder as `events.csv`

2. **Validate your data (optional):**
   ```bash
   # Ensure CSV has required columns (user_id, event_type, product_id, price)
   python scripts/validate_data.py
   ```

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
pip install -r requirements.txt
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

### Data Ingestion
```bash
# Activate virtual environment
source venv/bin/activate

# Ingest data to Kafka (streams CSV events to Kafka)
python ingestion/kafka_producer.py

# Monitor ingestion progress - you'll see real-time statistics
```

### Data Processing
```bash
# Process streamed data (consumes from Kafka, processes with Spark)
python processing/data_processor.py

# Monitor system health
python monitoring/pipeline_monitor.py
```

### Complete Pipeline Workflow
```bash
# 1. Start services
docker compose up -d

# 2. Activate Python environment
source venv/bin/activate

# 3. Run complete pipeline
python ingestion/kafka_producer.py        # Stream data to Kafka
python processing/data_processor.py   # Process data with Spark

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
