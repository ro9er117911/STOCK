# Restarting the Investment Cockpit Dashboard

Successfully restored the STOCK project's dashboard and API services. Stale processes on ports 8000 and 8001 have been cleared, and services are now running from the corrected `.venv` environment.

## 🛠️ Operational Commands

To manually restart or rebuild the services, use the following commands from the repository root:

### 1. Build Dashboard Assets
Rebuilds the L1/L2/L3 data structures and static site artifacts in `automation/run/dashboard-local/`.
```bash
./.venv/bin/python -m stock_research build-dashboard
```

### 2. Start Cockpit API (Backend)
Serves the observation lake write-back API on port **8001**.
```bash
./.venv/bin/python -m stock_research serve-cockpit-api
```

### 3. Start Static Frontend
Serves the private cockpit UI on port **8000**.
```bash
/usr/bin/python3 -m http.server 8000 --directory automation/run/dashboard-local
```

## 🏗️ Environment Configuration

- **Workspace Path**: `/Users/ro9air/projects/STOCK`
- **Frontend URL**: [http://localhost:8000](http://localhost:8000)
- **Backend API**: [http://localhost:8001](http://localhost:8001)
- **Data Source**: `automation/run/dashboard-local/` (L3 Observation Lake and Private Overlay enabled)

## ✅ Verification Plan

### Connectivity Check
Verify both services are listening:
```bash
nc -zv localhost 8000 8001
```

### UI Verification
Check for the presence of the **"投資駕駛艙 V2"** title and **"Macro Regime"** data points in your browser.

