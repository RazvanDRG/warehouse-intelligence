# Plan and architecture sync, 2026-10-04

Source documents (from CONNECT.md):
- Plan: `10-Week Plan v2 Warehouse Intelligence.docx`
- Architecture: `Warehouse Intelligence AI System Architecture.docx`

Decision: the architecture is the source of truth. The plan follows it. The architecture changes only where it contradicts itself, and each of those edits fixes the odd section out using the architecture's own wording from the other sections.

## Conflicts

| # | Plan says | Architecture says | Fix |
|---|---|---|---|
| 1 | W4 Mon: "read-only access to the System 1 database" | §4: the database is not exposed; schema arrives as a JSON snapshot from CI | Plan follows §4 |
| 2 | W1 misses three mandatory fixes | §4 "Mandatory fixes": rate limit on order creation, service read endpoints, schema export script | Plan follows §4 |
| 3 | W4 Wed: harness, no method | §6: test database, statements captured through SQLAlchemy events | Plan follows §6 |
| 4 | W8 Wed: simulator "through the System 1 API" | §10: integration endpoints, test operator accounts, test instance only | Plan follows §10 |
| 5 | W5 Thu: embeddings with Transformers | §7, §13: fastembed for serving; §17: Transformers for fine-tuning | Plan follows §7, §13, §17 |
| 6 | W7 Mon and W8 Thu: negative stock, blocked orders, duplicates, lag | §8 detectors and §10 faults | Plan follows §8 and §10 |
| 7 | W3 Mon: zones, shelves, locations | §14: zones, racks, bins, product_slots | Plan follows §14 |
| 8 | W1 Sat /health, W2 Sat /health/ingest, W3 Tue map endpoints | §15 /ops/live, /ops/ready; §5 map endpoints | Plan follows §5 and §15 |
| 9 | W10 Mon: kind without HPA; W10 Tue: no Redis host | §15: HPA and a local load test; §13: Upstash in deploy | Plan follows §13 and §15 |
| 10 | (inside the architecture) | §14 keeps the cache answer in Postgres; §7 and §17 keep it in Redis; §18 uses daily_reports, missing from §14 | §14 aligned with §7, §17, §18 |
| 11 | (inside the architecture) | §15 repo tree (backend/app, mcp_server) vs §19 (core/, adapters/warehouse/) | §15 tree aligned with §19 |
| 12 | (inside the architecture) | §13 puts Redis on Upstash in deploy; §15 "Deploy" leaves it out | §15 deploy aligned with §13 |

## Edits to the plan (`10-Week Plan v2 Warehouse Intelligence.docx`)

