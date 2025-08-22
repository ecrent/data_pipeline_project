"""
E-commerce Data Ingestion Service
================================
Kafka producer service that reads CSV data and publishes events to Kafka.

This service:
1. Reads e-commerce events from CSV file
2. Validates and transforms data to JSON
3. Publishes events to Kafka topic with proper partitioning
4. Handles errors and provides comprehensive logging
5. Supports configurable batch processing
"""

import os
import sys
import json
import csv
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Generator
from pathlib import Path
import pandas as pd

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError, KafkaTimeoutError
except ImportError:
    print("❌ Kafka client not installed. Run: pip install kafka-python")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EcommerceEventValidator:
    """Validates and transforms e-commerce event data."""
    
    REQUIRED_COLUMNS = [
        'event_time', 'event_type', 'product_id', 
        'user_id', 'user_session'
    ]
    
    OPTIONAL_COLUMNS = [
        'category_id', 'category_code', 'brand', 'price'
    ]
    
    VALID_EVENT_TYPES = [
        'view', 'cart', 'purchase', 'remove_from_cart'
    ]
    
    @classmethod
    def validate_event(cls, event: Dict[str, Any]) -> tuple[bool, str]:
        """Validate a single event record."""
        # Check required fields
        for field in cls.REQUIRED_COLUMNS:
            if field not in event or not event[field]:
                return False, f"Missing required field: {field}"
        
        # Validate event_type
        if event.get('event_type') not in cls.VALID_EVENT_TYPES:
            return False, f"Invalid event_type: {event.get('event_type')}"
        
        # Validate price if present
        if event.get('price'):
            try:
                float(event['price'])
            except (ValueError, TypeError):
                return False, f"Invalid price format: {event.get('price')}"
        
        return True, "Valid"
    
    @classmethod
    def transform_event(cls, event: Dict[str, Any]) -> Dict[str, Any]:
        """Transform and enrich event data."""
        # Parse timestamp
        try:
            if 'UTC' in str(event['event_time']):
                event_time = datetime.strptime(
                    event['event_time'], 
                    '%Y-%m-%d %H:%M:%S UTC'
                )
            else:
                event_time = datetime.fromisoformat(str(event['event_time']))
            
            # Ensure timezone info
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid timestamp format: {event['event_time']}, using current time")
            event_time = datetime.now(timezone.utc)
        
        # Build transformed event
        transformed = {
            'event_id': f"{event['user_id']}_{event['product_id']}_{int(event_time.timestamp())}",
            'timestamp': event_time.isoformat(),
            'event_type': event['event_type'],
            'user_id': str(event['user_id']),
            'user_session': event['user_session'],
            'product': {
                'id': str(event['product_id']),
                'category_id': str(event.get('category_id', '')),
                'category_code': event.get('category_code', ''),
                'brand': event.get('brand', ''),
                'price': float(event['price']) if event.get('price') else 0.0
            },
            'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'csv_ingestion'
        }
        
        return transformed

