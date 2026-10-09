import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Executive Operations Intelligence",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Port Operations & SLA Intelligence Engine")
st.caption("Deterministic DuckDB Columnar Telemetry + Groq LPU Root Cause Attribution")

# --- Sidebar Controls ---
st.sidebar.header("Incident Parameters")

region = st.sidebar.selectbox(
    "Region / Port",
    ["Jebel_Ali", "Singapore", "Rotterdam"]
)

quarter = st.sidebar.selectbox(
    "Quarter",
    ["2026-Q3", "2026-Q4"]
)

metric_name = st.sidebar.selectbox(
    "Observed Metric",
    ["Port_SLA", "Berth_Turnaround", "Gate_Throughput"]
)

drop_pct = st.sidebar.slider(
    "Observed SLA Drop (%)",
    min_value=-50.0,
    max_value=-1.0,
    value=-18.5,
    step=0.5
)

run_button = st.sidebar.button("Run Diagnostic Analysis", type="primary")

# --- Main Dashboard ---
if run_button:
    payload = {
        "region": region,
        "quarter": quarter,
        "metric_name": metric_name,
        "observed_drop_pct": drop_pct
    }

    with st.spinner("Executing DuckDB columnar query & Groq reasoning..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/analyze",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()

                # 1. Metric Overview Cards
                col1, col2, col3 = st.columns(3)
                col1.metric("Observed Delay", f"{data.get('operational_delay_hours', 0)} hrs")
                col2.metric("Financial Impact", f"${data.get('financial_impact_usd', 0):,.2f}")
                col3.metric("Engine Source", data.get("source", "N/A"))

                st.divider()

                # 2. Root Cause Attribution & Remediation
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔍 Primary Root Cause")
                    st.info(data.get("primary_root_cause", "No data returned."))

                with c2:
                    st.subheader("🛠️ Recommended Action")
                    st.success(data.get("recommended_action", "No action specified."))

                st.divider()

                # 3. Telemetry Visual Benchmark
                st.subheader("📈 Operational Impact Benchmark")
                chart_data = pd.DataFrame({
                    "Operational Metric": ["Operational Delay (hrs)", "Financial Impact ($K)"],
                    "Value": [
                        data.get("operational_delay_hours", 0),
                        data.get("financial_impact_usd", 0) / 1000
                    ]
                }).set_index("Operational Metric")
                
                st.bar_chart(chart_data)

                # 4. Deterministic Explainability & Latency Trace
                with st.expander("🛠️ Execution Trace & Telemetry Audit", expanded=True):
                    trace = data.get("telemetry_trace", {})
                    
                    t1, t2, t3 = st.columns(3)
                    t1.metric("DuckDB Query Latency", f"{trace.get('sql_latency_ms', 0)} ms")
                    t2.metric("Groq LLM Latency", f"{trace.get('llm_latency_ms', 0)} ms")
                    t3.metric("LLM Architecture", trace.get("model_used", "openai/gpt-oss-120b"))

                    st.markdown("**Deterministic SQL Query Executed:**")
                    st.code(trace.get("executed_sql", "No SQL executed."), language="sql")

                    st.markdown("**Raw API JSON Output:**")
                    st.json(data)

            else:
                st.error(f"Backend returned status {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to FastAPI backend. Ensure Uvicorn is running on http://127.0.0.1:8000")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
else:
    st.info("Select parameters in the sidebar and click **Run Diagnostic Analysis** to generate operational insights.")