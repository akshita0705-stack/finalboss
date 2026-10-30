# TraceGuard AI - Project status vs. spec

Last updated with the "Phase 1: security hardening + extension contract" change. **Nothing here was executed
in the authoring environment** (no network, no Python dependencies): run `pytest` yourself and treat all
"fixed" items as unverified until it passes.

## Fixed in Phase 1
| Issue found | Fix |
|---|---|
| `/ws/alerts` and `/api/v1/stream` were unauthenticated and subscribable to scope `*`, so any client received every user's alerts | Both now require a JWT (`?token=`), subscribe only to the token owner's installations; the global `*` fan-out was removed |
| `PUT /api/v1/settings` was unauthenticated and mutated process-wide config | Admin only |
| Shared dev API key and anonymous `X-Installation-ID` accepted regardless of environment | Disabled when `ENVIRONMENT=production` |
| CORS `allow_credentials=True` with wildcard fallback | Explicit origins/methods/headers; no credentials with `*`; extension origins allowed by regex |
| `last_used_at` assignment bug in API-key auth | Sets the current time |
| Extension called `/api/v1/extension/events` (did not exist) with a hostname-only payload and expected `{assessment:{severity,...}}` | New `extension` router; maps engine severities to the 5 status labels; API key accepted as Bearer |
| No GSQL, no root compose | `graph/` schema + queries, root `docker-compose.yml` |

## Still open (priority order)
1. **Graph isolation**: sync writes global `Website` vertices with no owner. Move to `<owner>:<value>` ids (schema ready).
2. **Graph sync completeness**: ExternalDomain/CONTACTED and ThreatIndicator/MATCHES_INDICATOR; real `get_subgraph` via `domain_subgraph`.
3. **Data model**: add `BrowserSession`, `ThreatLookup`, `Alert`, per-user `UserSetting`, `Investigation` tables + Alembic migration (current settings are process-global, not per-user).
4. **Privacy endpoints**: per-user pause/resume, `DELETE /api/v1/data`, retention cleanup job, installation id hashing.
5. **Rate limiting**: `RATE_LIMIT_PER_MINUTE` exists in config; verify it is actually enforced. Add request-size limits.
6. **Agent**: verify tool set matches spec (6 tools), per-user ownership checks, prompt-injection handling, labelled demo mode.
7. **Frontend** (3 of 10 pages exist: Overview, Reports, Site Check + Login): Live Threat Center, Finding Details, Relationship Explorer, Browsing Activity, AI Assistant (text + mic), Settings. `services/demo/*` must show a visible Demo banner.
8. **Extension**: voice input, delete-data hook to backend, consent/retention wiring to `/settings`.
9. **Docs/tests**: ARCHITECTURE.md, API.md; tests for retention, deletion, excluded domains, graph outage/recovery, agent-grounding.
10. **UI theme**: current Halloween theme (bats, pumpkins, lightning) conflicts with the spec's "restrained" product UI; decide whether to keep it.

11. **Production guards**: `backend/docker-compose.yml` runs `ENVIRONMENT=production` with a placeholder `SECRET_KEY` and the shared dev API key (now rejected in production). Make the app refuse to start in production with a default secret; update the compose/seed flow to use real per-installation API keys.

## Not verified
Backend test suite, alembic migration, GSQL install, frontend build, extension build, browser behaviour.
