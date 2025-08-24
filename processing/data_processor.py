"""
E-commerce Data Processing Engine
================================
Apache Spark application that processes e-commerce events from Kafka,
performs data cleaning, archival, and customer profile aggregation.

This application:
1. Consumes events from Kafka in batch mode
2. Validates and cleans the data
3. Archives raw data to MinIO (data lake) in Parquet format  
4. Aggregates customer behavior metrics
5. Stores customer profiles in Elasticsearch
6. Provides comprehensive monitoring and logging
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
    else:
        print("⚠️  No .env file found, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")

# Configure logging before importing Spark to avoid conflicts
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, LongType
    from pyspark.sql.window import Window
except ImportError:
    logger.error("❌ PySpark not installed. Run: pip install pyspark>=3.4.0")
    sys.exit(1)

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    logger.error("❌ boto3 not installed. Run: pip install boto3>=1.28.0")
    sys.exit(1)

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError:
    logger.error("❌ Elasticsearch client not installed. Run: pip install elasticsearch>=8.9.0")
    sys.exit(1)

class SparkKafkaProcessor:
    """Handles Kafka data consumption and processing with Spark."""
    
    def __init__(self, spark_session: SparkSession):
        self.spark = spark_session
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'raw_events')
        
    def read_kafka_batch(self) -> Optional[Any]:
        """Read all available messages from Kafka topic."""
        try:
            logger.info(f"🔄 Reading batch data from Kafka topic: {self.kafka_topic}")
            
            # Read from Kafka with earliest offset to get all data
            df = self.spark \
                .read \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.kafka_servers) \
                .option("subscribe", self.kafka_topic) \
                .option("startingOffsets", "earliest") \
                .option("endingOffsets", "latest") \
                .load()
            
            if df.count() == 0:
                logger.warning("⚠️ No messages found in Kafka topic")
                return None
                
            # Parse JSON from Kafka value
            json_df = df.selectExpr("CAST(value AS STRING) as json_str") \
                       .select(F.from_json(F.col("json_str"), self._get_event_schema()).alias("event")) \
                       .select("event.*")
            
            logger.info(f"✅ Successfully read {json_df.count():,} events from Kafka")
            return json_df
            
        except Exception as e:
            logger.error(f"❌ Failed to read from Kafka: {e}")
            return None
    
    def _get_event_schema(self):
        """Define the schema for incoming events."""
        return StructType([
            StructField("event_id", StringType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("event_type", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("user_session", StringType(), True),
            StructField("product", StructType([
                StructField("id", StringType(), True),
                StructField("category_id", StringType(), True),
                StructField("category_code", StringType(), True),
                StructField("brand", StringType(), True),
                StructField("price", DoubleType(), True)
            ]), True),
            StructField("ingestion_timestamp", TimestampType(), True),
            StructField("source", StringType(), True)
        ])

class DataLakeManager:
    """Manages data archival to MinIO (S3-compatible storage)."""
    
    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
        self.bucket_name = os.getenv('MINIO_BUCKET', 'data-lake')
        self.s3_client = None
        
    def initialize(self) -> bool:
        """Initialize connection to MinIO."""
        try:
            logger.info(f"🔗 Connecting to MinIO at: {self.endpoint}")
            
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f'http://{self.endpoint}',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name='us-east-1'  # MinIO doesn't care about region
            )
            
            # Check if bucket exists, create if not
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"✅ Bucket '{self.bucket_name}' exists")
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.info(f"📦 Creating bucket: {self.bucket_name}")
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    raise e
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MinIO: {e}")
            return False
    
    def archive_data(self, df, partition_date: str) -> bool:
        """Archive DataFrame to MinIO in Parquet format."""
        try:
            # Create partition path
            s3_path = f"s3a://{self.bucket_name}/raw_events/year={partition_date[:4]}/month={partition_date[5:7]}/day={partition_date[8:10]}"
            
            logger.info(f"💾 Archiving data to: {s3_path}")
            
            # Write to MinIO in Parquet format (S3 config already set in SparkSession)
            df.write \
                .mode('overwrite') \
                .parquet(s3_path)
            
            logger.info(f"✅ Data archived successfully to MinIO")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to archive data: {e}")
            return False

class CustomerProfileAggregator:
    """Aggregates customer behavior metrics from e-commerce events."""
    
    def __init__(self, spark_session: SparkSession):
        self.spark = spark_session
    
    def generate_customer_profiles(self, events_df) -> Any:
        """Generate comprehensive customer profiles from events."""
        logger.info("🔍 Generating customer profiles...")
        
        try:
            # Flatten product data for easier aggregation
            flattened_df = events_df.select(
                "user_id",
                "event_type", 
                "timestamp",
                "user_session",
                F.col("product.id").alias("product_id"),
                F.col("product.category_code").alias("category_code"),
                F.col("product.brand").alias("brand"),
                F.col("product.price").alias("price")
            ).filter(F.col("user_id").isNotNull())
            
            # Calculate customer metrics
            customer_profiles = flattened_df.groupBy("user_id").agg(
                # Basic metrics
                F.count("*").alias("total_events"),
                F.countDistinct("user_session").alias("total_sessions"),
                F.countDistinct("product_id").alias("unique_products_viewed"),
                F.countDistinct("category_code").alias("unique_categories"),
                F.countDistinct("brand").alias("unique_brands"),
                
                # Event type breakdown
                F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("total_views"),
                F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("total_cart_additions"),
                F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("total_purchases"),
                F.sum(F.when(F.col("event_type") == "remove_from_cart", 1).otherwise(0)).alias("total_cart_removals"),
                
                # Financial metrics
                F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_revenue"),
                F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))).alias("avg_purchase_value"),
                F.max(F.when(F.col("event_type") == "purchase", F.col("price"))).alias("max_purchase_value"),
                F.min(F.when(F.col("event_type") == "purchase", F.col("price"))).alias("min_purchase_value"),
                
                # Temporal metrics
                F.min("timestamp").alias("first_seen"),
                F.max("timestamp").alias("last_seen"),
                
                # Favorite categories and brands (most frequent)
                F.expr("first(category_code)").alias("most_viewed_category"),  # Simplified - could be improved
                F.expr("first(brand)").alias("most_viewed_brand")
            )
            
            # Calculate derived metrics
            customer_profiles = customer_profiles.withColumn(
                "conversion_rate",
                F.when(F.col("total_views") > 0, 
                      F.col("total_purchases") / F.col("total_views")).otherwise(0.0)
            ).withColumn(
                "cart_abandonment_rate",
                F.when(F.col("total_cart_additions") > 0,
                      F.col("total_cart_removals") / F.col("total_cart_additions")).otherwise(0.0)
            ).withColumn(
                "avg_session_duration_events",
                F.col("total_events") / F.col("total_sessions")
            ).withColumn(
                "customer_lifetime_days",
                F.datediff(F.col("last_seen"), F.col("first_seen")) + 1
            ).withColumn(
                "profile_generated_at",
                F.current_timestamp()
            )
            
            # Add customer segmentation
            customer_profiles = self._add_customer_segmentation(customer_profiles)
            
            logger.info(f"✅ Generated {customer_profiles.count():,} customer profiles")
            return customer_profiles
            
        except Exception as e:
            logger.error(f"❌ Failed to generate customer profiles: {e}")
            return None
    
    def _add_customer_segmentation(self, profiles_df):
        """Add customer segmentation based on behavior."""
        return profiles_df.withColumn(
            "customer_segment",
            F.when(
                (F.col("total_purchases") >= 5) & (F.col("total_revenue") >= 1000),
                "High Value"
            ).when(
                (F.col("total_purchases") >= 2) & (F.col("total_revenue") >= 100),
                "Regular"
            ).when(
                F.col("total_purchases") >= 1,
                "Occasional"
            ).when(
                (F.col("total_views") >= 10) & (F.col("total_cart_additions") >= 1),
                "Browser"
            ).otherwise("New/Inactive")
        )

class ElasticsearchManager:
    """Manages data storage to Elasticsearch."""
    
    def __init__(self):
        self.host = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
        self.port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        self.index = os.getenv('ELASTICSEARCH_INDEX', 'customer_profiles')
        self.client = None
        
    def initialize(self) -> bool:
        """Initialize Elasticsearch connection."""
        try:
            logger.info(f"🔗 Connecting to Elasticsearch at: {self.host}:{self.port}")
            
            self.client = Elasticsearch(
                [f"http://{self.host}:{self.port}"],
                timeout=30,
                retry_on_timeout=True,
                max_retries=3
            )
            
            # Test connection
            if self.client.ping():
                logger.info("✅ Elasticsearch connection established")
                self._create_index_if_not_exists()
                return True
            else:
                logger.error("❌ Failed to ping Elasticsearch")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Elasticsearch: {e}")
            return False
    
    def _create_index_if_not_exists(self):
        """Create index with proper mapping if it doesn't exist."""
        try:
            if not self.client.indices.exists(index=self.index):
                logger.info(f"📋 Creating Elasticsearch index: {self.index}")
                
                mapping = {
                    "mappings": {
                        "properties": {
                            "user_id": {"type": "keyword"},
                            "customer_segment": {"type": "keyword"},
                            "total_events": {"type": "long"},
                            "total_sessions": {"type": "long"},
                            "total_purchases": {"type": "long"},
                            "total_revenue": {"type": "double"},
                            "conversion_rate": {"type": "double"},
                            "first_seen": {"type": "date"},
                            "last_seen": {"type": "date"},
                            "profile_generated_at": {"type": "date"}
                        }
                    }
                }
                
                self.client.indices.create(index=self.index, body=mapping)
                logger.info(f"✅ Index '{self.index}' created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
    
    def store_profiles(self, profiles_df) -> bool:
        """Store customer profiles to Elasticsearch."""
        try:
            logger.info(f"💾 Storing customer profiles to Elasticsearch index: {self.index}")
            
            # Convert Spark DataFrame to list of dictionaries
            profiles_data = profiles_df.collect()
            
            # Prepare documents for bulk indexing
            documents = []
            for row in profiles_data:
                doc = {
                    "_index": self.index,
                    "_id": row["user_id"],  # Use user_id as document ID
                    "_source": row.asDict()
                }
                
                # Convert datetime objects to ISO format strings
                for key, value in doc["_source"].items():
                    if hasattr(value, 'isoformat'):
                        doc["_source"][key] = value.isoformat()
                
                documents.append(doc)
            
            # Bulk index documents
            success_count, errors = bulk(self.client, documents, refresh=True)
            
            if errors:
                logger.warning(f"⚠️ Some documents failed to index: {len(errors)} errors")
                for error in errors[:5]:  # Show first 5 errors
                    logger.warning(f"   Error: {error}")
            
            logger.info(f"✅ Successfully stored {success_count:,} customer profiles")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store profiles: {e}")
            return False

class EcommerceDataProcessor:
    """Main orchestrator for the e-commerce data processing pipeline."""
    
    def __init__(self):
        # Load configuration from environment
        self.spark_master_url = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
        self.app_name = "EcommerceDataProcessor"
        self.batch_date = datetime.now().strftime('%Y-%m-%d')
        
        # Initialize components
        self.spark = None
        self.kafka_processor = None
        self.data_lake_manager = DataLakeManager()
        self.profile_aggregator = None
        self.elasticsearch_manager = ElasticsearchManager()
        
    def initialize_spark(self) -> bool:
        """Initialize Spark session with required configurations."""
        try:
            logger.info(f"🔥 Initializing Spark session...")
            logger.info(f"   Master URL: {self.spark_master_url}")
            
            self.spark = SparkSession.builder \
                .appName(self.app_name) \
                .master(self.spark_master_url) \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
                .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.367") \
                .config("spark.hadoop.fs.s3a.endpoint", f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}") \
                .config("spark.hadoop.fs.s3a.access.key", os.getenv('MINIO_ACCESS_KEY', 'minioadmin')) \
                .config("spark.hadoop.fs.s3a.secret.key", os.getenv('MINIO_SECRET_KEY', 'minioadmin123')) \
                .config("spark.hadoop.fs.s3a.path.style.access", "true") \
                .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
                .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
                .getOrCreate()
            
            # Set log level to reduce noise
            self.spark.sparkContext.setLogLevel("WARN")
            
            logger.info("✅ Spark session initialized successfully")
            
            # Initialize other components that need Spark
            self.kafka_processor = SparkKafkaProcessor(self.spark)
            self.profile_aggregator = CustomerProfileAggregator(self.spark)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Spark: {e}")
            return False
    
    def run_processing_pipeline(self) -> bool:
        """Execute the complete data processing pipeline."""
        try:
            logger.info("🚀 Starting E-commerce Data Processing Pipeline")
            logger.info("=" * 60)
            
            # Step 1: Initialize all components
            if not self._initialize_all_components():
                return False
            
            # Step 2: Read data from Kafka
            logger.info("📖 Step 1: Reading events from Kafka...")
            events_df = self.kafka_processor.read_kafka_batch()
            if events_df is None:
                logger.error("❌ No data available from Kafka")
                return False
            
            # Step 3: Data quality checks and cleaning
            logger.info("🧹 Step 2: Data quality checks and cleaning...")
            cleaned_df = self._clean_and_validate_data(events_df)
            if cleaned_df is None:
                return False
            
            # Step 4: Archive raw data to data lake
            logger.info("💾 Step 3: Archiving data to MinIO data lake...")
            if not self.data_lake_manager.archive_data(cleaned_df, self.batch_date):
                logger.warning("⚠️ Data archival failed, but continuing with processing...")
            
            # Step 5: Generate customer profiles
            logger.info("👥 Step 4: Generating customer profiles...")
            customer_profiles = self.profile_aggregator.generate_customer_profiles(cleaned_df)
            if customer_profiles is None:
                return False
            
            # Step 6: Store profiles in Elasticsearch
            logger.info("💾 Step 5: Storing customer profiles to Elasticsearch...")
            if not self.elasticsearch_manager.store_profiles(customer_profiles):
                logger.warning("⚠️ Failed to store profiles in Elasticsearch")
                return False
            
            # Step 7: Generate summary statistics
            logger.info("📊 Step 6: Generating processing summary...")
            self._generate_processing_summary(cleaned_df, customer_profiles)
            
            logger.info("🎉 Data processing pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return False
        finally:
            self._cleanup()
    
    def _initialize_all_components(self) -> bool:
        """Initialize all required components."""
        components = [
            ("Data Lake Manager", self.data_lake_manager.initialize),
            ("Elasticsearch Manager", self.elasticsearch_manager.initialize)
        ]
        
        for name, init_func in components:
            logger.info(f"🔧 Initializing {name}...")
            if not init_func():
                logger.error(f"❌ Failed to initialize {name}")
                return False
        
        return True
    
    def _clean_and_validate_data(self, df):
        """Clean and validate the incoming data."""
        try:
            initial_count = df.count()
            logger.info(f"📊 Initial data count: {initial_count:,} events")
            
            # Remove records with null essential fields
            cleaned_df = df.filter(
                F.col("user_id").isNotNull() &
                F.col("event_type").isNotNull() &
                F.col("timestamp").isNotNull()
            )
            
            # Filter valid event types
            valid_events = ['view', 'cart', 'purchase', 'remove_from_cart']
            cleaned_df = cleaned_df.filter(F.col("event_type").isin(valid_events))
            
            # Remove events with invalid prices (negative values)
            cleaned_df = cleaned_df.filter(
                (F.col("product.price").isNull()) | (F.col("product.price") >= 0)
            )
            
            final_count = cleaned_df.count()
            removed_count = initial_count - final_count
            
            logger.info(f"✅ Data cleaning completed:")
            logger.info(f"   - Final count: {final_count:,} events")
            logger.info(f"   - Removed: {removed_count:,} invalid events")
            logger.info(f"   - Data quality: {(final_count/initial_count)*100:.2f}%")
            
            return cleaned_df
            
        except Exception as e:
            logger.error(f"❌ Data cleaning failed: {e}")
            return None
    
    def _generate_processing_summary(self, events_df, profiles_df):
        """Generate and log processing summary statistics."""
        try:
            logger.info("📈 Processing Summary:")
            logger.info("=" * 30)
            
            # Event statistics
            event_stats = events_df.groupBy("event_type").count().collect()
            logger.info("📋 Event Type Distribution:")
            for row in event_stats:
                logger.info(f"   - {row['event_type']}: {row['count']:,}")
            
            # Customer statistics  
            total_customers = profiles_df.count()
            segment_stats = profiles_df.groupBy("customer_segment").count().collect()
            
            logger.info(f"\n👥 Customer Statistics:")
            logger.info(f"   - Total customers: {total_customers:,}")
            logger.info("   - Segment distribution:")
            for row in segment_stats:
                percentage = (row['count'] / total_customers) * 100
                logger.info(f"     • {row['customer_segment']}: {row['count']:,} ({percentage:.1f}%)")
            
            # Revenue statistics
            revenue_stats = profiles_df.agg(
                F.sum("total_revenue").alias("total_revenue"),
                F.avg("total_revenue").alias("avg_revenue"),
                F.avg("conversion_rate").alias("avg_conversion_rate")
            ).collect()[0]
            
            logger.info(f"\n💰 Revenue Statistics:")
            logger.info(f"   - Total revenue: ${revenue_stats['total_revenue']:.2f}")
            logger.info(f"   - Average customer revenue: ${revenue_stats['avg_revenue']:.2f}")
            logger.info(f"   - Average conversion rate: {revenue_stats['avg_conversion_rate']*100:.2f}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate summary: {e}")
    
    def _cleanup(self):
        """Clean up resources."""
        if self.spark:
            logger.info("🧹 Cleaning up Spark session...")
            self.spark.stop()

def main():
    """Main entry point for the data processing application."""
    processor = EcommerceDataProcessor()
    
    # Initialize Spark
    if not processor.initialize_spark():
        logger.error("❌ Failed to initialize Spark session")
        sys.exit(1)
    
    # Run processing pipeline
    success = processor.run_processing_pipeline()
    
    if success:
        logger.info("✅ Processing completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
