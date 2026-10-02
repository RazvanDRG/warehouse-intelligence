# 10-Week Plan v2: Warehouse Intelligence

## How to read the plan

Plan v2 replaces the old System 2 (SalesOrder, Stripe, Twilio, Pandas, AKS, AWS, Terraform) with Warehouse Intelligence, the AI project described in the architecture document. Everything that was in v1 for code, NeetCode, English, review, HR and Mercor stays as the rhythm. Only what you build in the Code track, and in what order, changes.

What changed from v1

- Stripe, Twilio, AKS, AWS and Terraform are gone. Infrastructure is shown with Docker Compose, manifests for kind (local Kubernetes) and free deploys on Render, Vercel, Supabase and Aiven.
- The first week fixes System 1, because the bugs found (events lost when Kafka is down, broken compensation, creation without dedupe) would break everything built on top of it.
- Every week ends with a deliverable that works, not half-written code.

Structure of the day

| Track | Rhythm | Content |
|---|---|---|
| Code | daily, main block | what the week's table says |
| NeetCode | 2 problems a day, review on Sunday | the week's topic, written in the table |
| English | daily, 30 minutes | explain out loud what you built today, then write 5 lines |
| Review | daily, 20 minutes | flashcards with the concepts of today and the day before |
| HR, Mercor, Platform | one small action a day | last column of the table |

Sunday is an easy day: review, README, next week's plan. Times are approximate. If a day falls apart, move the deliverable to Saturday, but do not skip the review.

## Week 1: fix System 1 and start the repo

Deliverable: System 1 no longer loses events, compensation works, and the warehouse-intelligence repo runs with green CI. NeetCode: Arrays & Hashing.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Outbox: publish_event returns success or failure, the row is not marked published if Kafka is down; worker with FOR UPDATE SKIP LOCKED | Contains Duplicate, Valid Anagram | Platform: local test with Kafka off, then on |
| Tue | Compensation: on 409 at reservation the order goes to FAILED_RESERVATION; release also accepts NEW; tests | Two Sum, Group Anagrams | Mercor: profile completed |
| Wed | Dedupe on (source_company, reference): unique constraint, Alembic migration, idempotent response | Top K Frequent, Product of Array Except Self | HR: 3 STAR stories in English |
| Thu | Remove /auth/test-email and the prints, a single email send, rate limiting on /auth | Valid Sudoku, Longest Consecutive Sequence | Platform: check that .env is not in git |
| Fri | service user and token endpoint for WI; tests for the four fixes; green CI | Review: the problems I got wrong | HR: LinkedIn profile |
| Sat | warehouse-intelligence repo: structure, Docker Compose with Postgres, pgvector, Redis, Prometheus and Grafana, FastAPI with /health, CI | 1 Medium of your choice | Platform: multi-stage Dockerfile |
| Sun | README v0 and architecture sketch; week 2 plan | Review | HR: 3 applications |

## Week 2: Kafka ingestion and projections

Deliverable: events from System 1 reach the WI database, idempotent, with dead-letter. NeetCode: Two Pointers.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Core structure and adapters/warehouse with the EventSource interface; aiokafka consumer behind it: group, manual offset commit, Aiven SASL_SSL config | Valid Palindrome, Two Sum II | Platform: Aiven secrets in environment variables |
| Tue | processed_events table on event_id; duplicates are ignored; tests | 3Sum, Container With Most Water | Mercor: first application |
| Wed | Dead-letter: invalid message, broken payload, limited retry | Trapping Rain Water, Remove Duplicates | HR: 3 applications |
| Thu | Projections: orders, stock, audit from wms.order.audit, wms.pick.completed, stock events | One Medium Two Pointers problem | Platform: consumer healthcheck |
| Fri | Integration test: I produce events, check the projection; full replay | Review | HR: message to 2 recruiters |
| Sat | Consumer lag size, Prometheus metrics, /health/ingest endpoint | 1 Medium | Platform: Grafana dashboard for lag |
| Sun | Document the event contract in the README; week 3 plan | Review | HR: review STAR stories |

