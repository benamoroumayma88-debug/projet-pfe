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

import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
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
#  Incremental ETL helpers
# ──────────────────────────────────────────────

def _table_exists(conn, schema: str, table: str) -> bool:
    """Check if a table exists in the given schema."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1
            FROM sys.tables t
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = ?
            """,
            (schema, table),
        )
        return cur.fetchone() is not None
    finally:
        cur.close()


def _get_existing_ids(conn, schema: str, table: str, id_col: str) -> set:
    """Return the set of existing IDs from a table. Empty set if table missing."""
    if not _table_exists(conn, schema, table):
        return set()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT [{id_col}] FROM [{schema}].[{table}]")
        return {row[0] for row in cur.fetchall() if row[0] is not None}
    finally:
        cur.close()


def _normalize_id_set(ids) -> set:
    """Normalize an iterable of IDs to uppercase trimmed strings for set comparison."""
    return {str(x).strip().upper() for x in ids if x is not None}


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
          f"dw.dim_client={len(out['dim_client'])}, dw.dim_policy={len(out['dim_policy'])}, "
          f"dw.dim_vehicle={len(out['dim_vehicle'])}, dw.fact_claim={len(out['fact_claim'])}, "
          f"ml.ml_claim={len(out['ml_claim'])} rows")

    print("[ETL] Loading into database...")
    conn = get_connection()
    try:
        load_all(conn, out, mode="replace")
        print("[ETL] Load complete ✅")
    finally:
        conn.close()


def run_etl_incremental():
    """
    Run incremental ETL: only process new claims (not yet in dw.fact_claim
    or ml.ml_claim), then append the deltas to the DW and ML tables.

    Falls back to full ETL automatically if dw.fact_claim doesn't exist yet
    (first run / fresh install).

    Trade-offs vs --force mode:
      • Updates to existing client/policy/vehicle rows are NOT propagated.
      • Re-uploads of identical claims are silently skipped.
      • A periodic --force run is recommended for self-healing.
    """
    print("\n" + "=" * 60)
    print("  ETL PIPELINE (INCREMENTAL)")
    print("=" * 60)

    # Safety net: fresh DB or missing DW → fall back to full ETL
    conn = get_connection()
    try:
        if not _table_exists(conn, "dw", "fact_claim"):
            print("[INCREMENTAL] dw.fact_claim not found — falling back to full ETL.")
            conn.close()
            run_etl()
            return

        # Build the set of already-known claim_ids (union of DW and ML)
        existing_claim_ids = (
            _get_existing_ids(conn, "dw", "fact_claim", "claim_id")
            | _get_existing_ids(conn, "ml", "ml_claim", "claim_id")
        )
        existing_client_ids = _get_existing_ids(conn, "dw", "dim_client", "client_id")
        existing_contract_ids = _get_existing_ids(conn, "dw", "dim_policy", "contract_id")
        existing_vehicle_ids = _get_existing_ids(conn, "dw", "dim_vehicle", "vehicle_id")
        existing_date_keys = _get_existing_ids(conn, "dw", "dim_time", "date_key")
    finally:
        conn.close()

    print(
        f"[INCREMENTAL] DW state: {len(existing_claim_ids)} claims, "
        f"{len(existing_client_ids)} clients, "
        f"{len(existing_contract_ids)} policies, "
        f"{len(existing_vehicle_ids)} vehicles"
    )

    # Extract all raw data (small tables; the cost is in transform/load)
    print("[ETL] Extracting raw data from dbo tables...")
    clients = extract_table("dbo.Clients")
    policies = extract_table("dbo.Polices_Assurance")
    vehicles = extract_table("dbo.Vehicules")
    claims = extract_table("dbo.Sinistres")

    # Locate the raw claim_id column case-insensitively
    claim_id_col = next((c for c in claims.columns if c.lower() == "claim_id"), None)
    if claim_id_col is None:
        print("[INCREMENTAL] dbo.Sinistres has no Claim_ID column — falling back to full ETL.")
        run_etl()
        return

    # Find the set of NEW claim_ids
    raw_claim_ids = _normalize_id_set(claims[claim_id_col].dropna())
    existing_claim_ids_norm = _normalize_id_set(existing_claim_ids)
    new_claim_ids = raw_claim_ids - existing_claim_ids_norm

    if not new_claim_ids:
        print("[INCREMENTAL] No new claims found. Nothing to load.")
        return

    print(f"[INCREMENTAL] Found {len(new_claim_ids)} new claim(s) to process")

    # Filter raw claims to only the new ones
    mask_new = claims[claim_id_col].apply(
        lambda x: str(x).strip().upper() if pd.notna(x) else None
    ).isin(new_claim_ids)
    new_claims = claims[mask_new].copy()

    # Transform: full clients/policies/vehicles (cleaning needs full context for
    # outlier handling), filtered to only the new claims.
    print(f"[ETL] Transforming {len(new_claims)} new claim(s) + full reference data...")
    out = transform_all(clients, policies, vehicles, new_claims)

    # Filter dim outputs to exclude entities already in the DW (avoid PK violations).
    # fact_claim and ml_claim are already filtered (they're built from new_claims only).
    existing_client_ids_norm = _normalize_id_set(existing_client_ids)
    existing_contract_ids_norm = _normalize_id_set(existing_contract_ids)
    existing_vehicle_ids_norm = _normalize_id_set(existing_vehicle_ids)

    def _drop_existing(df, id_col, existing_norm):
        if df.empty or id_col not in df.columns:
            return df
        mask = df[id_col].apply(
            lambda x: str(x).strip().upper() if pd.notna(x) else None
        ).isin(existing_norm)
        return df[~mask].copy()

    out["dim_client"] = _drop_existing(out["dim_client"], "client_id", existing_client_ids_norm)
    out["dim_policy"] = _drop_existing(out["dim_policy"], "contract_id", existing_contract_ids_norm)
    out["dim_vehicle"] = _drop_existing(out["dim_vehicle"], "vehicle_id", existing_vehicle_ids_norm)

    if not out["dim_time"].empty and "date_key" in out["dim_time"].columns:
        out["dim_time"] = out["dim_time"][
            ~out["dim_time"]["date_key"].isin(existing_date_keys)
        ].copy()

    print(
        f"[INCREMENTAL] Deltas to append: "
        f"dim_client={len(out['dim_client'])}, "
        f"dim_policy={len(out['dim_policy'])}, "
        f"dim_vehicle={len(out['dim_vehicle'])}, "
        f"dim_time={len(out['dim_time'])}, "
        f"fact_claim={len(out['fact_claim'])}, "
        f"ml_claim={len(out['ml_claim'])}"
    )

    print("[ETL] Appending new rows to database...")
    conn = get_connection()
    try:
        load_all(conn, out, mode="append")
        print("[ETL] Incremental load complete ✅")
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
            # Model not trained yet — try to train it first
            print(f"[ML] {name} model not found — attempting to train...")
            train_path = module_path.replace(".predict", ".train")
            try:
                train_module = __import__(train_path, fromlist=["main"])
                train_module.main()
                print(f"[ML] {name} training complete — running predictions...")
                module = __import__(module_path, fromlist=["main"])
                module.main()
                results[name] = "✅ Trained + predicted"
                print(f"[ML] {name} predictions complete ✅")
            except Exception as train_err:
                results[name] = f"⚠️ Skipped (training failed: {train_err})"
                print(f"[ML] {name} training failed: {train_err}")
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


