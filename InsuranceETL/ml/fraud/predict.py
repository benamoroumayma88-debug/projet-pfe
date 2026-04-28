"""
ml/fraud/predict.py
Run fraud scoring and generate decision-focused KPI outputs.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table
from etl.db_connection import get_connection
from etl.load import load_table


MODEL_PATH = "ml/fraud/models/fraud_detection_model.pkl"
TRAINING_RESULTS_PATH = "ml/fraud/models/training_results.json"
DATA_TABLE = "ml.ml_claim"
OUTPUT_DIR = "ml/fraud"
PREDICTIONS_SCHEMA = "ml"
PREDICTIONS_TABLE = "claim_fraud_predictions"
SUMMARY_TABLE = "claim_fraud_summary"
PRIORITY_CASES_TABLE = "claim_fraud_priority_cases"

ACTIVE_STATUSES = ["Ouvert", "En_cours", "En_cours_d_expertise"]

# Agent cost calculation (Tunisia - TND)
AGENT_MONTHLY_SALARY = 3000.0  # TND
AGENT_MONTHLY_WORKING_HOURS = 160.0  # hours
AGENT_HOURLY_RATE = AGENT_MONTHLY_SALARY / AGENT_MONTHLY_WORKING_HOURS  # TND/hour
BASE_INVESTIGATION_HOURS = 1.5  # baseline hours
MAX_INVESTIGATION_HOURS = 7.5  # maximum hours


def _find_amount_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "montant_indemnisation_claim",
        "montant_indemnisation",
        "montant_estime_dommage_claim",
        "montant_estime",
        "montant_sinistre",
    ]
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _estimate_case_hours(fraud_probability: float) -> float:
    """Estimate hours to investigate case based on fraud probability.
    Higher probability = more complex investigation = more hours.
    """
    return BASE_INVESTIGATION_HOURS + (fraud_probability * (MAX_INVESTIGATION_HOURS - BASE_INVESTIGATION_HOURS))


def load_model() -> Any:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run ml/fraud/train.py first.")
    model = joblib.load(MODEL_PATH)
    print(f"[LOAD] Model loaded: {MODEL_PATH}")
    return model


def load_training_metadata() -> Dict[str, Any]:
    if not os.path.exists(TRAINING_RESULTS_PATH):
        print("[WARNING] Training metadata not found. Using default assumptions.")
        return {}

    with open(TRAINING_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[LOAD] Training metadata loaded: {TRAINING_RESULTS_PATH}")
    return data


def load_claims_data() -> pd.DataFrame:
    print("[LOAD] Loading claims for fraud scoring...")
    df = extract_table(DATA_TABLE)
    print(f"[LOAD] Loaded {len(df)} records from {DATA_TABLE}")

    if "statut_sinistre_claim" in df.columns:
        active_statuses = {"Ouvert", "En_cours", "En_cours_d_expertise"}
        active_df = df[df["statut_sinistre_claim"].isin(active_statuses)].copy()
        if len(active_df) > 0:
            print(f"[FILTER] Active claims retained: {len(active_df)}")
            return active_df
        print("[WARNING] No active claims found; scoring all claims.")

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    X = df.copy()

    non_feature_cols = [
        "claim_id",
        "client_id",
        "contract_id",
        "vehicle_id",
        "date_sinistre_claim",
        "date_cloture_claim",
        "description_sinistre_claim",
        "duree_traitement_jours",
        "duree_traitement_heures",
        "is_delayed",
        "claim_severity_bucket",
        "est_frauduleux_claim",
    ]

    X = X.drop(columns=[c for c in non_feature_cols if c in X.columns], errors="ignore")
    return X


def predict_fraud(df: pd.DataFrame, model: Any, threshold: float) -> pd.DataFrame:
    X = prepare_features(df)
    fraud_probability = model.predict_proba(X)[:, 1]

    out = df.copy()
    out["fraud_probability"] = fraud_probability
    out["predicted_fraud"] = (out["fraud_probability"] >= threshold).astype(int)
    out["estimated_investigation_hours"] = out["fraud_probability"].apply(_estimate_case_hours)
    out["estimated_investigation_cost_tnd"] = out["estimated_investigation_hours"] * AGENT_HOURLY_RATE

    # Risk levels derived FROM threshold for coherence:
    #   Critical = prob >= threshold       (= predicted fraud)
    #   High     = prob >= threshold * 0.7
    #   Medium   = prob >= threshold * 0.4
    #   Low      = below
    high_cutoff = round(threshold * 0.7, 4)
    medium_cutoff = round(threshold * 0.4, 4)
    conditions = [
        out["fraud_probability"] >= threshold,
        out["fraud_probability"] >= high_cutoff,
        out["fraud_probability"] >= medium_cutoff,
    ]
    choices = ["Critical", "High", "Medium"]
    out["risk_level"] = np.select(conditions, choices, default="Low")

    action_map = {
        "Critical": "Escalate: SIU review within 24h",
        "High": "Priority review within 48h",
        "Medium": "Desk review if capacity allows",
        "Low": "Straight-through processing",
    }
    out["recommended_action"] = out["risk_level"].map(action_map)

    return out


def calculate_kpis(predictions: pd.DataFrame, metadata: Dict[str, Any], threshold: float) -> Dict[str, Any]:
    amount_col = _find_amount_column(predictions)

    best_model_name = metadata.get("best_model")
    model_results = metadata.get("results", {}).get(best_model_name, {}) if best_model_name else {}
    assumptions = model_results.get("optimized_threshold", {}).get("assumptions", {})

    prevented_loss_ratio = _safe_float(assumptions.get("prevented_loss_ratio"), 0.70)
    agent_hourly_rate = _safe_float(assumptions.get("agent_hourly_rate"), AGENT_HOURLY_RATE)

    scored_count = len(predictions)
    flagged = predictions[predictions["predicted_fraud"] == 1].copy()
    total_investigation_hours = float(flagged["estimated_investigation_hours"].sum())

    if amount_col:
        amounts = predictions[amount_col].fillna(0)
        flagged_amounts = flagged[amount_col].fillna(0) if len(flagged) else pd.Series(dtype=float)

        expected_fraud_exposure_total = float((predictions["fraud_probability"] * amounts).sum())
        expected_preventable_loss = float((flagged["fraud_probability"] * flagged_amounts).sum() * prevented_loss_ratio) if len(flagged) else 0.0
    else:
        expected_fraud_exposure_total = 0.0
        expected_preventable_loss = 0.0

    expected_review_cost = float(flagged["estimated_investigation_hours"].sum() * agent_hourly_rate) if len(flagged) > 0 else 0.0
    expected_net_savings = float(expected_preventable_loss - expected_review_cost)
    expected_roi = float(expected_net_savings / expected_review_cost) if expected_review_cost > 0 else 0.0

    risk_distribution = {
        str(k): int(v)
        for k, v in predictions["risk_level"].value_counts(dropna=False).to_dict().items()
    }

    return {
        "run_timestamp": datetime.now().isoformat(),
        "threshold_used": float(threshold),
        "total_scored_claims": int(scored_count),
        "flagged_for_investigation": int(len(flagged)),
        "total_investigation_hours": total_investigation_hours,
        "expected_fraud_exposure_total": expected_fraud_exposure_total,
        "expected_preventable_loss": expected_preventable_loss,
        "expected_review_cost": expected_review_cost,
        "expected_net_savings": expected_net_savings,
        "expected_roi": expected_roi,
        "risk_distribution": risk_distribution,
        "assumptions": {
            "prevented_loss_ratio": prevented_loss_ratio,
            "agent_hourly_rate": agent_hourly_rate,
            "amount_column": amount_col,
        },
    }


def build_dashboard_payload(predictions: pd.DataFrame, kpis: Dict[str, Any]) -> Dict[str, Any]:
    top_cases = predictions.sort_values("fraud_probability", ascending=False).head(20).copy()

    desired_cols = [
        "claim_id",
        "fraud_probability",
        "risk_level",
        "recommended_action",
        "client_id",
        "contract_id",
        "type_sinistre_claim",
        "statut_sinistre_claim",
        "predicted_fraud",
    ]

    amount_col = kpis.get("assumptions", {}).get("amount_column")
    if amount_col and amount_col in predictions.columns:
        desired_cols.append(amount_col)

    available_cols = [col for col in desired_cols if col in top_cases.columns]

    return {
        "summary": kpis,
        "top_suspicious_claims": top_cases[available_cols].to_dict("records"),
    }


def build_prediction_records(
    predictions: pd.DataFrame,
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    threshold: float,
    run_id: str,
    scored_at: datetime,
    prediction_month: int,
) -> pd.DataFrame:
    amount_col = kpis.get("assumptions", {}).get("amount_column")

    records = predictions.copy()
    records.insert(0, "prediction_run_id", run_id)
    records.insert(1, "scored_at", scored_at)

    if amount_col and amount_col in records.columns:
        amount_values = pd.to_numeric(records[amount_col], errors="coerce").fillna(0.0)
        records["claim_amount_tnd"] = amount_values
        records["expected_fraud_exposure_claim_tnd"] = records["fraud_probability"] * amount_values
        records["expected_preventable_loss_claim_tnd"] = np.where(
            records["predicted_fraud"] == 1,
            records["expected_fraud_exposure_claim_tnd"] * kpis.get("assumptions", {}).get("prevented_loss_ratio", 0.70),
            0.0,
        )
    else:
        records["claim_amount_tnd"] = 0.0
        records["expected_fraud_exposure_claim_tnd"] = 0.0
        records["expected_preventable_loss_claim_tnd"] = 0.0

    # Add unique per-row identifier and prediction month (matches cost/delay model structure)
    records.insert(0, "prediction_record_id", [str(uuid.uuid4()) for _ in range(len(records))])
    records["prediction_month"] = prediction_month

    preferred_cols = [
        "prediction_record_id",
        "prediction_run_id",
        "scored_at",
        "claim_id",
        "client_id",
        "contract_id",
        "vehicle_id",
        "date_sinistre_claim",
        "statut_sinistre_claim",
        "type_sinistre_claim",
        "claim_severity_bucket",
        "fraud_probability",
        "risk_level",
        "recommended_action",
        "predicted_fraud",
        "estimated_investigation_hours",
        "estimated_investigation_cost_tnd",
        "claim_amount_tnd",
        "expected_fraud_exposure_claim_tnd",
        "expected_preventable_loss_claim_tnd",
        "prediction_month",
    ]
    available_cols = [col for col in preferred_cols if col in records.columns]
    records = records[available_cols].copy()

    for col in ["risk_level", "recommended_action", "statut_sinistre_claim", "type_sinistre_claim"]:
        if col in records.columns:
            records[col] = records[col].astype(str)

    return records


def build_summary_record(
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    run_id: str,
    scored_at: datetime,
    projection_month: int,
) -> pd.DataFrame:
    risk_distribution = kpis.get("risk_distribution", {})

    summary_row = {
        "prediction_run_id": run_id,
        "scored_at": scored_at,
        "model_name": metadata.get("best_model", "unknown"),
        "threshold_used": float(kpis.get("threshold_used", 0.0) or 0.0),
        "total_scored_claims": int(kpis.get("total_scored_claims", 0) or 0),
        "flagged_for_investigation": int(kpis.get("flagged_for_investigation", 0) or 0),
        "total_investigation_hours": float(kpis.get("total_investigation_hours", 0.0) or 0.0),
        "expected_fraud_exposure_total_tnd": float(kpis.get("expected_fraud_exposure_total", 0.0) or 0.0),
        "expected_preventable_loss_tnd": float(kpis.get("expected_preventable_loss", 0.0) or 0.0),
        "expected_review_cost_tnd": float(kpis.get("expected_review_cost", 0.0) or 0.0),
        "expected_net_savings_tnd": float(kpis.get("expected_net_savings", 0.0) or 0.0),
        "expected_roi": float(kpis.get("expected_roi", 0.0) or 0.0),
        "low_risk_count": int(risk_distribution.get("Low", 0) or 0),
        "medium_risk_count": int(risk_distribution.get("Medium", 0) or 0),
        "high_risk_count": int(risk_distribution.get("High", 0) or 0),
        "critical_risk_count": int(risk_distribution.get("Critical", 0) or 0),
        "projection_month": projection_month,
    }

    return pd.DataFrame([summary_row])


def build_priority_case_records(
    predictions: pd.DataFrame,
    run_id: str,
    scored_at: datetime,
) -> pd.DataFrame:
    """Build a single ranked investigation queue — top 20 claims by fraud probability."""
    top_risk_cases = predictions.sort_values("fraud_probability", ascending=False).head(20).copy()

    if top_risk_cases.empty:
        return pd.DataFrame(
            columns=[
                "prediction_run_id", "scored_at",
                "priority_rank", "claim_id",
                "client_id", "contract_id", "fraud_probability", "risk_level",
                "recommended_action", "predicted_fraud", "estimated_investigation_hours",
                "estimated_investigation_cost_tnd"
            ]
        )

    top_risk_cases.insert(0, "prediction_run_id", run_id)
    top_risk_cases.insert(1, "scored_at", scored_at)
    top_risk_cases["priority_rank"] = range(1, len(top_risk_cases) + 1)

    keep_cols = [
        "prediction_run_id", "scored_at",
        "priority_rank", "claim_id", "client_id", "contract_id",
        "fraud_probability", "risk_level", "recommended_action", "predicted_fraud",
        "estimated_investigation_hours", "estimated_investigation_cost_tnd"
    ]
    available_cols = [col for col in keep_cols if col in top_risk_cases.columns]
    top_risk_cases = top_risk_cases[available_cols].copy()

    for col in ["risk_level", "recommended_action"]:
        if col in top_risk_cases.columns:
            top_risk_cases[col] = top_risk_cases[col].astype(str)

    return top_risk_cases


def save_predictions_to_database(
    predictions: pd.DataFrame,
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    threshold: float,
    pred_month: int,
) -> None:
    run_id = datetime.now().strftime("FRD-%Y%m%d-%H%M%S")
    scored_at = datetime.now()

    prediction_records = build_prediction_records(predictions, kpis, metadata, threshold, run_id, scored_at, pred_month)
    summary_record = build_summary_record(kpis, metadata, run_id, scored_at, pred_month)
    priority_case_records = build_priority_case_records(predictions, run_id, scored_at)

    conn = get_connection()
    try:
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=PREDICTIONS_TABLE,
            df=prediction_records,
            mode="replace",
            primary_key=None,
        )
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=SUMMARY_TABLE,
            df=summary_record,
            mode="replace",
            primary_key=None,
        )
        if not priority_case_records.empty:
            load_table(
                conn=conn,
                schema=PREDICTIONS_SCHEMA,
                table=PRIORITY_CASES_TABLE,
                df=priority_case_records,
                mode="replace",
                primary_key=None,
            )
    finally:
        conn.close()

    print(
        f"[SAVE] SQL fraud predictions saved: "
        f"{PREDICTIONS_SCHEMA}.{PREDICTIONS_TABLE} ({len(prediction_records)} rows), "
        f"{PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} ({len(summary_record)} row), "
        f"{PREDICTIONS_SCHEMA}.{PRIORITY_CASES_TABLE} ({len(priority_case_records)} rows) "
        f"[run_id={run_id}]"
    )


def save_outputs(predictions: pd.DataFrame, dashboard_payload: Dict[str, Any]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dashboard_path = os.path.join(OUTPUT_DIR, "dashboard_insights.json")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_payload, f, indent=2, default=str)

    predictions_path = os.path.join(OUTPUT_DIR, "predictions.csv")
    predictions.to_csv(predictions_path, index=False, encoding="utf-8")

    print(f"[SAVE] Dashboard insights: {dashboard_path}")
    print(f"[SAVE] Scored predictions: {predictions_path}")


def resolve_threshold(metadata: Dict[str, Any], default_threshold: float = 0.5) -> float:
    best_model = metadata.get("best_model")
    if not best_model:
        return default_threshold

    result = metadata.get("results", {}).get(best_model, {})
    precision_first = (
        result.get("optimized_threshold", {})
        .get("operating_points", {})
        .get("precision_first", {})
        .get("threshold")
    )
    if precision_first is not None:
        return _safe_float(precision_first, default_threshold)

    return _safe_float(
        result.get("optimized_threshold", {}).get("recommended_threshold"),
        default_threshold,
    )


def _infer_prediction_period(active_df: pd.DataFrame) -> tuple:
    """
    Return (year, month) of the latest date_sinistre_claim in active claims.
    Ensures the fraud report always reflects the period of the scored claims,
    not the calendar clock. Automatically shifts when new data is injected.
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


