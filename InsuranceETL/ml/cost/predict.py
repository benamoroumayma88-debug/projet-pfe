"""
ml/cost/predict.py
────────────────────────────────────────────────────────────────
Predict indemnisation amount per active claim, then break it down
by claim type, coverage type and severity tier — giving finance teams
a rich, actionable budget picture rather than a single lump sum.

Per-claim output
─────────────────
  predicted_cost             – predicted indemnisation (TND), stored in SQL
  cost_risk_level            – Low / Medium / High  (3-tier)

Analytical breakdowns (printed + saved to CSV, not to SQL schema)
──────────────────────────────────────────────────────────────────
  • By type_sinistre_claim   – total / count / avg / % of budget per claim type
  • By type_couverture       – total / count / avg / % of budget per coverage type
  • By claim_severity_bucket – distribution across severity bands

Summary KPIs (SQL claim_cost_run_summary)
──────────────────────────────────────────
  total_predicted_cost            – total indemnisation exposure TND
  average_cost_per_claim          – average per active claim
  historical_avg_per_claim_tnd    – avg indemnisation of closed claims (historical)
  high_cost_rate                  – fraction of claims in High tier
  budget_deviation_risk           – % deviation of predicted total vs historical baseline
  (+ recovery_reserve printed to console: 15 % buffer over total)

Currency: TND (Tunisian Dinar).
"""

import json
import uuid
import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from etl.extract import extract_table
from etl.db_connection import get_connection
from etl.load import load_table

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL_PATH         = "ml/cost/models/cost_prediction_model.pkl"
DATA_TABLE         = "ml.ml_claim"
OUTPUT_DIR         = "ml/cost"
PREDICTIONS_SCHEMA = "ml"
PREDICTIONS_TABLE  = "claim_cost_predictions"
SUMMARY_TABLE      = "claim_cost_run_summary"

ACTIVE_STATUSES = ["Ouvert", "En_cours", "En_cours_d_expertise"]

# 3-tier risk thresholds (TND)
TIER_LOW    =  5_000.0   # < 5 000 TND          → Low
TIER_MEDIUM = 15_000.0   # 5 000 – 15 000 TND   → Medium
#                          > 15 000 TND          → High

COST_THRESHOLD        = TIER_MEDIUM   # kept for SQL column compatibility
RECOVERY_RESERVE_RATE = 0.15          # 15 % buffer over predicted total


