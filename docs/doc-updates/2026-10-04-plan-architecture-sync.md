# Plan and architecture sync, 2026-10-04

Source documents (from CONNECT.md):
- Plan: `10-Week Plan v2 Warehouse Intelligence.docx`
- Architecture: `Warehouse Intelligence AI System Architecture.docx`

Decision: update both.

## Conflicts

| # | Plan says (section) | Architecture says (section) | Why it matters | Proposed fix |
|---|---|---|---|---|
| 1 | W4 Mon: catalog extractor, "read-only access to the System 1 database" | §4: System 1 DB is not exposed; schema comes as a JSON snapshot from an export script, on demand from CI | Decides whether week 4 needs DB credentials for System 1 and whether System 1 needs an export script | Plan W4 Mon reads the JSON snapshot |
| 2 | W1 fixes omit rate limit on order creation, service read endpoints, schema export script | §4 "Mandatory fixes" lists them | Week 1 is the only System 1 week; W4 and the agent depend on them | Plan W1 Thu/Fri add them |
| 3 | W4 Wed: trace harness, no location | §6: SQLAlchemy events on a test DB, no location | SQLAlchemy events need hooks inside System 1's process, and System 1 is protected | Both: System 1 in local Docker, throwaway test DB with log_statement = all, SQL read from the Postgres log |
| 4 | W8 Wed: simulator writes through the System 1 API | §10: test operator accounts, test instance only | Conflicts with the rule: writes only through ActionClient, service account, idempotency key | Both: local System 1 only, through a dedicated adapter client |
| 5 | W5 Thu: embeddings with Transformers | §7, §13, §16: fastembed (ONNX, CPU) for serving; Transformers only for fine-tuning | PyTorch in the served image breaks the free Render memory limit | Plan W5 Thu uses fastembed; Transformers loading moves to W9 Wed |
| 6 | W2 Mon: core and adapters/warehouse | §15 tree: backend/app, pipelines, mcp_server; §19: core/ and adapters/warehouse/ | Two layouts; CLAUDE.md and the boundary check use core/adapters | Architecture §15 tree rewritten |
| 7 | W7 Mon detectors and W8 Thu faults: negative stock, blocked orders, duplicates, lag | §8 detectors and §10 faults: stuck orders, repeated FAILED_RESERVATION, low stock, outbox, burst | Detectors, faults and golden set must share one list; WI cannot see the System 1 outbox | Both use one shared list |
| 8 | W3 Mon: zones, shelves, locations; W6 Thu: cache_entries, answer in Redis | §14: zones, racks, bins; semantic_cache with answer in Postgres; no daily_reports | Migration contract for W3, W6, W8 | Architecture §14 and plan W3 Mon aligned |
| 9 | W1 Sat /health, W2 Sat /health/ingest, W3 Tue /map/zones, /map/orders, /map/routes | §15 /ops/live, /ops/ready; §5 /map/zones/{id}, /map/orders/{order_id}, /map/route?operator_id=, /map/stream | API contracts; frontend and keep-alive depend on them | Plan uses the architecture names |
| 10 | W10 Tue deploy: no Redis host; W10 Mon kind without HPA | §13: Upstash Redis in deploy; §15: HPA and autoscaling load test | Deployed cache and rate limit fall back to memory; HPA is extra scope | Plan W10 Tue adds Upstash; architecture §15 drops HPA |

## Edits to the plan (`10-Week Plan v2 Warehouse Intelligence.docx`)