class KafkaEventProducer:
    """Kafka producer for e-commerce events."""
    
    def __init__(
        self,
        bootstrap_servers: str = 'kafka:29092',
        topic: str = 'raw_events',
        batch_size: int = 1000
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.batch_size = batch_size
        self.producer = None
        self.stats = {
            'total_processed': 0,
            'total_sent': 0,
            'total_errors': 0,
            'start_time': time.time()
        }
        
    def connect(self) -> bool:
        """Initialize Kafka producer connection."""
        try:
            logger.info(f"🔌 Connecting to Kafka: {self.bootstrap_servers}")
            
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                batch_size=16384,  # 16KB batch size
                linger_ms=10,  # Wait up to 10ms to batch messages
                compression_type='gzip',  # Compress messages
                max_request_size=1048576  # 1MB max message size
            )
            
            # Test connection by getting metadata
            metadata = self.producer.bootstrap_connected()
            logger.info(f"✅ Kafka connection established: {metadata}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def send_event(self, event: Dict[str, Any]) -> bool:
        """Send a single event to Kafka."""
        try:
            # Use user_id as partition key for even distribution
            key = event.get('user_id')
            
            future = self.producer.send(
                self.topic,
                key=key,
                value=event
            )
            
            # Add callback for success/error handling
            future.add_callback(self._on_success)
            future.add_errback(self._on_error)
            
            self.stats['total_sent'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send event: {e}")
            self.stats['total_errors'] += 1
            return False
    
    def _on_success(self, record_metadata):
        """Callback for successful message delivery."""
        logger.debug(f"✅ Message sent to {record_metadata.topic}[{record_metadata.partition}] at offset {record_metadata.offset}")
    
    def _on_error(self, exception):
        """Callback for message delivery errors."""
        logger.error(f"❌ Message delivery failed: {exception}")
        self.stats['total_errors'] += 1
    
    def flush_and_close(self):
        """Flush pending messages and close producer."""
        if self.producer:
            logger.info("🔄 Flushing pending messages...")
            self.producer.flush(timeout=30)  # Wait up to 30 seconds
            self.producer.close(timeout=10)
            logger.info("✅ Producer closed")
    
    def print_stats(self):
        """Print ingestion statistics."""
        duration = time.time() - self.stats['start_time']
        rate = self.stats['total_processed'] / duration if duration > 0 else 0
        
        logger.info("📊 Ingestion Statistics:")
        logger.info(f"   - Total processed: {self.stats['total_processed']:,}")
        logger.info(f"   - Successfully sent: {self.stats['total_sent']:,}")
        logger.info(f"   - Errors: {self.stats['total_errors']:,}")
        logger.info(f"   - Duration: {duration:.2f}s")
        logger.info(f"   - Rate: {rate:.2f} events/sec")

class CSVEventReader:
    """Reads and processes CSV events in batches."""
    
    def __init__(self, file_path: str, batch_size: int = 1000):
        self.file_path = Path(file_path)
        self.batch_size = batch_size
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    def read_events(self) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields events from CSV file."""
        logger.info(f"📖 Reading events from: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Log column information
                logger.info(f"📋 CSV Columns: {reader.fieldnames}")
                
                for row_num, row in enumerate(reader, 1):
                    # Clean empty string values
                    cleaned_row = {k: v if v != '' else None for k, v in row.items()}
                    yield cleaned_row
                    
                    if row_num % 10000 == 0:
                        logger.info(f"📊 Processed {row_num:,} rows...")
                        
        except Exception as e:
            logger.error(f"❌ Error reading CSV file: {e}")
            raise

class EcommerceIngestionService:
    """Main ingestion service orchestrator."""
    
    def __init__(self):
        # Load configuration from environment
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'raw_events')
        self.source_file = os.getenv('SOURCE_FILE', '/app/data/electronics.csv')
        self.batch_size = int(os.getenv('BATCH_SIZE', '1000'))
        self.max_events = int(os.getenv('MAX_EVENTS', '0'))  # 0 = no limit
        
        # Initialize components
        self.validator = EcommerceEventValidator()
        self.producer = None
        self.reader = None
        
    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("🚀 Initializing E-commerce Ingestion Service")
        logger.info("=" * 50)
        
        # Log configuration
        logger.info(f"📋 Configuration:")
        logger.info(f"   - Kafka servers: {self.kafka_servers}")
        logger.info(f"   - Kafka topic: {self.kafka_topic}")
        logger.info(f"   - Source file: {self.source_file}")
        logger.info(f"   - Batch size: {self.batch_size}")
        logger.info(f"   - Max events: {self.max_events if self.max_events > 0 else 'unlimited'}")
        
        # Initialize CSV reader
        try:
            self.reader = CSVEventReader(self.source_file, self.batch_size)
            logger.info("✅ CSV reader initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CSV reader: {e}")
            return False
        
        # Initialize Kafka producer
        self.producer = KafkaEventProducer(
            self.kafka_servers,
            self.kafka_topic,
            self.batch_size
        )
        
        if not self.producer.connect():
            return False
        
        logger.info("✅ All components initialized successfully")
        return True
    
    def run(self):
        """Run the ingestion process."""
        if not self.initialize():
            logger.error("❌ Failed to initialize service")
            sys.exit(1)
        
        try:
            logger.info("🔄 Starting data ingestion...")
            
            event_count = 0
            valid_events = 0
            invalid_events = 0
            
            for raw_event in self.reader.read_events():
                event_count += 1
                self.producer.stats['total_processed'] = event_count
                
                # Validate event
                is_valid, error_msg = self.validator.validate_event(raw_event)
                
                if not is_valid:
                    invalid_events += 1
                    logger.debug(f"⚠️ Invalid event at row {event_count}: {error_msg}")
                    continue
                
                # Transform event
                try:
                    transformed_event = self.validator.transform_event(raw_event)
                    
                    # Send to Kafka
                    if self.producer.send_event(transformed_event):
                        valid_events += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error transforming event at row {event_count}: {e}")
                    invalid_events += 1
                
                # Check if we've reached max events limit
                if self.max_events > 0 and event_count >= self.max_events:
                    logger.info(f"🏁 Reached max events limit: {self.max_events}")
                    break
                
                # Periodic status update
                if event_count % 5000 == 0:
                    logger.info(f"📈 Progress: {event_count:,} processed, {valid_events:,} valid, {invalid_events:,} invalid")
            
            # Final statistics
            logger.info("🏁 Ingestion completed!")
            logger.info(f"📊 Final Results:")
            logger.info(f"   - Total processed: {event_count:,}")
            logger.info(f"   - Valid events: {valid_events:,}")
            logger.info(f"   - Invalid events: {invalid_events:,}")
            logger.info(f"   - Success rate: {(valid_events/event_count)*100:.2f}%" if event_count > 0 else "0%")
            
        except KeyboardInterrupt:
            logger.info("🛑 Ingestion interrupted by user")
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            raise
        finally:
            # Cleanup
            if self.producer:
                self.producer.flush_and_close()
                self.producer.print_stats()

def main():
    """Main entry point."""
    service = EcommerceIngestionService()
    service.run()

if __name__ == "__main__":
    main()
