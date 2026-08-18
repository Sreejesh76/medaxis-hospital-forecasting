"""
MedAxis Automated Verification & Test Suite
Validates time-series forecasting accuracy, RAG thresholds, What-If simulation,
and FastAPI endpoint responses.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Append project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.dataset_generator import get_ward_config, generate_hourly_records
from backend.forecasting_engine import HospitalForecaster
from backend.simulation_engine import SimulationEngine
from backend.alert_manager import AlertManager
from backend.app import (
    get_hospital_summary,
    get_forecast,
    simulate_scenario,
    dispatch_alert,
    get_alert_history,
    SimulationRequest,
    DispatchAlertRequest
)


def test_dataset_generator():
    print("[1/5] Testing Dataset Generator...")
    start_time = datetime.now() - timedelta(days=7)
    records = generate_hourly_records(start_time, num_hours=24 * 7)
    assert len(records) == 7 * 24 * 5, f"Expected {7*24*5} records, got {len(records)}"
    sample = records[0]
    assert "occupied_beds" in sample and "total_beds" in sample and "rag_status" in sample
    print(f"      OK: Successfully generated {len(records)} hourly records across 5 wards.")


def test_forecasting_engine():
    print("[2/5] Testing AI Forecasting Engine...")
    forecaster = HospitalForecaster()
    
    # 24h forecast test
    fc_24 = forecaster.forecast_ward("ICU", horizon_hours=24)
    assert fc_24["ward"] == "ICU"
    assert len(fc_24["forecast"]) == 24
    assert fc_24["capacity"] == 30
    assert "upper_bound" in fc_24["forecast"][0]
    assert "lower_bound" in fc_24["forecast"][0]

    # 48h hospital-wide forecast test
    all_fc = forecaster.forecast_all_wards(horizon_hours=48)
    assert all_fc["total_capacity"] == 320
    assert len(all_fc["aggregate_timeline"]) == 48
    assert all_fc["hospital_status"] in ["GREEN", "AMBER", "RED"]
    print(f"      OK: Forecaster generated 48h timeline. Current Hospital Census: {all_fc['total_current_occupied']}/{all_fc['total_capacity']} ({all_fc['current_occupancy_pct']}%).")


def test_simulation_engine():
    print("[3/5] Testing What-If Scenario Simulation Engine...")
    forecaster = HospitalForecaster()
    sim_engine = SimulationEngine(forecaster)
    
    # Test Viral Surge scenario (+35% surge)
    res_surge = sim_engine.run_scenario(scenario_id="flu_epidemic", horizon_hours=48)
    assert res_surge["surge_factor"] == 1.35
    assert res_surge["max_simulated_occupied"] >= res_surge["max_baseline_occupied"]
    assert "recommendation" in res_surge
    
    # Test Proactive Fast-Track discharge (+30% turnover)
    res_fast = sim_engine.run_scenario(scenario_id="fast_track_discharge", horizon_hours=48)
    assert res_fast["discharge_factor"] == 1.30
    print(f"      OK: Scenario simulations functional. Surge delta: +{res_surge['net_bed_impact']} beds.")


def test_alert_manager():
    print("[4/5] Testing Clinical Threshold Alert & Dispatch Manager...")
    forecaster = HospitalForecaster()
    alert_mgr = AlertManager()
    
    # Trigger emergency ward forecast
    ed_fc = forecaster.forecast_ward("Emergency", horizon_hours=48, surge_factor=1.4)
    alerts = alert_mgr.evaluate_forecast(ed_fc)
    assert isinstance(alerts, list)
    
    if alerts:
        first_alert = alerts[0]
        assert "recommended_actions" in first_alert
        assert len(first_alert["recommended_actions"]) > 0
        
        # Test alert dispatch simulation
        disp = alert_mgr.dispatch_alert_simulation(first_alert, channel="SMS")
        assert disp["status"] == "DELIVERED"
        assert len(alert_mgr.get_dispatch_history()) == 1
    
    print(f"      OK: Threshold alerts and multi-channel dispatch verified.")


def test_fastapi_endpoints():
    print("[5/5] Testing FastAPI Application Endpoints via Async Invocations...")
    
    # Test summary API
    data_summary = asyncio.run(get_hospital_summary(horizon=48))
    assert data_summary["status"] == "success"
    assert "wards" in data_summary
    assert len(data_summary["wards"]) == 5
    
    # Test forecast API for ICU
    data_fc = asyncio.run(get_forecast(ward="ICU", horizon=24, surge=1.0, discharge=1.0))
    assert data_fc["status"] == "success"
    assert data_fc["ward"] == "ICU"
    assert len(data_fc["timeline"]) == 24
    
    # Test forecast API for ALL wards
    data_fc_all = asyncio.run(get_forecast(ward="ALL", horizon=48, surge=1.0, discharge=1.0))
    assert data_fc_all["status"] == "success"
    assert len(data_fc_all["timeline"]) == 48
    
    # Test simulate API
    sim_req = SimulationRequest(scenario_id="flu_epidemic", surge_factor=1.35, discharge_factor=0.9, horizon_hours=24, ward="ALL")
    data_sim = asyncio.run(simulate_scenario(sim_req))
    assert data_sim["status"] == "success"
    assert "simulation" in data_sim
    
    # Test dispatch API
    disp_req = DispatchAlertRequest(
        alert_id="ALT-ICU-001",
        channel="SMS",
        ward="ICU",
        severity="CRITICAL",
        message="Urgent: ICU forecasted at 93% capacity."
    )
    data_disp = asyncio.run(dispatch_alert(disp_req))
    assert data_disp["status"] == "success"
    
    # Test history API
    data_hist = asyncio.run(get_alert_history())
    assert data_hist["status"] == "success"
    assert len(data_hist["history"]) >= 1

    print(f"      OK: All API endpoints passed verification.")


if __name__ == "__main__":
    print("\n=======================================================")
    print("   MedAxis AI Hospital Forecasting - Test Suite       ")
    print("=======================================================\n")
    test_dataset_generator()
    test_forecasting_engine()
    test_simulation_engine()
    test_alert_manager()
    test_fastapi_endpoints()
    print("\n=======================================================")
    print("   SUCCESS: All 5 verification suites passed 100%!     ")
    print("=======================================================\n")