1. Week 1, Thu, Code. New: "Remove /auth/test-email and the prints, a single email send, rate limiting on /auth and on order creation". (§4)
2. Week 1, Fri, Code. New: "service user and token endpoint for WI; read endpoints for the service role (orders, events including outbox rows not yet published, products); schema export script (JSON with tables, FKs, triggers, functions, constraints); tests for the fixes; green CI". (§4; the outbox rows feed the §8 detector)
3. Week 1, Sat, Code. Replace "FastAPI with /health, CI" with "FastAPI with /ops/live and /ops/ready, CI; repo layout core/ and adapters/warehouse/". (§15, §19)
4. Week 2, Sat, Code. Replace "/health/ingest endpoint" with "ingest status reported in /ops/ready". (§15)
5. Week 3, Mon, Code. Replace "zones, shelves, locations" with "zones, racks, bins and product_slots". (§14)
6. Week 3, Tue, Code. New: "Endpoints GET /map, /map/zones/{id}, /map/orders/{order_id}, /map/route?operator_id= (GET /map/stream comes on Saturday)". (§5)
7. Week 4, Mon. Code: "Extractor behind the SchemaSource interface, reading the JSON schema snapshot exported by System 1: tables, foreign keys, triggers, procedures, constraints". Platform: replace "read-only access to the System 1 database" with "System 1 CI produces the schema snapshot". (§4, §6)
8. Week 4, Wed, Code. New: "Runtime trace harness: runs each System 1 action on a test database and captures the statements through SQLAlchemy events; result: tables read and written, in real order". (§6)
9. Week 5, Thu, Code. Replace "Local embeddings with Transformers (Hugging Face)" with "Local embeddings with fastembed (BGE-small, ONNX, CPU)". (§7, §13)
10. Detailed steps, table "PyTorch and Transformers": move the row "W5, Thu" to "W9, Wed" (before the existing W9 Wed row). Steps: "Load the same base model with Transformers (tokenizer, model, pooling); check it gives the same vectors as fastembed on 10 documents". How you check: "Cosine similarity above 0.99 between the two". (§17)
11. Week 7, Mon, Code. New: "Detectors: rules and statistics with severity: an order stuck in RESERVED or PICKING past a time threshold, repeated FAILED_RESERVATION on the same SKU, stock below threshold or out of stock with a high consumption rate, events left in the outbox as a pipeline health indicator". (§8)
12. Week 8, Wed, Code. New: "Simulator with a fixed seed: creates orders through the integration endpoints of System 1 and moves them through states with test operator accounts; runs only on a test instance, never on the live one". (§10)
13. Week 8, Thu, Code. New: "Fault injection: out of stock on a SKU, orders left in PICKING, repeated FAILED_RESERVATION, blocked outbox (Kafka temporarily unavailable), burst traffic; recorded in fault_log (type, time, affected entities)". (§10)
14. Week 10, Mon, Code. New: "kind manifests: Deployment, Service, ConfigMap, Secret, HPA, liveness probes; a local load test shows the autoscaling; full local run". (§15)
15. Week 10, Tue, Code. Append ", Redis on Upstash (free tier)". (§13)

## Edits to the architecture (`Warehouse Intelligence AI System Architecture.docx`)

Only internal contradictions. Nothing new is decided here.

1. §14, data model table. Replace the row "semantic_cache | Cache for questions | query_embedding, answer, created_at, ttl" with "cache_entries | Semantic cache index (the answer is read from Redis by id) | id, query_embedding, created_at". Add after "fault_log": "daily_reports | Daily warehouse report | id, report_date, numbers, text, created_at". (matches §7, §17, §18)
2. §15, "Structure of the repo warehouse-intelligence". Replace the tree with: "warehouse-intelligence/ core/ (hybrid search, LLM gateway, cache, rate limiting, agent, MCP server, Quality Lab, observability, UMAP explorer) adapters/warehouse/ (Kafka event contract, projections, document builders, client for the System 1 API, warehouse map, incident detector rules) api/ migrations/ (Alembic) pipelines/ (indexer, umap_job, flow_extractor, trace_harness, simulator, evals) frontend/ src/features (map, copilot, flows, incidents, explorer, quality) infra/ (docker-compose, k8s for kind, GitHub workflows) docs/ (architecture, ADRs, screenshots) README.md". (matches §19)
3. §15, "Deploy", free cloud bullet: add "Upstash for Redis" after "Aiven for Kafka". (matches §13)

## Prompt for Claude in the browser