def main() -> None:
    print("\n" + "=" * 70)
    print("INSURANCE FRAUD DETECTION - PREDICTION & KPI GENERATION")
    print("=" * 70)

    model = load_model()
    metadata = load_training_metadata()
    threshold = resolve_threshold(metadata, default_threshold=0.5)

    claims = load_claims_data()

    # Auto-detect prediction period from the data
    pred_year, pred_month = _infer_prediction_period(claims)
    month_label = datetime(year=pred_year, month=pred_month, day=1).strftime("%B %Y")

    predictions = predict_fraud(claims, model, threshold)

    # ── Coherence assertion ──────────────────────────────────────
    critical_count = int((predictions["risk_level"] == "Critical").sum())
    predicted_fraud_count = int(predictions["predicted_fraud"].sum())
    assert critical_count == predicted_fraud_count, (
        f"INCOHERENCE: critical_count={critical_count} != predicted_fraud_count={predicted_fraud_count}"
    )

    kpis = calculate_kpis(predictions, metadata, threshold)
    dashboard_payload = build_dashboard_payload(predictions, kpis)

    save_outputs(predictions, dashboard_payload)
    save_predictions_to_database(predictions, kpis, metadata, threshold, pred_month)

    # ── Summary print ────────────────────────────────────────────
    risk_dist = kpis.get("risk_distribution", {})
    scored = kpis["total_scored_claims"]
    fraud_rate = predicted_fraud_count / scored * 100 if scored else 0
    print(f"\n[RESULTS] Prediction period : {month_label}  (auto-detected from data)")
    print(f"          Scored {scored} active claims  (threshold={threshold})")
    print(f"  Risk distribution:  Critical={risk_dist.get('Critical',0)}  |  High={risk_dist.get('High',0)}  |  Medium={risk_dist.get('Medium',0)}  |  Low={risk_dist.get('Low',0)}")
    print(f"  Predicted fraud (=Critical): {predicted_fraud_count}  ({fraud_rate:.2f}%)")
    print(f"  Flagged for investigation:   {kpis['flagged_for_investigation']}")
    print(f"  Investigation hours:         {kpis['total_investigation_hours']:.1f}h")
    print(f"  Expected preventable loss:   {kpis['expected_preventable_loss']:,.0f} TND")
    print(f"  Expected review cost:        {kpis['expected_review_cost']:,.0f} TND")
    print(f"  Expected net savings:        {kpis['expected_net_savings']:,.0f} TND")
    print(f"  Expected ROI:                {kpis['expected_roi']:.1f}x")
    print(f"  [COHERENCE] critical_count={critical_count} == predicted_fraud={predicted_fraud_count}  OK")

    print("\n" + "=" * 70)
    print("FRAUD PREDICTION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
