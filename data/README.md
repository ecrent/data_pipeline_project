# Data Directory

This directory contains the source datasets for the pipeline.

## Files

- `events.csv` - E-commerce events dataset (885K+ records)
  - Contains user interactions: views, cart additions, purchases
  - Used for customer profiling and analytics
  - Format: user_id, event_type, product_id, price, timestamp

## Usage

The pipeline automatically processes all CSV files in this directory.
Place your event data files here before running the ingestion process.
