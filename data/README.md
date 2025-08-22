# E-commerce Electronics Dataset

This directory contains the e-commerce events dataset for our data pipeline.

## 📊 Dataset: E-commerce Events History in Electronics Store

**Source**: [mkechinov/ecommerce-events-history-in-electronics-store](https://www.kaggle.com/mkechinov/ecommerce-events-history-in-electronics-store)

This dataset contains behavioral data from a large multi-category online electronics store. Each row represents a user interaction event with products.

## 📥 Manual Download Instructions

1. **Visit Kaggle Dataset Page**  
   Go to: https://www.kaggle.com/mkechinov/ecommerce-events-history-in-electronics-store

2. **Download the Dataset**  
   - Click the "Download" button (you may need to create a Kaggle account)
   - Extract the ZIP file if needed
   - Find the main CSV file (usually the largest one)

3. **Place in Project**  
   - Save the main events CSV file as `electronics.csv` in this directory
   - The file path should be: `/workspaces/data_pipeline_project/data/electronics.csv`

4. **Verify Setup**  
   ```bash
   make check-data
   ```

## 📊 Dataset Details

### Schema Overview
The dataset typically includes columns such as:
- `event_time`: Timestamp of the event
- `event_type`: Type of event (view, cart, purchase, etc.)
- `product_id`: Unique product identifier
- `category_id`: Product category ID
- `category_code`: Human-readable category path
- `brand`: Product brand
- `price`: Product price in USD
- `user_id`: Unique user identifier
- `user_session`: User session ID

### Expected Structure
```
data/
├── README.md
└── electronics.csv  # Your downloaded dataset (several GB)
```

### Sample Data Format
```csv
event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session
2019-10-01 00:00:00 UTC,view,1003461,2103807459595387724,electronics.smartphone,xiaomi,489.07,520088904,4d3b30da-a5e4-49df-b1a8-ba5943f1dd33
2019-10-01 00:00:00 UTC,view,5000088,2103807459595387724,electronics.video.tv,samsung,1545.77,530496790,8e5f4f83-366c-4f70-860e-ca7417414283
```

## 🔄 Pipeline Integration

Once you place the `electronics.csv` file here, it will be:

1. **Ingested**: Read by the Python service and published to Kafka as JSON events
2. **Processed**: Consumed by Spark for cleaning, validation, and aggregation  
3. **Archived**: Stored in Parquet format in the MinIO data lake
4. **Analyzed**: Customer profiles stored in Elasticsearch and visualized in Kibana

## ✅ Next Steps

After placing your dataset:

```bash
# Verify the dataset is ready
make check-data

# Start the pipeline services  
make start

# Run data ingestion
make ingest

# Run data processing
make process
```

## 🔧 Troubleshooting

### File Not Found
- Ensure the file is named exactly `electronics.csv`
- Check the file is in the correct directory
- Verify the file has read permissions

### Large File Handling
- The dataset can be several GB in size
- Ensure sufficient disk space is available
- The pipeline is designed to handle large files efficiently

### Download Issues
- You may need to accept the dataset terms on Kaggle
- Ensure you're logged into Kaggle
- Check your internet connection for large downloads
