import os
import duckdb

os.makedirs("data", exist_ok=True)
db_path = os.path.join("data", "supply_chain.duckdb")

conn = duckdb.connect(db_path)

conn.execute("""
CREATE OR REPLACE TABLE metrics (
    region VARCHAR,
    quarter VARCHAR,
    metric_name VARCHAR,
    fulfillment_delay_hours DOUBLE,
    financial_impact_usd DOUBLE
);
""")

records = [
    ("Jebel_Ali", "2026-Q3", "Port_SLA", 42.5, 210000.0),
    ("Jebel_Ali", "2026-Q4", "Port_SLA", 18.0, 85000.0),
    ("Singapore", "2026-Q3", "Port_SLA", 64.2, 340000.0),
    ("Singapore", "2026-Q4", "Berth_Turnaround", 29.5, 145000.0),
    ("Rotterdam", "2026-Q3", "Gate_Throughput", 51.0, 290000.0),
    ("Rotterdam", "2026-Q4", "Port_SLA", 12.3, 62000.0),
]

conn.executemany("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", records)
conn.close()

print("Multi-hub metrics seeded successfully!")