1. Week 1, Thu, Code. Now: "Remove /auth/test-email and the prints, a single email send, rate limiting on /auth". New: "Remove /auth/test-email and the prints, a single email send, rate limiting on /auth and on order creation".
2. Week 1, Fri, Code. Now: "service user and token endpoint for WI; tests for the four fixes; green CI". New: "service user and token endpoint for WI; read endpoints for the service role (orders, events, products); schema export script (JSON with tables, FKs, triggers, functions, constraints); tests for the fixes; green CI".
3. Week 1, Sat, Code. Now: "... FastAPI with /health, CI". New: "... FastAPI with /ops/live and /ops/ready, CI; repo layout core/ and adapters/warehouse/".
4. Week 2, Sat, Code. Now: "Consumer lag size, Prometheus metrics, /health/ingest endpoint". New: "Consumer lag size, Prometheus metrics, ingest status reported in /ops/ready".
5. Week 3, Mon, Code. Now: "Model for zones, shelves, locations (WI migration) ...". New: "Model for zones, racks, bins and product_slots (WI migration) ...".
6. Week 3, Tue, Code. Now: "Endpoints GET /map, /map/zones, /map/orders, /map/routes". New: "Endpoints GET /map, /map/zones/{id}, /map/orders/{order_id}, /map/route?operator_id= (GET /map/stream comes on Saturday)".
7. Week 4, Mon. Code now: "Extractor from the Postgres catalog behind the SchemaSource interface ...". New: "Extractor behind the SchemaSource interface, reading the JSON schema snapshot exported by System 1: tables, foreign keys, triggers, procedures, constraints". Platform now: "read-only access to the System 1 database". New: "System 1 CI produces the schema snapshot".
8. Week 4, Wed, Code. Now: "Runtime trace harness: I capture the real SQL per action". New: "Runtime trace harness in WI: runs System 1 locally in Docker against a throwaway test database with Postgres statement logging on (log_statement = all), triggering each action through the simulator client, and reads the real SQL per action from that log; it does not import System 1's code".
9. Week 5, Thu, Code. Now: "Local embeddings with Transformers (Hugging Face) and a pgvector column with an HNSW index". New: "Local embeddings with fastembed (BGE-small, ONNX, CPU) and a pgvector column with an HNSW index".
10. Detailed steps, PyTorch and Transformers, row W5 Thu. Now: "Load the embeddings model with Transformers ... generate vectors for documents". Move this row to W9 Wed and change to: "Load the same base model with Transformers (tokenizer, model, pooling); check it gives the same vectors as fastembed on 10 documents". Check column: "Cosine similarity above 0.99 between the two".
11. Week 7, Mon, Code. Now: "Detectors: rules and statistics (blocked orders, negative stock, lag) with severity". New: "Detectors: rules and statistics with severity, for the shared fault list: orders stuck in RESERVED or PICKING, repeated FAILED_RESERVATION on a SKU, out of stock or low stock with fast depletion, consumer lag or missing events".
12. Week 8, Wed, Code. Now: "Simulator: generates realistic orders and events through the System 1 API". New: "Simulator: generates realistic orders and events against a local System 1 instance only (never the deployed one), through a dedicated simulator client in adapters/warehouse/".
13. Week 8, Thu, Code. Now: "Fault injection: negative stock, blocked orders, duplicates, with fault_log ...". New: "Fault injection for the shared fault list: out of stock on a SKU, orders left in PICKING, repeated FAILED_RESERVATION, Kafka temporarily unavailable, burst traffic, duplicate submissions; with fault_log (type, moment, what was touched)".
14. Week 10, Mon, Code. Now: "kind manifests: deployments, secrets, liveness probes; full local run". Unchanged (HPA is out of scope).
15. Week 10, Tue, Code. Now: "Deploy: backend on Render, frontend on Vercel, Postgres on Supabase, Kafka on Aiven". New: "Deploy: backend on Render, frontend on Vercel, Postgres on Supabase, Kafka on Aiven, Redis on Upstash (free tier)".

## Edits to the architecture (`Warehouse Intelligence AI System Architecture.docx`)

1. §6, paragraph "The trace". Now: "A harness runs each action on a test database and captures the statements through SQLAlchemy events." Replace with: "A harness in the WI repo runs System 1 locally in Docker against a throwaway test database with Postgres statement logging on (log_statement = all), triggering each action through the simulator client, and reads the statements from that log. It does not import System 1's code, so System 1 is not changed and the live database is never touched."
2. §8, "Detectors" list. Now: the fourth item is "events left in the outbox, as a pipeline health indicator". New: "consumer lag above threshold or a gap in the event stream, as a pipeline health indicator (WI cannot read System 1's outbox)". Add after the list: "Detectors, simulator faults (section 10) and the incident cases in the golden set use the same list of types."
3. §10, paragraph "The simulator". Now: "... creates orders through the integration endpoints of System 1 and moves them through states with test operator accounts. It runs only on a test instance, never on the live one." New: "... creates orders through the integration endpoints of a local System 1 instance and moves them through states with test operator accounts. It uses its own client in adapters/warehouse/ and never targets the deployed System 1." Add "duplicate submissions" to the fault list.
4. §14, data model table. Replace the row "semantic_cache | Cache for questions | query_embedding, answer, created_at, ttl" with "cache_entries | Semantic cache index (answer lives in Redis under the id) | id, query_embedding, model_version, created_at". Add a row "daily_reports | Daily warehouse report | id, report_date, numbers_json, text, status, created_at".
5. §15, "Structure of the repo". Replace the tree with: "warehouse-intelligence/ core/ (search, LLM gateway, cache, agent, MCP server, Quality Lab, observability, explorer) adapters/warehouse/ (event source, schema source, action client, simulator client, projections, document builders, map, detector rules) api/ (FastAPI routers) migrations/ (Alembic) pipelines/ (indexer, umap_job, flow_extractor, trace_harness, simulator, evals) frontend/ src/features (map, copilot, flows, incidents, explorer, quality) infra/ (docker-compose, k8s for kind, GitHub workflows) tools/ (boundary_check) docs/ README.md". Add one line: "core/ never imports from adapters/; a boundary check in CI enforces it (section 19)."
6. §15, "Deploy", Kubernetes bullet. Now: "manifests (Deployment, Service, ConfigMap, Secret, HPA) run on kind. A local load test shows the autoscaling." New: "manifests (Deployment, Service, ConfigMap, Secret, liveness and readiness probes) run on kind." Free cloud bullet: add "Redis on Upstash (free tier)".

