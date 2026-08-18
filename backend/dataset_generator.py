"""
MedAxis - Hospital Dataset & Time-Series Data Generator
Generates realistic multi-ward hospital occupancy, admission, and discharge data
incorporating diurnal cycles, day-of-week trends, and clinical bed dynamics.
"""

import os
import csv
import math
import random
from datetime import datetime, timedelta

# Ward specifications and capacities
WARD_CONFIG = {
    "Emergency": {
        "name": "Emergency Department (ED)",
        "capacity": 50,
        "base_occupancy_ratio": 0.76,
        "admission_rate_mean": 3.8,
        "discharge_rate_mean": 3.7,
        "peak_hours": [15, 16, 17, 18, 19, 20, 21, 22],
        "low_hours": [2, 3, 4, 5, 6],
        "critical_threshold": 0.90,
        "warning_threshold": 0.75,
        "unit_type": "Critical Flow",
        "description": "High turnover unit with volatile emergency patient inflow."
    },
    "ICU": {
        "name": "Intensive Care Unit (ICU)",
        "capacity": 30,
        "base_occupancy_ratio": 0.83,
        "admission_rate_mean": 0.9,
        "discharge_rate_mean": 0.85,
        "peak_hours": [11, 12, 14, 18, 20],
        "low_hours": [3, 4, 5],
        "critical_threshold": 0.90,
        "warning_threshold": 0.80,
        "unit_type": "High Acuity",
        "description": "Bottleneck unit with long average length of stay (ALOS)."
    },
    "General Medicine": {
        "name": "General Medicine Ward",
        "capacity": 120,
        "base_occupancy_ratio": 0.80,
        "admission_rate_mean": 4.5,
        "discharge_rate_mean": 4.4,
        "peak_hours": [13, 14, 15, 16, 17],
        "low_hours": [1, 2, 3, 4, 5],
        "critical_threshold": 0.90,
        "warning_threshold": 0.75,
        "unit_type": "Inpatient",
        "description": "Largest inpatient ward with heavy morning discharge and afternoon intake cycles."
    },
    "Surgical Ward": {
        "name": "Surgical & Post-Op Ward",
        "capacity": 80,
        "base_occupancy_ratio": 0.72,
        "admission_rate_mean": 3.0,
        "discharge_rate_mean": 2.9,
        "peak_hours": [8, 9, 10, 11, 14],
        "low_hours": [0, 1, 2, 3, 4],
        "critical_threshold": 0.90,
        "warning_threshold": 0.75,
        "unit_type": "Surgical",
        "description": "Scheduled weekday elective surgeries combined with emergent surgical beds."
    },
    "Pediatrics": {
        "name": "Pediatric Ward",
        "capacity": 40,
        "base_occupancy_ratio": 0.65,
        "admission_rate_mean": 1.6,
        "discharge_rate_mean": 1.5,
        "peak_hours": [10, 11, 16, 17, 18],
        "low_hours": [2, 3, 4, 5],
        "critical_threshold": 0.88,
        "warning_threshold": 0.70,
        "unit_type": "Specialized",
        "description": "Pediatric inpatient care with family-assisted discharge planning."
    }
}


def get_ward_config():
    """Returns the hospital ward configuration metadata."""
    return WARD_CONFIG


