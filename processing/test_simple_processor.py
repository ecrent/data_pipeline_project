#!/usr/bin/env python3
"""
Simplified Local Data Processor
==============================
A simplified version of the data processor for local testing and development.
Uses Spark in local mode and processes a smaller batch of data.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from kafka import KafkaConsumer
    import pandas as pd
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError as e:
    logger.error(f"❌ Missing dependency: {e}")
    logger.error("Run: pip install kafka-python pandas elasticsearch")
    sys.exit(1)

class SimpleKafkaProcessor:
    """Simple Kafka consumer for testing."""
    
    def __init__(self):
        self.kafka_servers = 'localhost:9092'  # External port
        self.topic = 'raw_events'
        
    def consume_batch(self, max_messages: int = 1000):
        """Consume a batch of messages from Kafka."""
        try:
            logger.info(f"📖 Consuming up to {max_messages:,} messages from Kafka...")
            
            consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=30000,  # 30 second timeout
            group_id='simple_processor_group'
        )
            
            messages = []
            for message in consumer:
                messages.append(message.value)
                if len(messages) >= max_messages:
                    break
            
            consumer.close()
            
            logger.info(f"✅ Consumed {len(messages):,} messages")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Failed to consume from Kafka: {e}")
            return []

class SimpleProfileGenerator:
    """Simple customer profile generator."""
    
    def generate_profiles(self, events_data: list) -> list:
        """Generate customer profiles from events."""
        try:
            logger.info("🔍 Generating customer profiles...")
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(events_data)
            
            if df.empty:
                logger.warning("⚠️ No events data to process")
                return []
            
            # Flatten product data
            product_df = pd.json_normalize(df['product']).add_prefix('product_')
            df = pd.concat([df.drop('product', axis=1), product_df], axis=1)
            
            # Group by user_id and calculate metrics
            profiles = []
            
            for user_id, user_events in df.groupby('user_id'):
                profile = {
                    'user_id': user_id,
                    'total_events': len(user_events),
                    'total_sessions': user_events['user_session'].nunique(),
                    'unique_products_viewed': user_events['product_id'].nunique(),
                    'unique_categories': user_events['product_category_code'].nunique() if 'product_category_code' in user_events else 0,
                    'unique_brands': user_events['product_brand'].nunique() if 'product_brand' in user_events else 0,
                    
                    # Event type breakdown
                    'total_views': len(user_events[user_events['event_type'] == 'view']),
                    'total_cart_additions': len(user_events[user_events['event_type'] == 'cart']),
                    'total_purchases': len(user_events[user_events['event_type'] == 'purchase']),
                    'total_cart_removals': len(user_events[user_events['event_type'] == 'remove_from_cart']),
                    
                    # Financial metrics
                    'total_revenue': user_events[user_events['event_type'] == 'purchase']['product_price'].sum() if 'product_price' in user_events else 0.0,
                    'avg_purchase_value': user_events[user_events['event_type'] == 'purchase']['product_price'].mean() if 'product_price' in user_events else 0.0,
                    'max_purchase_value': user_events[user_events['event_type'] == 'purchase']['product_price'].max() if 'product_price' in user_events else 0.0,
                    
                    # Temporal metrics
                    'first_seen': user_events['timestamp'].min(),
                    'last_seen': user_events['timestamp'].max(),
                }
                
                # Calculate derived metrics
                profile['conversion_rate'] = profile['total_purchases'] / profile['total_views'] if profile['total_views'] > 0 else 0.0
                profile['cart_abandonment_rate'] = profile['total_cart_removals'] / profile['total_cart_additions'] if profile['total_cart_additions'] > 0 else 0.0
                profile['avg_session_duration_events'] = profile['total_events'] / profile['total_sessions']
                
                # Customer segmentation
                if profile['total_purchases'] >= 5 and profile['total_revenue'] >= 1000:
                    profile['customer_segment'] = 'High Value'
                elif profile['total_purchases'] >= 2 and profile['total_revenue'] >= 100:
                    profile['customer_segment'] = 'Regular'
                elif profile['total_purchases'] >= 1:
                    profile['customer_segment'] = 'Occasional'
                elif profile['total_views'] >= 10 and profile['total_cart_additions'] >= 1:
                    profile['customer_segment'] = 'Browser'
                else:
                    profile['customer_segment'] = 'New/Inactive'
                
                profile['profile_generated_at'] = pd.Timestamp.now().isoformat()
                
                profiles.append(profile)
            
            logger.info(f"✅ Generated {len(profiles):,} customer profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"❌ Failed to generate profiles: {e}")
            return []

class SimpleElasticsearchManager:
    """Simple Elasticsearch manager."""
    
    def __init__(self):
        self.client = None
        self.index = 'customer_profiles'
        
    def initialize(self) -> bool:
        """Initialize Elasticsearch connection."""
        try:
            logger.info("🔗 Connecting to Elasticsearch...")
            
            self.client = Elasticsearch(
                ['http://localhost:9200'],
                request_timeout=30,
                retry_on_timeout=True
            )
            
            if self.client.ping():
                logger.info("✅ Elasticsearch connection established")
                self._create_index_if_not_exists()
                return True
            else:
                logger.error("❌ Failed to connect to Elasticsearch")
                return False
                
        except Exception as e:
            logger.error(f"❌ Elasticsearch connection failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _create_index_if_not_exists(self):
        """Create index with mapping if it doesn't exist."""
        try:
            if not self.client.indices.exists(index=self.index):
                logger.info(f"📋 Creating index: {self.index}")
                
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
                logger.info(f"✅ Index created successfully")
        
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
    
    def store_profiles(self, profiles: list) -> bool:
        """Store profiles to Elasticsearch."""
        try:
            logger.info(f"💾 Storing {len(profiles):,} profiles to Elasticsearch...")
            
            # Prepare documents for bulk indexing
            documents = []
            for profile in profiles:
                doc = {
                    "_index": self.index,
                    "_id": profile["user_id"],
                    "_source": profile
                }
                documents.append(doc)
            
            # Bulk index
            success_count, errors = bulk(self.client, documents, refresh=True)
            
            if errors:
                logger.warning(f"⚠️ {len(errors)} documents failed to index")
            
            logger.info(f"✅ Successfully stored {success_count:,} profiles")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store profiles: {e}")
            return False