## Week 3: digital twin and the warehouse map

Deliverable: interactive warehouse map with colored zones, hover, per-user filter and live updates through SSE. NeetCode: Stack and Binary Search.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Model for zones, shelves, locations (WI migration) and allocation by product category | Valid Parentheses, Min Stack | Platform: migrations run in CI |
| Tue | Endpoints GET /map, /map/zones, /map/orders, /map/routes | Evaluate Reverse Polish Notation, Daily Temperatures | Mercor: task session |
| Wed | SVG map in React: zones, colors by occupancy, tooltip on hover | Binary Search, Search a 2D Matrix | HR: 3 applications |
| Thu | Per-user filter (their orders and the zones they pick from) and exact search bar that colors the zones holding the stock found | Koko Eating Bananas, Find Min in Rotated Array | Platform: frontend build in CI |
| Fri | Pick route with nearest-neighbor over zones | Review | HR: answer one mock interview |
| Sat | Live SSE: events update the colors without reload; tests | 1 Medium | Platform: preview deploy on Vercel |
| Sun | Screenshot and GIF for the README; week 4 plan | Review | HR: LinkedIn, short post about the map |

## Week 4: process topology

Deliverable: page with the table of actions by category; clicking a row opens the flow graph (tables, triggers, procedures, constraints). NeetCode: Sliding Window and Linked List.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Extractor from the Postgres catalog behind the SchemaSource interface: tables, foreign keys, triggers, procedures, constraints | Best Time to Buy and Sell Stock, Longest Substring Without Repeating | Platform: read-only access to the System 1 database |
| Tue | Python AST extractor: which routes and services touch which tables | Permutation in String, Reverse Linked List | Mercor: task session |
| Wed | Runtime trace harness: I capture the real SQL per action | Merge Two Sorted Lists, Linked List Cycle | HR: 3 applications |
| Thu | Unified graph; every edge has a source (catalog, AST, trace) and a status, confirmed or unconfirmed | Reorder List, Remove Nth Node | Platform: re-extraction job |
| Fri | LLM through the gateway: describes nodes and proposes only unconfirmed edges | Review | HR: explain the project in English, 2 minutes |
| Sat | UI: table by category, React Flow with elkjs, arcs colored by source | 1 Medium | Platform: Vercel preview |
| Sun | Edge precision against the trace; README with the graph; week 5 plan | Review | HR: short post about topology |

## Week 5: indexing, hybrid search and LLM gateway

Deliverable: hybrid search over the warehouse data, with results filtered by metadata, and an LLM gateway with fallback. NeetCode: Trees.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | LLM gateway: single interface for Groq, Gemini, OpenRouter, retry, circuit breaker, mock provider | Invert Binary Tree, Maximum Depth | Platform: keys in environment variables |
| Tue | Token budget and fallback between providers; tests with the mock provider | Same Tree, Subtree of Another Tree | Mercor: task session |
| Wed | Document builder: orders, events, incidents become documents with metadata | Lowest Common Ancestor, Level Order Traversal | HR: 3 applications |
| Thu | Local embeddings with Transformers (Hugging Face) and a pgvector column with an HNSW index | Right Side View, Count Good Nodes | Platform: measure indexing time |
| Fri | Postgres full-text, metadata filters, Reciprocal Rank Fusion between the two lists | Review | HR: mock interview |
| Sat | Optional cross-encoder reranker; VectorStore interface with a Qdrant backend (Docker) and a benchmark against pgvector | Validate BST, Kth Smallest | Platform: simple load test |
| Sun | Note with the comparison results; week 6 plan | Review | HR: CV review |

## Week 6: copilot, router and safe text-to-SQL

