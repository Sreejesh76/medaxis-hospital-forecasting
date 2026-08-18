"""
MedAxis - Rule-Based Threshold Alert & Notification Dispatcher
Evaluates 24–48h forecasts against hospital capacity thresholds,
generates actionable clinical advisories, and simulates multi-channel alerts (SMS/Email/Banner).
"""

from datetime import datetime
from typing import List, Dict, Any


CLINICAL_ACTION_PLAYBOOK = {
    "Emergency": {
        "CRITICAL": [
            "Initiate ED Rapid Triage Protocol & divert non-critical ambulances to sister units.",
            "Deploy fast-track physician to ED Waiting Room for rapid discharge of Level 4/5 patients.",
            "Expedite transfer of admitted ED boarders to General Medicine overflow holding."
        ],
        "WARNING": [
            "Monitor ED bed turnover rate and stage 4 surge holding chairs.",
            "Alert on-call triage nurses for 18:00–22:00 peak inflow coverage.",
            "Pre-authorize point-of-care lab tests to reduce ED boarding turnaround."
        ]
    },
    "ICU": {
        "CRITICAL": [
            "URGENT: Step-down evaluation for 2–3 stable ICU patients to High Dependency Unit (HDU).",
            "Hold scheduled elective surgeries requiring post-op ICU bed reservation.",
            "Notify Chief Medical Officer (CMO) and Intensivist on-call of ICU capacity freeze."
        ],
        "WARNING": [
            "Audit ICU discharge readiness scores with attending critical care team.",
            "Verify ventilator and monitor availability in Step-Down HDU ward.",
            "Advise surgical booking team of tight ICU availability for tomorrow's schedule."
        ]
    },
    "General Medicine": {
        "CRITICAL": [
            "Activate Discharge Lounge: move medically stable patients awaiting ride/meds by 11:00 AM.",
            "Expedite pharmacy discharge medication delivery directly to bedside.",
            "Open 8 reserve overflow beds in Step-Down Annex."
        ],
        "WARNING": [
            "Conduct multidisciplinary 10:00 AM discharge huddle to identify noon discharges.",
            "Prioritize pending morning lab clearances for discharge-eligible patients.",
            "Coordinate with transport service for expedited patient repatriation."
        ]
    },
    "Surgical Ward": {
        "CRITICAL": [
            "Postpone non-urgent elective admissions scheduled for tomorrow morning.",
            "Convert 4 day-surgery recovery bays into overnight observation beds.",
            "Expedite post-op wound checks for Day-2 surgical patients eligible for home care."
        ],
        "WARNING": [
            "Review tomorrow's surgical slate with OR coordinator to balance bed load.",
            "Confirm post-discharge home nursing support for elective orthopedic cases."
        ]
    },
    "Pediatrics": {
        "CRITICAL": [
            "Open pediatric observation overflow room.",
            "Consult Pediatric Intensivist for step-down candidates.",
            "Mobilize pediatric respiratory therapists for evening viral influx."
        ],
        "WARNING": [
            "Audit pediatric hydration admissions for early afternoon discharge.",
            "Ensure adequate nebulizer and pediatric telemetry stock."
        ]
    }
}


