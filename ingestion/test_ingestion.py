#!/usr/bin/env python3
"""
Test script for the ingestion service
"""

import sys
import json
from pathlib import Path
import pandas as pd

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from kafka_producer import EcommerceEventValidator, CSVEventReader

def test_validator():
    """Test the event validator."""
    print("🧪 Testing Event Validator")
    print("=" * 30)
    
    validator = EcommerceEventValidator()
    
    # Test valid event
    valid_event = {
        'event_time': '2020-09-24 11:57:06 UTC',
        'event_type': 'view',
        'product_id': '1996170',
        'category_code': 'electronics.telephone',
        'brand': 'samsung',
        'price': '31.90',
        'user_id': '1515915625519388267',
        'user_session': 'LJuJVLEjPT'
    }
    
    is_valid, msg = validator.validate_event(valid_event)
    print(f"Valid event test: {'✅ PASS' if is_valid else '❌ FAIL'} - {msg}")
    
    if is_valid:
        transformed = validator.transform_event(valid_event)
        print("📋 Transformed event sample:")
        print(json.dumps(transformed, indent=2))
    
    # Test invalid event
    invalid_event = {
        'event_time': '2020-09-24 11:57:06 UTC',
        'event_type': 'invalid_type',  # Invalid type
        'product_id': '1996170',
        'user_id': '1515915625519388267',
        'user_session': 'LJuJVLEjPT'
    }
    
    is_valid, msg = validator.validate_event(invalid_event)
    print(f"Invalid event test: {'✅ PASS' if not is_valid else '❌ FAIL'} - {msg}")

def test_csv_reader():
    """Test the CSV reader."""
    print("\n📖 Testing CSV Reader")
    print("=" * 25)
    
    csv_file = "/workspaces/data_pipeline_project/data/electronics.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    try:
        reader = CSVEventReader(csv_file, batch_size=10)
        
        # Read first 5 events
        events = []
        for i, event in enumerate(reader.read_events()):
            events.append(event)
            if i >= 4:  # Read only first 5
                break
        
        print(f"✅ Successfully read {len(events)} sample events")
        print("📋 Sample event:")
        if events:
            print(json.dumps(events[0], indent=2, default=str))
        
    except Exception as e:
        print(f"❌ CSV reader test failed: {e}")

def analyze_dataset():
    """Analyze the dataset."""
    print("\n📊 Dataset Analysis")
    print("=" * 25)
    
    csv_file = "/workspaces/data_pipeline_project/data/electronics.csv"
    
    try:
        # Read a sample for analysis
        df = pd.read_csv(csv_file, nrows=10000)
        
        print(f"📈 Dataset shape: {df.shape}")
        print(f"📋 Columns: {list(df.columns)}")
        print(f"🎯 Event types: {df['event_type'].value_counts().to_dict()}")
        print(f"💰 Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
        print(f"🏷️ Unique brands: {df['brand'].nunique()}")
        print(f"👥 Unique users: {df['user_id'].nunique()}")
        
    except Exception as e:
        print(f"❌ Dataset analysis failed: {e}")

if __name__ == "__main__":
    print("🚀 Data Pipeline - Ingestion Service Test")
    print("=" * 45)
    
    test_validator()
    test_csv_reader()
    analyze_dataset()
    
    print("\n✅ All tests completed!")
