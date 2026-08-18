"""
MedAxis - AI-Driven Predictive Hospital Bed & Patient-Flow Forecasting
Command Center Runner Script
"""

import os
import sys
import uvicorn
from datetime import datetime, timedelta

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.dataset_generator import (
    generate_hourly_records,
    export_dataset_to_csv,
    export_sample_upload_template
)

def init_data():
    """Initializes hospital baseline datasets if not already present."""
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    historical_csv = os.path.join(data_dir, "sample_hospital_historical.csv")
    template_csv = os.path.join(data_dir, "sample_upload_template.csv")
    
    if not os.path.exists(historical_csv):
        print("[MedAxis Init] Generating baseline 90-day multi-ward historical time series...")
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        start_time = now - timedelta(days=90)
        records = generate_hourly_records(start_time, num_hours=90 * 24)
        export_dataset_to_csv(records, historical_csv)
        print(f"[MedAxis Init] Successfully generated {len(records)} records in {historical_csv}")

    if not os.path.exists(template_csv):
        export_sample_upload_template(template_csv)
        print(f"[MedAxis Init] Sample CSV upload template ready at {template_csv}")

def print_banner():
    banner = """
========================================================================
   __  __          _     _            _     
  |  \/  | ___  __| |   / \   __  __ (_)___ 
  | |\/| |/ _ \/ _` |  / _ \  \ \/ / | / __|
  | |  | |  __/ (_| | / ___ \  >  <  | \__ \\
  |_|  |_|\___|\__,_|/_/   \_\/_/\_\ |_|___/
                                             
  AI-Driven Predictive Hospital Bed & Patient-Flow Forecasting
  Focus Feature: 24-48h Census & Inflow Prediction with Threshold Alerts
  Prepared for: MedAxis (SIH 2025/2026)
========================================================================
* Web Application URL: http://127.0.0.1:8000
* Interactive API Docs: http://127.0.0.1:8000/docs
* Status: Server starting up... Press Ctrl+C to terminate.
========================================================================
"""
    print(banner)

if __name__ == "__main__":
    init_data()
    print_banner()
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )
