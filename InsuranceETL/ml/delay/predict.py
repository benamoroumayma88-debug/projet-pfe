"""
ml/delay/predict.py
────────────────────────────────────────────────────────────────
Predict delays for active insurance claims and persist results
to SQL Server for Power BI dashboards.

Two SQL tables produced (schema: ml):
  1. claim_delay_predictions   – one row per active claim
  2. claim_delay_run_summary   – one row per prediction run

Design principles:
  • ONE decision threshold drives everything (risk levels, predicted_delayed, KPIs).
  • Risk levels are threshold-relative so there is ZERO contradiction:
        High   = prob >= threshold          → predicted_delayed = 1
        Medium = prob in [threshold*0.6, threshold)  → predicted_delayed = 0
        Low    = prob < threshold*0.6       → predicted_delayed = 0
  • The summary table derives ALL numbers from the predictions table, so a manager
    can drill down from summary → individual claims without seeing different numbers.
  • Currency: TND (Tunisian Dinar).
"""

import json
import os
import sys
import uuid
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table
from etl.db_connection import get_connection
from etl.load import load_table

# ─── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH          = "ml/delay/models/delay_prediction_model.pkl"
MODEL_METADATA_PATH = "ml/delay/models/model_metadata.pkl"
DURATION_MODEL_PATH = "ml/delay/models/duration_model.pkl"
DATA_TABLE          = "ml.ml_claim"
OUTPUT_DIR          = "ml/delay"
PREDICTIONS_SCHEMA  = "ml"
PREDICTIONS_TABLE   = "claim_delay_predictions"
SUMMARY_TABLE       = "claim_delay_run_summary"

ACTIVE_STATUSES = ["Ouvert", "En_cours", "En_cours_d_expertise"]


# ─── Period inference (data-driven) ───────────────────────────────────────
def _infer_prediction_period(active_df: pd.DataFrame) -> tuple:
    """
    Return (year, month) of the latest date_sinistre_claim in active claims.
    This makes prediction_month follow the data automatically every time
    new sinistres are injected, with no manual code changes needed.
    """
    date_col = "date_sinistre_claim"
    if date_col in active_df.columns:
        dates = pd.to_datetime(active_df[date_col], errors="coerce").dropna()
        if not dates.empty:
            latest = dates.max()
            year, month = int(latest.year), int(latest.month)
            print(
                f"[PERIOD] Prediction period auto-detected: "
                f"{latest.strftime('%B %Y')}  "
                f"(latest active claim: {latest.strftime('%Y-%m-%d')})"
            )
            return year, month
    now = datetime.now()
    print(f"[PERIOD] No date column — falling back to current month: {now.strftime('%B %Y')}")
    return int(now.year), int(now.month)

# Business constants (TND)
DELAY_COST_PER_CLAIM        = 1_200.0   # penalty + rework per delayed claim
AGENT_MONTHLY_CAPACITY      = 80        # routine claims per agent per month
PRIORITY_CAPACITY_FACTOR    = 0.5       # high-risk claims take 2x time -> half capacity
AGENT_MONTHLY_SALARY        = 3_000.0   # TND


