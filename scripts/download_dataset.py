#!/usr/bin/env python3
"""
Data Acquisition Script for E-commerce Electronics Dataset
=========================================================
Downloads and prepares the Kaggle e-commerce events dataset for the pipeline.

Dataset: E-commerce Events History in Electronics Store
Source: https://www.kaggle.com/mkechinov/ecommerce-events-history-in-electronics-store
"""

import os
import sys
import pandas as pd
import logging
from pathlib import Path
from typing import Optional
import kagglehub

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KaggleDatasetDownloader:
    """Downloads and processes the Kaggle e-commerce dataset."""
    
    def __init__(self, output_dir: str = None):
        # Use current directory's data folder when running locally
        if output_dir is None:
            if os.path.exists("/app/data"):  # Docker environment
                output_dir = "/app/data"
            else:  # Local environment
                # Get the project root (parent of scripts directory)
                script_dir = Path(__file__).parent
                project_root = script_dir.parent
                output_dir = str(project_root / "data")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.dataset_id = "mkechinov/ecommerce-events-history-in-electronics-store"
        
    def download_dataset(self) -> str:
        """Download the dataset from Kaggle."""
        logger.info(f"🔄 Downloading dataset: {self.dataset_id}")
        
        try:
            # Download latest version
            path = kagglehub.dataset_download(self.dataset_id)
            logger.info(f"✅ Dataset downloaded to: {path}")
            return path
            
        except Exception as e:
            logger.error(f"❌ Failed to download dataset: {e}")
            logger.info("💡 Make sure you have:")
            logger.info("   1. Kaggle API credentials configured")
            logger.info("   2. Internet connectivity")
            logger.info("   3. Accepted the dataset terms on Kaggle")
            raise
    
    def process_dataset(self, dataset_path: str) -> Optional[str]:
        """Process the downloaded dataset and prepare it for the pipeline."""
        dataset_dir = Path(dataset_path)
        
        # Look for CSV files in the downloaded directory
        csv_files = list(dataset_dir.glob("*.csv"))
        
        if not csv_files:
            logger.error("❌ No CSV files found in the downloaded dataset")
            return None
            
        logger.info(f"📊 Found {len(csv_files)} CSV file(s):")
        for csv_file in csv_files:
            logger.info(f"   - {csv_file.name} ({csv_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Use the largest CSV file (likely the main events file)
        main_file = max(csv_files, key=lambda f: f.stat().st_size)
        logger.info(f"📈 Using main file: {main_file.name}")
        
        return self._copy_and_validate(main_file)
    
    def _copy_and_validate(self, source_file: Path) -> str:
        """Copy the dataset to our data directory and validate it."""
        # Copy to our standard location
        target_file = self.output_dir / "electronics.csv"
        
        logger.info(f"📋 Copying {source_file.name} to {target_file}")
        
        # Read and validate the CSV
        try:
            # Read a sample to understand the structure
            sample_df = pd.read_csv(source_file, nrows=1000)
            logger.info(f"📊 Dataset preview:")
            logger.info(f"   - Shape: {sample_df.shape}")
            logger.info(f"   - Columns: {list(sample_df.columns)}")
            
            # Check for expected e-commerce columns
            expected_columns = ['user_id', 'event_type', 'product_id', 'category_code', 'brand', 'price', 'user_session']
            found_columns = [col for col in expected_columns if col in sample_df.columns]
            logger.info(f"   - E-commerce columns found: {found_columns}")
            
            # Copy the file
            import shutil
            shutil.copy2(source_file, target_file)
            
            logger.info(f"✅ Dataset prepared at: {target_file}")
            return str(target_file)
            
        except Exception as e:
            logger.error(f"❌ Failed to process dataset: {e}")
            raise
    
    def get_dataset_info(self) -> dict:
        """Get information about the prepared dataset."""
        target_file = self.output_dir / "electronics.csv"
        
        if not target_file.exists():
            return {"error": "Dataset not found. Run download first."}
        
        try:
            # Get file info without loading the entire file
            df_sample = pd.read_csv(target_file, nrows=10000)
            file_size = target_file.stat().st_size
            
            info = {
                "file_path": str(target_file),
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "columns": list(df_sample.columns),
                "sample_shape": df_sample.shape,
                "dtypes": df_sample.dtypes.to_dict(),
                "sample_data": df_sample.head().to_dict('records')
            }
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to read dataset: {e}"}

def main():
    """Main function to download and prepare the dataset."""
    print("🚀 Data Pipeline - Dataset Acquisition")
    print("=====================================")
    
    # Initialize downloader
    downloader = KaggleDatasetDownloader()
    
    try:
        # Download dataset
        dataset_path = downloader.download_dataset()
        
        # Process dataset
        prepared_file = downloader.process_dataset(dataset_path)
        
        if prepared_file:
            print(f"\n✅ SUCCESS!")
            print(f"Dataset is ready at: {prepared_file}")
            
            # Show dataset info
            info = downloader.get_dataset_info()
            if "error" not in info:
                print(f"\n📊 Dataset Information:")
                print(f"   - File size: {info['file_size_mb']} MB")
                print(f"   - Columns: {len(info['columns'])}")
                print(f"   - Sample rows: {info['sample_shape'][0]:,}")
                print(f"\n📋 Available columns:")
                for col in info['columns']:
                    print(f"   - {col}")
            
            print(f"\n🚀 Next steps:")
            print(f"   1. Start the pipeline services: make start")
            print(f"   2. Run the ingestion service: make ingest")
            print(f"   3. Process the data: make process")
        
    except Exception as e:
        logger.error(f"❌ Dataset acquisition failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
