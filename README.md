# MedAxis: AI-Driven Predictive Hospital Bed & Patient-Flow Forecasting ,
[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-medaxis--hospital--forecasting.onrender.com-00C7B7?style=for-the-badge&logo=render&logoColor=white)](https://medaxis-hospital-forecasting.onrender.com)

> 🔗 **Public Prototype URL**: [https://medaxis-hospital-forecasting.onrender.com](https://medaxis-hospital-forecasting.onrender.com)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.5%2B-orange.svg?logo=scikit-learn)](https://scikit-learn.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384.svg?logo=chartdotjs)](https://www.chartjs.org/)
[![SIH 2025/2026 Ready](https://img.shields.io/badge/SIH-2025%2F2026-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **From Hackathon Prototype to a Deployable Web AI Application**  
> Focus feature: *24–48 hour hospital bed-occupancy & patient-inflow forecasting with automated Red/Amber/Green (RAG) threshold alerting and clinical decision support.*

---

## 📌 Executive Summary & Problem Context

Hospital emergency departments and inpatient wards routinely operate at or near capacity. Traditional bed-allocation decisions are **largely reactive** — nursing supervisors and bed managers only discover bed shortages after patients begin boarding in hallways, ambulances are diverted, or elective surgeries are canceled last-minute.

**MedAxis** transforms hospital capacity management from **reactive scrambling to proactive scheduling** by providing:
1. **24–48 Hour Hourly Predictive Census**: Machine learning forecasting of patient admissions, discharges, and bed occupancy across multiple wards.
2. **Automated RAG Threshold Alerts**: Red (>90%), Amber (75–90%), and Green (<75%) threshold alerts paired with actionable clinical countermeasures.
3. **Interactive "What-If" Scenario Simulator**: Real-time stress testing for epidemic surges (e.g., Dengue/Flu spikes), mass casualty incidents, and discharge bottlenecks.
4. **Self-Serve, Low-Friction Deployment**: Zero expensive hardware requirements; runs in lightweight cloud or on-premise environments with CSV log ingestion.

---

## 📊 Market Opportunity & Competitive Positioning

According to third-party healthcare market intelligence (*Fact.MR, Mordor Intelligence 2026*):
- The **AI in hospital operations market** is valued at **$10–12 billion (2025–26)**, expanding at a **16.1% CAGR to $52.4B by 2036**.
- **Hospital workflow automation and bed/patient-flow management** represent the largest single share (**~39%**) of AI operational spend.
- Published clinical studies (*BMC Medical Informatics & Decision Making 2026*) validate that interpretable time-series models reduce total bed requirements by **up to 53.7%** and patient waiting times by **63.9%**.

### Competitive Landscape Matrix

| Vendor | Core Offering | Deployment Model | Limitation / MedAxis Advantage |
| :--- | :--- | :--- | :--- |
| **LeanTaaS (iQueue)** | Predictive OR & Infusion capacity | Enterprise, custom pricing | Inaccessible to single wards / Tier-2/3 hospitals |
| **Qventus** | AI operational automation | Enterprise multi-year contracts | High cost; 6–12 month implementation cycle |
| **TeleTracking** | Real-time bed visibility | Hardware + Software suite | Focuses on tracking, weak on predictive ML forecasting |
| **GE HealthCare Command** | Enterprise census forecasting | Large hospital networks | Heavy change management overhead and pricing |
| **MocDoc / NuvertOS** | Cloud hospital management | Regional SaaS | Administrative ERP only; lacks predictive AI forecasting |
| **MedAxis (Ours)** | **24–48h Bed & Inflow AI Forecast** | **Self-serve Web AI App** | **Rapid setup (minutes), low cost, interpretable, RAG alerts** |

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Hospital Data Ingestion / CSV Logs] --> B[MedAxis AI Forecasting Engine]
    B --> C[Seasonal Diurnal Harmonics + Autoregressive Flow]
    C --> D[24-48h Hourly Inflow & Bed Census Forecast]
    D --> E[RAG Threshold Alerting Engine]
    E --> F[FastAPI REST API Backend]
    F --> G[Interactive Hospital Command Dashboard]
    G --> H[Departmental Status Cards]
    G --> I[24-48h Predictive Curves & 95% CI]
    G --> J[What-If Surge & Scenario Simulator]
    G --> K[SMS / Email Alert Dispatcher]
    G --> L[Executive Printable Briefing]
```

### Departmental Wards Supported
- **Emergency Department (ED)**: 50 beds &bull; High turnover with evening peak intake (15:00–22:00).
- **Intensive Care Unit (ICU)**: 30 beds &bull; Bottleneck unit with high length-of-stay and critical care reserve.
- **General Medicine Ward**: 120 beds &bull; Morning discharge cycles (09:00–12:00) with afternoon intake.
- **Surgical & Post-Op Ward**: 80 beds &bull; Weekday scheduled elective loads combined with emergency trauma.
- **Pediatric Ward**: 40 beds &bull; Specialized pediatric inpatient care with family-assisted discharge paths.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10, 3.11, 3.12, 3.13, 3.14)
- Web Browser (Chrome, Edge, Firefox, Safari)

### 1. Clone & Navigate to Project
```bash
git clone https://github.com/<your-username>/medaxis-hospital-forecasting.git
cd medaxis-hospital-forecasting
```

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Launch the Application
#### Windows:
Double-click `start.bat` or run:
```bash
python run.py
```

#### Linux / macOS:
```bash
chmod +x start.sh
./start.sh
```

### 4. Open in Browser
Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to access the MedAxis Command Center.  
Interactive API Swagger Docs: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧪 Automated Verification & Testing

To run the complete 5-stage automated test suite:
```bash
python test_system.py
```

**Test Coverage:**
- `[1/5]` Multi-ward historical time series dataset generation
- `[2/5]` AI 24h & 48h forecasting math and 95% confidence bounds
- `[3/5]` What-If scenario simulation (Viral surge, MCI, Discharge bottleneck)
- `[4/5]` Clinical threshold evaluation and SMS notification dispatch
- `[5/5]` FastAPI asynchronous REST endpoints (`/api/summary`, `/api/forecast`, `/api/simulate`, `/api/alerts`)

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/summary` | `GET` | Overall hospital census, active alerts count, and ward summaries |
| `/api/forecast` | `GET` | Detailed 24/48h hourly timeline with confidence intervals for specific wards |
| `/api/alerts` | `GET` | Active Red and Amber capacity alerts with clinical actions |
| `/api/simulate` | `POST` | Run What-If scenario simulations with custom surge and discharge factors |
| `/api/alerts/dispatch` | `POST` | Simulate alert transmission via SMS, Email, or Hospital Pager |
| `/api/alerts/history` | `GET` | Audit log of dispatched notifications |
| `/api/upload-csv` | `POST` | Ingest hospital CSV log file and validate schema |
| `/data/download-template` | `GET` | Download sample CSV format for custom hospital data |

---

## 📁 Repository Structure

```
medaxis-hospital-forecasting/
├── backend/
│   ├── __init__.py               # Package metadata
│   ├── dataset_generator.py      # Multi-ward time-series generator & CSV exporter
│   ├── forecasting_engine.py     # AI harmonic & autoregressive 24-48h forecaster
│   ├── simulation_engine.py      # What-If surge & capacity stress simulator
│   ├── alert_manager.py          # Clinical threshold evaluation & SMS dispatcher
│   └── app.py                    # FastAPI application & REST endpoints
├── data/
│   ├── sample_hospital_historical.csv  # 90-day multi-ward baseline dataset
│   └── sample_upload_template.csv      # Sample CSV template for user uploads
├── static/
│   ├── css/styles.css            # Command center styling & print rules
│   └── js/app.js                 # Chart.js, real-time UI controller & modals
├── templates/
│   └── index.html                # Healthcare Command Dashboard UI
├── test_system.py                # 5-stage automated test suite
├── run.py                        # Server runner & data initializer
├── requirements.txt              # Production dependencies
├── start.bat                     # 1-click Windows startup script
├── start.sh                      # 1-click Linux/macOS startup script
├── .gitignore                    # Git ignore file
└── README.md                     # Comprehensive documentation
```

---

## 📤 Step-by-Step GitHub Upload Guide

Follow these steps to upload this complete repository to your personal GitHub account:

### Step 1: Create a New Repository on GitHub
1. Log into your account at [github.com](https://github.com).
2. Click the **`+`** icon in the top right corner and select **"New repository"**.
3. Name your repository: `medaxis-hospital-forecasting` (or any name you prefer).
4. Keep it **Public** (or Private).
5. **Do NOT** initialize with a README, `.gitignore`, or license (we already have all of these).
6. Click **"Create repository"**.

### Step 2: Push Local Code to Your GitHub Repository
Open a terminal (PowerShell or Bash) in the project directory `C:\Users\Sivadath.R\.gemini\antigravity\scratch\medaxis-hospital-forecasting` and run:

```bash
# 1. Initialize git (if not already done)
git init

# 2. Add all files to staging
git add .

# 3. Commit the project
git commit -m "feat: initial release of MedAxis AI hospital bed & patient flow forecasting web app"

# 4. Set the default branch to main
git branch -M main

# 5. Link your GitHub remote repository (replace with your GitHub URL)
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/medaxis-hospital-forecasting.git

# 6. Push code to GitHub
git push -u origin main
```

---

## 📜 License & Acknowledgements

Developed as an open-source clinical operations decision support system for **SIH 2025/2026** and healthcare capacity optimization.  
Released under the **MIT License**.