## Prompt for Claude in the browser

```
I have two documents for my project Warehouse Intelligence, attached (or in the project knowledge):
- "10-Week Plan v2 Warehouse Intelligence.docx" (the plan)
- "Warehouse Intelligence AI System Architecture.docx" (the architecture)

They disagree in a few places. Apply exactly the edits below, one by one, and keep everything else exactly as it is: the structure, headings, section numbers, week and day numbering, tables, tone and style. Do not rewrite, shorten or reorder anything I do not list.

PLAN edits (10-Week Plan v2 Warehouse Intelligence.docx)

1. Week 1, Thu, Code column. Replace with: "Remove /auth/test-email and the prints, a single email send, rate limiting on /auth and on order creation".
   Reason: the architecture's mandatory fixes include rate limiting on order creation.
2. Week 1, Fri, Code column. Replace with: "service user and token endpoint for WI; read endpoints for the service role (orders, events, products); schema export script (JSON with tables, FKs, triggers, functions, constraints); tests for the fixes; green CI".
   Reason: week 1 is the only week that touches System 1, and weeks 4 and 7 depend on these.
3. Week 1, Sat, Code column. Replace "FastAPI with /health, CI" with "FastAPI with /ops/live and /ops/ready, CI; repo layout core/ and adapters/warehouse/".
   Reason: the architecture names the endpoints /ops/live and /ops/ready (Render keep-alive pings /ops/live) and the repo uses the core/adapters split.
4. Week 2, Sat, Code column. Replace "/health/ingest endpoint" with "ingest status reported in /ops/ready".
   Reason: same endpoint naming as the architecture.
5. Week 3, Mon, Code column. Replace "zones, shelves, locations" with "zones, racks, bins and product_slots".
   Reason: match the architecture's data model.
6. Week 3, Tue, Code column. Replace with: "Endpoints GET /map, /map/zones/{id}, /map/orders/{order_id}, /map/route?operator_id= (GET /map/stream comes on Saturday)".
   Reason: match the architecture's API.
7. Week 4, Mon. Code column: replace with "Extractor behind the SchemaSource interface, reading the JSON schema snapshot exported by System 1: tables, foreign keys, triggers, procedures, constraints". Platform column: replace "read-only access to the System 1 database" with "System 1 CI produces the schema snapshot".
   Reason: the architecture says System 1's database is never exposed; the schema arrives as a JSON snapshot.
8. Week 4, Wed, Code column. Replace with: "Runtime trace harness in WI: runs System 1 locally in Docker against a throwaway test database with Postgres statement logging on (log_statement = all), triggering each action through the simulator client, and reads the real SQL per action from that log; it does not import System 1's code".
   Reason: System 1 must not be changed for this project.
9. Week 5, Thu, Code column. Replace "Local embeddings with Transformers (Hugging Face)" with "Local embeddings with fastembed (BGE-small, ONNX, CPU)".
   Reason: the architecture chose fastembed for serving because PyTorch does not fit the free Render memory.
10. Section "Detailed steps for the added pieces", table "PyTorch and Transformers": move the row "W5, Thu" to day "W9, Wed" (place it before the existing W9 Wed row). Steps: "Load the same base model with Transformers (tokenizer, model, pooling); check it gives the same vectors as fastembed on 10 documents". How you check: "Cosine similarity above 0.99 between the two".
    Reason: Transformers is used for fine-tuning only.
11. Week 7, Mon, Code column. Replace with: "Detectors: rules and statistics with severity, for the shared fault list: orders stuck in RESERVED or PICKING, repeated FAILED_RESERVATION on a SKU, out of stock or low stock with fast depletion, consumer lag or missing events".
    Reason: detectors, simulator faults and golden set must use one list.
12. Week 8, Wed, Code column. Replace with: "Simulator: generates realistic orders and events against a local System 1 instance only (never the deployed one), through a dedicated simulator client in adapters/warehouse/".
    Reason: the project never writes to the deployed System 1 outside approved actions.
13. Week 8, Thu, Code column. Replace with: "Fault injection for the shared fault list: out of stock on a SKU, orders left in PICKING, repeated FAILED_RESERVATION, Kafka temporarily unavailable, burst traffic, duplicate submissions; with fault_log (type, moment, what was touched)".
    Reason: same shared list as the detectors.
14. Week 10, Tue, Code column. Append ", Redis on Upstash (free tier)".
    Reason: without a Redis host the deployed cache and rate limit fall back to memory.

ARCHITECTURE edits (Warehouse Intelligence AI System Architecture.docx)

1. Section 6, paragraph "The trace": replace the first sentence ("A harness runs each action on a test database and captures the statements through SQLAlchemy events.") with: "A harness in the WI repo runs System 1 locally in Docker against a throwaway test database with Postgres statement logging on (log_statement = all), triggering each action through the simulator client, and reads the statements from that log. It does not import System 1's code, so System 1 is not changed and the live database is never touched."
   Reason: SQLAlchemy events would need hooks inside System 1's process; the Postgres log captures the same SQL from outside, with no change to System 1.
2. Section 8, "Detectors" list: replace the item "events left in the outbox, as a pipeline health indicator" with "consumer lag above threshold or a gap in the event stream, as a pipeline health indicator (WI cannot read System 1's outbox)". After the list add: "Detectors, simulator faults (section 10) and the incident cases in the golden set use the same list of types."
   Reason: WI has no access to System 1's database, so it cannot see the outbox.
3. Section 10, paragraph "The simulator": replace "creates orders through the integration endpoints of System 1" with "creates orders through the integration endpoints of a local System 1 instance", and replace "It runs only on a test instance, never on the live one." with "It uses its own client in adapters/warehouse/ and never targets the deployed System 1." Add "duplicate submissions" as the last item of the fault list.
   Reason: matches the plan and the write rules.
4. Section 14, data model table: replace the row "semantic_cache | Cache for questions | query_embedding, answer, created_at, ttl" with "cache_entries | Semantic cache index (answer lives in Redis under the id) | id, query_embedding, model_version, created_at". Add a row after "fault_log": "daily_reports | Daily warehouse report | id, report_date, numbers_json, text, status, created_at".
   Reason: section 17 puts cache answers in Redis, and section 18 uses a daily_reports table that was missing.
5. Section 15, "Structure of the repo warehouse-intelligence": replace the tree with: "warehouse-intelligence/ core/ (search, LLM gateway, cache, agent, MCP server, Quality Lab, observability, explorer) adapters/warehouse/ (event source, schema source, action client, simulator client, projections, document builders, map, detector rules) api/ (FastAPI routers) migrations/ (Alembic) pipelines/ (indexer, umap_job, flow_extractor, trace_harness, simulator, evals) frontend/ src/features (map, copilot, flows, incidents, explorer, quality) infra/ (docker-compose, k8s for kind, GitHub workflows) tools/ (boundary_check) docs/ README.md". Then add the sentence: "core/ never imports from adapters/; a boundary check in CI enforces it (section 19)."
   Reason: section 15 contradicted the core/adapters split in section 19.
6. Section 15, "Deploy": in the Kubernetes bullet replace "(Deployment, Service, ConfigMap, Secret, HPA) run on kind. A local load test shows the autoscaling." with "(Deployment, Service, ConfigMap, Secret, liveness and readiness probes) run on kind." In the free cloud bullet add "Redis on Upstash (free tier)" after "Aiven for Kafka".
   Reason: HPA is out of scope for the plan; Redis needs a host in deploy.

Give me back both complete updated documents as .docx files, with exactly the same file names as the originals.
```