# ─── Model loading ────────────────────────────────────────────────────────────
def load_model():
    """Load the best delay model and its metadata."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train.py first.")

    metadata = {"best_model_name": "lightgbm", "best_threshold": 0.5}
    if os.path.exists(MODEL_METADATA_PATH):
        metadata.update(joblib.load(MODEL_METADATA_PATH))

    model = joblib.load(MODEL_PATH)
    threshold = float(metadata.get("best_threshold", 0.5))
    name = metadata.get("best_model_name", "unknown")
    print(f"[LOAD] Model: {name}  |  Threshold: {threshold:.2f}")
    return model, metadata

def load_duration_model():
    """Load trained duration prediction model."""
    if os.path.exists(DURATION_MODEL_PATH):
        m = joblib.load(DURATION_MODEL_PATH)
        print(f"[LOAD] Duration model loaded")
        return m
    print("[INFO] No duration model — will estimate delay days from probability")
    return None


# ─── Data loading ─────────────────────────────────────────────────────────────
def load_claims():
    """Load only ACTIVE claims for prediction."""
    print("[LOAD] Loading claims from ml.ml_claim ...")
    df = extract_table(DATA_TABLE)
    total = len(df)
    print(f"[LOAD] {total} total rows")

    if "statut_sinistre_claim" in df.columns:
        df = df[df["statut_sinistre_claim"].isin(ACTIVE_STATUSES)].copy()
        if df.empty:
            raise ValueError("No active claims found. Check data or status values.")
        print(f"[FILTER] {len(df)} active claims  |  {total - len(df)} closed (excluded)")
    else:
        print("[WARNING] Status column missing — using all claims")

    return df


# ─── Feature preparation ─────────────────────────────────────────────────────
DROP_COLS = [
    "claim_id", "client_id", "contract_id", "vehicle_id",
    "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
    "is_delayed", "duree_traitement_jours",
]


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors="ignore")


# ─── Prediction engine ───────────────────────────────────────────────────────
def predict_delays(model, duration_model, df, threshold):
    """
    Score every active claim and add four coherent prediction columns:

      delay_probability         float  [0, 1]
      predicted_delayed         int    0 or 1  (ALWAYS = prob >= threshold)
      risk_level                str    High / Medium / Low  — derived FROM threshold
      predicted_excess_days     int    Estimated extra days beyond SLA if delayed
    """
    X = _prepare_features(df)
    proba = model.predict_proba(X)[:, 1].astype(float)

    out = df.copy()
    out["delay_probability"] = proba

    # ── Binary decision (the SINGLE source of truth) ──────────
    out["predicted_delayed"] = (proba >= threshold).astype(int)

    # ── Risk level derived FROM the threshold ─────────────────
    #   High     = prob >= threshold                  (WILL be delayed)
    #   Medium   = prob >= threshold * 0.6 AND < threshold  (borderline — watch zone)
    #   Low      = prob <  threshold * 0.6            (likely on time)
    #
    # Guarantee:
    #   • Every High  → predicted_delayed = 1
    #   • Every Medium → predicted_delayed = 0
    #   • Every Low    → predicted_delayed = 0
    mid_boundary = threshold * 0.6
    conditions = [
        proba >= threshold,
        proba >= mid_boundary,
    ]
    choices = ["High", "Medium"]
    out["risk_level"] = np.select(conditions, choices, default="Low")

    # ── Estimated excess days beyond SLA ──────────────────────
    if duration_model is not None:
        out["predicted_excess_days"] = 0
        mask = out["predicted_delayed"] == 1
        if mask.sum() > 0:
            X_high = X[mask]
            try:
                pred_days = np.expm1(duration_model.predict(X_high))
                pred_days = np.clip(np.rint(pred_days), 1, 120).astype(int)
                out.loc[mask, "predicted_excess_days"] = pred_days
            except Exception as e:
                print(f"[WARNING] Duration model predict failed ({e}); using dynamic fallback")
                duration_model = None  # trigger fallback below
        out["predicted_excess_days"] = out["predicted_excess_days"].fillna(0).astype(int)
    if duration_model is None:
        # Dynamic fallback: estimate excess delay days from probability + SLA context
        sla = pd.to_numeric(out.get("sla_jours", pd.Series(20, index=out.index)), errors="coerce").fillna(20)
        excess = (np.maximum(proba - threshold, 0) * (sla.values * 1.5 + 15)).round()
        excess = np.clip(excess, 1, 90)
        out["predicted_excess_days"] = np.where(
            out["predicted_delayed"] == 1, excess.astype(int), 0
        )

    print(f"[PREDICT] {len(out)} claims scored")
    print(f"  predicted_delayed=1 : {int(out['predicted_delayed'].sum())}")
    print(f"  risk_level : {out['risk_level'].value_counts().to_dict()}")
    return out

# ─── Build SQL payloads ──────────────────────────────────────────────────────

def _find_amount_col(df):
    for c in ["montant_indemnisation_claim", "montant_estime_dommage_claim"]:
        if c in df.columns:
            return c
    return None


def build_prediction_records(predictions_df, threshold, metadata):
    """Build the per-claim DataFrame for ml.claim_delay_predictions."""
    run_id    = datetime.now().strftime("RUN-%Y%m%d-%H%M%S")
    scored_at = datetime.now()
    amt_col   = _find_amount_col(predictions_df)

    rec = predictions_df.copy()

    # Cost at risk per claim = amount * probability (expected loss from delay)
    if amt_col:
        amount = pd.to_numeric(rec[amt_col], errors="coerce").fillna(0.0)
    else:
        amount = pd.Series(0.0, index=rec.index)
    rec["delay_cost_at_risk_tnd"] = np.where(
        rec["predicted_delayed"] == 1,
        (amount * rec["delay_probability"]).round(2),
        0.0,
    )

    # Select dashboard-friendly columns
    base = [
        "claim_id", "client_id", "contract_id", "vehicle_id",
        "date_sinistre_claim", "statut_sinistre_claim",
        "type_sinistre_claim", "type_couverture",
        "sla_jours",
    ]
    if amt_col:
        base.append(amt_col)

    pred = [
        "delay_probability", "predicted_delayed", "risk_level",
        "predicted_excess_days", "delay_cost_at_risk_tnd",
    ]

    keep = [c for c in base + pred if c in rec.columns]
    rec = rec[keep].copy()

    # Add run metadata
    rec.insert(0, "prediction_record_id", [str(uuid.uuid4()) for _ in range(len(rec))])
    rec.insert(1, "prediction_run_id", run_id)
    rec.insert(2, "scored_at", scored_at)
    rec["decision_threshold"] = threshold
    rec["model_name"] = metadata.get("best_model_name", "unknown")

    # Ensure clean types for SQL
    rec["risk_level"] = rec["risk_level"].astype(str)
    rec["predicted_delayed"] = rec["predicted_delayed"].astype(int)
    rec["predicted_excess_days"] = rec["predicted_excess_days"].astype(int)

    return rec, run_id, scored_at


def _add_prediction_month(rec_df: pd.DataFrame, prediction_month: int) -> pd.DataFrame:
    """Append prediction_month column so Power BI can filter/slicer by month."""
    rec_df = rec_df.copy()
    rec_df["prediction_month"] = prediction_month
    return rec_df


def build_run_summary(run_id, scored_at, predictions_df, threshold, metadata):
    """
    Build a single-row summary DataFrame.
    EVERY number here is derived from the predictions table
    so there is ZERO ambiguity when a manager cross-checks.
    """
    total   = len(predictions_df)
    delayed = predictions_df["predicted_delayed"]
    proba   = predictions_df["delay_probability"]
    risk    = predictions_df["risk_level"]
    excess  = predictions_df["predicted_excess_days"]
    amt_col = _find_amount_col(predictions_df)

    n_delayed    = int(delayed.sum())
    n_on_time    = total - n_delayed
    delay_rate   = round(n_delayed / max(total, 1) * 100, 1)

    n_high       = int((risk == "High").sum())
    n_medium     = int((risk == "Medium").sum())
    n_low        = int((risk == "Low").sum())

    # Excess days stats (only among delayed claims)
    delayed_excess = excess[delayed == 1]
    total_excess_days = int(delayed_excess.sum())
    avg_excess_days   = round(float(delayed_excess.mean()), 1) if len(delayed_excess) > 0 else 0.0

    # Cost impact
    if amt_col and amt_col in predictions_df.columns:
        amount = pd.to_numeric(predictions_df[amt_col], errors="coerce").fillna(0.0)
        cost_at_risk = float((amount[delayed == 1] * proba[delayed == 1]).sum())
        total_amount_delayed = float(amount[delayed == 1].sum())
    else:
        cost_at_risk = 0.0
        total_amount_delayed = 0.0

    total_delay_penalty = n_delayed * DELAY_COST_PER_CLAIM

    # Staffing recommendation
    high_workload  = n_high / (AGENT_MONTHLY_CAPACITY * PRIORITY_CAPACITY_FACTOR)
    rest_workload  = (n_medium + n_low) / AGENT_MONTHLY_CAPACITY
    recommended_agents = max(1, int(np.ceil(high_workload + rest_workload)))
    staffing_cost = recommended_agents * AGENT_MONTHLY_SALARY

    # Probability statistics (for transparency)
    avg_proba = round(float(proba.mean()), 4)
    max_proba = round(float(proba.max()), 4)

    row = {
        "summary_record_id":            str(uuid.uuid4()),
        "prediction_run_id":            run_id,
        "scored_at":                    scored_at,
        "model_name":                   metadata.get("best_model_name", "unknown"),
        "decision_threshold":           threshold,

        # Portfolio overview
        "total_active_claims":          total,
        "predicted_delayed_count":      n_delayed,
        "predicted_on_time_count":      n_on_time,
        "predicted_delay_rate_pct":     delay_rate,

        # Risk distribution (matches exactly with predictions table)
        "high_risk_count":              n_high,
        "medium_risk_count":            n_medium,
        "low_risk_count":               n_low,

        # Delay duration
        "total_excess_days":            total_excess_days,
        "avg_excess_days_per_delayed":  avg_excess_days,

        # Financial impact (TND)
        "total_amount_at_risk_tnd":     round(total_amount_delayed, 2),
        "cost_at_risk_tnd":             round(cost_at_risk, 2),
        "estimated_delay_penalty_tnd":  round(total_delay_penalty, 2),

        # Staffing
        "recommended_agents":           recommended_agents,
        "staffing_cost_tnd":            round(staffing_cost, 2),

        # Probability transparency
        "avg_delay_probability":        avg_proba,
        "max_delay_probability":        max_proba,
        "projection_month":             0,  # filled by caller
    }
    return pd.DataFrame([row])


# ─── SQL persistence ─────────────────────────────────────────────────────────
def save_to_database(predictions_df, threshold, metadata, pred_month: int):
    """Persist predictions + summary to SQL Server (replace mode — one run at a time)."""
    rec_df, run_id, scored_at = build_prediction_records(predictions_df, threshold, metadata)
    rec_df = _add_prediction_month(rec_df, pred_month)

    summary_df = build_run_summary(run_id, scored_at, predictions_df, threshold, metadata)
    summary_df["projection_month"] = pred_month

    conn = get_connection()
    try:
        load_table(conn, PREDICTIONS_SCHEMA, PREDICTIONS_TABLE, rec_df, mode="replace")
        print(f"[SQL] {PREDICTIONS_SCHEMA}.{PREDICTIONS_TABLE} <- {len(rec_df)} rows  (replaced)")

        load_table(conn, PREDICTIONS_SCHEMA, SUMMARY_TABLE, summary_df, mode="replace")
        print(f"[SQL] {PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} <- 1 row  [run_id={run_id}]  (replaced)")
    finally:
        conn.close()

    return run_id, scored_at, summary_df


# ─── Dashboard JSON ──────────────────────────────────────────────────────────
def save_dashboard_json(predictions_df, summary_df):
    """Save dashboard insights JSON for Power BI or frontend consumption."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    s = summary_df.iloc[0].to_dict()

    risk_dist = predictions_df["risk_level"].value_counts().to_dict()

    top_high = (
        predictions_df[predictions_df["risk_level"] == "High"]
        .nlargest(15, "delay_probability")
    )
    top_cols = [c for c in [
        "claim_id", "delay_probability", "predicted_excess_days",
        "delay_cost_at_risk_tnd", "type_sinistre_claim", "sla_jours",
    ] if c in top_high.columns]

    dashboard = {
        "run_timestamp":      str(s.get("scored_at", "")),
        "model_name":         s.get("model_name"),
        "decision_threshold": s.get("decision_threshold"),
        "currency":           "TND",
        "summary": {
            "total_active_claims":        s.get("total_active_claims"),
            "predicted_delayed_count":    s.get("predicted_delayed_count"),
            "predicted_on_time_count":    s.get("predicted_on_time_count"),
            "predicted_delay_rate_pct":   s.get("predicted_delay_rate_pct"),
            "high_risk_count":            s.get("high_risk_count"),
            "medium_risk_count":          s.get("medium_risk_count"),
            "low_risk_count":             s.get("low_risk_count"),
            "total_excess_days":          s.get("total_excess_days"),
            "avg_excess_days_per_delayed": s.get("avg_excess_days_per_delayed"),
            "total_amount_at_risk_tnd":   s.get("total_amount_at_risk_tnd"),
            "cost_at_risk_tnd":           s.get("cost_at_risk_tnd"),
            "estimated_delay_penalty_tnd": s.get("estimated_delay_penalty_tnd"),
            "recommended_agents":         s.get("recommended_agents"),
            "staffing_cost_tnd":          s.get("staffing_cost_tnd"),
        },
        "risk_distribution":    risk_dist,
        "top_high_risk_claims": top_high[top_cols].to_dict("records") if not top_high.empty else [],
    }

    path = os.path.join(OUTPUT_DIR, "dashboard_insights.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, default=str)
    print(f"[SAVE] {path}")


# ─── Console report ──────────────────────────────────────────────────────────
def print_report(summary_df, prediction_year: int = 0, prediction_month: int = 0):
    """Print a clean, coherent summary report to console."""
    s = summary_df.iloc[0]
    W = 70
    month_label = (
        datetime(year=prediction_year, month=prediction_month, day=1).strftime("%B %Y")
        if prediction_year and prediction_month
        else "N/A"
    )
    print("\n" + "=" * W)
    print("  DELAY PREDICTION - RUN SUMMARY")
    print("=" * W)
    print(f"  Prediction period: {month_label}  (auto-detected from data)")
    print(f"  Model            : {s['model_name']}")
    print(f"  Threshold        : {s['decision_threshold']:.2f}")
    print(f"  Active claims    : {s['total_active_claims']}")
    print("-" * W)
    print(f"  Predicted delayed     : {s['predicted_delayed_count']}  ({s['predicted_delay_rate_pct']}%)")
    print(f"  Predicted on time     : {s['predicted_on_time_count']}")
    print(f"  High risk  (= delayed): {s['high_risk_count']}")
    print(f"  Medium risk (watchlist): {s['medium_risk_count']}")
    print(f"  Low risk   (on track) : {s['low_risk_count']}")
    print("-" * W)
    print(f"  Total excess days     : {s['total_excess_days']} days")
    print(f"  Avg excess / delayed  : {s['avg_excess_days_per_delayed']} days")
    print("-" * W)
    print(f"  Amount at risk        : {s['total_amount_at_risk_tnd']:,.0f} TND")
    print(f"  Cost at risk (prob.)  : {s['cost_at_risk_tnd']:,.0f} TND")
    print(f"  Delay penalty (est.)  : {s['estimated_delay_penalty_tnd']:,.0f} TND")
    print("-" * W)
    print(f"  Recommended agents    : {s['recommended_agents']}")
    print(f"  Staffing cost         : {s['staffing_cost_tnd']:,.0f} TND")
    print("-" * W)
    print(f"  Avg probability       : {s['avg_delay_probability']:.4f}")
    print(f"  Max probability       : {s['max_delay_probability']:.4f}")
    print("=" * W)

    # Coherence verification
    assert s["high_risk_count"] == s["predicted_delayed_count"], \
        "BUG: high_risk_count must equal predicted_delayed_count"
    assert s["high_risk_count"] + s["medium_risk_count"] + s["low_risk_count"] == s["total_active_claims"], \
        "BUG: risk counts must sum to total_active_claims"
    print("  Coherence check passed: all numbers consistent\n")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    """Main prediction pipeline."""
    print("=" * 65)
    print("  DELAY PREDICTION & DASHBOARD GENERATION")
    print("=" * 65 + "\n")

    model, metadata = load_model()
    threshold = float(metadata.get("best_threshold", 0.5))
    duration_model = load_duration_model()
    claims_df = load_claims()

    # Auto-detect prediction period from the data (no clock-based month offset)
    pred_year, pred_month = _infer_prediction_period(claims_df)

    predictions_df = predict_delays(model, duration_model, claims_df, threshold)

    run_id, scored_at, summary_df = save_to_database(predictions_df, threshold, metadata, pred_month)

    save_dashboard_json(predictions_df, summary_df)
    print_report(summary_df, prediction_year=pred_year, prediction_month=pred_month)

    print("[DONE] Delay prediction complete.")


if __name__ == "__main__":
    main()
