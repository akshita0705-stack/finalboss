# TraceGuard AI — Frontend & Chrome Extension API Integration Contract

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000/api/v1`  
**WebSocket URL:** `ws://localhost:8000/ws/alerts`  
**Swagger Interactive Docs:** `http://localhost:8000/docs`  
**ReDoc Documentation:** `http://localhost:8000/redoc`

---

## 1. Authentication & Security Scope

TraceGuard AI employs two authentication models:
1. **Analyst / Dashboard User (JWT Bearer Token):** Used by web frontend dashboards.
   - Header: `Authorization: Bearer <jwt_access_token>`
2. **Chrome Extension (API Key & Installation Scope):** Used by the browser extension.
   - Header: `X-API-Key: <api_key>` (Default local dev key: `tg_ext_dev_secret_key_987654321`)
   - Header: `X-Installation-ID: <unique_client_uuid>`

---

## 2. API Endpoints Reference

### 2.1 Health & Readiness Probes

#### `GET /health`
Liveness probe.
- **Request:** None
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "app": "TraceGuard AI",
  "version": "1.0.0",
  "timestamp": "2026-10-29T18:00:00Z"
}
```

#### `GET /ready`
Readiness probe verifying database connectivity and TigerGraph/ThreatIntel status.
- **Response `200 OK`:**
```json
{
  "ready": true,
  "database": {
    "connected": true,
    "error": null
  },
  "graph_database": {
    "connected": true,
    "provider": "mock",
    "degraded": true,
    "status_message": "Mock TigerGraph client operational (Development Mode)"
  },
  "threat_intel": {
    "enabled": false,
    "provider": "mock"
  },
  "timestamp": "2026-10-29T18:00:00Z"
}
```

---

### 2.2 Authentication & User Management

#### `POST /api/v1/auth/register`
- **Request Body:**
```json
{
  "email": "analyst@traceguard.ai",
  "password": "Password123!Secure",
  "full_name": "Senior SOC Analyst",
  "role": "analyst"
}
```
- **Response `201 Created`:**
```json
{
  "id": "c1f757f4-0b13-4c91-9efb-9f939e6022e1",
  "email": "analyst@traceguard.ai",
  "full_name": "Senior SOC Analyst",
  "role": "analyst",
  "is_active": true,
  "created_at": "2026-10-29T18:05:00Z"
}
```

#### `POST /api/v1/auth/login`
- **Request Body:**
```json
{
  "email": "analyst@traceguard.ai",
  "password": "Password123!Secure"
}
```
- **Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "analyst",
  "user_id": "c1f757f4-0b13-4c91-9efb-9f939e6022e1"
}
```

#### `POST /api/v1/auth/api-keys`
Requires `Authorization: Bearer <token>`.
- **Request Body:**
```json
{
  "name": "Chrome Extension Workstation A",
  "installation_id": "inst-workstation-883"
}
```
- **Response `201 Created`:**
```json
{
  "id": "e305e9ca-9a3b-4861-8ff8-91c6f966d9bb",
  "installation_id": "inst-workstation-883",
  "name": "Chrome Extension Workstation A",
  "api_key": "tg_ext_v1_random32characterstringhere",
  "is_active": true,
  "created_at": "2026-10-29T18:10:00Z",
  "last_used_at": null
}
```

---

### 2.3 Chrome Extension Event Ingestion

