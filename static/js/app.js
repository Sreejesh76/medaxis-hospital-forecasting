/**
 * MedAxis - AI Hospital Bed & Patient-Flow Frontend Controller
 * Powers interactive forecasting charts, RAG threshold alerts,
 * What-If scenario simulations, and CSV data ingestion.
 */

// Application State
let appState = {
    selectedWard: 'ALL',
    horizonHours: 48,
    surgeFactor: 1.0,
    dischargeFactor: 1.0,
    datasetMode: 'apex_live',
    isDark: true,
    summaryData: null,
    currentForecastData: null,
    chartInstance: null
};

// Initialization on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initTheme();
    refreshData();
    
    // Auto-refresh polling every 60s
    setInterval(() => {
        refreshData(false);
    }, 60000);
});

// Theme Toggle
function initTheme() {
    const isDark = localStorage.getItem('medaxis_theme') !== 'light';
    appState.isDark = isDark;
    applyThemeClass();
}

function toggleTheme() {
    appState.isDark = !appState.isDark;
    localStorage.setItem('medaxis_theme', appState.isDark ? 'dark' : 'light');
    applyThemeClass();
    if (appState.chartInstance) {
        renderChart(appState.currentForecastData);
    }
}

function applyThemeClass() {
    const html = document.documentElement;
    if (appState.isDark) {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
}

// Dataset Switcher
function switchDataset(mode) {
    appState.datasetMode = mode;
    document.querySelectorAll('.dataset-pill').forEach(btn => {
        btn.classList.remove('active', 'bg-emerald-500', 'text-white', 'font-semibold');
        btn.classList.add('text-slate-300');
    });

    const activeBtn = document.getElementById(`dataset-btn-${mode === 'apex_live' ? 'live' : (mode === 'sih_demo' ? 'sih' : 'mimic')}`);
    if (activeBtn) {
        activeBtn.classList.add('active', 'bg-emerald-500', 'text-white', 'font-semibold');
        activeBtn.classList.remove('text-slate-300');
    }

    const titleMap = {
        'apex_live': 'Apex Metro Health System',
        'sih_demo': 'SIH 2025 Tier-2 District Hospital Pilot',
        'mimic_iv': 'MIMIC-IV Emergency Resuscitation Unit'
    };
    document.getElementById('hospital-title').innerText = titleMap[mode] || 'Apex Metro Health System';
    
    showToast(`Loaded ${titleMap[mode]} dataset profile`, 'info');
    refreshData();
}

// Main Data Fetcher
async function refreshData(showSpinner = true) {
    const refreshIcon = document.getElementById('refresh-icon');
    if (showSpinner && refreshIcon) refreshIcon.classList.add('animate-spin');

    try {
        // Fetch Summary
        const summaryRes = await fetch(`/api/summary?horizon=${appState.horizonHours}`);
        const summary = await summaryRes.json();
        appState.summaryData = summary;
        updateKPICards(summary);
        renderWardCards(summary.wards);
        renderAlerts(summary.alerts);

        // Fetch Detailed Forecast for active ward
        await loadForecast(appState.selectedWard);

        // Update clock
        const now = new Date();
        document.getElementById('sync-time').innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    } catch (err) {
        console.error("Error refreshing data:", err);
        showToast("Failed to fetch forecast updates", "error");
    } finally {
        if (showSpinner && refreshIcon) {
            setTimeout(() => refreshIcon.classList.remove('animate-spin'), 400);
        }
    }
}

// Update Top KPI Metrics
function updateKPICards(data) {
    if (!data) return;

    document.getElementById('kpi-occupied').innerText = data.occupied_beds;
    document.getElementById('kpi-capacity').innerText = `/ ${data.total_beds} beds`;
    document.getElementById('kpi-available').innerText = data.available_beds;
    document.getElementById('kpi-occ-pct').innerText = `${data.occupancy_rate_pct}% Occupied`;

    const occBar = document.getElementById('kpi-occ-bar');
    occBar.style.width = `${Math.min(100, data.occupancy_rate_pct)}%`;
    
    // Color status badge
    const badge = document.getElementById('hospital-status-badge');
    if (data.occupancy_rate_pct >= 90) {
        badge.className = 'px-2.5 py-1 text-xs font-bold rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse';
        badge.innerText = `● CRITICAL RED (${data.occupancy_rate_pct}%)`;
        occBar.className = 'bg-rose-500 h-1.5 rounded-full transition-all duration-500';
    } else if (data.occupancy_rate_pct >= 75) {
        badge.className = 'px-2.5 py-1 text-xs font-bold rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse';
        badge.innerText = `● AMBER WARNING (${data.occupancy_rate_pct}%)`;
        occBar.className = 'bg-amber-500 h-1.5 rounded-full transition-all duration-500';
    } else {
        badge.className = 'px-2.5 py-1 text-xs font-bold rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
        badge.innerText = `● GREEN NORMAL (${data.occupancy_rate_pct}%)`;
        occBar.className = 'bg-emerald-500 h-1.5 rounded-full transition-all duration-500';
    }

    document.getElementById('kpi-net-flow').innerText = `${data.net_patient_flow >= 0 ? '+' : ''}${data.net_patient_flow}`;
    document.getElementById('kpi-adm-count').innerText = data.total_predicted_admissions_48h;
    document.getElementById('kpi-dis-count').innerText = data.total_predicted_discharges_48h;
    document.getElementById('kpi-alert-count').innerText = data.active_alerts_count;
}

// Render Departmental Status Cards
function renderWardCards(wards) {
    const container = document.getElementById('wards-grid');
    if (!container || !wards) return;

    container.innerHTML = '';

    wards.forEach(w => {
        const isSelected = (appState.selectedWard === w.id);
        const card = document.createElement('div');
        
        let statusBadgeClass = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
        let barColor = "bg-emerald-500";
        if (w.overall_status === 'RED') {
            statusBadgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse";
            barColor = "bg-rose-500";
        } else if (w.overall_status === 'AMBER') {
            statusBadgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
            barColor = "bg-amber-500";
        }

        const borderStyle = isSelected ? 'border-emerald-500 ring-2 ring-emerald-500/30 bg-slate-850' : 'border-slate-800 hover:border-slate-700 bg-slate-900/90';

        card.className = `${borderStyle} rounded-2xl p-4 cursor-pointer transition shadow-sm relative group`;
        card.onclick = () => selectWard(w.id);

        card.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">${w.unit_type}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold rounded-full border ${statusBadgeClass}">${w.overall_status}</span>
            </div>
            <h3 class="text-sm font-bold text-white mt-1 group-hover:text-emerald-400 transition">${w.name}</h3>
            <div class="mt-2 flex items-baseline justify-between">
                <span class="text-xl font-black text-white">${w.current_occupancy} <span class="text-xs font-normal text-slate-400">/ ${w.capacity}</span></span>
                <span class="text-xs font-bold ${w.overall_status === 'RED' ? 'text-rose-400' : (w.overall_status === 'AMBER' ? 'text-amber-400' : 'text-emerald-400')}">${w.current_occupancy_pct}%</span>
            </div>
            <div class="mt-2 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div class="${barColor} h-1.5 rounded-full" style="width: ${Math.min(100, w.current_occupancy_pct)}%"></div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span>Peak: <strong class="text-slate-200">${w.peak_occupancy_pct}%</strong></span>
                <span>Buffer: <strong class="text-slate-200">${Math.max(0, w.capacity - w.current_occupancy)} beds</strong></span>
            </div>
        `;

        container.appendChild(card);
    });
}

// Select Ward & Refresh Chart
async function selectWard(wardId) {
    appState.selectedWard = wardId;
    
    // Update Tab Buttons
    document.querySelectorAll('.ward-tab').forEach(tab => {
        if (tab.getAttribute('data-ward') === wardId) {
            tab.className = 'ward-tab px-2.5 py-1 rounded-md active bg-emerald-600 text-white font-semibold';
        } else {
            tab.className = 'ward-tab px-2.5 py-1 rounded-md text-slate-300 hover:text-white';
        }
    });

    if (appState.summaryData) {
        renderWardCards(appState.summaryData.wards);
    }

    await loadForecast(wardId);
}

// Set Horizon (24 or 48)
async function setHorizon(hours) {
    appState.horizonHours = hours;
    
    const h24 = document.getElementById('horizon-24');
    const h48 = document.getElementById('horizon-48');

    if (hours === 24) {
        h24.className = 'horizon-btn px-2.5 py-1 rounded-md active bg-slate-700 text-white font-semibold';
        h48.className = 'horizon-btn px-2.5 py-1 rounded-md text-slate-300 hover:text-white';
    } else {
        h48.className = 'horizon-btn px-2.5 py-1 rounded-md active bg-slate-700 text-white font-semibold';
        h24.className = 'horizon-btn px-2.5 py-1 rounded-md text-slate-300 hover:text-white';
    }

    await loadForecast(appState.selectedWard);
}

// Fetch and Render Forecast
async function loadForecast(wardId) {
    try {
        const url = `/api/forecast?ward=${encodeURIComponent(wardId)}&horizon=${appState.horizonHours}&surge=${appState.surgeFactor}&discharge=${appState.dischargeFactor}`;
        const res = await fetch(url);
        const data = await res.json();
        appState.currentForecastData = data;

        document.getElementById('chart-main-title').innerText = `${data.ward_name} — ${appState.horizonHours}-Hour Forecast`;
        document.getElementById('chart-subtitle').innerText = `Capacity: ${data.capacity} beds | Current Census: ${data.current_occupancy} beds (${data.current_occupancy_pct}%)`;

        // Update footer stats
        let maxCensus = 0;
        let maxDeficit = 0;
        data.timeline.forEach(pt => {
            if (pt.predicted_occupied > maxCensus) maxCensus = pt.predicted_occupied;
            const def = pt.predicted_occupied - data.capacity;
            if (def > maxDeficit) maxDeficit = def;
        });

        const peakPct = roundNumber((maxCensus / data.capacity) * 100, 1);
        document.getElementById('chart-stat-peak').innerText = `${maxCensus} beds (${peakPct}%)`;
        
        if (maxDeficit > 0) {
            document.getElementById('chart-stat-deficit').innerText = `-${maxDeficit} Bed Deficit`;
            document.getElementById('chart-stat-deficit').className = 'text-base font-bold text-rose-400 mt-0.5 block';
        } else {
            const minBuffer = data.capacity - maxCensus;
            document.getElementById('chart-stat-deficit').innerText = `+${minBuffer} Beds Buffer`;
            document.getElementById('chart-stat-deficit').className = 'text-base font-bold text-emerald-400 mt-0.5 block';
        }

        renderChart(data);

    } catch (err) {
        console.error("Error loading forecast:", err);
    }
}

// Render Chart.js
function renderChart(data) {
    const ctx = document.getElementById('forecastChart');
    if (!ctx) return;

    if (appState.chartInstance) {
        appState.chartInstance.destroy();
    }

    const labels = data.timeline.map(pt => pt.display_time);
    const predictedOccupied = data.timeline.map(pt => pt.predicted_occupied);
    const upperBounds = data.timeline.map(pt => pt.upper_bound);
    const lowerBounds = data.timeline.map(pt => pt.lower_bound);
    const inflows = data.timeline.map(pt => pt.predicted_inflow);
    const outflows = data.timeline.map(pt => pt.predicted_outflow);
    const capacityLine = new Array(labels.length).fill(data.capacity);
    const warningLine = new Array(labels.length).fill(data.capacity * (data.warning_threshold_pct / 100));
    const criticalLine = new Array(labels.length).fill(data.capacity * (data.critical_threshold_pct / 100));

    const isDark = appState.isDark;
    const gridColor = isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(226, 232, 240, 0.8)';
    const textColor = isDark ? '#94a3b8' : '#475569';

    appState.chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Bed Census',
                    data: predictedOccupied,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: false,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#10b981',
                    yAxisID: 'y'
                },
                {
                    label: '95% Upper Bound',
                    data: upperBounds,
                    borderColor: 'rgba(16, 185, 129, 0.25)',
                    borderDash: [4, 4],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: '95% Lower Bound',
                    data: lowerBounds,
                    borderColor: 'rgba(16, 185, 129, 0.25)',
                    borderDash: [4, 4],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: '-1',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    yAxisID: 'y'
                },
                {
                    label: 'Critical Threshold (90%)',
                    data: criticalLine,
                    borderColor: '#f43f5e',
                    borderDash: [6, 4],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: 'Warning Threshold (75%)',
                    data: warningLine,
                    borderColor: '#f59e0b',
                    borderDash: [4, 4],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: 'Hourly Inflow',
                    data: inflows,
                    type: 'bar',
                    backgroundColor: 'rgba(59, 130, 246, 0.35)',
                    hoverBackgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderRadius: 4,
                    yAxisID: 'y1'
                },
                {
                    label: 'Hourly Outflow',
                    data: outflows,
                    type: 'bar',
                    backgroundColor: 'rgba(147, 51, 234, 0.35)',
                    hoverBackgroundColor: 'rgba(147, 51, 234, 0.7)',
                    borderRadius: 4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: textColor,
                        font: { size: 11, weight: '500' },
                        boxWidth: 12,
                        boxHeight: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#ffffff',
                    bodyColor: '#cbd5e1',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                label += context.dataset.yAxisID === 'y1' ? `${context.parsed.y} pts/hr` : `${context.parsed.y} beds`;
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 11 } },
                    title: { display: true, text: 'Occupied Beds Census', color: textColor, font: { size: 11 } },
                    suggestedMax: data.capacity * 1.05
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#818cf8', font: { size: 10 } },
                    title: { display: true, text: 'Patients / Hour (In/Out)', color: '#818cf8', font: { size: 11 } },
                    suggestedMax: 15
                }
            }
        }
    });
}

// Render Alerts & Clinical Actions
function renderAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="text-center p-8 bg-slate-950/40 rounded-xl border border-slate-800">
                <i data-lucide="check-circle-2" class="w-10 h-10 text-emerald-400 mx-auto mb-2"></i>
                <div class="text-xs font-bold text-white">All Hospital Wards Operating in Green Zone</div>
                <div class="text-[11px] text-slate-400 mt-0.5">No critical threshold breaches forecasted for next ${appState.horizonHours} hours.</div>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = '';

    alerts.forEach((alt, idx) => {
        const isCrit = (alt.severity === 'CRITICAL');
        const borderColor = isCrit ? 'border-rose-500/40 bg-rose-950/10' : 'border-amber-500/40 bg-amber-950/10';
        const badgeColor = isCrit ? 'bg-rose-500 text-white' : 'bg-amber-500 text-white';

        const alertCard = document.createElement('div');
        alertCard.className = `rounded-xl border ${borderColor} p-4 space-y-3 shadow-md`;

        let actionListHtml = alt.recommended_actions.map(act => `
            <li class="flex items-start text-xs text-slate-300">
                <span class="text-emerald-400 font-bold mr-1.5">&bull;</span> ${act}
            </li>
        `).join('');

        alertCard.innerHTML = `
            <div class="flex items-start justify-between">
                <div>
                    <span class="px-2 py-0.5 text-[10px] font-black uppercase rounded ${badgeColor}">${alt.severity}</span>
                    <h4 class="text-sm font-bold text-white mt-1">${alt.ward_name}</h4>
                    <span class="text-xs text-slate-400 flex items-center mt-0.5">
                        <i data-lucide="clock" class="w-3 h-3 inline mr-1 text-slate-500"></i> ${alt.time_window}
                    </span>
                </div>
                <div class="text-right">
                    <span class="text-base font-black ${isCrit ? 'text-rose-400' : 'text-amber-400'}">${alt.peak_occupancy_pct}%</span>
                    <span class="text-[11px] text-slate-400 block">${alt.peak_occupied_beds}/${alt.capacity} beds</span>
                </div>
            </div>

            <div class="bg-slate-950/60 rounded-lg p-2.5 border border-slate-800/80">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Recommended Clinical Action</span>
                <ul class="space-y-1">${actionListHtml}</ul>
            </div>

            <div class="flex items-center justify-between pt-1">
                <span class="text-[10px] text-slate-500">ID: ${alt.id}</span>
                <button onclick="dispatchAlert('${alt.id}', '${alt.ward}', '${alt.severity}', '${escape(alt.sms_preview)}')" class="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-white transition flex items-center shadow-sm">
                    <i data-lucide="send" class="w-3.5 h-3.5 mr-1 text-emerald-400"></i> Dispatch SMS / Pager
                </button>
            </div>
        `;

        container.appendChild(alertCard);
    });

    lucide.createIcons();
}

// Dispatch Alert Notification
async function dispatchAlert(alertId, ward, severity, encodedMsg) {
    const message = unescape(encodedMsg);
    try {
        const res = await fetch('/api/alerts/dispatch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                alert_id: alertId,
                ward: ward,
                severity: severity,
                message: message,
                channel: 'SMS'
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`Dispatched SMS Alert to Nursing Supervisor (+91-98765-43210)`, 'success');
        }
    } catch (err) {
        showToast('Failed to dispatch alert', 'error');
    }
}

// Sliders and What-If Simulation
async function updateSliders() {
    const surge = parseFloat(document.getElementById('slider-surge').value);
    const discharge = parseFloat(document.getElementById('slider-discharge').value);

    appState.surgeFactor = surge;
    appState.dischargeFactor = discharge;

    const surgePct = Math.round((surge - 1.0) * 100);
    document.getElementById('slider-surge-val').innerText = `${surgePct >= 0 ? '+' : ''}${surgePct}% (${surge}x)`;
    document.getElementById('slider-discharge-val').innerText = `${discharge}x`;

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenario_id: 'custom',
                surge_factor: surge,
                discharge_factor: discharge,
                horizon_hours: appState.horizonHours,
                ward: appState.selectedWard
            })
        });
        const data = await res.json();
        const sim = data.simulation;

        document.getElementById('sim-scenario-name').innerText = sim.scenario_name;
        document.getElementById('sim-recommendation-text').innerText = sim.recommendation;
        document.getElementById('sim-peak-census').innerText = `${sim.max_simulated_occupied} beds`;
        document.getElementById('sim-critical-hours').innerText = `${sim.hours_in_critical} hrs`;

        const badge = document.getElementById('sim-impact-badge');
        if (sim.net_bed_impact > 0) {
            badge.className = 'px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30';
            badge.innerText = `+${sim.net_bed_impact} Bed Deficit`;
        } else if (sim.net_bed_impact < 0) {
            badge.className = 'px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
            badge.innerText = `${sim.net_bed_impact} Beds Buffer Saved`;
        } else {
            badge.className = 'px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 text-slate-300';
            badge.innerText = '0 Net Delta';
        }

        // Live chart update with simulated surge
        await loadForecast(appState.selectedWard);

    } catch (err) {
        console.error("Simulation error:", err);
    }
}

function applyPreset(presetId) {
    const presets = {
        'flu_epidemic': { surge: 1.35, discharge: 0.90 },
        'mass_casualty': { surge: 1.75, discharge: 0.80 },
        'discharge_bottleneck': { surge: 1.05, discharge: 0.70 },
        'fast_track_discharge': { surge: 1.00, discharge: 1.30 }
    };

    if (presets[presetId]) {
        document.getElementById('slider-surge').value = presets[presetId].surge;
        document.getElementById('slider-discharge').value = presets[presetId].discharge;
        updateSliders();
        showToast(`Applied preset scenario`, 'info');
    }
}

function resetSimulation() {
    document.getElementById('slider-surge').value = 1.0;
    document.getElementById('slider-discharge').value = 1.0;
    updateSliders();
}

// CSV File Upload
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const statusBox = document.getElementById('upload-status');
    statusBox.classList.remove('hidden');
    statusBox.innerText = `Ingesting and analyzing ${file.name}...`;

    try {
        const res = await fetch('/api/upload-csv', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();

        if (res.ok) {
            statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/50 text-emerald-300';
            statusBox.innerText = `Ingested ${result.total_rows_ingested} records across: ${result.wards_detected.join(', ')}`;
            showToast('Hospital CSV successfully ingested!', 'success');
            setTimeout(() => {
                closeModal('upload-modal');
                refreshData();
            }, 1200);
        } else {
            statusBox.className = 'text-xs p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300';
            statusBox.innerText = `Error: ${result.detail || 'Upload failed'}`;
        }
    } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300';
        statusBox.innerText = `Failed to connect to ingestion server.`;
    }
}

// Executive Briefing Builder
function populateBriefingModal() {
    const sum = appState.summaryData;
    if (!sum) return;

    const container = document.getElementById('briefing-preview-content');
    const nowStr = new Date().toLocaleString();

    let content = `=================================================================\n`;
    content += `         MEDAXIS HOSPITAL EXECUTIVE CAPACITY BRIEFING            \n`;
    content += `=================================================================\n`;
    content += `Facility: Apex Metro Health System\n`;
    content += `Generated: ${nowStr}\n`;
    content += `System Status: ${sum.hospital_rag_status} (${sum.occupancy_rate_pct}% Occupancy)\n`;
    content += `Current Bed Census: ${sum.occupied_beds} / ${sum.total_beds} beds\n`;
    content += `Operational Buffer Available: ${sum.available_beds} beds\n`;
    content += `Forecast 48h Admissions: ${sum.total_predicted_admissions_48h} pts\n`;
    content += `Forecast 48h Discharges: ${sum.total_predicted_discharges_48h} pts\n`;
    content += `Net Balance: ${sum.net_patient_flow >= 0 ? '+' : ''}${sum.net_patient_flow} patients\n\n`;
    content += `--- DEPARTMENTAL SUMMARY ---\n`;
    
    sum.wards.forEach(w => {
        content += `- ${w.name.padEnd(25)}: ${w.current_occupancy}/${w.capacity} beds (${w.current_occupancy_pct}%) [${w.overall_status}] Peak: ${w.peak_occupancy_pct}%\n`;
    });

    content += `\n--- ACTIVE THRESHOLD ALERTS (${sum.active_alerts_count}) ---\n`;
    if (sum.alerts.length === 0) {
        content += `No active red/amber threshold breaches.\n`;
    } else {
        sum.alerts.forEach((alt, idx) => {
            content += `[${idx+1}] ${alt.title} (${alt.time_window})\n`;
            content += `    Peak: ${alt.peak_occupancy_pct}% (${alt.peak_occupied_beds}/${alt.capacity} beds)\n`;
            content += `    Action: ${alt.recommended_actions[0]}\n`;
        });
    }
    content += `=================================================================\n`;

    container.innerText = content;
}

// Modal Helpers
function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
    if (id === 'export-modal') populateBriefingModal();
    if (id === 'history-modal') loadDispatchHistory();
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

async function loadDispatchHistory() {
    const container = document.getElementById('dispatch-history-list');
    try {
        const res = await fetch('/api/alerts/history');
        const data = await res.json();
        
        if (!data.history || data.history.length === 0) {
            container.innerHTML = `<p class="text-slate-500 text-center py-4">No notifications dispatched yet in this session.</p>`;
            return;
        }

        container.innerHTML = data.history.map(item => `
            <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <div class="flex justify-between items-center text-[10px]">
                    <span class="font-bold text-emerald-400">${item.dispatch_id} &bull; ${item.channel}</span>
                    <span class="text-slate-500">${item.dispatched_at}</span>
                </div>
                <div class="text-slate-200 text-xs">${item.message}</div>
                <div class="text-[10px] text-slate-400">Recipient: ${item.recipient} | Status: <strong class="text-emerald-400">${item.status}</strong></div>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<p class="text-rose-400 text-center py-4">Failed to load history</p>`;
    }
}

// Smooth scroll utilities
function scrollToSimulation() {
    document.getElementById('simulation-section').scrollIntoView({ behavior: 'smooth' });
}

function scrollToAlerts() {
    document.getElementById('alerts-section').scrollIntoView({ behavior: 'smooth' });
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const colorClass = type === 'success' ? 'bg-emerald-600 text-white' : (type === 'error' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-white border border-slate-700');

    toast.className = `${colorClass} px-4 py-2.5 rounded-xl shadow-xl text-xs font-semibold flex items-center space-x-2 transition-all transform duration-300 opacity-0 translate-y-2`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('opacity-0', 'translate-y-2');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function roundNumber(num, dec = 1) {
    return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec);
}