def run_full_pipeline_incremental(reason: str = "incremental trigger"):
    """
    Run the pipeline in incremental mode:
      • ETL: only process new claims (append to dw.* and ml.ml_claim)
      • ML : still scores ALL active claims (cannot be incremental — active
             status changes over time and every run must re-evaluate the
             full active portfolio)
    """
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print(f"  AUTO PIPELINE (INCREMENTAL) — {run_time}")
    print(f"  Reason: {reason}")
    print("=" * 60)

    start = time.time()

    # 1. Incremental ETL (auto-falls-back to full if DW doesn't exist)
    run_etl_incremental()

    # 2. ML predictions still run on full data — see docstring above
    ml_results = run_ml_predictions()

    # 3. Save fingerprint state so change detection stays consistent
    conn = get_connection()
    try:
        fingerprints = get_current_fingerprints(conn)
    finally:
        conn.close()
    save_state(fingerprints, run_time)

    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE (INCREMENTAL)")
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
        help="Force run the FULL pipeline regardless of changes (truncates and rebuilds dw.* + ml.ml_claim)"
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="Run in incremental mode: only process new claims (appends to dw.* + ml.ml_claim). "
             "Fast path used by the web upload. Falls back to full ETL if dw.fact_claim doesn't exist."
    )

    args = parser.parse_args()

    if args.incremental:
        run_full_pipeline_incremental(reason="Incremental run (--incremental flag)")
    elif args.force:
        run_full_pipeline(reason="Forced by --force flag")
    elif args.watch:
        watch_mode(interval=args.interval)
    else:
        check_and_run()