```
I have two documents for my project Warehouse Intelligence, attached:
- "Warehouse Intelligence AI System Architecture.docx" (the architecture, the source of truth)
- "10-Week Plan v2 Warehouse Intelligence.docx" (the plan)

The plan must follow the architecture. Apply exactly the edits below, one by one, and keep everything else exactly as it is: structure, headings, section numbers, week and day numbering, tables, tone and style. Do not rewrite, shorten or reorder anything I do not list. Do not change the architecture beyond the three edits listed for it.

PLAN edits (10-Week Plan v2 Warehouse Intelligence.docx)

1. Week 1, Thu, Code column. Replace with: "Remove /auth/test-email and the prints, a single email send, rate limiting on /auth and on order creation".
2. Week 1, Fri, Code column. Replace with: "service user and token endpoint for WI; read endpoints for the service role (orders, events including outbox rows not yet published, products); schema export script (JSON with tables, FKs, triggers, functions, constraints); tests for the fixes; green CI".
3. Week 1, Sat, Code column. Replace "FastAPI with /health, CI" with "FastAPI with /ops/live and /ops/ready, CI; repo layout core/ and adapters/warehouse/".
4. Week 2, Sat, Code column. Replace "/health/ingest endpoint" with "ingest status reported in /ops/ready".
5. Week 3, Mon, Code column. Replace "zones, shelves, locations" with "zones, racks, bins and product_slots".
6. Week 3, Tue, Code column. Replace with: "Endpoints GET /map, /map/zones/{id}, /map/orders/{order_id}, /map/route?operator_id= (GET /map/stream comes on Saturday)".
7. Week 4, Mon. Code column: replace with "Extractor behind the SchemaSource interface, reading the JSON schema snapshot exported by System 1: tables, foreign keys, triggers, procedures, constraints". Platform column: replace "read-only access to the System 1 database" with "System 1 CI produces the schema snapshot".
8. Week 4, Wed, Code column. Replace with: "Runtime trace harness: runs each System 1 action on a test database and captures the statements through SQLAlchemy events; result: tables read and written, in real order".
9. Week 5, Thu, Code column. Replace "Local embeddings with Transformers (Hugging Face)" with "Local embeddings with fastembed (BGE-small, ONNX, CPU)".
10. Section "Detailed steps for the added pieces", table "PyTorch and Transformers": move the row "W5, Thu" to day "W9, Wed" (place it before the existing W9 Wed row). Steps: "Load the same base model with Transformers (tokenizer, model, pooling); check it gives the same vectors as fastembed on 10 documents". How you check: "Cosine similarity above 0.99 between the two".
11. Week 7, Mon, Code column. Replace with: "Detectors: rules and statistics with severity: an order stuck in RESERVED or PICKING past a time threshold, repeated FAILED_RESERVATION on the same SKU, stock below threshold or out of stock with a high consumption rate, events left in the outbox as a pipeline health indicator".
12. Week 8, Wed, Code column. Replace with: "Simulator with a fixed seed: creates orders through the integration endpoints of System 1 and moves them through states with test operator accounts; runs only on a test instance, never on the live one".
13. Week 8, Thu, Code column. Replace with: "Fault injection: out of stock on a SKU, orders left in PICKING, repeated FAILED_RESERVATION, blocked outbox (Kafka temporarily unavailable), burst traffic; recorded in fault_log (type, time, affected entities)".
14. Week 10, Mon, Code column. Replace with: "kind manifests: Deployment, Service, ConfigMap, Secret, HPA, liveness probes; a local load test shows the autoscaling; full local run".
15. Week 10, Tue, Code column. Append ", Redis on Upstash (free tier)".

ARCHITECTURE edits (Warehouse Intelligence AI System Architecture.docx), only to remove contradictions between its own sections

1. Section 14, data model table: replace the row "semantic_cache | Cache for questions | query_embedding, answer, created_at, ttl" with "cache_entries | Semantic cache index (the answer is read from Redis by id) | id, query_embedding, created_at". Add a row after "fault_log": "daily_reports | Daily warehouse report | id, report_date, numbers, text, created_at".
   Reason: sections 7 and 17 keep the cached answer in Redis, and section 18 saves the report in daily_reports.
2. Section 15, "Structure of the repo warehouse-intelligence": replace the tree with: "warehouse-intelligence/ core/ (hybrid search, LLM gateway, cache, rate limiting, agent, MCP server, Quality Lab, observability, UMAP explorer) adapters/warehouse/ (Kafka event contract, projections, document builders, client for the System 1 API, warehouse map, incident detector rules) api/ migrations/ (Alembic) pipelines/ (indexer, umap_job, flow_extractor, trace_harness, simulator, evals) frontend/ src/features (map, copilot, flows, incidents, explorer, quality) infra/ (docker-compose, k8s for kind, GitHub workflows) docs/ (architecture, ADRs, screenshots) README.md".
   Reason: section 19 splits the code into core/ and adapters/warehouse/.
3. Section 15, "Deploy", free cloud bullet: add "Upstash for Redis" after "Aiven for Kafka".
   Reason: section 13 already puts Redis on Upstash in deploy.

Give me back both complete updated documents as .docx files, with exactly the same file names as the originals.
```
