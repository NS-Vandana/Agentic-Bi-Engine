import os
import time
import json
import duckdb
import pandas as pd
import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="Executive Operations Intelligence",
    page_icon="⚡",
    layout="wide"
)

# Read key from Streamlit Cloud Secrets or local environment
GROQ_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

st.title("⚡ Port Operations & SLA Intelligence Engine")
st.caption("Deterministic DuckDB Columnar Telemetry + Groq LPU Root Cause Attribution")

# --- Sidebar Controls ---
st.sidebar.header("Incident Parameters")
region = st.sidebar.selectbox("Region / Port", ["Jebel_Ali", "Singapore", "Rotterdam"])
quarter = st.sidebar.selectbox("Quarter", ["2026-Q3", "2026-Q4"])
metric_name = st.sidebar.selectbox("Observed Metric", ["Port_SLA", "Berth_Turnaround", "Gate_Throughput"])
drop_pct = st.sidebar.slider("Observed SLA Drop (%)", min_value=-50.0, max_value=-1.0, value=-18.5, step=0.5)
run_button = st.sidebar.button("Run Diagnostic Analysis", type="primary")

# --- Main Dashboard ---
if run_button:
    if not groq_client:
        st.error("GROQ_API_KEY is not configured in Secrets. Add it under App Settings -> Secrets.")
    else:
        with st.spinner("Executing DuckDB columnar query & Groq reasoning..."):
            # 1. Deterministic DuckDB SQL Execution & Timing
            sql_query = (
                f"SELECT fulfillment_delay_hours, financial_impact_usd "
                f"FROM metrics "
                f"WHERE region = '{region}' AND quarter = '{quarter}'"
            )

            sql_start = time.perf_counter()
            conn = duckdb.connect("data/supply_chain.duckdb", read_only=True)
            row = conn.execute(
                "SELECT fulfillment_delay_hours, financial_impact_usd FROM metrics WHERE region = ? AND quarter = ?",
                [region, quarter]
            ).fetchone()
            conn.close()
            sql_latency_ms = round((time.perf_counter() - sql_start) * 1000, 2)

            delay = row[0] if row else 0.0
            impact = row[1] if row else 0.0

            # 2. AI Reasoning via Groq & Timing
            prompt = f"""
            You are an expert Chief Operating Officer analyzing port supply chain telemetry.
            Region: {region}
            Quarter: {quarter}
            Metric Affected: {metric_name}
            Observed Drop: {drop_pct}%
            DuckDB Measured Delay: {delay} hours
            DuckDB Measured Loss: ${impact}

            Return strict JSON with two keys:
            - "primary_root_cause": concise 1-sentence technical explanation
            - "recommended_action": concrete 1-sentence mitigation plan
            """

            llm_start = time.perf_counter()
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)

            data = json.loads(chat_completion.choices[0].message.content)

            # --- Visual Section 1: KPI Cards ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Observed Delay", f"{delay} hrs")
            col2.metric("Financial Impact", f"${impact:,.2f}")
            col3.metric("Engine Source", "Groq LPU Engine")

            st.divider()

            # --- Visual Section 2: Diagnostic Attribution ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🔍 Primary Root Cause")
                st.info(data.get("primary_root_cause", "No data returned."))
            with c2:
                st.subheader("🛠️ Recommended Action")
                st.success(data.get("recommended_action", "No action specified."))

            st.divider()

            # --- Visual Section 3: Interactive Bar Chart ---
            st.subheader("📈 Operational Impact Benchmark")
            chart_data = pd.DataFrame({
                "Operational Metric": ["Operational Delay (hrs)", "Financial Impact ($K)"],
                "Value": [delay, impact / 1000]
            }).set_index("Operational Metric")
            st.bar_chart(chart_data)

            # --- Visual Section 4: Telemetry & Audit Expander ---
            with st.expander("🛠️ Execution Trace & Telemetry Audit", expanded=True):
                t1, t2, t3 = st.columns(3)
                t1.metric("DuckDB Query Latency", f"{sql_latency_ms} ms")
                t2.metric("Groq LLM Latency", f"{llm_latency_ms} ms")
                t3.metric("LLM Architecture", "openai/gpt-oss-120b")

                st.markdown("**Deterministic SQL Query Executed:**")
                st.code(sql_query, language="sql")

                st.markdown("**Raw API JSON Output:**")
                raw_debug = {
                    "region": region,
                    "quarter": quarter,
                    "metric_name": metric_name,
                    "operational_delay_hours": delay,
                    "financial_impact_usd": impact,
                    "primary_root_cause": data.get("primary_root_cause"),
                    "recommended_action": data.get("recommended_action"),
                    "telemetry_trace": {
                        "executed_sql": sql_query,
                        "sql_latency_ms": sql_latency_ms,
                        "llm_latency_ms": llm_latency_ms,
                        "model_used": "openai/gpt-oss-120b"
                    }
                }
                st.json(raw_debug)
else:
    st.info("Select parameters in the sidebar and click **Run Diagnostic Analysis** to generate operational insights.")