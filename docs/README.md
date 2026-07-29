# DocuMindAI — Documentation Index

Entry point to the project's technical documentation. Everything here is written against the code, and where a document disagrees with the repository, **the repository is correct**.

> **A note on the audit documents.** `docs/audit/` captures a read-only inspection carried out before the repair phase, and `docs/engineering/DEBUG_MASTER_PLAN.md` is the dependency-ordered backlog produced from it. They are kept deliberately: they record *why* the system is shaped the way it is, and the findings are annotated with their resolutions. Read them as engineering history, not as a description of the system today.

---

## Start here

| If you want to… | Read |
|---|---|
| Run the project | [Installation guide](deployment/installation.md) · [Root README](../README.md) |
| Understand the system | [System architecture](architecture/ARCHITECTURE.md) |
| Understand one workspace | [Workspace documentation](architecture/WORKSPACES.md) |
| Change code safely | [Dependency graph](architecture/DEPENDENCY_GRAPH.md) · [Repair rulebook](engineering/REPAIR_RULEBOOK.md) |
| Deploy it | [Audit & deployment guide](deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md) |

## Architecture

| Document | Read it for |
|---|---|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | Folder map, bootstrap, request routing, auth pipeline, ingestion, the full RAG pipeline, SSE streaming, worker/queue design, data layer, caching, observability |
| [WORKSPACES.md](architecture/WORKSPACES.md) | Per-workspace deep dives (General, HR, Legal, Finance, Study, Research, Exam): purpose, flow, endpoints, tables, workers, limitations |
| [DEPENDENCY_GRAPH.md](architecture/DEPENDENCY_GRAPH.md) | Import graph, change-impact matrix, environment-variable table, end-to-end flows. **Read before editing anything with a wide blast radius.** |
| [API_AUDIT.md](architecture/API_AUDIT.md) | Endpoint inventory and the frontend↔backend contract |
| [INTEGRATIONS.md](architecture/INTEGRATIONS.md) | Every external service and API key, with wiring status |
| [project-map.md](architecture/project-map.md) | Condensed file-level map |

## Engineering

| Document | Read it for |
|---|---|
| [REPAIR_RULEBOOK.md](engineering/REPAIR_RULEBOOK.md) | The binding engineering rules — invariants, safe-modification process, care levels |
| [DEBUG_MASTER_PLAN.md](engineering/DEBUG_MASTER_PLAN.md) | The dependency-ordered repair backlog (C-1…L-13) with implementation notes |
| [INTERVIEW_GUIDE.md](engineering/INTERVIEW_GUIDE.md) | System-design walkthrough, trade-offs, and likely questions about this codebase |

## Deployment

| Document | Read it for |
|---|---|
| [installation.md](deployment/installation.md) | Local setup |
| [PROJECT_AUDIT_AND_DEPLOYMENT.md](deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md) | Pre-launch audit, complete environment-variable reference, platform comparison, step-by-step deployment, troubleshooting |

## Audit history *(point-in-time; findings annotated with resolutions)*

| Document | Read it for |
|---|---|
| [REPORT.md](audit/REPORT.md) | Executive overview, production-readiness scorecard, marketing-vs-reality gaps |
| [FINAL_AUDIT.md](audit/FINAL_AUDIT.md) | Consolidated, severity-ranked findings with evidence |
| [SECURITY_AUDIT.md](audit/SECURITY_AUDIT.md) | Auth, tenancy, secrets, payments, prompt-injection review |
| [QUALITY_AUDIT.md](audit/QUALITY_AUDIT.md) | Dead code, duplication, testing, concurrency, migrations |

## Reference material

- [demo-documents/](demo-documents/) — synthetic PDFs for reproducing the demo locally (fictional company, `*@example.com` personas, invented figures)
- [screenshots/](screenshots/) — application screenshots used by the root README
- [brand/](brand/) — master logo source, used to regenerate the app icons

---

## The project in one paragraph

**DocuMindAI** is a multi-tenant, seven-workspace RAG platform — FastAPI + async SQLAlchemy + PostgreSQL/pgvector + Redis/Celery + Next.js 16 — that answers questions about uploaded documents with Gemini, grounded and cited to a page, streamed over Server-Sent Events. Retrieval is hybrid: pgvector ANN plus lexical full-text search, fused by Reciprocal Rank Fusion, reranked by a cross-encoder, then trimmed to a token budget before generation. Its defining design choice is **extract-then-compute** — the LLM extracts fields and Python computes every number, all fifteen finance ratios, legal escalation and citation formatting included, so figures are never hallucinated. When the evidence isn't there, the system refuses to answer.