def generate_hourly_records(start_time, num_hours=2160, seed=42):
    """
    Generates realistic hourly hospital admission, discharge, and census records
    across all wards for the specified number of hours (default 90 days = 2160 hrs).
    """
    random.seed(seed)
    records = []

    # Initial state tracking for occupied beds
    current_beds = {
        ward: int(cfg["capacity"] * cfg["base_occupancy_ratio"])
        for ward, cfg in WARD_CONFIG.items()
    }

    for step in range(num_hours):
        current_time = start_time + timedelta(hours=step)
        hour = current_time.hour
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        is_weekend = (weekday >= 5)

        for ward, cfg in WARD_CONFIG.items():
            cap = cfg["capacity"]

            # Hourly diurnal multiplier
            if hour in cfg["peak_hours"]:
                hour_admission_mult = 1.45 + (math.sin(hour / 24 * 2 * math.pi) * 0.15)
                hour_discharge_mult = 1.35 if (9 <= hour <= 14) else 0.75
            elif hour in cfg["low_hours"]:
                hour_admission_mult = 0.35
                hour_discharge_mult = 0.15
            else:
                hour_admission_mult = 0.95
                hour_discharge_mult = 1.1 if (10 <= hour <= 15) else 0.8

            # Day of week multiplier (electives drop on weekends)
            if is_weekend:
                if ward == "Surgical Ward":
                    weekend_mult = 0.40
                elif ward == "General Medicine":
                    weekend_mult = 0.75
                else:
                    weekend_mult = 1.10  # ED often busier on weekends
            else:
                weekend_mult = 1.05

            # Random Poisson-like jitter
            lambda_adm = cfg["admission_rate_mean"] * hour_admission_mult * weekend_mult
            lambda_dis = cfg["discharge_rate_mean"] * hour_discharge_mult

            # Generate integer admissions and discharges
            admissions = max(0, int(random.gauss(lambda_adm, math.sqrt(max(0.5, lambda_adm)))))
            discharges = max(0, int(random.gauss(lambda_dis, math.sqrt(max(0.5, lambda_dis)))))

            # Discharges cannot exceed currently occupied beds
            discharges = min(discharges, current_beds[ward])

            # Update occupied beds with boundary dampening
            new_occupied = current_beds[ward] + admissions - discharges
            # Keep within realistic capacity limits (can slightly overflow during peak surge up to 105%)
            max_limit = int(cap * 1.08)
            new_occupied = max(0, min(max_limit, new_occupied))
            current_beds[ward] = new_occupied

            occupancy_pct = round((new_occupied / cap) * 100, 1)

            # Determine RAG status
            if occupancy_pct >= (cfg["critical_threshold"] * 100):
                rag_status = "RED"
            elif occupancy_pct >= (cfg["warning_threshold"] * 100):
                rag_status = "AMBER"
            else:
                rag_status = "GREEN"

            record = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:00:00"),
                "ward": ward,
                "ward_name": cfg["name"],
                "total_beds": cap,
                "occupied_beds": new_occupied,
                "available_beds": max(0, cap - new_occupied),
                "occupancy_rate": round(new_occupied / cap, 4),
                "occupancy_percent": occupancy_pct,
                "admissions": admissions,
                "discharges": discharges,
                "net_change": admissions - discharges,
                "rag_status": rag_status,
                "hour": hour,
                "weekday": weekday,
                "is_weekend": int(is_weekend)
            }
            records.append(record)

    return records


def export_dataset_to_csv(records, filepath):
    """Exports records to CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    if not records:
        return

    fieldnames = list(records[0].keys())
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def export_sample_upload_template(filepath):
    """Creates a sample CSV template for user uploads."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    headers = ["timestamp", "ward", "occupied_beds", "total_beds", "admissions", "discharges"]
    
    # Generate 48 hours of sample upload records for Emergency & ICU
    now = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=48)
    sample_rows = []
    
    for i in range(48):
        dt = now + timedelta(hours=i)
        t_str = dt.strftime("%Y-%m-%d %H:00:00")
        sample_rows.append({
            "timestamp": t_str,
            "ward": "Emergency",
            "occupied_beds": random.randint(34, 48),
            "total_beds": 50,
            "admissions": random.randint(2, 6),
            "discharges": random.randint(1, 5)
        })
        sample_rows.append({
            "timestamp": t_str,
            "ward": "ICU",
            "occupied_beds": random.randint(22, 28),
            "total_beds": 30,
            "admissions": random.randint(0, 2),
            "discharges": random.randint(0, 2)
        })

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sample_rows)


if __name__ == "__main__":
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_dt = now - timedelta(days=90)
    print(f"Generating 90-day dataset from {start_dt} to {now}...")
    dataset = generate_hourly_records(start_dt, num_hours=90 * 24)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    
    export_dataset_to_csv(dataset, os.path.join(data_dir, "sample_hospital_historical.csv"))
    export_sample_upload_template(os.path.join(data_dir, "sample_upload_template.csv"))
    print(f"Successfully generated {len(dataset)} records in {data_dir}!")