Deliverable: copilot with answers that carry citations, query router, and generated SQL only in read-only mode. NeetCode: Heap and Backtracking.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Router: the question goes to SQL, vector, hybrid, tool or CAG (runbooks in context) | Kth Largest Element in a Stream, Last Stone Weight | Platform: log of chosen routes |
| Tue | Text-to-SQL: SELECT only, table allowlist, LIMIT, timeout, read-only database role | K Closest Points, Kth Largest in Array | Mercor: task session |
| Wed | RAG pipeline with LangChain (prompts, retriever, output parsers): context, prompt with anti-injection rules, citations to the source | Subsets, Combination Sum | HR: 3 applications |
| Thu | Semantic cache: similarity in pgvector, answers in Redis with TTL; invalidation on new events | Permutations, Subsets II | Platform: cache hit rate |
| Fri | Copilot UI: streamed answer, clickable citations, deep link to System 1 | Review | HR: 3-minute presentation |
| Sat | Security tests: injection through reference and source_company | 1 Medium | Platform: rate limit on the copilot with Redis |
| Sun | Design note; week 7 plan | Review | HR: LinkedIn |

## Week 7: incident inbox, agent and MCP

Deliverable: inbox that detects incidents, agent that proposes actions, human approval and an MCP server. NeetCode: Graphs.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | Detectors: rules and statistics (blocked orders, negative stock, lag) with severity | Number of Islands, Max Area of Island | Platform: alerts for detectors |
| Tue | Timeline per incident with evidence from events and documents | Clone Graph, Pacific Atlantic Water Flow | Mercor: task session |
| Wed | LangGraph agent with LangChain tools: investigation nodes, read-only tools, step budget | Surrounded Regions, Rotting Oranges | HR: 3 applications |
| Thu | propose_action and approval, through the ActionClient interface: the service account does the execution, with an idempotency key | Course Schedule, Course Schedule II | Platform: audit log for approvals |
| Fri | MCP server: tools search, get_order, propose_action; test with an MCP client | Review | HR: mock interview |
| Sat | Inbox UI: filterable list, incident detail, approve button; panel for free-text orders | Graph Valid Tree | Platform: Vercel preview |
| Sun | Demo scenarios with simulated incidents; week 8 plan | Review | HR: post about the agent with approval |

## Week 8: UMAP explorer and the Quality Lab simulator

Deliverable: UMAP semantic map with HDBSCAN and a simulator with fault injection and fault_log. NeetCode: Advanced Graphs and 1-D DP.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | UMAP projection with fixed random_state, transform for new points; HDBSCAN clusters | Climbing Stairs, House Robber | Platform: nightly re-projection job |
| Tue | Canvas 2D explorer: colors by type, hover, selection, open document | Min Cost Climbing Stairs, Coin Change | Mercor: task session |
| Wed | Simulator: generates realistic orders and events through the System 1 API | Word Break, Longest Increasing Subsequence | HR: 3 applications |
| Thu | Fault injection: negative stock, blocked orders, duplicates, with fault_log (type, moment, what was touched) | Network Delay Time, Cheapest Flights | Platform: simulator run in CI |
| Fri | Golden set of 40-60 questions with answer and source, derived from fault_log | Review | HR: mock interview |
| Sat | Golden set for topology (known edges from the trace) and synthetic pairs for fine-tuning | 1 Medium DP | Platform: versioned test data |
| Sun | Daily report with verified numbers; screenshot of the explorer; week 9 plan | Review | HR: LinkedIn, post about UMAP |

## Week 9: evaluation, observability and security

Deliverable: RAGAS and LLM-as-judge reports, embeddings benchmark, traces in Langfuse, security tests. NeetCode: 2-D DP, Greedy, Intervals.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | RAGAS on the golden set, with RAG and CAG compared on score, tokens and latency: faithfulness, context relevance, answer relevance | Unique Paths, Longest Common Subsequence | Platform: report saved in CI |
| Tue | LLM-as-judge with a fixed rubric; I check agreement with 10 labels I provide | Jump Game, Maximum Subarray | Mercor: task session |
| Wed | Embeddings benchmark on 2-3 models; fine-tuning with PyTorch and Transformers (training loop, CPU or Colab), compared before and after | Merge Intervals, Insert Interval | HR: 3 applications |
| Thu | Langfuse: trace per question, prompt versions, cost and latency p50 and p95 | Non-overlapping Intervals, Meeting Rooms II | Platform: Grafana dashboard (latency, cost, lag) and alerts on lag and on budget |
| Fri | Security: RBAC at retrieval with role_scope, rate limiting, prompt injection tests | Review | HR: mock interview |
| Sat | Quality gate in CI: if the score drops below the threshold, the build fails | 1 Medium | Platform: X-Request-ID correlation |
| Sun | Evaluation report with the limits acknowledged; week 10 plan | Review | HR: review stories |

