# ⚡ Agentic BI Engine: Autonomous Port SLA Intelligence

An end-to-end operational intelligence system combining deterministic columnar telemetry (DuckDB) with sub-second LLM reasoning (Groq LPU) to diagnose port supply chain disruptions, calculate financial impact, and deliver actionable remediation protocols.

---

## 🏛️ System Architecture

```text
[ Streamlit Client UI ] 
        │ (HTTP / JSON)
        ▼
[ FastAPI Async Middleware ]
        │
   ┌────┴──────────────────────────┐
   ▼                               ▼
[ In-Memory Semantic Cache ]   [ DuckDB Columnar Store ]
   │ (Cache Hit)                   │ (Parameterized SQL: <5ms)
   │                               ▼
   │                   [ Context Grounding Engine ]
   │                               │
   │                               ▼
   │                   [ Groq LPU: GPT-OSS-120B ]
   │                               │ (Structured JSON Output)
   └───────────────┬───────────────┘
                   ▼
         [ Response Delivery & Telemetry Trace ]