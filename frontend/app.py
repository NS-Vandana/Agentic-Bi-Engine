import os
import json
import duckdb
import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="Executive Operations Intelligence",
    page_icon="⚡",
    layout="wide"
)

# Safely read the key from Streamlit Cloud Secrets or local environment
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

if run_button:
    if not groq_client:
        st.error("GROQ_API_KEY is not configured in Secrets. Add it in App settings -> Secrets.")
    else:
        with st.spinner("Executing DuckDB columnar query & Groq reasoning..."):
            # 1. Deterministic DuckDB SQL Execution
            conn = duckdb.connect("data/supply_chain.duckdb", read_only=True)
            row = conn.execute(
                "SELECT fulfillment_delay_hours, financial_impact_usd FROM metrics WHERE region = ? AND quarter = ?",
                [region, quarter]
            ).fetchone()
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

            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            data = json.loads(chat_completion.choices[0].message.content)

            # 3. Render Metric Cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Observed Delay", f"{delay} hrs")
            col2.metric("Financial Impact", f"${impact:,.2f}")
            col3.metric("Engine Source", "Groq LPU Engine")

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🔍 Primary Root Cause")
                st.info(data.get("primary_root_cause", "No data returned."))
            with c2:
                st.subheader("🛠️ Recommended Action")
                st.success(data.get("recommended_action", "No action specified."))