class AlertManager:
    """Evaluates forecasts and issues structured clinical threshold alerts."""

    def __init__(self):
        self.notification_log: List[Dict[str, Any]] = []

    def evaluate_forecast(self, ward_forecast_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scans a ward forecast across the 24-48h horizon and generates
        consolidated alerts for any capacity breach windows.
        """
        alerts = []
        ward = ward_forecast_data["ward"]
        ward_name = ward_forecast_data["ward_name"]
        capacity = ward_forecast_data["capacity"]
        forecast_pts = ward_forecast_data["forecast"]

        # Track continuous breach windows
        in_breach = False
        breach_severity = "NORMAL"
        breach_start = None
        breach_end = None
        max_breach_occ = 0

        for pt in forecast_pts:
            status = pt["rag_status"]
            occ = pt["predicted_occupied"]
            pct = pt["predicted_occupancy_pct"]

            if status in ["RED", "AMBER"]:
                if not in_breach:
                    in_breach = True
                    breach_severity = "CRITICAL" if status == "RED" else "WARNING"
                    breach_start = pt["display_time"]
                    breach_end = pt["display_time"]
                    max_breach_occ = occ
                else:
                    if status == "RED":
                        breach_severity = "CRITICAL"
                    breach_end = pt["display_time"]
                    max_breach_occ = max(max_breach_occ, occ)
            else:
                if in_breach:
                    # Close out current breach window
                    alerts.append(self._build_alert(
                        ward=ward,
                        ward_name=ward_name,
                        severity=breach_severity,
                        capacity=capacity,
                        max_occ=max_breach_occ,
                        start_time=breach_start,
                        end_time=breach_end
                    ))
                    in_breach = False
                    breach_severity = "NORMAL"

        # If breach continues until end of horizon
        if in_breach:
            alerts.append(self._build_alert(
                ward=ward,
                ward_name=ward_name,
                severity=breach_severity,
                capacity=capacity,
                max_occ=max_breach_occ,
                start_time=breach_start,
                end_time=breach_end
            ))

        return alerts

    def _build_alert(
        self,
        ward: str,
        ward_name: str,
        severity: str,
        capacity: int,
        max_occ: int,
        start_time: str,
        end_time: str
    ) -> Dict[str, Any]:
        """Constructs an actionable clinical alert card."""
        occ_pct = round((max_occ / capacity) * 100, 1)
        deficit = max(0, max_occ - capacity)
        
        playbook = CLINICAL_ACTION_PLAYBOOK.get(ward, {}).get(severity, [
            "Monitor patient census and coordinate with nursing supervisor.",
            "Prepare contingency discharge rounds."
        ])

        if severity == "CRITICAL":
            title = f"CRITICAL SURGE ALERT: {ward_name}"
            badge = "bg-red-500 text-white"
            rag = "RED"
            sms_text = f"[MedAxis CRITICAL] {ward_name} forecasted at {occ_pct}% ({max_occ}/{capacity} beds) from {start_time} to {end_time}. Action required."
        else:
            title = f"CAPACITY WARNING: {ward_name}"
            badge = "bg-amber-500 text-white"
            rag = "AMBER"
            sms_text = f"[MedAxis WARNING] {ward_name} forecasted at {occ_pct}% capacity ({start_time} - {end_time}). Review discharge pipeline."

        alert_id = f"ALT-{ward[:3].upper()}-{datetime.now().strftime('%H%M%S')}"

        return {
            "id": alert_id,
            "ward": ward,
            "ward_name": ward_name,
            "severity": severity,
            "rag_status": rag,
            "title": title,
            "badge_class": badge,
            "time_window": f"{start_time} → {end_time}",
            "start_time": start_time,
            "end_time": end_time,
            "peak_occupancy_pct": occ_pct,
            "peak_occupied_beds": max_occ,
            "capacity": capacity,
            "bed_deficit": deficit,
            "recommended_actions": playbook,
            "sms_preview": sms_text,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def dispatch_alert_simulation(self, alert: Dict[str, Any], channel: str = "SMS") -> Dict[str, Any]:
        """Simulates sending an alert via SMS, Email, or Hospital Pager."""
        dispatch_record = {
            "dispatch_id": f"DISP-{len(self.notification_log) + 1:04d}",
            "alert_id": alert.get("id"),
            "ward": alert.get("ward"),
            "severity": alert.get("severity"),
            "channel": channel,
            "recipient": "Nursing Supervisor / Bed Manager (+91-98765-43210)" if channel == "SMS" else "bed-ops-team@apexhealth.org",
            "message": alert.get("sms_preview"),
            "status": "DELIVERED",
            "dispatched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.notification_log.insert(0, dispatch_record)
        return dispatch_record

    def get_dispatch_history(self) -> List[Dict[str, Any]]:
        """Returns the history of dispatched notifications."""
        return self.notification_log[:20]
