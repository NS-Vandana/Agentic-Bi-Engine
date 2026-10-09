import os
import time
import json
import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Agentic BI SLA Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
groq_client = Groq(api_key=GROQ_KEY)

# In-memory query cache
cache = {}

class QueryPayload(BaseModel):
    region: str = "Jebel_Ali"
    quarter: str = "2026-Q3"
    metric_name: str = "Port_SLA"
    observed_drop_pct: float = -18.5

@app.post("/api/v1/analyze")
async def analyze_incident(payload: QueryPayload):
    cache_key = f"{payload.region}_{payload.quarter}_{payload.metric_name}_{payload.observed_drop_pct}"
    
    # 1. Return cached trace immediately if available
    if cache_key in cache:
        cached_result = cache[cache_key].copy()
        cached_result["source"] = "In-Memory Semantic Cache"
        return cached_result

    # 2. Benchmark DuckDB execution
    sql_query = (
        f"SELECT fulfillment_delay_hours, financial_impact_usd "
        f"FROM metrics "
        f"WHERE region = '{payload.region}' AND quarter = '{payload.quarter}'"
    )
    
    sql_start = time.perf_counter()
    conn = duckdb.connect("data/supply_chain.duckdb", read_only=True)
    row = conn.execute(
        "SELECT fulfillment_delay_hours, financial_impact_usd FROM metrics WHERE region = ? AND quarter = ?",
        [payload.region, payload.quarter]
    ).fetchone()
    conn.close()
    sql_latency_ms = round((time.perf_counter() - sql_start) * 1000, 2)

    delay = row[0] if row else 0.0
    impact = row[1] if row else 0.0

    # 3. Construct grounded prompt
    prompt = f"""
    You are an expert Chief Operating Officer analyzing port supply chain telemetry.
    Region: {payload.region}
    Quarter: {payload.quarter}
    Metric Affected: {payload.metric_name}
    Observed Drop: {payload.observed_drop_pct}%
    DuckDB SQL Measured Delay: {delay} hours
    DuckDB SQL Measured Financial Loss: ${impact}

    Return strict JSON with exactly two fields:
    - "primary_root_cause": A concise, plausible technical explanation (1 sentence).
    - "recommended_action": A concrete mitigation plan (1 sentence).
    Do not output markdown codeblocks. Return plain raw JSON only.
    """

    # 4. Benchmark Groq inference
    llm_start = time.perf_counter()
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-120b",
        temperature=0.2,
    )
    llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)

    raw_text = chat_completion.choices[0].message.content.strip()
    clean_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed_llm = json.loads(clean_text)
    except Exception:
        parsed_llm = {
            "primary_root_cause": clean_text,
            "recommended_action": "Conduct immediate telemetry review and preventative calibration."
        }

    response_payload = {
        "primary_root_cause": parsed_llm.get("primary_root_cause"),
        "operational_delay_hours": delay,
        "financial_impact_usd": impact,
        "recommended_action": parsed_llm.get("recommended_action"),
        "source": "Groq LPU Engine",
        "telemetry_trace": {
            "executed_sql": sql_query,
            "sql_latency_ms": sql_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "model_used": "openai/gpt-oss-120b"
        }
    }

    cache[cache_key] = response_payload
    return response_payload