#### `POST /api/v1/events`
Requires `X-API-Key` and `X-Installation-ID` headers.
- **Request Body:**
```json
{
  "url": "https://paypa1-security-login.com/account/recovery?ref=email",
  "event_type": "navigation",
  "timestamp": "2026-10-29T18:15:00Z",
  "idempotency_key": "optional-client-hash-12345",
  "referrer_url": "https://mail.google.com/",
  "metadata": {
    "tab_id": 42,
    "transition_type": "link"
  }
}
```
- **Response `200 OK`:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "idempotency_key": "optional-client-hash-12345",
  "status": "received",
  "is_duplicate": false,
  "normalized_domain": "paypa1-security-login.com",
  "sanitized_url_path": "/account",
  "preliminary_assessment": {
    "risk_score": 85,
    "severity": "high",
    "confidence": "high",
    "immediate_alert": true,
    "explanation": "Lookalike candidate for 'paypal.com' | Deceptive pattern: Brand 'paypal' combined with action keyword 'recovery'",
    "rules_triggered": [
      "RULE_LOOKALIKE_DOMAIN",
      "RULE_DECEPTIVE_STRUCTURE"
    ]
  },
  "timestamp": "2026-10-29T18:15:00.123456Z"
}
```

*Note:* If the client sends a duplicate/retry event with the same idempotency key, the backend returns `"status": "deduplicated"`, `"is_duplicate": true`, and **does not** inflate visit counters.

#### `GET /api/v1/events`
Query parameters: `domain`, `severity`, `limit` (default: 50), `offset` (default: 0).
- **Response `200 OK`:** Array of `BrowserEventResponse`.

---

### 2.4 Security Findings

#### `GET /api/v1/findings`
Query parameters: `domain`, `severity` (low, medium, high, critical), `category`, `status` (active, resolved, false_positive), `limit`, `offset`.
- **Response `200 OK`:**
```json
[
  {
    "id": "7d953930-cb10-449e-b816-1f3ef6725227",
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "installation_id": "demo-extension-install-001",
    "domain": "paypa1-security-login.com",
    "category": "homograph",
    "severity": "high",
    "risk_score": 85,
    "status": "active",
    "confidence": "high",
    "explanation": "Lookalike candidate for 'paypal.com' (edit distance: 1, similarity: 0.88).",
    "rule_id": "RULE_LOOKALIKE_DOMAIN",
    "provider_source": "deterministic_detection_engine",
    "evidence": {
      "candidate_domain": "paypa1-security-login.com",
      "target_domain": "paypal.com",
      "edit_distance": 1,
      "similarity_score": 0.88,
      "disclaimer": "Lookalike candidate match alone does not prove malicious intent."
    },
    "created_at": "2026-10-29T18:15:00Z",
    "updated_at": "2026-10-29T18:15:00Z"
  }
]
```

#### `GET /api/v1/findings/{finding_id}`
Returns individual finding by ID with full structured evidence.

#### `PATCH /api/v1/findings/{finding_id}`
- **Request Body:**
```json
{
  "status": "resolved"
}
```
- **Response `200 OK`:** Updated finding record.

---

### 2.5 Activity & Analytics

#### `GET /api/v1/activity`
Query parameters: `days` (default: 7), `installation_id`.
- **Response `200 OK`:**
```json
{
  "total_events": 142,
  "unique_domains": 18,
  "repeated_visits_count": 89,
  "top_domains": [
    {
      "domain": "google.com",
      "visit_count": 42,
      "last_seen_at": "2026-10-29T18:00:00Z",
      "highest_risk_score": 0,
      "severity": "low"
    }
  ],
  "hourly_distribution": [
    { "hour": 9, "count": 14 },
    { "hour": 10, "count": 28 }
  ],
  "recent_timeline": [
    {
      "id": "event-uuid",
      "timestamp": "2026-10-29T18:15:00Z",
      "domain": "github.com",
      "event_type": "navigation",
      "risk_score": 0,
      "severity": "low",
      "has_finding": false,
      "finding_id": null
    }
  ]
}
```

---

### 2.6 Daily Reports & Export

#### `GET /api/v1/reports/activity/daily`
Query parameters: `report_date` (YYYY-MM-DD, defaults to current date), `installation_id`.
- **Response `200 OK`:** JSON report object with `estimated_time_on_site` and clear disclaimer.

#### `GET /api/v1/reports/security/daily`
Query parameters: `report_date`, `installation_id`.
- **Response `200 OK`:** JSON security report with severity counts, lookalike candidates, and recommended next steps.

#### `GET /api/v1/reports/{report_id}/export?format=csv`
Downloads report formatted as CSV file attachment.

---

### 2.7 Knowledge Graph (TigerGraph Integration)

#### `GET /api/v1/graph/relationships`
Query parameters: `domain` (optional center filter), `limit` (default: 100).
- **Response `200 OK`:**
```json
{
  "nodes": [
    {
      "id": "site::paypa1-security-login.com",
      "label": "paypa1-security-login.com",
      "entity_type": "Website",
      "properties": { "domain": "paypa1-security-login.com", "status": "monitored" }
    },
    {
      "id": "site::paypal.com",
      "label": "paypal.com",
      "entity_type": "Website",
      "properties": { "domain": "paypal.com", "role": "target_impersonated" }
    }
  ],
  "edges": [
    {
      "id": "edge-uuid",
      "source": "site::paypa1-security-login.com",
      "target": "site::paypal.com",
      "label": "LOOKALIKE_CANDIDATE",
      "edge_type": "CONTACTED",
      "properties": { "similarity": 0.88 },
      "is_inferred": true,
      "confidence": "medium"
    }
  ],
  "total_nodes": 2,
  "total_edges": 1,
  "is_mock": true
}
```

#### `GET /api/v1/graph/status`
Returns TigerGraph connection status, provider (`tigergraph` or `mock`), degraded status flag, and pending/failed sync queue count.

---

### 2.8 AI Investigation Agent

#### `POST /api/v1/investigations`
- **Request Body:**
```json
{
  "question": "Is paypa1-security-login.com safe to visit or a phishing candidate?",
  "domain": "paypa1-security-login.com"
}
```
- **Response `200 OK`:**
```json
{
  "question": "Is paypa1-security-login.com safe to visit or a phishing candidate?",
  "answer": "**Investigation Summary for `paypa1-security-login.com`**:\n**Observed Facts & Telemetry**:\n- Security finding '7d953930...' recorded with severity 'high' (risk score 85) under rule 'RULE_LOOKALIKE_DOMAIN'.\n\n**Inferred Relationships (Subject to Verification)**:\n- Domain 'paypa1-security-login.com' inferred as potential lookalike candidate for legitimate domain 'paypal.com' with edit distance 1.\n\n**Conclusion**: Based solely on stored evidence, `paypa1-security-login.com` has associated security findings or elevated heuristics. Review the cited finding IDs and evidence signals prior to taking containment action.",
  "target_domain": "paypa1-security-login.com",
  "confidence": "high",
  "supporting_evidence": [
    {
      "source_type": "finding",
      "id": "7d953930-cb10-449e-b816-1f3ef6725227",
      "summary": "HOMOGRAPH finding: Lookalike candidate for 'paypal.com'",
      "timestamp": "2026-10-29T18:15:00Z",
      "confidence": "high",
      "is_inferred": false
    }
  ],
  "cited_finding_ids": ["7d953930-cb10-449e-b816-1f3ef6725227"],
  "cited_event_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "observed_facts": [
    "Security finding '7d953930...' recorded with severity 'high' (risk score 85) under rule 'RULE_LOOKALIKE_DOMAIN'."
  ],
  "inferred_relationships": [
    "Domain 'paypa1-security-login.com' inferred as potential lookalike candidate for legitimate domain 'paypal.com' with edit distance 1."
  ],
  "unknown_information": [],
  "limitations": "TraceGuard AI analysis is strictly restricted to locally recorded browser navigation events, deterministic heuristics, and authorized threat intelligence feeds. It does not replace full endpoint protection or guarantee that an unflagged domain is benign.",
  "llm_provider_used": "evidence_fallback",
  "timestamp": "2026-10-29T18:20:00Z"
}
```

---

## 3. Real-Time Alert Streaming

### 3.1 WebSocket Integration (`/ws/alerts`)
Connect with standard WebSocket client:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/alerts?installation_id=YOUR_INSTALL_ID");

ws.onopen = () => {
  console.log("TraceGuard alert stream connected");
};

ws.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  console.log("Live Security Alert received:", alert);
};

ws.onclose = () => {
  console.log("WebSocket disconnected. Retrying in 3 seconds...");
  setTimeout(reconnect, 3000);
};
```

### 3.2 Server-Sent Events Integration (`/api/v1/stream`)
Connect with browser standard `EventSource`:
```javascript
const eventSource = new EventSource("http://localhost:8000/api/v1/stream?installation_id=YOUR_INSTALL_ID");

eventSource.addEventListener("alert", (event) => {
  const alertData = JSON.parse(event.data);
  console.log("SSE Alert:", alertData);
});

eventSource.addEventListener("ping", (event) => {
  console.log("SSE Ping keepalive received");
});
```

