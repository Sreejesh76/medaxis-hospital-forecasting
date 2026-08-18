"""
MedAxis - What-If Scenario & Surge Simulation Engine
Simulates hospital stress scenarios (Epidemic Surge, Mass Casualty, Discharge Backlog,
Fast-Track Clearance) and calculates the delta against baseline forecasts.
"""

from typing import Dict, Any, List
from .forecasting_engine import HospitalForecaster


PRESET_SCENARIOS = {
    "flu_epidemic": {
        "id": "flu_epidemic",
        "name": "Seasonal Epidemic / Viral Surge",
        "description": "+35% Emergency and Pediatric patient inflow, with slightly delayed general discharges.",
        "surge_factor": 1.35,
        "discharge_factor": 0.90,
        "primary_impact_wards": ["Emergency", "Pediatrics", "General Medicine"]
    },
    "mass_casualty": {
        "id": "mass_casualty",
        "name": "Mass Casualty / Major Incident (MCI)",
        "description": "Acute +75% influx into Emergency, Trauma Surgical, and ICU over the next 12–24 hours.",
        "surge_factor": 1.75,
        "discharge_factor": 0.80,
        "primary_impact_wards": ["Emergency", "ICU", "Surgical Ward"]
    },
    "discharge_bottleneck": {
        "id": "discharge_bottleneck",
        "name": "Pharmacy / Transport Discharge Backlog",
        "description": "Discharges slowed by 30% due to administrative bottleneck, compounding ward boarding.",
        "surge_factor": 1.05,
        "discharge_factor": 0.70,
        "primary_impact_wards": ["General Medicine", "Surgical Ward", "ICU"]
    },
    "fast_track_discharge": {
        "id": "fast_track_discharge",
        "name": "Proactive Bed Turnover Intervention",
        "description": "Bed managers enforce early 10:00 AM discharge rounds (+30% turnover) before afternoon intake.",
        "surge_factor": 1.00,
        "discharge_factor": 1.30,
        "primary_impact_wards": ["General Medicine", "Surgical Ward", "Emergency"]
    }
}


class SimulationEngine:
    """Executes what-if scenario analyses and compares against baseline."""

    def __init__(self, forecaster: HospitalForecaster):
        self.forecaster = forecaster

    def run_scenario(
        self,
        scenario_id: str = "custom",
        custom_surge: float = 1.0,
        custom_discharge: float = 1.0,
        horizon_hours: int = 48,
        selected_ward: str = "ALL"
    ) -> Dict[str, Any]:
        """Runs a simulation scenario comparing baseline vs simulated conditions."""
        if scenario_id in PRESET_SCENARIOS:
            preset = PRESET_SCENARIOS[scenario_id]
            surge = preset["surge_factor"]
            discharge = preset["discharge_factor"]
            name = preset["name"]
            desc = preset["description"]
        else:
            surge = max(0.2, min(3.0, custom_surge))
            discharge = max(0.2, min(3.0, custom_discharge))
            name = "Custom What-If Scenario"
            desc = f"Simulating custom surge of {round((surge-1)*100):+d}% and discharge rate of {round((discharge-1)*100):+d}%."

        # Compute baseline
        baseline_data = self.forecaster.forecast_all_wards(
            horizon_hours=horizon_hours,
            surge_factor=1.0,
            discharge_factor=1.0
        )

        # Compute scenario
        simulated_data = self.forecaster.forecast_all_wards(
            horizon_hours=horizon_hours,
            surge_factor=surge,
            discharge_factor=discharge
        )

        # Calculate comparative metrics
        if selected_ward == "ALL" or selected_ward not in self.forecaster.ward_config:
            base_timeline = baseline_data["aggregate_timeline"]
            sim_timeline = simulated_data["aggregate_timeline"]
            capacity = baseline_data["total_capacity"]
            ward_display = "Entire Hospital"
        else:
            base_timeline = baseline_data["wards"][selected_ward]["forecast"]
            sim_timeline = simulated_data["wards"][selected_ward]["forecast"]
            capacity = baseline_data["wards"][selected_ward]["capacity"]
            ward_display = baseline_data["wards"][selected_ward]["ward_name"]

        comparison_series = []
        max_baseline_occ = 0
        max_sim_occ = 0
        hours_in_critical = 0

        for i in range(horizon_hours):
            b_pt = base_timeline[i]
            s_pt = sim_timeline[i]

            b_occ = b_pt.get("predicted_occupied", b_pt.get("predicted_occupied", 0))
            s_occ = s_pt.get("predicted_occupied", s_pt.get("predicted_occupied", 0))

            max_baseline_occ = max(max_baseline_occ, b_occ)
            max_sim_occ = max(max_sim_occ, s_occ)

            sim_pct = round((s_occ / capacity) * 100, 1)
            if sim_pct >= 90.0:
                hours_in_critical += 1

            comparison_series.append({
                "step": i + 1,
                "timestamp": b_pt["timestamp"],
                "display_time": b_pt["display_time"],
                "date_display": b_pt["date_display"],
                "baseline_occupied": b_occ,
                "simulated_occupied": s_occ,
                "baseline_pct": round((b_occ / capacity) * 100, 1),
                "simulated_pct": sim_pct,
                "delta_beds": s_occ - b_occ,
                "capacity": capacity,
                "simulated_rag": "RED" if sim_pct >= 90 else ("AMBER" if sim_pct >= 75 else "GREEN")
            })

        net_bed_impact = max_sim_occ - max_baseline_occ

        # Recommendation based on simulation
        if max_sim_occ > capacity:
            recommendation = f"CRITICAL DEFICIT: Simulation projects an overflow of {max_sim_occ - capacity} beds above capacity. Activate overflow wing or divert ambulance intake."
        elif hours_in_critical > 0:
            recommendation = f"HIGH STRESS: Ward will spend {hours_in_critical} hours in Red Zone (>90%). Recommend mobilizing 4–6 early discharges."
        elif surge < 1.0 or discharge > 1.0:
            recommendation = "POSITIVE RECOVERY: Intervention successfully lowers peak census by {abs(net_bed_impact)} beds, keeping hospital in Green/Amber safe zone."
        else:
            recommendation = "STABLE: Occupancy remains within manageable buffer limits throughout the forecast period."

        return {
            "scenario_name": name,
            "scenario_description": desc,
            "ward_analyzed": ward_display,
            "surge_factor": surge,
            "discharge_factor": discharge,
            "horizon_hours": horizon_hours,
            "max_baseline_occupied": max_baseline_occ,
            "max_simulated_occupied": max_sim_occ,
            "capacity": capacity,
            "net_bed_impact": net_bed_impact,
            "hours_in_critical": hours_in_critical,
            "recommendation": recommendation,
            "timeline": comparison_series,
            "presets": PRESET_SCENARIOS
        }
