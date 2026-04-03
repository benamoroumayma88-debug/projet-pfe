"""
auto_pipeline.py
────────────────────────────────────────────────────────────
Automatic pipeline that detects changes in raw dbo.* tables
and re-runs ETL + ML predictions so dashboards stay current.

How it works:
  1. Computes a fingerprint (row count + checksum) of each dbo.* table
  2. Compares against last known fingerprint stored in .pipeline_state.json
  3. If ANY table changed → runs full ETL + all 4 ML predict pipelines
  4. Saves new fingerprint for next run

Usage:
  # One-shot check + run if needed:
  python auto_pipeline.py

  # Watch mode — poll every N seconds (default 60):
  python auto_pipeline.py --watch
  python auto_pipeline.py --watch --interval 120

  # Force run (skip change detection):
  python auto_pipeline.py --force

This script does NOT modify any existing file.
It only imports and calls existing functions.
────────────────────────────────────────────────────────────
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connection import get_connection
from etl.extract import extract_table
from etl.transform import transform_all
from etl.load import load_all

STATE_FILE = os.path.join(PROJECT_ROOT, ".pipeline_state.json")

# The raw tables to monitor for changes
MONITORED_TABLES = [
    "dbo.Clients",
    "dbo.Polices_Assurance",
    "dbo.Vehicules",
    "dbo.Sinistres",
    "dbo.addon_sinistres",
]


# ──────────────────────────────────────────────
#  Change detection
# ──────────────────────────────────────────────

def _table_fingerprint(conn, table_name: str) -> str:
    """
    Build a lightweight fingerprint of a table using row count
    and a checksum of the first ID column + row count.
    Fast and avoids reading the full table.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name.split('.')[-1]}]")
        row_count = cursor.fetchone()[0]

        # Use CHECKSUM_AGG for a fast content hash
        cursor.execute(
            f"SELECT CHECKSUM_AGG(CHECKSUM(*)) FROM [{table_name.split('.')[-1]}]"
        )
        checksum = cursor.fetchone()[0]
        checksum = checksum if checksum is not None else 0

        return f"{row_count}:{checksum}"
    except Exception:
        # Table might not exist yet
        return "0:0"
    finally:
        cursor.close()


def get_current_fingerprints(conn) -> dict:
    """Get fingerprints for all monitored tables."""
    fingerprints = {}
    for table in MONITORED_TABLES:
        fingerprints[table] = _table_fingerprint(conn, table)
    return fingerprints


