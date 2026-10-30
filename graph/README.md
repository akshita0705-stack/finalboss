# TraceGuard graph (TigerGraph)

> Status: schema and queries are written to the project spec but have **not been run against a live
> TigerGraph instance** by the author of this change. Run the verification steps below and report errors.

## Install (Docker, Windows PowerShell)
```powershell
docker compose up -d tigergraph           # from repo root; first start takes a few minutes
docker exec -it traceguard-tigergraph gsql -f /graph/schema/01_schema.gsql
docker exec -it traceguard-tigergraph gsql -f /graph/queries/domain_subgraph.gsql
docker exec -it traceguard-tigergraph gsql -f /graph/queries/domain_summary.gsql
docker exec -it traceguard-tigergraph gsql "USE GRAPH TraceGuardGraph INSTALL QUERY ALL"
```
Then set `TIGERGRAPH_ENABLED=true`, `TIGERGRAPH_USE_MOCK=false`, host, username/password (or token) in `backend/.env`.

## Verify
```powershell
curl http://localhost:14240/gsql/v1/version          # GSQL reachable
curl http://localhost:9000/echo                      # REST++ reachable
```

## Idempotency
REST++ `POST /graph/...` is an upsert: re-sending the same vertex/edge id updates attributes instead of
duplicating. Backend sync jobs rely on that, so retries after a TigerGraph outage are safe.

## Known gaps in the backend sync (tracked in docs/STATUS.md)
- `ExternalDomain`/`CONTACTED` and `ThreatIndicator`/`MATCHES_INDICATOR` are defined here but not yet synced.
- Vertex ids are not yet `<owner>:<value>`; until they are, do not point multiple users at one graph.
- `RealTigerGraphClient.get_subgraph` does not yet call `domain_subgraph`.
