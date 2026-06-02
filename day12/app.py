"""
Sigma Command Center — Business Incident Dashboard
Reads directly from your team's S3 bucket (Phase 3 output).

Prerequisites:
  - lab/.env must have SIGMA_S3_BUCKET and AWS credentials set
  - Phase 3 must have completed (incident report and quarantine file in S3)

Run:  streamlit run app.py
"""

import io, json, os, re
from datetime import datetime
from pathlib import Path

import boto3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "lab" / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
BUCKET = os.getenv("SIGMA_S3_BUCKET", "")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

SEVERITY_COLOR = {
    "critical": "🔴",
    "warning":  "🟡",
    "info":     "🔵",
    "success":  "🟢",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sigma Command Center",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Premium Custom CSS (Matte Black Theme) ────────────────────────────────────
st.markdown("""
<style>
    /* Global Theme & Background */
    .stApp {
        background-color: #0a0a0a;
        color: #e2e8f0;
        font-family: 'Inter', 'Roboto', sans-serif;
    }
    
    /* Hide top header line */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* Title */
    h1 {
        font-size: 3rem !important;
        font-weight: 800 !important;
        color: #f8fafc !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Metric Cards Styling (Matte Black) */
    div[data-testid="stMetric"] {
        background-color: #18181b;
        border: 1px solid #27272a;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        transition: border-color 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        border: 1px solid #52525b;
    }
    
    /* Metric Values */
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #a1a1aa !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    /* Alert / Status Boxes */
    div[data-testid="stAlert"] {
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Success Box (Muted Green) */
    .st-emotion-cache-1215b49 {
        background-color: #064e3b !important;
        border-left: 4px solid #10b981 !important;
        color: #d1fae5 !important;
    }
    
    /* Error Box (Muted Red) */
    .st-emotion-cache-1kqj710 {
        background-color: #450a0a !important;
        border-left: 4px solid #ef4444 !important;
        color: #fee2e2 !important;
    }
    
    /* Dataframe Container */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #27272a;
    }
    
    /* Refresh Button Styling */
    button[kind="secondary"] {
        background-color: #27272a !important;
        color: #f4f4f5 !important;
        border: 1px solid #3f3f46 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 2rem !important;
        transition: all 0.2s ease !important;
    }
    
    button[kind="secondary"]:hover {
        background-color: #3f3f46 !important;
        border-color: #52525b !important;
    }
    
    /* Expander styling */
    div[data-testid="stExpander"] {
        background-color: #18181b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
    }
    
    /* Subheaders */
    h3 {
        color: #f8fafc !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #27272a;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Guard: bucket must be set ─────────────────────────────────────────────────
if not BUCKET:
    st.error("SIGMA_S3_BUCKET is not set. Check lab/.env")
    st.stop()

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_data() -> dict:
    s3  = boto3.client("s3", region_name=REGION)
    cw  = boto3.client("cloudwatch", region_name=REGION)

    # ── Snowflake Total Records ───────────────────────────────────────────────
    total_loaded = "—"
    try:
        import snowflake.connector
        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SIGMA"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "SILVER"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "SIGMA_WH"),
            role="ACCOUNTADMIN",
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM SIGMA.SILVER.TRANSACTIONS")
        total_loaded = f"{cur.fetchone()[0]:,}"
        conn.close()
    except Exception as e:
        st.warning(f"Could not connect to Snowflake: {e}")

    # ── Incident report ───────────────────────────────────────────────────────
    report_md   = ""
    report_key  = ""
    try:
        resp    = s3.list_objects_v2(Bucket=BUCKET, Prefix="reports/")
        objects = resp.get("Contents", [])
        if objects:
            latest     = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[0]
            report_key = latest["Key"]
            report_md  = s3.get_object(Bucket=BUCKET, Key=report_key)["Body"].read().decode()
    except Exception as e:
        st.warning(f"Could not read incident report from S3: {e}")

    # ── Quarantine CSV ────────────────────────────────────────────────────────
    quarantine_df = pd.DataFrame()
    try:
        resp    = s3.list_objects_v2(Bucket=BUCKET, Prefix="quarantine/")
        objects = resp.get("Contents", [])
        if objects:
            latest  = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[0]
            csv_raw = s3.get_object(Bucket=BUCKET, Key=latest["Key"])["Body"].read().decode()
            quarantine_df = pd.read_csv(io.StringIO(csv_raw))
    except Exception as e:
        st.warning(f"Could not read quarantine file from S3: {e}")

    # ── CloudWatch alarm states ───────────────────────────────────────────────
    alarms = []
    try:
        alarm_names = [
            "sigma-snowflake-zero-load",
            "sigma-lambda-version-change",
            "sigma-pipeline-row-divergence",
        ]
        resp   = cw.describe_alarms(AlarmNames=alarm_names)
        alarms = [
            {
                "name":    a["AlarmName"],
                "trigger": a.get("AlarmDescription", "—"),
                "state":   a["StateValue"],
            }
            for a in resp.get("MetricAlarms", [])
        ]
    except Exception as e:
        st.warning(f"Could not read CloudWatch alarms: {e}")

    # ── Parse incident report for key numbers ─────────────────────────────────
    def extract(pattern, default="—"):
        m = re.search(pattern, report_md, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else default

    records_lost    = extract(r"Records (?:lost|missing)[:\s]+([\d,]+)")
    recovered       = extract(r"records? (?:restored|loaded|recovered)[:\s]+([\d,]+)")
    root_cause      = extract(r"## Root Cause\n+(.*?)\n+##")
    fix_applied     = extract(r"## Fix Applied\n+(.*?)\n+##")
    report_time     = report_key.split("_")[-1].replace(".md", "") if report_key else "—"

    return {
        "report_md":      report_md,
        "report_key":     report_key,
        "records_lost":   records_lost,
        "recovered":      recovered,
        "quarantined":    str(len(quarantine_df)) if not quarantine_df.empty else "—",
        "root_cause":     root_cause,
        "fix_applied":    fix_applied,
        "report_time":    report_time,
        "alarms":         alarms,
        "quarantine_df":  quarantine_df,
        "bucket":         BUCKET,
        "total_loaded":   total_loaded,
    }


# ── Load ──────────────────────────────────────────────────────────────────────
with st.spinner("Reading from your S3 bucket and Snowflake..."):
    data = load_data()

# ── Sidebar Controls ──────────────────────────────────────────────────────────
import subprocess
import sys

with st.sidebar:
    st.header("🛠️ Pipeline Controls")
    st.markdown("Use these controls to interact with the pipeline directly from the dashboard.")
    
    st.subheader("1. Chaos Engineering")
    if st.button("🚨 Inject Disaster", width='stretch'):
        with st.spinner("Injecting silent failure..."):
            res = subprocess.run([sys.executable, "lab/disaster/inject_failure.py"], capture_output=True, text=True, cwd=str(Path(__file__).parent))
            if res.returncode == 0:
                st.success("Disaster injected!")
            else:
                st.error("Injection failed")
                st.code(res.stderr)
                
    st.subheader("2. Self-Healing AI")
    if st.button("🧠 Unleash AI Recovery", width='stretch'):
        with st.spinner("Agents are running... this takes ~2-3 minutes"):
            res = subprocess.run([sys.executable, "lab/trigger/pipeline_trigger.py"], capture_output=True, text=True, cwd=str(Path(__file__).parent))
            if res.returncode == 0:
                st.success("Recovery complete!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Recovery encountered an issue")
                st.code(res.stderr)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Sigma Command Center")
st.caption(
    f"Bucket: **{data['bucket']}** · "
    f"Report: **{data['report_key'] or 'not found'}** · "
    f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}"
)
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.markdown("---")

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.subheader("System Metrics")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total Records Loaded", data["total_loaded"])
with c2:
    st.metric("Records Lost",     data["records_lost"])
with c3:
    st.metric("Records Recovered", data["recovered"])
with c4:
    st.metric("Records Quarantined", data["quarantined"])
with c5:
    alarms_ok = sum(1 for a in data["alarms"] if a["state"] == "OK")
    st.metric("Alarms Configured", f"{alarms_ok} / {len(data['alarms'])}")

st.markdown("---")

# ── Root Cause + Fix ──────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Root Cause")
    if data["root_cause"] != "—":
        st.error(data["root_cause"])
    else:
        st.warning("Root cause not found in report — check S3")

with right:
    st.subheader("Fix Applied")
    if data["fix_applied"] != "—":
        st.success(data["fix_applied"])
    else:
        st.warning("Fix details not found in report — check S3")

st.markdown("---")

# ── Prevention Measures ───────────────────────────────────────────────────────
st.subheader("Prevention — CloudWatch Alarms Created")
if data["alarms"]:
    cols = st.columns(len(data["alarms"]))
    for col, alarm in zip(cols, data["alarms"]):
        with col:
            state = alarm["state"]
            icon  = "🟢" if state == "OK" else ("🔴" if state == "ALARM" else "🟡")
            st.markdown(f"**{icon} {alarm['name']}**")
            st.caption(f"State: {state}")
            if alarm["trigger"] != "—":
                st.caption(alarm["trigger"])
else:
    st.warning("No alarms found — did the Hardening Agent complete?")

st.markdown("---")

# ── Quarantine Table ──────────────────────────────────────────────────────────
st.subheader(f"Quarantined Records ({data['quarantined']})")
if not data["quarantine_df"].empty:
    st.dataframe(data["quarantine_df"], width='stretch')
else:
    st.info("No quarantine file found in S3")

st.markdown("---")

# ── Incident Report ───────────────────────────────────────────────────────────
st.subheader("Full Incident Report")
if data["report_md"]:
    with st.expander("Click to read the CTO-ready post-mortem", expanded=True):
        st.markdown(data["report_md"])
else:
    st.warning(
        "No incident report found in S3. "
        f"Expected: s3://{BUCKET}/reports/incident_*.md\n\n"
        "Did Phase 3 complete successfully? Re-run:\n"
        "`python lab/trigger/pipeline_trigger.py --bucket " + BUCKET + "`"
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Sigma Intelligence Platform · "
    f"Reading from s3://{BUCKET} · "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
