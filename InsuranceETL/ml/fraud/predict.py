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

    out["risk_level"] = pd.cut(
        out["fraud_probability"],
        bins=[0.0, 0.30, 0.60, 0.85, 1.0],
        labels=["Low", "Medium", "High", "Critical"],
        include_lowest=True,
    )

    action_map = {
        "Critical": "Escalate: SIU review within 24h",
        "High": "Priority review within 48h",
        "Medium": "Desk review if capacity allows",
        "Low": "Straight-through processing",
    }
    out["recommended_action"] = out["risk_level"].astype(str).map(action_map)

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
    total_investigation_hours = float(predictions[predictions["predicted_fraud"] == 1]["estimated_investigation_hours"].sum())

    high_or_critical_mask = predictions["risk_level"].astype(str).isin(["High", "Critical"])
    critical_mask = predictions["risk_level"].astype(str) == "Critical"

    expected_fraud_cases = float(predictions["fraud_probability"].sum())
    flagged_expected_true_fraud = float(flagged["fraud_probability"].sum()) if len(flagged) else 0.0

    if amount_col:
        amounts = predictions[amount_col].fillna(0)
        flagged_amounts = flagged[amount_col].fillna(0) if len(flagged) else pd.Series(dtype=float)

        expected_fraud_exposure_total = float((predictions["fraud_probability"] * amounts).sum())
        expected_preventable_loss = float((flagged["fraud_probability"] * flagged_amounts).sum() * prevented_loss_ratio) if len(flagged) else 0.0
        avg_ticket_in_queue = float(flagged_amounts.mean()) if len(flagged) else 0.0
    else:
        expected_fraud_exposure_total = 0.0
        expected_preventable_loss = 0.0
        avg_ticket_in_queue = 0.0

    expected_review_cost = float(flagged["estimated_investigation_hours"].sum() * agent_hourly_rate) if len(flagged) > 0 else 0.0
    expected_net_savings = float(expected_preventable_loss - expected_review_cost)
    expected_roi = float(expected_net_savings / expected_review_cost) if expected_review_cost > 0 else 0.0

    top_5pct = max(1, int(np.ceil(0.05 * scored_count))) if scored_count else 0
    top_10pct = max(1, int(np.ceil(0.10 * scored_count))) if scored_count else 0
    sorted_pred = predictions.sort_values("fraud_probability", ascending=False)

    top5 = sorted_pred.head(top_5pct) if top_5pct else sorted_pred.iloc[0:0]
    top10 = sorted_pred.head(top_10pct) if top_10pct else sorted_pred.iloc[0:0]

    precision_at_top_5pct = float(top5["fraud_probability"].mean()) if len(top5) else 0.0
    precision_at_top_10pct = float(top10["fraud_probability"].mean()) if len(top10) else 0.0
    capture_rate_top_10pct = float(top10["fraud_probability"].sum() / expected_fraud_cases) if expected_fraud_cases > 0 else 0.0

    risk_distribution = {
        str(k): int(v)
        for k, v in predictions["risk_level"].value_counts(dropna=False).to_dict().items()
    }

    # Requested business KPIs (English labels)
    high_risk_claim_rate = float(high_or_critical_mask.mean()) if scored_count else 0.0
    average_predictive_risk_score = float(predictions["fraud_probability"].mean()) if scored_count else 0.0
    managerial_intervention_rate = float(critical_mask.mean()) if scored_count else 0.0
    suspected_fraud_claim_rate = float((predictions["predicted_fraud"] == 1).mean()) if scored_count else 0.0

    return {
        "currency": "TND (Tunisian Dinar)",
        "run_timestamp": datetime.now().isoformat(),
        "threshold_used": float(threshold),
        "total_scored_claims": int(scored_count),
        "flagged_for_investigation": int(len(flagged)),
        "investigation_load_rate": float(len(flagged) / scored_count) if scored_count else 0.0,
        "expected_fraud_cases_total": expected_fraud_cases,
        "expected_true_fraud_in_queue": flagged_expected_true_fraud,
        "expected_fraud_exposure_total": expected_fraud_exposure_total,
        "expected_preventable_loss": expected_preventable_loss,
        "expected_review_cost": expected_review_cost,
        "expected_net_savings": expected_net_savings,
        "expected_roi": expected_roi,
        "total_investigation_hours": total_investigation_hours,
        "precision_at_top_5pct": precision_at_top_5pct,
        "precision_at_top_10pct": precision_at_top_10pct,
        "capture_rate_top_10pct": capture_rate_top_10pct,
        "avg_ticket_size_in_queue": avg_ticket_in_queue,
        "risk_distribution": risk_distribution,
        "high_risk_claim_rate": high_risk_claim_rate,
        "average_predictive_risk_score": average_predictive_risk_score,
        "managerial_intervention_rate": managerial_intervention_rate,
        "suspected_fraud_claim_rate": suspected_fraud_claim_rate,
        "assumptions": {
            "prevented_loss_ratio": prevented_loss_ratio,
            "agent_monthly_salary": AGENT_MONTHLY_SALARY,
            "agent_monthly_working_hours": AGENT_MONTHLY_WORKING_HOURS,
            "agent_hourly_rate": agent_hourly_rate,
            "base_investigation_hours": BASE_INVESTIGATION_HOURS,
            "max_investigation_hours": MAX_INVESTIGATION_HOURS,
            "amount_column": amount_col,
        },
    }