# ── Period inference (data-driven, no hardcoding) ──────────────────────────────
def _infer_prediction_period(active_df: pd.DataFrame) -> tuple:
    """
    Derive (year, month) from the latest date_sinistre_claim in active claims.
    Falls back to the current calendar month if the column is missing / empty.
    This means prediction_month always matches the most recently injected data.
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


# ── Model loading ──────────────────────────────────────────────────────────────
def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train.py first.")
    model = joblib.load(MODEL_PATH)
    print(f"[LOAD] Cost model loaded from {MODEL_PATH}")
    return model


# ── Data loading ───────────────────────────────────────────────────────────────
def load_claims_data():
    print("[LOAD] Loading claims from ml.ml_claim …")
    df = extract_table(DATA_TABLE)
    total = len(df)
    print(f"[LOAD] {total} total rows")
    if "statut_sinistre_claim" in df.columns:
        df = df[df["statut_sinistre_claim"].isin(ACTIVE_STATUSES)].copy()
        print(f"[FILTER] {len(df)} active claims  |  {total - len(df)} closed (excluded)")
    else:
        print("[WARNING] Status column missing – using all rows")
    if df.empty:
        raise ValueError("No active claims found. Check data or status values.")
    return df


# ── Feature preparation ────────────────────────────────────────────────────────
_DROP_FOR_MODEL = [
    "claim_id", "client_id", "contract_id", "vehicle_id",
    "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
    "montant_indemnisation_claim", "montant_estime_dommage_claim",
    "montant_indemnisation", "montant_estime", "claim_cost",
]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in _DROP_FOR_MODEL if c in df.columns], errors="ignore")


# ── Prediction engine ──────────────────────────────────────────────────────────
def predict_costs(model, df: pd.DataFrame) -> pd.DataFrame:
    """
    Score every active claim and add:
      predicted_cost     – TND amount Astrée is expected to pay
      cost_risk_level    – Low / Medium / High
    """
    X = prepare_features(df)
    raw_preds = model.predict(X)
    out = df.copy()
    out["predicted_cost"] = np.maximum(raw_preds, 0.0)

    conditions = [
        out["predicted_cost"] < TIER_LOW,
        out["predicted_cost"] < TIER_MEDIUM,
    ]
    choices = ["Low", "Medium"]
    out["cost_risk_level"] = np.select(conditions, choices, default="High")

    print(f"[PREDICT] {len(out)} claims scored")
    tier_counts = out["cost_risk_level"].value_counts().to_dict()
    for tier in ["High", "Medium", "Low"]:
        print(f"  {tier:<10} {tier_counts.get(tier, 0):>5} claims")
    return out


# ── Analytical breakdowns ──────────────────────────────────────────────────────
def _breakdown(df: pd.DataFrame, group_col: str, label: str) -> pd.DataFrame:
    """Aggregate predicted_cost by a categorical column."""
    if group_col not in df.columns:
        return pd.DataFrame()
    total_budget = df["predicted_cost"].sum()
    grp = (
        df.groupby(group_col)["predicted_cost"]
        .agg(claim_count="count", total_indemnisation_tnd="sum", avg_indemnisation_tnd="mean")
        .reset_index()
    )
    grp.rename(columns={group_col: label}, inplace=True)
    grp["pct_of_total_budget"] = (
        (grp["total_indemnisation_tnd"] / max(total_budget, 1)) * 100
    ).round(1)
    grp["avg_indemnisation_tnd"] = grp["avg_indemnisation_tnd"].round(2)
    grp["total_indemnisation_tnd"] = grp["total_indemnisation_tnd"].round(2)
    grp.sort_values("total_indemnisation_tnd", ascending=False, inplace=True)
    return grp.reset_index(drop=True)


def compute_breakdowns(preds: pd.DataFrame) -> dict:
    by_type     = _breakdown(preds, "type_sinistre_claim", "claim_type")
    by_coverage = _breakdown(preds, "type_couverture",     "coverage_type")
    by_severity = _breakdown(preds, "claim_severity_bucket", "severity_bucket")
    return {
        "by_claim_type":    by_type,
        "by_coverage_type": by_coverage,
        "by_severity":      by_severity,
    }


# ── KPI computation ────────────────────────────────────────────────────────────
def calculate_kpis(preds: pd.DataFrame, breakdowns: dict) -> dict:
    total    = float(preds["predicted_cost"].sum())
    count    = len(preds)
    avg_cost = total / count if count > 0 else 0.0

    # High tier only (no Critical any more)
    high_cost_rate = float(
        (preds["cost_risk_level"] == "High").mean()
    ) if count > 0 else 0.0

    recovery_reserve = total * RECOVERY_RESERVE_RATE

    # ── Historical baseline from closed claims ────────────────────
    hist_df = extract_table(DATA_TABLE)
    if "statut_sinistre_claim" in hist_df.columns:
        closed = hist_df[~hist_df["statut_sinistre_claim"].isin(ACTIVE_STATUSES)]
    else:
        closed = hist_df

    hist_col = next(
        (c for c in ["claim_cost", "montant_indemnisation_claim", "montant_estime_dommage_claim"]
         if c in closed.columns),
        None,
    )
    hist_avg = (
        pd.to_numeric(closed[hist_col], errors="coerce").mean()
        if hist_col else np.nan
    )

    # budget deviation: (predicted_total - historical_total_if_same_count) / historical_total
    budget_deviation = (
        (total - hist_avg * count) / (hist_avg * count)
        if pd.notna(hist_avg) and count > 0 else np.nan
    )

    # Top items from breakdowns
    top_type     = "N/A"
    top_coverage = "N/A"
    if not breakdowns["by_claim_type"].empty:
        top_type = str(breakdowns["by_claim_type"].iloc[0]["claim_type"])
    if not breakdowns["by_coverage_type"].empty:
        top_coverage = str(breakdowns["by_coverage_type"].iloc[0]["coverage_type"])

    return {
        "total_predicted_indemnisation_tnd":  total,
        "average_cost_per_claim":             avg_cost,
        "historical_avg_per_claim_tnd":       float(hist_avg) if pd.notna(hist_avg) else np.nan,
        "high_cost_rate":                     high_cost_rate,
        "recovery_reserve_tnd":               recovery_reserve,
        "budget_deviation_risk":              budget_deviation,
        "top_claim_type_by_cost":             top_type,
        "top_coverage_type_by_cost":          top_coverage,
        # alias for SQL column name
        "estimated_monthly_budget":           total,
    }


# ── CSV save ───────────────────────────────────────────────────────────────────
def save_predictions(preds: pd.DataFrame, breakdowns: dict) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    preds_path = os.path.join(OUTPUT_DIR, "predictions.csv")
    preds.to_csv(preds_path, index=False)
    print(f"[SAVE] Per-claim predictions  → {preds_path}")

    for key, df_bd in breakdowns.items():
        if not df_bd.empty:
            path = os.path.join(OUTPUT_DIR, f"breakdown_{key}.csv")
            df_bd.to_csv(path, index=False)
            print(f"[SAVE] Breakdown ({key}) → {path}")


# ── SQL persistence ────────────────────────────────────────────────────────────
def build_prediction_records(
    predictions_df: pd.DataFrame,
    run_id: str,
    scored_at: datetime,
    prediction_month: int,
) -> pd.DataFrame:
    base_cols = [
        "claim_id", "client_id", "contract_id", "vehicle_id",
        "date_sinistre_claim", "statut_sinistre_claim",
        "type_sinistre_claim", "type_couverture", "claim_severity_bucket",
    ]
    pred_cols = ["predicted_cost", "cost_risk_level"]
    keep = [c for c in base_cols + pred_cols if c in predictions_df.columns]
    rec = predictions_df[keep].copy()

    rec.insert(0, "prediction_record_id", [str(uuid.uuid4()) for _ in range(len(rec))])
    rec.insert(1, "prediction_run_id", run_id)
    rec.insert(2, "scored_at", scored_at)
    rec["prediction_month"] = prediction_month

    for col in ["statut_sinistre_claim", "type_sinistre_claim", "type_couverture",
                "claim_severity_bucket", "cost_risk_level"]:
        if col in rec.columns:
            rec[col] = rec[col].astype(str)

    return rec


def build_summary_record(
    run_id: str,
    scored_at: datetime,
    kpis: dict,
    total_claims: int,
    prediction_month: int,
) -> pd.DataFrame:
    return pd.DataFrame([{
        "summary_record_id":      str(uuid.uuid4()),
        "prediction_run_id":      run_id,
        "scored_at":              scored_at,
        "total_active_claims":    int(total_claims),
        "total_predicted_cost":   float(kpis.get("total_predicted_indemnisation_tnd", 0.0)),
        "average_cost_per_claim": float(kpis.get("average_cost_per_claim", 0.0)),
        "high_cost_rate":         float(kpis.get("high_cost_rate", 0.0)),
        "budget_deviation_risk":  float(
            kpis.get("budget_deviation_risk", 0.0)
            if pd.notna(kpis.get("budget_deviation_risk")) else 0.0
        ),
        "cost_threshold_tnd":     float(COST_THRESHOLD),
        "projection_month":       prediction_month,
    }])


def save_predictions_to_database(predictions_df: pd.DataFrame, kpis: dict, prediction_month: int) -> None:
    run_id    = datetime.now().strftime("CST-%Y%m%d-%H%M%S")
    scored_at = datetime.now()

    pred_recs   = build_prediction_records(predictions_df, run_id, scored_at, prediction_month)
    summary_rec = build_summary_record(run_id, scored_at, kpis, len(predictions_df), prediction_month)

    conn = get_connection()
    try:
        load_table(conn=conn, schema=PREDICTIONS_SCHEMA, table=PREDICTIONS_TABLE,
                   df=pred_recs, mode="replace", primary_key=None)
        load_table(conn=conn, schema=PREDICTIONS_SCHEMA, table=SUMMARY_TABLE,
                   df=summary_rec, mode="replace", primary_key=None)
    finally:
        conn.close()

    print(
        f"[SAVE] SQL cost predictions: {PREDICTIONS_SCHEMA}.{PREDICTIONS_TABLE} "
        f"({len(pred_recs)} rows) + {PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} (1 row) "
        f"[run_id={run_id}]"
    )


# ── Console report ─────────────────────────────────────────────────────────────
def print_cost_report(preds: pd.DataFrame, breakdowns: dict, kpis: dict, prediction_month: int) -> None:
    W = 76
    total = kpis["total_predicted_indemnisation_tnd"]
    reserve = kpis["recovery_reserve_tnd"]

    # Derive year from the data itself
    _year = int(pd.to_datetime(preds.get("date_sinistre_claim", pd.Series(dtype=str)), errors="coerce").dropna().max().year) \
        if "date_sinistre_claim" in preds.columns and not preds["date_sinistre_claim"].dropna().empty \
        else datetime.now().year
    month_name = datetime(year=_year, month=prediction_month, day=1).strftime("%B %Y")

    print("\n" + "═" * W)
    print("  INSURANCE CLAIMS – ACTIVE PORTFOLIO COST INTELLIGENCE REPORT")
    print(f"  Prediction period : {month_name}  (auto-detected from data)")
    print(f"  Run at            : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * W)

    # ── Risk tier distribution
    print("\n  RISK TIER DISTRIBUTION  (Low < 5K ≤ Medium < 15K ≤ High TND)")
    print("  " + "─" * (W - 2))
    tier_order = ["High", "Medium", "Low"]
    for tier in tier_order:
        mask  = preds["cost_risk_level"] == tier
        cnt   = int(mask.sum())
        tot   = float(preds.loc[mask, "predicted_cost"].sum())
        pct   = cnt / len(preds) * 100 if len(preds) > 0 else 0
        bar   = "█" * int(pct / 2)
        print(f"  {tier:<10} {cnt:>5} claims  {tot:>14,.0f} TND  {pct:>5.1f}%  {bar}")

    # ── Budget summary
    hist_avg    = kpis.get("historical_avg_per_claim_tnd", np.nan)
    hist_total  = hist_avg * len(preds) if pd.notna(hist_avg) else np.nan
    dev         = kpis.get("budget_deviation_risk", np.nan)
    dev_str     = f"{dev*100:>+.1f} %" if pd.notna(dev) else "N/A"
    dev_note    = (" ▲ above historical — review reserve" if pd.notna(dev) and dev > 0.05
                   else " ▼ below historical — favourable" if pd.notna(dev) and dev < -0.05
                   else "")

    print("\n  BUDGET SUMMARY")
    print("  " + "─" * (W - 2))
    items = [
        ("Total predicted indemnisation",       f"{total:>14,.0f} TND"),
        ("Average per claim (predicted)",        f"{kpis['average_cost_per_claim']:>14,.0f} TND"),
        ("Historical avg per claim (closed)",
         f"{hist_avg:>14,.0f} TND" if pd.notna(hist_avg) else f"{'N/A':>14}"),
        ("Historical total (same claim count)",
         f"{hist_total:>14,.0f} TND" if pd.notna(hist_total) else f"{'N/A':>14}"),
        ("Budget vs historical avg",             f"{dev_str:>14}{dev_note}"),
        ("Recovery reserve (15%)",               f"{reserve:>14,.0f} TND"),
        ("Recommended total reserve",            f"{total + reserve:>14,.0f} TND"),
        ("High-cost rate (> 15K TND)",           f"{kpis['high_cost_rate']*100:>13.1f} %"),
    ]
    for label, value in items:
        print(f"  {label:<45} {value}")

    # ── By claim type
    if not breakdowns["by_claim_type"].empty:
        print("\n  INDEMNISATION BREAKDOWN BY CLAIM TYPE")
        print("  " + "─" * (W - 2))
        print(f"  {'Claim Type':<30} {'Claims':>7} {'Total (TND)':>14} {'Avg (TND)':>12} {'% Budget':>9}")
        for _, row in breakdowns["by_claim_type"].iterrows():
            print(
                f"  {str(row['claim_type']):<30} {int(row['claim_count']):>7} "
                f"{row['total_indemnisation_tnd']:>14,.0f} {row['avg_indemnisation_tnd']:>12,.0f} "
                f"{row['pct_of_total_budget']:>8.1f}%"
            )

    # ── By coverage type
    if not breakdowns["by_coverage_type"].empty:
        print("\n  INDEMNISATION BREAKDOWN BY COVERAGE TYPE")
        print("  " + "─" * (W - 2))
        print(f"  {'Coverage Type':<30} {'Claims':>7} {'Total (TND)':>14} {'Avg (TND)':>12} {'% Budget':>9}")
        for _, row in breakdowns["by_coverage_type"].iterrows():
            print(
                f"  {str(row['coverage_type']):<30} {int(row['claim_count']):>7} "
                f"{row['total_indemnisation_tnd']:>14,.0f} {row['avg_indemnisation_tnd']:>12,.0f} "
                f"{row['pct_of_total_budget']:>8.1f}%"
            )

    # ── By severity bucket
    if not breakdowns["by_severity"].empty:
        print("\n  INDEMNISATION BREAKDOWN BY SEVERITY BUCKET")
        print("  " + "─" * (W - 2))
        print(f"  {'Severity Bucket':<30} {'Claims':>7} {'Total (TND)':>14} {'Avg (TND)':>12} {'% Budget':>9}")
        for _, row in breakdowns["by_severity"].iterrows():
            print(
                f"  {str(row['severity_bucket']):<30} {int(row['claim_count']):>7} "
                f"{row['total_indemnisation_tnd']:>14,.0f} {row['avg_indemnisation_tnd']:>12,.0f} "
                f"{row['pct_of_total_budget']:>8.1f}%"
            )

    # ── Key insights
    print("\n  KEY INSIGHTS")
    print("  " + "─" * (W - 2))
    print(f"  • Highest-cost claim type   : {kpis['top_claim_type_by_cost']}")
    print(f"  • Highest-cost coverage     : {kpis['top_coverage_type_by_cost']}")
    print(f"  • Recommended total reserve : {total + reserve:,.0f} TND "
          f"(predicted {total:,.0f} + 15% buffer {reserve:,.0f})")
    if pd.notna(kpis["budget_deviation_risk"]) and abs(kpis["budget_deviation_risk"]) > 0.05:
        direction = "above" if kpis["budget_deviation_risk"] > 0 else "below"
        print(
            f"  • Budget deviation : {abs(kpis['budget_deviation_risk'])*100:.1f}% {direction} "
            "historical average – review reserve allocation."
        )

    print("\n" + "═" * W + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("[START] COST PREDICTION PIPELINE")
    model  = load_model()
    claims = load_claims_data()
    preds  = predict_costs(model, claims)

    # Auto-detect which month's data we are scoring (driven by the data, not the clock)
    _year, prediction_month = _infer_prediction_period(preds)

    breakdowns = compute_breakdowns(preds)
    kpis       = calculate_kpis(preds, breakdowns)

    save_predictions(preds, breakdowns)
    save_predictions_to_database(preds, kpis, prediction_month)
    print_cost_report(preds, breakdowns, kpis, prediction_month)
    print("[DONE] COST PREDICTION PIPELINE COMPLETED")


if __name__ == "__main__":
    main()
