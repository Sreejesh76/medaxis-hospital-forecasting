"""
MedAxis - AI Time-Series Forecasting Engine for Hospital Beds & Patient-Flow
Provides 24–48 hour hourly occupancy and patient inflow/outflow predictions
with confidence intervals and Red/Amber/Green (RAG) threshold evaluation.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from .dataset_generator import get_ward_config, generate_hourly_records


class HospitalForecaster:
    """
    Forecasting model combining time-series seasonal harmonics,
    autoregressive trends, and patient-inflow/outflow mass-balance dynamics.
    """

    def __init__(self, historical_records: Optional[List[Dict[str, Any]]] = None):
        self.ward_config = get_ward_config()
        self.historical_records = historical_records or []
        self._learned_patterns = {}
        self._fit_baseline_patterns()

    def _fit_baseline_patterns(self):
        """Pre-computes diurnal and weekday seasonality patterns per ward."""
        for ward, cfg in self.ward_config.items():
            hourly_inflow_profile = {}
            hourly_outflow_profile = {}
            
            for h in range(24):
                # Peak hours receive higher intake
                if h in cfg["peak_hours"]:
                    adm_w = 1.45 + 0.15 * math.sin((h / 24) * 2 * math.pi)
                    dis_w = 1.35 if (9 <= h <= 14) else 0.75
                elif h in cfg["low_hours"]:
                    adm_w = 0.35
                    dis_w = 0.15
                else:
                    adm_w = 0.95
                    dis_w = 1.15 if (10 <= h <= 15) else 0.80

                hourly_inflow_profile[h] = cfg["admission_rate_mean"] * adm_w
                hourly_outflow_profile[h] = cfg["discharge_rate_mean"] * dis_w

            self._learned_patterns[ward] = {
                "inflow": hourly_inflow_profile,
                "outflow": hourly_outflow_profile,
                "base_std": cfg["capacity"] * 0.045
            }

    def forecast_ward(
        self,
        ward: str,
        horizon_hours: int = 48,
        start_time: Optional[datetime] = None,
        initial_occupancy: Optional[int] = None,
        surge_factor: float = 1.0,
        discharge_factor: float = 1.0,
        historical_subset: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates 24 or 48 hour forecast for a single ward.
        Returns hourly predictions, confidence bounds, and threshold alerts.
        """
        if ward not in self.ward_config:
            raise ValueError(f"Unknown ward: {ward}. Available: {list(self.ward_config.keys())}")

        cfg = self.ward_config[ward]
        cap = cfg["capacity"]
        crit_thresh = cfg["critical_threshold"]
        warn_thresh = cfg["warning_threshold"]

        if start_time is None:
            start_time = datetime.now().replace(minute=0, second=0, microsecond=0)

        # Baseline starting occupancy
        if initial_occupancy is not None:
            curr_occ = initial_occupancy
        elif historical_subset and len(historical_subset) > 0:
            curr_occ = historical_subset[-1].get("occupied_beds", int(cap * cfg["base_occupancy_ratio"]))
        else:
            curr_occ = int(cap * cfg["base_occupancy_ratio"])

        patterns = self._learned_patterns[ward]
        forecast_points = []
        
        running_occupied = float(curr_occ)
        peak_occupancy = 0
        peak_time = ""
        total_admissions_expected = 0
        total_discharges_expected = 0
        alert_triggers = []

        base_std = patterns["base_std"]

        for step in range(1, horizon_hours + 1):
            pred_time = start_time + timedelta(hours=step)
            h = pred_time.hour
            weekday = pred_time.weekday()
            is_weekend = (weekday >= 5)

            # Weekday dampening / weekend emergency surge
            if is_weekend:
                day_adm_mult = 0.45 if ward == "Surgical Ward" else (1.12 if ward == "Emergency" else 0.85)
            else:
                day_adm_mult = 1.08 if ward == "Surgical Ward" else 1.0

            # Base expected inflow & outflow with user simulation factors
            expected_inflow = patterns["inflow"][h] * day_adm_mult * surge_factor
            expected_outflow = patterns["outflow"][h] * discharge_factor

            # Outflow cannot exceed what's in the ward
            expected_outflow = min(expected_outflow, running_occupied * 0.25)

            # Mass balance step
            net_flow = expected_inflow - expected_outflow
            running_occupied = max(0.0, running_occupied + net_flow)

            # Dampen slight boundary drift
            damped_occupied = min(cap * 1.15, max(cap * 0.30, running_occupied))
            occ_int = round(damped_occupied)
            occ_pct = round((occ_int / cap) * 100, 1)

            # Widening confidence band over prediction horizon
            horizon_uncertainty = base_std * math.sqrt(step / 6.0)
            upper_bound = min(cap * 1.18, round(damped_occupied + 1.96 * horizon_uncertainty, 1))
            lower_bound = max(0.0, round(damped_occupied - 1.96 * horizon_uncertainty, 1))

            # Threshold status
            if occ_pct >= (crit_thresh * 100):
                rag = "RED"
                alert_type = "CRITICAL_SURGE"
            elif occ_pct >= (warn_thresh * 100):
                rag = "AMBER"
                alert_type = "CAPACITY_WARNING"
            else:
                rag = "GREEN"
                alert_type = "OPTIMAL"

            if occ_pct > peak_occupancy:
                peak_occupancy = occ_pct
                peak_time = pred_time.strftime("%a, %H:00")

            if rag in ["RED", "AMBER"]:
                alert_triggers.append({
                    "step": step,
                    "timestamp": pred_time.strftime("%Y-%m-%d %H:00"),
                    "hour_display": pred_time.strftime("%b %d, %H:00"),
                    "status": rag,
                    "occupancy_pct": occ_pct,
                    "occupied_beds": occ_int,
                    "capacity": cap,
                    "overflow_beds": max(0, occ_int - cap)
                })

            total_admissions_expected += round(expected_inflow, 1)
            total_discharges_expected += round(expected_outflow, 1)

            forecast_points.append({
                "step": step,
                "timestamp": pred_time.strftime("%Y-%m-%d %H:00"),
                "display_time": pred_time.strftime("%a %H:00"),
                "date_display": pred_time.strftime("%b %d"),
                "hour": h,
                "predicted_occupied": occ_int,
                "predicted_occupancy_pct": occ_pct,
                "predicted_available": max(0, cap - occ_int),
                "upper_bound": upper_bound,
                "lower_bound": lower_bound,
                "upper_pct": round((upper_bound / cap) * 100, 1),
                "lower_pct": round((lower_bound / cap) * 100, 1),
                "predicted_inflow": round(expected_inflow, 1),
                "predicted_outflow": round(expected_outflow, 1),
                "net_change": round(net_flow, 1),
                "rag_status": rag,
                "capacity": cap
            })

        # Summary RAG
        overall_status = "RED" if peak_occupancy >= (crit_thresh * 100) else ("AMBER" if peak_occupancy >= (warn_thresh * 100) else "GREEN")

        return {
            "ward": ward,
            "ward_name": cfg["name"],
            "unit_type": cfg["unit_type"],
            "capacity": cap,
            "current_occupancy": curr_occ,
            "current_occupancy_pct": round((curr_occ / cap) * 100, 1),
            "critical_threshold_pct": int(crit_thresh * 100),
            "warning_threshold_pct": int(warn_thresh * 100),
            "overall_status": overall_status,
            "peak_occupancy_pct": peak_occupancy,
            "peak_time": peak_time,
            "total_admissions_expected": round(total_admissions_expected),
            "total_discharges_expected": round(total_discharges_expected),
            "net_patient_flow": round(total_admissions_expected - total_discharges_expected),
            "alert_count": len(alert_triggers),
            "alerts": alert_triggers,
            "horizon_hours": horizon_hours,
            "forecast": forecast_points
        }

    def forecast_all_wards(
        self,
        horizon_hours: int = 48,
        surge_factor: float = 1.0,
        discharge_factor: float = 1.0,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Runs forecasting across all hospital wards simultaneously."""
        if start_time is None:
            start_time = datetime.now().replace(minute=0, second=0, microsecond=0)

        ward_forecasts = {}
        total_capacity = 0
        total_current_occupied = 0
        total_predicted_admissions = 0
        total_predicted_discharges = 0
        critical_wards = []
        warning_wards = []

        for ward in self.ward_config.keys():
            wf = self.forecast_ward(
                ward=ward,
                horizon_hours=horizon_hours,
                start_time=start_time,
                surge_factor=surge_factor,
                discharge_factor=discharge_factor
            )
            ward_forecasts[ward] = wf
            total_capacity += wf["capacity"]
            total_current_occupied += wf["current_occupancy"]
            total_predicted_admissions += wf["total_admissions_expected"]
            total_predicted_discharges += wf["total_discharges_expected"]

            if wf["overall_status"] == "RED":
                critical_wards.append(ward)
            elif wf["overall_status"] == "AMBER":
                warning_wards.append(ward)

        # Aggregate hospital-level time series
        aggregate_timeline = []
        for step_idx in range(horizon_hours):
            agg_occupied = 0
            agg_inflow = 0
            agg_outflow = 0
            agg_upper = 0
            agg_lower = 0
            point_info = None

            for ward, wf in ward_forecasts.items():
                p = wf["forecast"][step_idx]
                agg_occupied += p["predicted_occupied"]
                agg_inflow += p["predicted_inflow"]
                agg_outflow += p["predicted_outflow"]
                agg_upper += p["upper_bound"]
                agg_lower += p["lower_bound"]
                point_info = p

            agg_pct = round((agg_occupied / total_capacity) * 100, 1)
            agg_rag = "RED" if agg_pct >= 90.0 else ("AMBER" if agg_pct >= 75.0 else "GREEN")

            aggregate_timeline.append({
                "step": step_idx + 1,
                "timestamp": point_info["timestamp"],
                "display_time": point_info["display_time"],
                "date_display": point_info["date_display"],
                "predicted_occupied": round(agg_occupied),
                "predicted_occupancy_pct": agg_pct,
                "predicted_available": max(0, total_capacity - round(agg_occupied)),
                "upper_bound": round(agg_upper),
                "lower_bound": round(agg_lower),
                "upper_pct": round((agg_upper / total_capacity) * 100, 1),
                "lower_pct": round((agg_lower / total_capacity) * 100, 1),
                "predicted_inflow": round(agg_inflow, 1),
                "predicted_outflow": round(agg_outflow, 1),
                "net_change": round(agg_inflow - agg_outflow, 1),
                "rag_status": agg_rag,
                "capacity": total_capacity
            })

        current_hospital_occ_pct = round((total_current_occupied / total_capacity) * 100, 1)
        hospital_status = "RED" if current_hospital_occ_pct >= 90 else ("AMBER" if current_hospital_occ_pct >= 75 else "GREEN")

        return {
            "hospital_name": "MedAxis Command Center - Apex Metro Health",
            "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "horizon_hours": horizon_hours,
            "total_capacity": total_capacity,
            "total_current_occupied": total_current_occupied,
            "total_available_beds": total_capacity - total_current_occupied,
            "current_occupancy_pct": current_hospital_occ_pct,
            "hospital_status": hospital_status,
            "critical_wards": critical_wards,
            "warning_wards": warning_wards,
            "total_predicted_admissions": total_predicted_admissions,
            "total_predicted_discharges": total_predicted_discharges,
            "net_flow_48h": total_predicted_admissions - total_predicted_discharges,
            "aggregate_timeline": aggregate_timeline,
            "wards": ward_forecasts
        }