def build_dashboard_payload(predictions: pd.DataFrame, kpis: Dict[str, Any]) -> Dict[str, Any]:
    top_cases = predictions.sort_values("fraud_probability", ascending=False).head(25).copy()
    top_risk_cases_20 = predictions.sort_values("fraud_probability", ascending=False).head(20).copy()
    critical_cases = predictions[predictions["risk_level"].astype(str) == "Critical"].copy()
    critical_cases_to_monitor = critical_cases.sort_values("fraud_probability", ascending=False).head(20)

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
        "top_risk_cases_20": top_risk_cases_20[available_cols].to_dict("records"),
        "critical_cases_to_monitor": critical_cases_to_monitor[available_cols].to_dict("records"),
    }


def build_prediction_records(
    predictions: pd.DataFrame,
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    threshold: float,
    run_id: str,
    scored_at: datetime,
) -> pd.DataFrame:
    amount_col = kpis.get("assumptions", {}).get("amount_column")

    records = predictions.copy()
    records.insert(0, "prediction_record_id", [str(uuid.uuid4()) for _ in range(len(records))])
    records.insert(1, "prediction_run_id", run_id)
    records.insert(2, "scored_at", scored_at)

    records["model_name"] = metadata.get("best_model", "unknown")
    records["decision_threshold"] = float(threshold)
    records["currency"] = "TND"
    records["high_risk_flag"] = records["risk_level"].astype(str).isin(["High", "Critical"]).astype(int)
    records["managerial_intervention_required"] = (records["risk_level"].astype(str) == "Critical").astype(int)
    records["suspected_fraud_flag"] = records["predicted_fraud"].astype(int)

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

    preferred_cols = [
        "prediction_record_id",
        "prediction_run_id",
        "scored_at",
        "model_name",
        "decision_threshold",
        "currency",
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
        "suspected_fraud_flag",
        "high_risk_flag",
        "managerial_intervention_required",
        "estimated_investigation_hours",
        "estimated_investigation_cost_tnd",
        "claim_amount_tnd",
        "expected_fraud_exposure_claim_tnd",
        "expected_preventable_loss_claim_tnd",
    ]
    available_cols = [col for col in preferred_cols if col in records.columns]
    records = records[available_cols].copy()

    for col in ["risk_level", "recommended_action", "model_name", "currency", "statut_sinistre_claim", "type_sinistre_claim"]:
        if col in records.columns:
            records[col] = records[col].astype(str)

    return records