## Week 10: deploy, demo and going to market

Deliverable: system deployed for free, README with architecture and results, demo video, 3-minute pitch. NeetCode: review by topic.

| Day | Code | NeetCode | HR, Mercor, Platform |
|---|---|---|---|
| Mon | kind manifests: deployments, secrets, liveness probes; full local run | Review Arrays, Stack | Platform: fluent kubectl |
| Tue | Deploy: backend on Render, frontend on Vercel, Postgres on Supabase, Kafka on Aiven | Review Trees, Graphs | Mercor: task session |
| Wed | Smoke test on the deployed environment; fix what breaks | Review DP | HR: 5 applications |
| Thu | README: diagram, decisions, evaluation results, acknowledged limits | Review Heap, Backtracking | HR: final CV with both systems |
| Fri | 3-4 minute demo video: map, topology, copilot, inbox with approval | Mock technical interview | HR: 3-minute pitch, rehearsed |
| Sat | Code review in both repos; close the small issues | 1 Medium | HR: final LinkedIn post |
| Sun | Plan for how much time I apply in parallel with meetings; what I add after | Review | HR: applications and messages to recruiters |

## Success criteria

At the end, the following must be true and demonstrable in 3 minutes.

| Typical requirement in AI Engineer job posts | Proof from the project |
|---|---|
| RAG, vectors, hybrid search | pgvector with HNSW, full-text, Reciprocal Rank Fusion, reranker, embeddings benchmark, pgvector compared with Qdrant and RAG compared with CAG |
| Agents and tool use | LangGraph agent with LangChain tools, human approval and MCP server |
| Evaluation | golden set, RAGAS, LLM-as-judge, quality gate in CI |
| Observability and cost | Langfuse traces, prompt versions, Grafana dashboards for cost and latency |
| Security | RBAC at retrieval, anti-injection, read-only text-to-SQL, rate limiting |
| Distributed systems | idempotent Kafka, dead-letter, outbox fixed in System 1 |
| Delivery | CI, Docker, kind, free deploy, README with acknowledged limits |
| PyTorch, Transformers, Redis | embeddings fine-tuning with before and after results, semantic cache and rate limiting in Redis |

Weekly criteria: the deliverable runs and has tests; the README is updated; you did the review on at least 6 days out of 7; you sent at least 3 applications.

## Detailed steps for the added pieces

The weekly tables say what you work on each day. Here are the concrete steps for the pieces added after the job post analysis. Every row points to the day in the weekly table.

### Redis

| Day | Steps | How you check |
|---|---|---|
| W1, Sat | Add the redis service in Compose, with a healthcheck; install the async client redis-py; write a redis_client module with a reusable connection | A test does PING and writes, then reads a key |
| W6, Thu | cache_entries table (embedding in pgvector, id); the answer is saved in Redis under that id, with TTL; on a new question you look for the closest entry and read from Redis only above the threshold | The second, similar question does not call the LLM; the hit rate shows in the metrics |
| W6, Thu | Tags per SKU and order in Redis sets; the Kafka consumer deletes the tagged entries on stock or pick events | After an event, the identical question gets a new answer |
| W6, Sat | Rate limiting: INCR with EXPIRE on the key user:route; over the limit you answer 429 | Test that goes over the limit; test with Redis off, where it falls back to the in-memory limiter |
| W5, Tue | Daily token budget in a Redis counter, read by the gateway before the call | After the budget is exceeded, requests go to the small model or to the mock |

### Grafana

