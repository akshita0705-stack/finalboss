# TraceGuard AI — Backend Service

**TraceGuard AI** is a graph-powered browser security investigation platform designed to monitor navigation telemetry, assess spoofing and lookalike domain candidates, detect phishing patterns, and track investigation entities across a TigerGraph knowledge graph.

---

## 1. Architecture & Security Event Flow

```
+------------------+         POST /api/v1/events          +-------------------------+
| Chrome Extension | -----------------------------------> | FastAPI Ingestion Engine|
+------------------+                                      +-------------------------+
                                                                       |
                         1. URL Normalization (IDNA, port, query sanitize)
                         2. Idempotency Check (prevents visit inflation)
                         3. Instant Deterministic Assessment (0-100 score)
                                                                       |
        +--------------------------------------------------------------+
        |                                                              |
        v                                                              v
+------------------------+                               +--------------------------+
| PostgreSQL / SQLite    |                               | Notification Service     |
| (Events, Visits,       |                               | (WebSocket & SSE Stream) |
|  Findings, Indicators) |                               +--------------------------+
+------------------------+                                             |
        |                                                              v
        | Background Task:                               +--------------------------+
        | - Threat Intel Lookup (Safe Browsing / Mock)   | Frontend SOC Dashboard   |
        | - Process GraphSyncJob with exponential backoff+--------------------------+
        v
+------------------------+
| TigerGraph Cluster     |
| (Websites, Visits,     |
|  Indicators, Findings) |
+------------------------+
```

---

## 2. Windows 11 / Terminal Setup (Step-by-Step)

Follow these instructions in PowerShell or VS Code Terminal on Windows:

### Step 1: Open PowerShell in the `backend/` Directory
```powershell
cd d:\Final\backend
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell throws an execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
By default, `.env` uses local SQLite (`sqlite:///./traceguard.db`) so the backend runs immediately without requiring a local PostgreSQL service installed.

If you have PostgreSQL installed or are running Docker, update `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traceguard
```

### Step 5: Run Alembic Database Migrations
```powershell
alembic upgrade head
```

### Step 6: (Optional) Seed Representative Development Data
Populates default accounts, sample benign navigations, lookalike candidates, findings, and graph jobs:
```powershell
python seed.py
```
**Default Credentials Created:**
- **Admin:** `admin@traceguard.ai` / `AdminPassword123!`
- **Analyst:** `analyst@traceguard.ai` / `AnalystPassword123!`
- **Extension API Key:** `tg_ext_dev_secret_key_987654321`

### Step 7: Run Automated Tests
Execute the full test suite with pytest:
```powershell
pytest -v
```

### Step 8: Start the FastAPI Server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 9: Open Interactive API Documentation
Open your browser to:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. TigerGraph Schema & Integration

TraceGuard AI synchronizes investigation entities to TigerGraph using an asynchronous retry queue (`GraphSyncJob`). When TigerGraph is offline or not configured, the backend automatically operates in **degraded / mock mode** without dropping alerts or blocking event ingestion.

### Graph Vertex Schema
- **`Website`**: Primary domain node (`domain`, `scheme`, `risk_score`)
- **`Visit`**: Aggregated navigation session (`visit_count`, `last_seen`)
- **`ExternalDomain`**: Contacted external domains (`domain`, `role`)
- **`ThreatIndicator`**: External intelligence match (`verdict`, `provider`)
- **`SecurityFinding`**: Detected threat incident (`category`, `severity`, `risk_score`)

### Graph Edge Schema
- **`VISITED_DOMAIN`**: `Visit` -> `Website`
- **`REDIRECTED_TO`**: `Website` -> `Website` (redirect hops)
- **`CONTACTED`**: `Website` -> `ExternalDomain`
- **`MATCHES_INDICATOR`**: `Website` -> `ThreatIndicator`
- **`GENERATED_FINDING`**: `Website` -> `SecurityFinding`
- **`LOOKALIKE_CANDIDATE`**: `Website` -> `Website` (labeled as `is_inferred: true`)

---

## 4. Threat Intelligence Integration

TraceGuard AI supports:
1. **Mock Threat Intelligence Provider (Default):** Offline development provider with test malicious and clean datasets (`testsafebrowsing.appspot.com`, `google.com`).
2. **Google Safe Browsing v4/v5:** Enabled by setting:
   ```env
   THREAT_INTEL_ENABLED=true
   THREAT_INTEL_PROVIDER=safebrowsing
   GOOGLE_SAFE_BROWSING_API_KEY=YOUR_GOOGLE_CLOUD_API_KEY
   ```
*Design Rule:* Provider timeouts or network errors **never** mark a domain safe. Incomplete checks remain `unknown`.

---

## 5. Running with Docker Compose

To start PostgreSQL and the FastAPI backend together using Docker:
```bash
docker-compose up --build
```
This automatically runs database migrations, seeds initial data, and exposes the API on port `8000`.

---

## 6. Common Errors & Troubleshooting

| Error | Root Cause | Solution |
|---|---|---|
| `ImportError: email-validator is not installed` | Missing Pydantic email validation package | Run `pip install email-validator>=2.0.0` |
| `ValidationError: DEBUG: Input should be a valid boolean` | Windows OS environment has system variable `DEBUG=release` | The custom validator in `app/core/config.py` safely handles non-standard boolean strings (`release`, `debug`, `1`, `0`). |
| `401 Unauthorized on POST /api/v1/events` | Missing or mismatched extension API key | Pass header `X-API-Key: tg_ext_dev_secret_key_987654321` and `X-Installation-ID: test-inst-01`. |
| `TigerGraph connection failed` | Live TigerGraph cluster is unreachable | Set `TIGERGRAPH_USE_MOCK=true` in `.env` to use the built-in development graph mock. |

