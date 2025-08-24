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
- Java 11+ (OpenJDK recommended, required for Spark processing)

---

## 🖥️ Data Setup

1. **Download the dataset:**
   - Visit: https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store  
   - Download the CSV file
   - Place it in the `data/` folder as `events.csv`

2. **Validate your data (optional):**
   ```bash
   # Check if data file exists and preview structure
   ls -la data/
   head -5 data/events.csv
   
   # Verify CSV has required columns: event_time, event_type, product_id, price, user_id
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
# Install Python dependencies and Java (required for Spark)
sudo apt install python3 python3-pip python3-venv git curl openjdk-11-jdk -y

# If you haven't cloned the project yet:
# git clone <your-repository-url>
# cd data_pipeline_project

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
# 1. Start all services and wait for initialization
docker compose up -d && sleep 120

# 2. Activate Python environment  
source venv/bin/activate

# 3. Run the complete data pipeline (execute in sequence)
python ingestion/kafka_producer.py     # Stream CSV data to Kafka topics
python processing/data_processor.py    # Process with Spark, store in MinIO + Elasticsearch

# 4. Monitor the pipeline
python monitoring/pipeline_monitor.py  # Check system health and metrics
```

### Access Web Interfaces
- **Spark Master UI:** http://localhost:8080 (Monitor cluster and job execution)
- **Kibana Dashboard:** http://localhost:5601 (Customer analytics and visualizations)
- **MinIO Console:** http://localhost:9001 (Data lake management - login: `minioadmin`/`minioadmin123`)
- **Elasticsearch API:** http://localhost:9200 (Direct database queries)

### Verify Pipeline Success
```bash
# Check if data was processed successfully
curl -s "http://localhost:9200/customer_profiles/_count" | jq '.'

# View sample customer profile
curl -s "http://localhost:9200/customer_profiles/_search?size=1" | jq '.hits.hits[0]._source'
```

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

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| Kibana | 5601 | Analytics dashboard | http://localhost:5601 |
| Spark Master | 8080 | Cluster monitoring | http://localhost:8080 |
| MinIO Console | 9001 | Storage management | http://localhost:9001 |
| Elasticsearch | 9200 | Search API | http://localhost:9200/_cluster/health |
| Kafka | 9092 | Message streaming | Internal (docker network) |
| Zookeeper | 2181 | Kafka coordination | Internal (docker network) |

---

## 🆘 Troubleshooting

### Common Issues:

**Services not starting:**
```bash
# Check service logs
docker compose logs -f elasticsearch
docker compose logs -f kafka

# Restart specific service
docker compose restart elasticsearch
```

**Out of memory errors:**
```bash
# Check system resources
free -h
docker stats

# Increase Elasticsearch memory (if needed)
export ES_JAVA_OPTS="-Xms2g -Xmx2g"
docker compose up -d elasticsearch
```

**Data file not found:**
```bash
# Ensure data file exists
ls -la data/events.csv

# Check file format
head -5 data/events.csv
```

**Python import errors:**
```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

---