| Day | Steps | How you check |
|---|---|---|
| W1, Sat | Compose starts Prometheus and Grafana; provisioning file for the data source | Grafana opens with Prometheus connected, no manual steps |
| W2, Sat | First dashboard: Kafka consumer lag, processed events, ingestion errors; saved as JSON in the repo | You stop the consumer and see the lag go up |
| W9, Thu | Final dashboard: latency p50 and p95, tokens and cost per day, cache hit rate, LLM fallbacks, open incidents; one alert on lag | You run the simulator and the panels move; the alert fires on induced lag |
| W10, Thu | Screenshots of the dashboards in the README | The screenshots show real data from the simulator |

### LangChain

| Day | Steps | How you check |
|---|---|---|
| W5, Tue | Custom ChatModel over the gateway, keeping budget and fallback | Test with the mock provider and with a failing provider: fallback works through the LangChain interface |
| W5, Fri | Hybrid search wrapped in a BaseRetriever | Same results as the direct call, checked in a test |
| W6, Wed | Versioned prompt with ChatPromptTemplate and Pydantic parser for an answer with citations | The answer always has the required fields; an invalid answer is rejected |
| W7, Wed | @tool tools with Pydantic schemas, called from the LangGraph nodes | The agent calls the right tool on three test questions |

### PyTorch and Transformers

| Day | Steps | How you check |
|---|---|---|
| W5, Thu | Load the embeddings model with Transformers (tokenizer, model, pooling) and generate vectors for documents | The vectors have the expected size; search finds a known document |
| W8, Sat | Generate (question, relevant document) pairs from the simulator and fault_log; split train, validation, test by incident | No incident appears in two sets |
| W9, Wed | Training loop in PyTorch: batch, cosine similarity, cross-entropy with in-batch negatives; a few epochs on CPU or Colab | The loss goes down on train and on validation |
| W9, Sat | Evaluate hit@k and MRR on the golden set, base model against trained model; reindex if it wins | Comparison table in the report, including if there is no gain |

### CAG

| Day | Steps | How you check |
|---|---|---|
| W6, Tue | Runbook corpus in a fixed prompt; the router sends questions about procedures on this path | Three questions about procedures go to CAG, one about an order goes to RAG |
| W9, Mon | Same golden set on RAG and on CAG; score, tokens per answer, latency | Table with the three measures; conclusion written in the README |

### Qdrant

| Day | Steps | How you check |
|---|---|---|
| W5, Sat | VectorStore interface with upsert, search with filters and delete; pgvector implementation and Qdrant implementation (Docker) | The same test passes on both implementations |
| W5, Sun | Benchmark: same set of documents and questions; recall, query latency, operating effort | Table in the results note; the choice of pgvector justified with numbers |

### Free-text order

| Day | Steps | How you check |
|---|---|---|
| W7, Sat | Pydantic schema OrderDraft; prompt with structured output through LangChain; match products by SKU, then hybrid search by name; uncertain fields marked "to confirm" | Three test messages produce correct drafts; an ambiguous product is marked |
| W7, Sat | Panel in the UI: you paste the text, see the draft with the source fragments, approve or correct; approval goes through propose_action | After approval a single order appears in System 1; a second approval of the same message does not create a duplicate |
| W7, Sun | Security test: a message that asks for something other than an order or a huge quantity | The message is treated as data; a quantity over the cap is rejected |
| W9, Mon | Set of 30 test messages in Quality Lab; metric on correct fields | The score appears in the report and in the CI gate |

### Daily warehouse report

| Day | Steps | How you check |
|---|---|---|
| W8, Sun | Daily job that computes the numbers from the projections and sends them as JSON to the LLM, with the instruction to use only those numbers | The report appears in the inbox for the simulated day |
| W8, Sun | Check: every number in the text must exist in the JSON; otherwise it is regenerated once, then only the numbers are shown | Test with a mock LLM that sneaks in a false number: the report is rejected |
| W9, Thu | Cost and latency of the report in the Grafana dashboard | One call per day shows in the cost panel |
