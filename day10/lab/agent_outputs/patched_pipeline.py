# Patched by Self-Healing Agent — 2026-05-29T17:36:41.778804
# Attempts needed: 5

import duckdb
import os
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "sigma_platform.duckdb")

def run_merchant_report():
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute("SELECT * FROM silver_transactions WHERE amount > 0").fetchdf()

    total = df["amount"].sum()

    df2 = df.groupby("merchant_id").agg({"amount": "mean"}).reset_index()
    df2.columns = ["merchant_id", "avg_amount"]

    conn.close()
    print(f"Done. Total: {total:.2f}, Merchants: {len(df2)}")

    if not df2.empty:
        top = df2.iloc[df2['avg_amount'].idxmax()]["merchant_id"]
        print(f"Top merchant by avg amount: {top}")

if __name__ == "__main__":
    run_merchant_report()