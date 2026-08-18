"""
MedAxis - AI Hospital Bed & Patient-Flow Forecasting API Server
FastAPI backend powering the interactive web command center.
"""

import os
import io
import csv
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .dataset_generator import get_ward_config, generate_hourly_records, export_sample_upload_template
from .forecasting_engine import HospitalForecaster
from .simulation_engine import SimulationEngine, PRESET_SCENARIOS
from .alert_manager import AlertManager

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize core engines
forecaster = HospitalForecaster()
simulation_engine = SimulationEngine(forecaster)
alert_manager = AlertManager()

# Create sample template CSV if not existing
sample_template_path = os.path.join(DATA_DIR, "sample_upload_template.csv")
if not os.path.exists(sample_template_path):
    export_sample_upload_template(sample_template_path)

# Initialize FastAPI App
app = FastAPI(
    title="MedAxis - AI Hospital Bed & Patient-Flow Forecasting",
    description="24–48 hour predictive bed-occupancy and patient inflow forecasting with threshold alerting.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Pydantic Request Models
class SimulationRequest(BaseModel):
    scenario_id: Optional[str] = "custom"
    surge_factor: Optional[float] = 1.0
    discharge_factor: Optional[float] = 1.0
    horizon_hours: Optional[int] = 48
    ward: Optional[str] = "ALL"


class DispatchAlertRequest(BaseModel):
    alert_id: str
    channel: str = "SMS"
    ward: str
    severity: str
    message: str


# API Routes

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main Command Center dashboard."""
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>MedAxis Web App Loading... Please ensure index.html exists in templates/</h1>")


@app.get("/api/summary")
async def get_hospital_summary(horizon: int = Query(48, ge=12, le=72)):
    """Returns top-level hospital occupancy, forecast summary, and active alerts."""
    forecast_data = forecaster.forecast_all_wards(horizon_hours=horizon)
    
    # Collect all alerts
    all_alerts = []
    for ward_name, wf in forecast_data["wards"].items():
        ward_alerts = alert_manager.evaluate_forecast(wf)
        all_alerts.extend(ward_alerts)

    return {
        "status": "success",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hospital_name": "Apex Metro Health System",
        "total_beds": forecast_data["total_capacity"],
        "occupied_beds": forecast_data["total_current_occupied"],
        "available_beds": forecast_data["total_available_beds"],
        "occupancy_rate_pct": forecast_data["current_occupancy_pct"],
        "hospital_rag_status": forecast_data["hospital_status"],
        "critical_wards": forecast_data["critical_wards"],
        "warning_wards": forecast_data["warning_wards"],
        "total_predicted_admissions_48h": forecast_data["total_predicted_admissions"],
        "total_predicted_discharges_48h": forecast_data["total_predicted_discharges"],
        "net_patient_flow": forecast_data["net_flow_48h"],
        "active_alerts_count": len(all_alerts),
        "alerts": all_alerts,
        "wards": [
            {
                "id": w_id,
                "name": w_data["ward_name"],
                "unit_type": w_data["unit_type"],
                "capacity": w_data["capacity"],
                "current_occupancy": w_data["current_occupancy"],
                "current_occupancy_pct": w_data["current_occupancy_pct"],
                "overall_status": w_data["overall_status"],
                "peak_occupancy_pct": w_data["peak_occupancy_pct"],
                "peak_time": w_data["peak_time"]
            }
            for w_id, w_data in forecast_data["wards"].items()
        ]
    }


@app.get("/api/forecast")
async def get_forecast(
    ward: str = Query("ALL", description="Ward name or ALL for aggregate"),
    horizon: int = Query(48, ge=12, le=72),
    surge: float = Query(1.0, ge=0.2, le=3.0),
    discharge: float = Query(1.0, ge=0.2, le=3.0)
):
    """Returns detailed hourly forecast curve with upper/lower bounds."""
    if ward == "ALL":
        all_data = forecaster.forecast_all_wards(
            horizon_hours=horizon,
            surge_factor=surge,
            discharge_factor=discharge
        )
        return {
            "status": "success",
            "ward": "ALL",
            "ward_name": "Entire Hospital (All Wards)",
            "capacity": all_data["total_capacity"],
            "current_occupancy": all_data["total_current_occupied"],
            "current_occupancy_pct": all_data["current_occupancy_pct"],
            "overall_status": all_data["hospital_status"],
            "critical_threshold_pct": 90,
            "warning_threshold_pct": 75,
            "timeline": all_data["aggregate_timeline"],
            "wards_breakdown": all_data["wards"]
        }
    else:
        if ward not in forecaster.ward_config:
            raise HTTPException(status_code=404, detail=f"Ward '{ward}' not found.")
        
        ward_data = forecaster.forecast_ward(
            ward=ward,
            horizon_hours=horizon,
            surge_factor=surge,
            discharge_factor=discharge
        )
        return {
            "status": "success",
            "ward": ward_data["ward"],
            "ward_name": ward_data["ward_name"],
            "unit_type": ward_data["unit_type"],
            "capacity": ward_data["capacity"],
            "current_occupancy": ward_data["current_occupancy"],
            "current_occupancy_pct": ward_data["current_occupancy_pct"],
            "overall_status": ward_data["overall_status"],
            "critical_threshold_pct": ward_data["critical_threshold_pct"],
            "warning_threshold_pct": ward_data["warning_threshold_pct"],
            "peak_occupancy_pct": ward_data["peak_occupancy_pct"],
            "peak_time": ward_data["peak_time"],
            "total_admissions_expected": ward_data["total_admissions_expected"],
            "total_discharges_expected": ward_data["total_discharges_expected"],
            "net_patient_flow": ward_data["net_patient_flow"],
            "timeline": ward_data["forecast"],
            "alerts": ward_data["alerts"]
        }


@app.get("/api/alerts")
async def get_alerts(horizon: int = Query(48)):
    """Evaluates and returns all active clinical threshold alerts."""
    forecast_data = forecaster.forecast_all_wards(horizon_hours=horizon)
    all_alerts = []
    for ward_name, wf in forecast_data["wards"].items():
        ward_alerts = alert_manager.evaluate_forecast(wf)
        all_alerts.extend(ward_alerts)

    return {
        "status": "success",
        "total_alerts": len(all_alerts),
        "alerts": all_alerts
    }


@app.post("/api/simulate")
async def simulate_scenario(req: SimulationRequest):
    """Runs What-If scenario simulation."""
    res = simulation_engine.run_scenario(
        scenario_id=req.scenario_id or "custom",
        custom_surge=req.surge_factor or 1.0,
        custom_discharge=req.discharge_factor or 1.0,
        horizon_hours=req.horizon_hours or 48,
        selected_ward=req.ward or "ALL"
    )
    return {"status": "success", "simulation": res}


@app.post("/api/alerts/dispatch")
async def dispatch_alert(req: DispatchAlertRequest):
    """Simulates an alert notification dispatch via SMS / Email / Pager."""
    res = alert_manager.dispatch_alert_simulation(
        alert={
            "id": req.alert_id,
            "ward": req.ward,
            "severity": req.severity,
            "sms_preview": req.message
        },
        channel=req.channel
    )
    return {"status": "success", "dispatch": res}


@app.get("/api/alerts/history")
async def get_alert_history():
    """Returns the notification dispatch history."""
    return {
        "status": "success",
        "history": alert_manager.get_dispatch_history()
    }


@app.post("/api/upload-csv")
async def upload_hospital_csv(file: UploadFile = File(...)):
    """
    Accepts custom hospital CSV upload, validates schema, and returns analysis.
    Expected columns: timestamp, ward, occupied_beds, total_beds, admissions, discharges
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .csv file")

    content = await file.read()
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    required_cols = {"timestamp", "ward", "occupied_beds", "total_beds"}
    found_cols = set(rows[0].keys())
    
    missing = required_cols - found_cols
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns in CSV: {list(missing)}. Required: {list(required_cols)}"
        )

    # Process rows and extract ward latest census
    ward_summaries = {}
    for r in rows:
        w = r.get("ward", "General")
        occ = int(float(r.get("occupied_beds", 0)))
        tot = int(float(r.get("total_beds", 100)))
        adm = int(float(r.get("admissions", 0))) if "admissions" in r else 0
        dis = int(float(r.get("discharges", 0))) if "discharges" in r else 0

        if w not in ward_summaries:
            ward_summaries[w] = {
                "ward": w,
                "latest_occupied": occ,
                "total_beds": tot,
                "admissions_sum": 0,
                "discharges_sum": 0,
                "record_count": 0
            }
        
        ward_summaries[w]["latest_occupied"] = occ
        ward_summaries[w]["total_beds"] = tot
        ward_summaries[w]["admissions_sum"] += adm
        ward_summaries[w]["discharges_sum"] += dis
        ward_summaries[w]["record_count"] += 1

    return {
        "status": "success",
        "filename": file.filename,
        "total_rows_ingested": len(rows),
        "wards_detected": list(ward_summaries.keys()),
        "ward_summaries": list(ward_summaries.values()),
        "message": f"Successfully ingested {len(rows)} records across {len(ward_summaries)} wards. Forecast pipeline synchronized."
    }


@app.get("/data/download-template")
async def download_csv_template():
    """Serves sample CSV template for download."""
    if os.path.exists(sample_template_path):
        return FileResponse(
            sample_template_path,
            media_type="text/csv",
            filename="medaxis_sample_hospital_template.csv"
        )
    raise HTTPException(status_code=404, detail="Template file not found")