def build_summary_record(
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    run_id: str,
    scored_at: datetime,
) -> pd.DataFrame:
    risk_distribution = kpis.get("risk_distribution", {})

    summary_row = {
        "summary_record_id": str(uuid.uuid4()),
        "prediction_run_id": run_id,
        "scored_at": scored_at,
        "model_name": metadata.get("best_model", "unknown"),
        "currency": kpis.get("currency", "TND (Tunisian Dinar)"),
        "threshold_used": float(kpis.get("threshold_used", 0.0) or 0.0),
        "total_scored_claims": int(kpis.get("total_scored_claims", 0) or 0),
        "flagged_for_investigation": int(kpis.get("flagged_for_investigation", 0) or 0),
        "investigation_load_rate": float(kpis.get("investigation_load_rate", 0.0) or 0.0),
        "total_investigation_hours": float(kpis.get("total_investigation_hours", 0.0) or 0.0),
        "expected_fraud_cases_total": float(kpis.get("expected_fraud_cases_total", 0.0) or 0.0),
        "expected_true_fraud_in_queue": float(kpis.get("expected_true_fraud_in_queue", 0.0) or 0.0),
        "expected_fraud_exposure_total_tnd": float(kpis.get("expected_fraud_exposure_total", 0.0) or 0.0),
        "expected_preventable_loss_tnd": float(kpis.get("expected_preventable_loss", 0.0) or 0.0),
        "expected_review_cost_tnd": float(kpis.get("expected_review_cost", 0.0) or 0.0),
        "expected_net_savings_tnd": float(kpis.get("expected_net_savings", 0.0) or 0.0),
        "expected_roi": float(kpis.get("expected_roi", 0.0) or 0.0),
        "precision_at_top_5pct": float(kpis.get("precision_at_top_5pct", 0.0) or 0.0),
        "precision_at_top_10pct": float(kpis.get("precision_at_top_10pct", 0.0) or 0.0),
        "capture_rate_top_10pct": float(kpis.get("capture_rate_top_10pct", 0.0) or 0.0),
        "avg_ticket_size_in_queue_tnd": float(kpis.get("avg_ticket_size_in_queue", 0.0) or 0.0),
        "high_risk_claim_rate": float(kpis.get("high_risk_claim_rate", 0.0) or 0.0),
        "average_predictive_risk_score": float(kpis.get("average_predictive_risk_score", 0.0) or 0.0),
        "managerial_intervention_rate": float(kpis.get("managerial_intervention_rate", 0.0) or 0.0),
        "suspected_fraud_claim_rate": float(kpis.get("suspected_fraud_claim_rate", 0.0) or 0.0),
        "low_risk_count": int(risk_distribution.get("Low", 0) or 0),
        "medium_risk_count": int(risk_distribution.get("Medium", 0) or 0),
        "high_risk_count": int(risk_distribution.get("High", 0) or 0),
        "critical_risk_count": int(risk_distribution.get("Critical", 0) or 0),
    }

    return pd.DataFrame([summary_row])


