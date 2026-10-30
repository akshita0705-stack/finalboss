# Setup (Windows, PowerShell)

Prerequisites: Python 3.11+, Node 20+, Chrome. Docker is optional (PostgreSQL/TigerGraph).

## 1. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
Copy-Item .env.example .env           # defaults to SQLite + mock threat provider + mock graph
alembic upgrade head
python seed.py                        # local demo users only
pytest -v                             # run this and read the result before continuing
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs. For PostgreSQL: `docker compose up -d postgres` at repo root, then set
`DATABASE_URL=postgresql+psycopg://traceguard:change-me-local-only@localhost:5432/traceguard`.

**Production**: set `ENVIRONMENT=production`, `DEBUG=false`, a long random `SECRET_KEY`, and explicit `CORS_ORIGINS`.
This disables the shared dev API key.

## 2. Frontend
```powershell
cd frontend\frontend\web
npm install
Copy-Item .env.example .env           # VITE_API_BASE_URL=http://localhost:8000
npm run dev                           # http://localhost:5173
```

## 3. Extension
```powershell
cd frontend\frontend\extension
npm install
npm run build
```
Chrome -> `chrome://extensions` -> Developer mode -> Load unpacked -> select `...\extension\dist`.
In the extension Options: grant consent, set backend URL, paste an extension API key (create via
`POST /api/v1/auth/api-keys`), turn Demo mode off.

## 4. Chrome test checklist
- [ ] Popup shows protection state; Pause/Resume changes it and the badge.
- [ ] Visit a normal site: status shows an assessment, not "safe".
- [ ] Visit a synthetic test domain (`.test` / `.invalid` fixtures, demo mode): alert notification appears once, not repeatedly.
- [ ] Stop the backend: popup shows disconnected; restart: queued events are sent.
- [ ] Excluded domain produces no event. Incognito produces no event.
- [ ] Delete data removes local queue/alerts.

## 5. TigerGraph (optional)
See `graph/README.md`.