def load_saved_state() -> dict:
    """Load the last saved pipeline state from disk."""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(fingerprints: dict, run_time: str):
    """Save the current fingerprints + run timestamp."""
    state = {
        "fingerprints": fingerprints,
        "last_run": run_time,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def detect_changes(conn) -> tuple[bool, list[str]]:
    """
    Compare current table fingerprints with saved state.
    Returns (has_changes, list_of_changed_tables).
    """
    current = get_current_fingerprints(conn)
    saved = load_saved_state().get("fingerprints", {})

    changed = []
    for table, fp in current.items():
        old_fp = saved.get(table, "")
        if fp != old_fp:
            changed.append(table)

    return len(changed) > 0, changed


# ──────────────────────────────────────────────
#  Pipeline execution
# ──────────────────────────────────────────────

def run_etl():
    """Run the full ETL pipeline: extract → transform → load."""
    print("\n" + "=" * 60)
    print("  ETL PIPELINE")
    print("=" * 60)

    print("[ETL] Extracting raw data from dbo tables...")
    clients = extract_table("dbo.Clients")
    policies = extract_table("dbo.Polices_Assurance")
    vehicles = extract_table("dbo.Vehicules")
    claims = extract_table("dbo.Sinistres")

    print(f"[ETL] Extracted: {len(clients)} clients, {len(policies)} policies, "
          f"{len(vehicles)} vehicles, {len(claims)} claims")

    print("[ETL] Transforming...")
    out = transform_all(clients, policies, vehicles, claims)

    print(f"[ETL] Transform complete: "
          f"stg={len(out['clean_clients'])}+{len(out['clean_policies'])}+"
          f"{len(out['clean_vehicles'])}+{len(out['clean_claims'])} rows, "
          f"dw.fact_claim={len(out['fact_claim'])} rows, "
          f"ml.ml_claim={len(out['ml_claim'])} rows")

    print("[ETL] Loading into database...")
    conn = get_connection()
    try:
        load_all(conn, out, mode="replace")
        print("[ETL] Load complete ✅")
    finally:
        conn.close()


def run_ml_predictions():
    """Run all 4 ML prediction pipelines."""
    print("\n" + "=" * 60)
    print("  ML PREDICTIONS")
    print("=" * 60)

    pipelines = [
        ("Delay",    "ml.delay.predict"),
        ("Cost",     "ml.cost.predict"),
        ("Fraud",    "ml.fraud.predict"),
        ("Forecast", "ml.forecast.predict"),
    ]

    results = {}
    for name, module_path in pipelines:
        print(f"\n[ML] Running {name} predictions...")
        try:
            # Import and call main() from each predict module
            module = __import__(module_path, fromlist=["main"])
            module.main()
            results[name] = "✅ Success"
            print(f"[ML] {name} predictions complete ✅")
        except FileNotFoundError as e:
            # Model not trained yet — skip gracefully
            results[name] = f"⚠️ Skipped (model not trained: {e})"
            print(f"[ML] {name} skipped — {e}")
        except Exception as e:
            results[name] = f"❌ Failed: {e}"
            print(f"[ML] {name} FAILED: {e}")
            traceback.print_exc()

    return results


def run_full_pipeline(reason: str = "manual trigger"):
    """Run the complete pipeline: ETL + ML predictions."""
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print(f"  AUTO PIPELINE — {run_time}")
    print(f"  Reason: {reason}")
    print("=" * 60)

    start = time.time()

    # 1. ETL
    run_etl()

    # 2. ML Predictions
    ml_results = run_ml_predictions()

    # 3. Save new fingerprint state
    conn = get_connection()
    try:
        fingerprints = get_current_fingerprints(conn)
    finally:
        conn.close()
    save_state(fingerprints, run_time)

    elapsed = time.time() - start

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  ML Results:")
    for name, status in ml_results.items():
        print(f"    {name}: {status}")
    print(f"  State saved to: {STATE_FILE}")
    print(f"  Dashboards are now up to date.")
    print("=" * 60 + "\n")


# ──────────────────────────────────────────────
#  Entry points
# ──────────────────────────────────────────────

def check_and_run():
    """Check for data changes and run pipeline if needed."""
    conn = get_connection()
    try:
        has_changes, changed_tables = detect_changes(conn)
    finally:
        conn.close()

    if has_changes:
        print(f"[DETECT] Changes found in: {', '.join(changed_tables)}")
        run_full_pipeline(reason=f"Data changed in: {', '.join(changed_tables)}")
        return True
    else:
        print(f"[DETECT] No changes detected. Dashboards are current.")
        return False


def watch_mode(interval: int = 60):
    """Poll for changes every `interval` seconds."""
    print(f"[WATCH] Monitoring for data changes every {interval}s...")
    print(f"[WATCH] Press Ctrl+C to stop.\n")

    try:
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Checking for changes...", end=" ")
            ran = check_and_run()
            if not ran:
                print(f"Next check in {interval}s.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto-pipeline: detect data changes → ETL → ML → dashboard update"
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Run in watch mode (poll for changes continuously)"
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Polling interval in seconds for watch mode (default: 60)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force run the pipeline regardless of changes"
    )

    args = parser.parse_args()

    if args.force:
        run_full_pipeline(reason="Forced by --force flag")
    elif args.watch:
        watch_mode(interval=args.interval)
    else:
        check_and_run()
