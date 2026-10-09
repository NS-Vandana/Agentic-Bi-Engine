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
st.sidebar.header("📁 Data Source & Ingestion")
uploaded_file = st.sidebar.file_uploader(
    "Upload Custom Operational Telemetry (CSV or Excel)",
    type=["csv", "xlsx"]
)

# Connect to DuckDB (in-memory for uploads, or file for default seed)
conn = duckdb.connect()

if uploaded_file is not None:
    # 1. Parse custom uploaded file
    if uploaded_file.name.endswith(".csv"):
        df_uploaded = pd.read_csv(uploaded_file)
    else:
        df_uploaded = pd.read_excel(uploaded_file)

    conn.register("metrics", df_uploaded)
    st.sidebar.success(f"Loaded {len(df_uploaded)} rows from `{uploaded_file.name}`")

    # Dynamically extract filter choices from uploaded columns
    region_options = sorted(df_uploaded["region"].dropna().unique().tolist()) if "region" in df_uploaded.columns else ["Default"]
    quarter_options = sorted(df_uploaded["quarter"].dropna().unique().tolist()) if "quarter" in df_uploaded.columns else ["Default"]
    metric_options = sorted(df_uploaded["metric_name"].dropna().unique().tolist()) if "metric_name" in df_uploaded.columns else ["Default"]
else:
    # 2. Fall back to local seeded DuckDB
    if os.path.exists("data/supply_chain.duckdb"):
        conn.execute("ATTACH 'data/supply_chain.duckdb' AS db (READ_ONLY);")
        conn.execute("USE db;")
    
    region_options = ["Jebel_Ali", "Singapore", "Rotterdam"]
    quarter_options = ["2026-Q3", "2026-Q4"]
    metric_options = ["Port_SLA", "Berth_Turnaround", "Gate_Throughput"]

st.sidebar.header("Incident Parameters")
region = st.sidebar.selectbox("Region / Port", region_options)
quarter = st.sidebar.selectbox("Quarter", quarter_options)
metric_name = st.sidebar.selectbox("Observed Metric", metric_options)
drop_pct = st.sidebar.slider("Observed SLA Drop (%)", min_value=-50.0, max_value=-1.0, value=-18.5, step=0.5)

run_button = st.sidebar.button("Run Diagnostic Analysis", type="primary")

# --- Main Dashboard ---
if run_button:
    if not groq_client:
        st.error("GROQ_API_KEY is not configured in Secrets. Add it under App Settings -> Secrets.")
    else:
        with st.spinner("Executing DuckDB columnar query & Groq reasoning..."):
            # 1. Deterministic SQL Execution
            sql_query = (
                f"SELECT fulfillment_delay_hours, financial_impact_usd "
                f"FROM metrics "
                f"WHERE region = '{region}' AND quarter = '{quarter}'"
            )

            sql_start = time.perf_counter()
            try:
                row = conn.execute(
                    "SELECT fulfillment_delay_hours, financial_impact_usd FROM metrics WHERE region = ? AND quarter = ?",
                    [region, quarter]
                ).fetchone()
            except Exception as e:
                row = None
                st.warning(f"Query note: Ensure uploaded table has 'fulfillment_delay_hours' and 'financial_impact_usd' columns. ({e})")

            sql_latency_ms = round((time.perf_counter() - sql_start) * 1000, 2)
            conn.close()

            delay = row[0] if row else 0.0
            impact = row[1] if row else 0.0

            # 2. AI Reasoning via Groq
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

            # 3. KPI Overview Cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Observed Delay", f"{delay} hrs")
            col2.metric("Financial Impact", f"${impact:,.2f}")
            col3.metric("Engine Source", "Groq LPU Engine")

            st.divider()

            # 4. Diagnostic Panels
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🔍 Primary Root Cause")
                st.info(data.get("primary_root_cause", "No data returned."))
            with c2:
                st.subheader("🛠️ Recommended Action")
                st.success(data.get("recommended_action", "No action specified."))

            st.divider()

            # 5. Visual Chart Benchmark
            st.subheader("📈 Operational Impact Benchmark")
            chart_data = pd.DataFrame({
                "Operational Metric": ["Operational Delay (hrs)", "Financial Impact ($K)"],
                "Value": [delay, impact / 1000]
            }).set_index("Operational Metric")
            st.bar_chart(chart_data)

            # 6. Audit & Explainability Expander
            with st.expander("🛠️ Execution Trace & Telemetry Audit", expanded=True):
                t1, t2, t3 = st.columns(3)
                t1.metric("DuckDB Query Latency", f"{sql_latency_ms} ms")
                t2.metric("Groq LLM Latency", f"{llm_latency_ms} ms")
                t3.metric("LLM Architecture", "openai/gpt-oss-120b")

                st.markdown("**Deterministic SQL Query Executed:**")
                st.code(sql_query, language="sql")

                st.markdown("**Raw API JSON Output:**")
                st.json({
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
                })
else:
    st.info("Select parameters or upload a custom CSV/Excel file in the sidebar, then click **Run Diagnostic Analysis**.")