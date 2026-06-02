import os
import boto3
import json
import subprocess
import snowflake.connector
from datetime import datetime

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return False, str(e)

def run_normal_pipeline():
    """Generates 500 clean records and loads them to simulate normal state."""
    return run_command("../venv/bin/python lab/data_generator.py --mode clean --records 500")

def inject_disaster():
    """Injects a failure into the pipeline."""
    return run_command("../venv/bin/python lab/disaster/inject_failure.py")

def get_snowflake_metrics():
    """Queries Snowflake for real metrics."""
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SIGMA"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "SILVER")
        )
        cur = conn.cursor()
        
        # Get total rows
        cur.execute("SELECT COUNT(*) FROM TRANSACTIONS")
        total_rows = cur.fetchone()[0]
        
        # Get total GMV
        cur.execute("SELECT SUM(AMOUNT) FROM TRANSACTIONS WHERE AMOUNT > 0")
        total_gmv = cur.fetchone()[0] or 0
        
        conn.close()
        return {"total_transactions": total_rows, "total_gmv": total_gmv, "status": "success"}
    except Exception as e:
        return {"total_transactions": 0, "total_gmv": 0, "status": "error", "message": str(e)}

def get_s3_reports():
    """Fetches incident reports from S3."""
    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        bucket = os.getenv("SIGMA_S3_BUCKET")
        if not bucket:
            return []
            
        resp = s3.list_objects_v2(Bucket=bucket, Prefix="reports/")
        objects = [o for o in resp.get("Contents", []) if not o["Key"].endswith("/")]
        objects.sort(key=lambda x: x["LastModified"], reverse=True)
        return objects
    except Exception:
        return []

def get_s3_report_content(key):
    """Fetches a specific report from S3."""
    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        bucket = os.getenv("SIGMA_S3_BUCKET")
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read().decode("utf-8")
    except Exception:
        return ""

def get_s3_quarantine_data():
    """Fetches quarantine data from S3."""
    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        bucket = os.getenv("SIGMA_S3_BUCKET")
        if not bucket:
            return []
            
        resp = s3.list_objects_v2(Bucket=bucket, Prefix="tmp/quarantine_records.json")
        objects = [o for o in resp.get("Contents", []) if not o["Key"].endswith("/")]
        
        if not objects:
            return []
            
        obj = s3.get_object(Bucket=bucket, Key=objects[0]["Key"])
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return data
    except Exception:
        return []

def get_cloudwatch_alarms():
    """Fetches the state of CloudWatch alarms."""
    try:
        cw = boto3.client('cloudwatch', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        response = cw.describe_alarms()
        alarms = []
        for a in response.get('MetricAlarms', []):
            if a['AlarmName'].startswith('sigma-'):
                alarms.append({
                    "name": a['AlarmName'],
                    "status": a['StateValue']
                })
        return alarms
    except Exception:
        return []
