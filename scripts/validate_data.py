#!/usr/bin/env python3
"""
Data Validation Script for E-commerce Dataset
============================================
Validates and prepares manually downloaded CSV files for the pipeline.
"""

import os
import pandas as pd
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataValidator:
    """Validates and prepares CSV data for the pipeline."""
    
    def __init__(self):
        # Get project root directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        self.data_dir = project_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        
    def validate_csv(self, csv_path: str) -> bool:
        """Validate CSV file has required columns for the pipeline."""
        try:
            # Read sample to check structure
            df_sample = pd.read_csv(csv_path, nrows=1000)
            
            # Required columns for e-commerce pipeline
            required_cols = ['user_id', 'event_type', 'product_id', 'price']
            optional_cols = ['timestamp', 'category_code', 'brand', 'user_session']
            
            # Check required columns
            missing_cols = [col for col in required_cols if col not in df_sample.columns]
            if missing_cols:
                logger.error(f"❌ Missing required columns: {missing_cols}")
                return False
                
            # Show available columns
            logger.info(f"✅ Required columns found: {required_cols}")
            available_optional = [col for col in optional_cols if col in df_sample.columns]
            if available_optional:
                logger.info(f"📋 Optional columns found: {available_optional}")
                
            # Show basic info
            file_size = Path(csv_path).stat().st_size / 1024 / 1024
            logger.info(f"📊 File size: {file_size:.1f} MB")
            logger.info(f"📊 Sample shape: {df_sample.shape}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to validate CSV: {e}")
            return False
    
    def prepare_data(self, source_csv: str) -> str:
        """Copy CSV to standard location for pipeline."""
        source_path = Path(source_csv)
        target_path = self.data_dir / "events.csv"
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_csv}")
            
        # Validate first
        if not self.validate_csv(str(source_path)):
            raise ValueError("CSV validation failed")
            
        # Copy to pipeline location
        import shutil
        shutil.copy2(source_path, target_path)
        
        logger.info(f"✅ Data prepared at: {target_path}")
        return str(target_path)

def main():
    """Main function to validate and prepare data."""
    print("� Data Pipeline - CSV Validator")
    print("===============================")
    
    validator = DataValidator()
    
    # Look for CSV in data directory
    data_dir = validator.data_dir
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found in data/ directory")
        print("📥 Please:")
        print("   1. Download your e-commerce CSV file manually")
        print("   2. Place it in the data/ directory")
        print("   3. Run this script again")
        return
        
    # Use the first CSV file found
    csv_file = csv_files[0]
    print(f"📄 Found CSV file: {csv_file.name}")
    
    try:
        if validator.validate_csv(str(csv_file)):
            # If it's not already named events.csv, prepare it
            if csv_file.name != "events.csv":
                validator.prepare_data(str(csv_file))
            else:
                print("✅ File is already prepared as events.csv")
                
            print("\n🚀 Ready to run pipeline!")
            print("Next steps:")
            print("   1. docker compose up -d")
            print("   2. python processing/run_complete_pipeline.py")
        else:
            print("❌ CSV validation failed")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
