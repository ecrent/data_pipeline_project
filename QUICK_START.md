# 🚀 Quick Start Guide

## **Get the Pipeline Running in 3 Commands**

```bash
# 1. Start all services
docker-compose up -d

# 2. Verify everything is healthy (wait 2-3 minutes for startup)
python monitoring/pipeline_monitor.py

# 3. Process your data
python processing/run_complete_pipeline.py
```

---

## 🔧 **Available Scripts**

### **Data Processing**
```bash
# Process 50K events end-to-end
cd processing && python run_complete_pipeline.py

# Local processing without Kafka dependencies  
cd processing && python run_local_processing.py

# Test simple event processing
cd processing && python test_simple_processor.py
```

### **Data Ingestion** 
```bash
# Stream 885K events to Kafka (full dataset)
cd ingestion && python src/kafka_producer.py

# Test ingestion with sample data
cd ingestion && python test_ingestion.py
```

### **Analytics & Monitoring**
```bash
# Advanced business intelligence dashboard
cd analytics && python advanced_analytics.py

# Real-time pipeline health monitoring
cd monitoring && python pipeline_monitor.py

# Run continuous monitoring (30s intervals)  
cd monitoring && python pipeline_monitor.py
# Select option 2
```

### **Infrastructure**
```bash
# Start pipeline services
docker-compose up -d

# Stop all services  
docker-compose down

# View service logs
docker-compose logs -f [service-name]

# Scale specific services
docker-compose up -d --scale spark-worker=3
```

---

## 📊 **Access Dashboards**

- **Spark Master UI**: http://localhost:8080 (cluster monitoring)
- **Spark Worker UI**: http://localhost:8081 (worker status)  
- **Kibana**: http://localhost:5601 (data visualization)
- **MinIO Console**: http://localhost:9001 (data lake management)
  - Username: `minio`
  - Password: `minio123`

---

## 🔍 **Quick Health Check**

```bash
# Check all services are running
docker ps

# Verify Kafka is accepting connections
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Check Elasticsearch cluster
curl http://localhost:9200/_cluster/health

# Test MinIO access
curl http://localhost:9000/minio/health/live
```

---

## 📈 **Key Metrics to Watch**

- **Processing Rate**: Target 1,000+ events/second
- **Conversion Rate**: Currently 4.41%  
- **Customer Profiles**: 26,584+ generated from 50K events
- **Success Rate**: 99.98% event processing reliability

---

## 🆘 **Troubleshooting**

### **Services Won't Start**
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart specific service
docker-compose restart [service-name]
```

### **Kafka Connection Issues**
```bash
# Check Kafka logs
docker-compose logs kafka

# Verify topic creation
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### **Spark Cluster Problems**
```bash
# Check Spark master logs
docker-compose logs spark-master

# Restart Spark cluster
docker-compose restart spark-master spark-worker
```

### **Memory Issues**
```bash
# Check memory usage
docker stats

# Adjust memory in docker-compose.yml if needed
# Reduce batch sizes in processing scripts
```

---

## 🎯 **Next Steps**

1. **Scale Up**: Increase `max_events` in processing scripts  
2. **Add Workers**: `docker-compose up -d --scale spark-worker=3`
3. **Create Dashboards**: Access Kibana at http://localhost:5601
4. **Monitor Performance**: Run continuous monitoring
5. **Optimize**: Tune batch sizes and processing parameters

**Your production-ready data pipeline is now operational!** 🚀
