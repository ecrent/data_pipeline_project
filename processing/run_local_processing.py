#!/usr/bin/env python3
"""
Local Spark Data Processing Pipeline
====================================

This script runs our comprehensive data processing pipeline locally without Docker.
It demonstrates the complete flow from Kafka consumption to customer profiling,
MinIO archival, and Elasticsearch storage.

Author: Data Pipeline Team  
Version: 1.0.0
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import *
    from pyspark.sql.types import *
    from kafka import KafkaConsumer
    from elasticsearch import Elasticsearch
    from minio import Minio
    from minio.error import S3Error
    import io
    import traceback
except ImportError as e:
    logger.error(f"❌ Missing dependency: {e}")
    logger.error("Run: pip install pyspark kafka-python elasticsearch minio pandas")
    sys.exit(1)

class LocalDataProcessor:
    """Local implementation of our data processing pipeline."""
    
    def __init__(self):
        """Initialize the local processor."""
        self.kafka_servers = 'localhost:9092'
        self.kafka_topic = 'raw_events'
        self.es_host = 'localhost:9200'
        self.es_index = 'customer_profiles'
        self.minio_endpoint = 'localhost:9000'
        self.minio_bucket = 'data-lake'
        
        # Initialize components
        self.spark = None
        self.kafka_consumer = None
        self.elasticsearch = None
        self.minio_client = None
        
    def initialize_spark(self):
        """Initialize Spark session."""
        try:
            logger.info("🔥 Initializing Spark session...")
            self.spark = SparkSession.builder \
                .appName("LocalDataProcessor") \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .getOrCreate()
            
            logger.info("✅ Spark session initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Spark: {e}")
            return False
    
    def initialize_kafka(self):
        """Initialize Kafka consumer."""
        try:
            logger.info("📖 Initializing Kafka consumer...")
            self.kafka_consumer = KafkaConsumer(
                self.kafka_topic,
                bootstrap_servers=[self.kafka_servers],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=30000,  # 30 second timeout
                group_id='local_processor_group',
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("✅ Kafka consumer initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka consumer: {e}")
            return False
    
    def initialize_elasticsearch(self):
        """Initialize Elasticsearch client."""
        try:
            logger.info("🔍 Initializing Elasticsearch client...")
            self.elasticsearch = Elasticsearch(
                [self.es_host],
                request_timeout=30,
                retry_on_timeout=True
            )
            
            if self.elasticsearch.ping():
                logger.info("✅ Elasticsearch client initialized successfully")
                self._create_index_if_not_exists()
                return True
            else:
                logger.error("❌ Failed to ping Elasticsearch")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Elasticsearch: {e}")
            return False
    
    def initialize_minio(self):
        """Initialize MinIO client."""
        try:
            logger.info("💾 Initializing MinIO client...")
            self.minio_client = Minio(
                self.minio_endpoint,
                access_key='minioadmin',
                secret_key='minioadmin123',
                secure=False
            )
            
            # Create bucket if it doesn't exist
            if not self.minio_client.bucket_exists(self.minio_bucket):
                logger.info(f"Creating bucket: {self.minio_bucket}")
                self.minio_client.make_bucket(self.minio_bucket)
            
            logger.info("✅ MinIO client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize MinIO: {e}")
            return False
    
    def _create_index_if_not_exists(self):
        """Create Elasticsearch index if it doesn't exist."""
        try:
            if not self.elasticsearch.indices.exists(index=self.es_index):
                logger.info(f"📋 Creating index: {self.es_index}")
                
                mapping = {
                    "mappings": {
                        "properties": {
                            "user_id": {"type": "keyword"},
                            "customer_segment": {"type": "keyword"},
                            "total_events": {"type": "long"},
                            "total_sessions": {"type": "long"},
                            "total_purchases": {"type": "long"},
                            "total_revenue": {"type": "double"},
                            "avg_session_duration": {"type": "double"},
                            "conversion_rate": {"type": "double"},
                            "avg_order_value": {"type": "double"},
                            "first_seen": {"type": "date"},
                            "last_seen": {"type": "date"},
                            "favorite_category": {"type": "keyword"},
                            "favorite_brand": {"type": "keyword"},
                            "profile_generated_at": {"type": "date"}
                        }
                    }
                }
                
                self.elasticsearch.indices.create(index=self.es_index, body=mapping)
                logger.info("✅ Index created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
    
    def consume_events(self, max_events: int = 1000) -> List[Dict]:
        """Consume events from Kafka."""
        try:
            logger.info(f"📖 Consuming up to {max_events:,} events from Kafka...")
            
            events = []
            event_count = 0
            
            for message in self.kafka_consumer:
                if event_count >= max_events:
                    break
                
                events.append(message.value)
                event_count += 1
                
                if event_count % 100 == 0:
                    logger.info(f"Consumed {event_count:,} events...")
            
            logger.info(f"✅ Successfully consumed {len(events):,} events")
            return events
            
        except Exception as e:
            logger.error(f"❌ Failed to consume events: {e}")
            return []
    
    def generate_customer_profiles(self, events: List[Dict]) -> List[Dict]:
        """Generate customer profiles from events."""
        try:
            logger.info(f"👤 Generating customer profiles from {len(events):,} events...")
            
            # Group events by user
            user_events = defaultdict(list)
            for event in events:
                user_id = event.get('user_id')
                if user_id:
                    user_events[user_id].append(event)
            
            profiles = []
            
            for user_id, user_event_list in user_events.items():
                profile = self._create_user_profile(user_id, user_event_list)
                if profile:
                    profiles.append(profile)
            
            logger.info(f"✅ Generated {len(profiles):,} customer profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"❌ Failed to generate customer profiles: {e}")
            return []
    
    def _create_user_profile(self, user_id: str, events: List[Dict]) -> Dict:
        """Create a comprehensive customer profile."""
        try:
            # Basic metrics
            total_events = len(events)
            sessions = set(event.get('user_session') for event in events if event.get('user_session'))
            total_sessions = len(sessions)
            
            # Purchase metrics
            purchases = [e for e in events if e.get('event_type') == 'purchase']
            total_purchases = len(purchases)
            total_revenue = sum(float(p.get('product', {}).get('price', 0)) for p in purchases)
            
            # Time-based metrics
            timestamps = []
            for event in events:
                try:
                    ts = pd.to_datetime(event.get('timestamp'))
                    timestamps.append(ts)
                except:
                    continue
            
            if timestamps:
                first_seen = min(timestamps)
                last_seen = max(timestamps)
            else:
                first_seen = last_seen = datetime.utcnow()
            
            # Category and brand analysis
            categories = [e.get('product', {}).get('category_code') for e in events 
                         if e.get('product', {}).get('category_code')]
            brands = [e.get('product', {}).get('brand') for e in events 
                     if e.get('product', {}).get('brand')]
            
            favorite_category = max(set(categories), key=categories.count) if categories else None
            favorite_brand = max(set(brands), key=brands.count) if brands else None
            
            # Calculate metrics
            conversion_rate = (total_purchases / total_events) * 100 if total_events > 0 else 0
            avg_order_value = total_revenue / total_purchases if total_purchases > 0 else 0
            
            # Customer segmentation
            if total_purchases > 10 and total_revenue > 500:
                segment = "High Value"
            elif total_purchases > 5 and total_revenue > 100:
                segment = "Medium Value"
            elif total_purchases > 0:
                segment = "Low Value"
            else:
                segment = "Browser"
            
            return {
                "user_id": user_id,
                "customer_segment": segment,
                "total_events": total_events,
                "total_sessions": total_sessions,
                "total_purchases": total_purchases,
                "total_revenue": round(total_revenue, 2),
                "conversion_rate": round(conversion_rate, 2),
                "avg_order_value": round(avg_order_value, 2),
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "favorite_category": favorite_category,
                "favorite_brand": favorite_brand,
                "profile_generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create profile for user {user_id}: {e}")
            return None
    
    def store_to_minio(self, profiles: List[Dict], events: List[Dict]) -> bool:
        """Store processed data to MinIO."""
        try:
            logger.info("💾 Storing data to MinIO...")
            
            # Store customer profiles
            profiles_df = pd.DataFrame(profiles)
            profiles_parquet = profiles_df.to_parquet(index=False)
            
            profiles_key = f"customer_profiles/{datetime.utcnow().strftime('%Y/%m/%d')}/profiles_{datetime.utcnow().strftime('%H%M%S')}.parquet"
            
            self.minio_client.put_object(
                self.minio_bucket,
                profiles_key,
                io.BytesIO(profiles_parquet),
                len(profiles_parquet),
                content_type="application/octet-stream"
            )
            
            logger.info(f"✅ Stored {len(profiles):,} profiles to MinIO: {profiles_key}")
            
            # Store raw events archive
            events_df = pd.DataFrame(events)
            events_parquet = events_df.to_parquet(index=False)
            
            events_key = f"raw_events/{datetime.utcnow().strftime('%Y/%m/%d')}/events_{datetime.utcnow().strftime('%H%M%S')}.parquet"
            
            self.minio_client.put_object(
                self.minio_bucket,
                events_key,
                io.BytesIO(events_parquet),
                len(events_parquet),
                content_type="application/octet-stream"
            )
            
            logger.info(f"✅ Stored {len(events):,} events to MinIO: {events_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store data to MinIO: {e}")
            return False
    
    def store_to_elasticsearch(self, profiles: List[Dict]) -> bool:
        """Store customer profiles to Elasticsearch."""
        try:
            logger.info(f"🔍 Storing {len(profiles):,} profiles to Elasticsearch...")
            
            # Prepare documents for bulk indexing
            documents = []
            for profile in profiles:
                documents.extend([
                    {"index": {"_index": self.es_index, "_id": profile["user_id"]}},
                    profile
                ])
            
            if documents:
                response = self.elasticsearch.bulk(body=documents)
                
                if response.get('errors', False):
                    logger.warning("Some documents failed to index")
                else:
                    logger.info("✅ All profiles stored to Elasticsearch successfully")
                    
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store profiles to Elasticsearch: {e}")
            return False
    
    def run_pipeline(self, max_events: int = 1000):
        """Run the complete data processing pipeline."""
        try:
            logger.info("🚀 Starting Local Data Processing Pipeline")
            logger.info("=" * 50)
            
            # Initialize all components
            if not self.initialize_spark():
                return False
            if not self.initialize_kafka():
                return False
            if not self.initialize_elasticsearch():
                return False
            if not self.initialize_minio():
                return False
            
            # Process the data pipeline
            logger.info("📊 Starting data processing...")
            
            # 1. Consume events from Kafka
            events = self.consume_events(max_events)
            if not events:
                logger.warning("⚠️ No events consumed from Kafka")
                return False
            
            # 2. Generate customer profiles
            profiles = self.generate_customer_profiles(events)
            if not profiles:
                logger.warning("⚠️ No customer profiles generated")
                return False
            
            # 3. Store to MinIO (Data Lake)
            if not self.store_to_minio(profiles, events):
                logger.warning("⚠️ Failed to store data to MinIO")
            
            # 4. Store to Elasticsearch (Analytics)
            if not self.store_to_elasticsearch(profiles):
                logger.warning("⚠️ Failed to store profiles to Elasticsearch")
            
            # 5. Generate summary
            self._generate_summary(events, profiles)
            
            logger.info("✅ Data processing pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _generate_summary(self, events: List[Dict], profiles: List[Dict]):
        """Generate processing summary."""
        logger.info("📈 Processing Summary")
        logger.info("-" * 30)
        logger.info(f"Events Processed: {len(events):,}")
        logger.info(f"Customer Profiles Generated: {len(profiles):,}")
        
        if profiles:
            segments = defaultdict(int)
            total_revenue = 0
            total_purchases = 0
            
            for profile in profiles:
                segments[profile['customer_segment']] += 1
                total_revenue += profile.get('total_revenue', 0)
                total_purchases += profile.get('total_purchases', 0)
            
            logger.info(f"Total Revenue: ${total_revenue:,.2f}")
            logger.info(f"Total Purchases: {total_purchases:,}")
            
            logger.info("Customer Segments:")
            for segment, count in segments.items():
                logger.info(f"  {segment}: {count:,} customers")
    
    def cleanup(self):
        """Clean up resources."""
        if self.kafka_consumer:
            self.kafka_consumer.close()
        if self.spark:
            self.spark.stop()

def main():
    """Main execution function."""
    processor = LocalDataProcessor()
    
    try:
        success = processor.run_pipeline(max_events=2000)  # Process 2K events
        if success:
            logger.info("🎉 Pipeline execution completed successfully!")
        else:
            logger.error("❌ Pipeline execution failed!")
            
    except KeyboardInterrupt:
        logger.info("⏹️ Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        processor.cleanup()

if __name__ == "__main__":
    main()