def main():
    """Main function for simple processing pipeline."""
    logger.info("🚀 Simple Data Processing Pipeline")
    logger.info("=" * 40)
    
    # Initialize components
    kafka_processor = SimpleKafkaProcessor()
    profile_generator = SimpleProfileGenerator()
    es_manager = SimpleElasticsearchManager()
    
    try:
        # Step 1: Initialize Elasticsearch
        if not es_manager.initialize():
            logger.error("❌ Failed to initialize Elasticsearch")
            return
        
        # Step 2: Consume events from Kafka
        events = kafka_processor.consume_batch(max_messages=500)  # Process 500 events for testing
        if not events:
            logger.error("❌ No events retrieved from Kafka")
            return
        
        # Step 3: Generate customer profiles
        profiles = profile_generator.generate_profiles(events)
        if not profiles:
            logger.error("❌ No profiles generated")
            return
        
        # Step 4: Store profiles in Elasticsearch
        if not es_manager.store_profiles(profiles):
            logger.error("❌ Failed to store profiles")
            return
        
        # Step 5: Print summary
        logger.info("📊 Processing Summary:")
        logger.info(f"   - Events processed: {len(events):,}")
        logger.info(f"   - Profiles generated: {len(profiles):,}")
        
        # Segment breakdown
        segments = {}
        for profile in profiles:
            segment = profile['customer_segment']
            segments[segment] = segments.get(segment, 0) + 1
        
        logger.info("   - Customer segments:")
        for segment, count in segments.items():
            percentage = (count / len(profiles)) * 100
            logger.info(f"     • {segment}: {count} ({percentage:.1f}%)")
        
        logger.info("✅ Simple processing pipeline completed!")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    main()