def build_priority_case_records(
    predictions: pd.DataFrame,
    metadata: Dict[str, Any],
    threshold: float,
    run_id: str,
    scored_at: datetime,
) -> pd.DataFrame:
    top_risk_cases = predictions.sort_values("fraud_probability", ascending=False).head(20).copy()
    top_risk_cases["priority_list_type"] = "TOP_20_RISK"

    critical_cases = predictions[predictions["risk_level"].astype(str) == "Critical"].copy()
    critical_cases = critical_cases.sort_values("fraud_probability", ascending=False).head(20)
    critical_cases["priority_list_type"] = "CRITICAL_TO_MONITOR"

    priority_df = pd.concat([top_risk_cases, critical_cases], ignore_index=True)
    if priority_df.empty:
        return pd.DataFrame(
            columns=[
                "priority_case_record_id", "prediction_run_id", "scored_at", "model_name",
                "decision_threshold", "priority_list_type", "priority_rank", "claim_id",
                "client_id", "contract_id", "fraud_probability", "risk_level",
                "recommended_action", "predicted_fraud", "estimated_investigation_hours",
                "estimated_investigation_cost_tnd"
            ]
        )

    priority_df.insert(0, "priority_case_record_id", [str(uuid.uuid4()) for _ in range(len(priority_df))])
    priority_df.insert(1, "prediction_run_id", run_id)
    priority_df.insert(2, "scored_at", scored_at)
    priority_df["model_name"] = metadata.get("best_model", "unknown")
    priority_df["decision_threshold"] = float(threshold)
    priority_df["priority_rank"] = priority_df.groupby("priority_list_type")["fraud_probability"].rank(method="first", ascending=False).astype(int)

    keep_cols = [
        "priority_case_record_id", "prediction_run_id", "scored_at", "model_name", "decision_threshold",
        "priority_list_type", "priority_rank", "claim_id", "client_id", "contract_id",
        "fraud_probability", "risk_level", "recommended_action", "predicted_fraud",
        "estimated_investigation_hours", "estimated_investigation_cost_tnd"
    ]
    available_cols = [col for col in keep_cols if col in priority_df.columns]
    priority_df = priority_df[available_cols].copy()

    for col in ["priority_list_type", "risk_level", "recommended_action", "model_name"]:
        if col in priority_df.columns:
            priority_df[col] = priority_df[col].astype(str)

    return priority_df


def save_predictions_to_database(
    predictions: pd.DataFrame,
    kpis: Dict[str, Any],
    metadata: Dict[str, Any],
    threshold: float,
) -> None:
    run_id = datetime.now().strftime("FRD-%Y%m%d-%H%M%S")
    scored_at = datetime.now()

    prediction_records = build_prediction_records(predictions, kpis, metadata, threshold, run_id, scored_at)
    summary_record = build_summary_record(kpis, metadata, run_id, scored_at)
    priority_case_records = build_priority_case_records(predictions, metadata, threshold, run_id, scored_at)

    conn = get_connection()
    try:
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=PREDICTIONS_TABLE,
            df=prediction_records,
            mode="append",
            primary_key=None,
        )
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=SUMMARY_TABLE,
            df=summary_record,
            mode="append",
            primary_key=None,
        )
        if not priority_case_records.empty:
            load_table(
                conn=conn,
                schema=PREDICTIONS_SCHEMA,
                table=PRIORITY_CASES_TABLE,
                df=priority_case_records,
                mode="append",
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


def main() -> None:
    print("\n" + "=" * 70)
    print("INSURANCE FRAUD DETECTION - PREDICTION & KPI GENERATION")
    print("=" * 70)

    model = load_model()
    metadata = load_training_metadata()
    threshold = resolve_threshold(metadata, default_threshold=0.5)

    claims = load_claims_data()
    predictions = predict_fraud(claims, model, threshold)

    kpis = calculate_kpis(predictions, metadata, threshold)
    dashboard_payload = build_dashboard_payload(predictions, kpis)

    save_outputs(predictions, dashboard_payload)
    save_predictions_to_database(predictions, kpis, metadata, threshold)

    print("\n[EXECUTIVE KPI SNAPSHOT]")
    print(f"  Total investigation hours: {kpis['total_investigation_hours']:.1f} hours")
    print(f"  Expected preventable loss: {kpis['expected_preventable_loss']:.2f} TND")
    print(f"  Expected review cost: {kpis['expected_review_cost']:.2f} TND")
    print(f"  Expected net savings: {kpis['expected_net_savings']:.2f} TND")
    print(f"  Expected ROI: {kpis['expected_roi']:.2f}x")
    print(f"  High-risk claim rate: {kpis['high_risk_claim_rate']:.2%}")
    print(f"  Average predictive risk score: {kpis['average_predictive_risk_score']:.4f}")
    print(f"  Managerial intervention rate: {kpis['managerial_intervention_rate']:.2%}")
    print(f"  Suspected fraud claim rate: {kpis['suspected_fraud_claim_rate']:.2%}")

    print("\n" + "=" * 70)
    print("FRAUD PREDICTION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
