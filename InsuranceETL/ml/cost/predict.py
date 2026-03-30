"""
ml/cost/predict.py
Load the trained cost prediction model and apply it to active claims.
Generate monthly cost forecasts to help finance teams know how much should
be reserved for incoming claims.
"""

import json
import uuid
import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime, timedelta

# add repository root to path so we can import packages cleanly
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from etl.extract import extract_table
from etl.db_connection import get_connection
from etl.load import load_table

# configuration
MODEL_PATH = "ml/cost/models/cost_prediction_model.pkl"
DATA_TABLE = "ml.ml_claim"
OUTPUT_DIR = "ml/cost"
PREDICTIONS_SCHEMA = "ml"
PREDICTIONS_TABLE = "claim_cost_predictions"
SUMMARY_TABLE = "claim_cost_run_summary"

# statuses considered "active" when forecasting incoming cost
ACTIVE_STATUSES = ['Ouvert', 'En_cours', 'En_cours_d_expertise']

# KPI settings
COST_THRESHOLD = 10000  # threshold for high-cost claims (adjustable)


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train.py first.")
    model = joblib.load(MODEL_PATH)
    print(f"[LOAD] Model loaded from {MODEL_PATH}")
    return model


def load_claims_data():
    print("[LOAD] Loading claims data for prediction...")
    df = extract_table(DATA_TABLE)
    print(f"[LOAD] {len(df)} total rows from {DATA_TABLE}")
    if 'statut_sinistre_claim' in df.columns:
        df = df[df['statut_sinistre_claim'].isin(ACTIVE_STATUSES)].copy()
        print(f"[FILTER] {len(df)} active claims after status filter")
    else:
        print("[WARNING] status column missing; using all claims")
    if df.empty:
        raise ValueError("No active claims to predict cost for")
    return df


def prepare_features(df):
    # similar to training preprocessing
    X = df.copy()
    drop_cols = [
        "claim_id", "client_id", "contract_id", "vehicle_id",
        "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
        "montant_indemnisation_claim", "montant_estime_dommage_claim",
        "montant_indemnisation", "montant_estime",
    ]
    # also remove the target column if it accidentally appears (prediction stage)
    if 'claim_cost' in X.columns:
        drop_cols.append('claim_cost')
    X = X.drop(columns=[c for c in drop_cols if c in X.columns], errors='ignore')
    return X


def predict_costs(model, df):
    X = prepare_features(df)
    preds = model.predict(X)
    df = df.copy()
    df['predicted_cost'] = np.maximum(preds, 0)
    df['cost_risk_level'] = pd.cut(
        df['predicted_cost'],
        bins=[-np.inf, 5000, COST_THRESHOLD, np.inf],
        labels=['Low', 'Medium', 'High'],
        include_lowest=True,
    ).astype(str)
    print(f"[PREDICT] Generated cost estimates for {len(df)} claims")
    print(f"Risk distribution: {df['cost_risk_level'].value_counts().to_dict()}")
    return df


def aggregate_monthly(df):
    upcoming_month = pd.Period((datetime.now() + timedelta(days=30)).strftime('%Y-%m'), freq='M')
    total_cost = df['predicted_cost'].sum()
    monthly = pd.DataFrame({
        'year_month': [upcoming_month],
        'total_predicted_cost': [total_cost]
    })
    return monthly


def calculate_kpis(preds):
    """Return dictionary of KPIs for the upcoming period.

    KPIs:
      * estimated_monthly_budget    - total predicted cost (previous title)
      * average_cost_per_claim     - total / count, shows rising cost per claim
      * high_cost_rate             - percentage of claims above COST_THRESHOLD
      * budget_deviation_risk      - deviation from historical average cost
    """
    total = preds['predicted_cost'].sum()
    count = len(preds)
    avg_cost = total / count if count > 0 else 0
    high_cost_rate = (preds['predicted_cost'] > COST_THRESHOLD).mean() if count > 0 else 0

    # compute historical average cost from closed claims
    hist_df = extract_table(DATA_TABLE)
    if 'statut_sinistre_claim' in hist_df.columns:
        closed = hist_df[~hist_df['statut_sinistre_claim'].isin(ACTIVE_STATUSES)]
    else:
        closed = hist_df

    if 'claim_cost' in closed.columns:
        hist_vals = closed['claim_cost']
    elif 'montant_indemnisation_claim' in closed.columns:
        hist_vals = closed['montant_indemnisation_claim']
    elif 'montant_estime_dommage_claim' in closed.columns:
        hist_vals = closed['montant_estime_dommage_claim']
    else:
        hist_vals = pd.Series(dtype=float)

    hist_avg = pd.to_numeric(hist_vals, errors='coerce').mean() if not hist_vals.empty else np.nan
    if pd.notna(hist_avg) and count > 0:
        budget_deviation = (total - hist_avg * count) / (hist_avg * count)
    else:
        budget_deviation = np.nan

    return {
        'estimated_monthly_budget': total,
        'average_cost_per_claim': avg_cost,
        'high_cost_rate': high_cost_rate,
        'budget_deviation_risk': budget_deviation
    }


def save_predictions(df, monthly):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    predictions_path = os.path.join(OUTPUT_DIR, 'predictions.csv')
    df.to_csv(predictions_path, index=False)
    monthly_path = os.path.join(OUTPUT_DIR, 'monthly_forecast.csv')
    monthly.to_csv(monthly_path, index=False)
    print(f"[SAVE] Predictions -> {predictions_path}")
    print(f"[SAVE] Monthly forecast -> {monthly_path}")


def build_prediction_records(predictions_df, run_id, scored_at):
    """Build per-claim rows ready for SQL insertion."""
    records = predictions_df.copy()

    base_cols = [
        'claim_id', 'client_id', 'contract_id', 'vehicle_id',
        'date_sinistre_claim', 'statut_sinistre_claim', 'type_sinistre_claim',
        'type_couverture', 'claim_severity_bucket',
    ]
    pred_cols = ['predicted_cost', 'cost_risk_level']
    keep_cols = [c for c in base_cols + pred_cols if c in records.columns]
    records = records[keep_cols].copy()

    records.insert(0, 'prediction_record_id', [str(uuid.uuid4()) for _ in range(len(records))])
    records.insert(1, 'prediction_run_id', run_id)
    records.insert(2, 'scored_at', scored_at)
    records['prediction_month'] = int((datetime.now() + timedelta(days=30)).month)

    for col in ['statut_sinistre_claim', 'type_sinistre_claim', 'type_couverture',
                'claim_severity_bucket', 'cost_risk_level']:
        if col in records.columns:
            records[col] = records[col].astype(str)

    return records


def build_summary_record(run_id, scored_at, kpis, total_claims):
    """Build a single aggregate row for the current prediction run."""
    summary_row = {
        'summary_record_id':          str(uuid.uuid4()),
        'prediction_run_id':          run_id,
        'scored_at':                  scored_at,
        'total_active_claims':        int(total_claims),
        'total_predicted_cost':       float(kpis.get('estimated_monthly_budget', 0.0) or 0.0),
        'average_cost_per_claim':     float(kpis.get('average_cost_per_claim', 0.0) or 0.0),
        'high_cost_rate':             float(kpis.get('high_cost_rate', 0.0) or 0.0),
        'budget_deviation_risk':      float(kpis.get('budget_deviation_risk', 0.0)
                                            if pd.notna(kpis.get('budget_deviation_risk')) else 0.0),
        'cost_threshold_tnd':         float(COST_THRESHOLD),
        'projection_month':           int((datetime.now() + timedelta(days=30)).month),
    }
    return pd.DataFrame([summary_row])


def save_predictions_to_database(predictions_df, kpis):
    """Persist per-claim predictions and run summary into SQL Server."""
    run_id = datetime.now().strftime('CST-%Y%m%d-%H%M%S')
    scored_at = datetime.now()

    prediction_records = build_prediction_records(predictions_df, run_id, scored_at)
    summary_record = build_summary_record(run_id, scored_at, kpis, len(predictions_df))

    conn = get_connection()
    try:
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=PREDICTIONS_TABLE,
            df=prediction_records,
            mode='append',
            primary_key=None,
        )
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=SUMMARY_TABLE,
            df=summary_record,
            mode='append',
            primary_key=None,
        )
    finally:
        conn.close()

    print(
        f"[SAVE] SQL cost predictions saved: "
        f"{PREDICTIONS_SCHEMA}.{PREDICTIONS_TABLE} ({len(prediction_records)} rows), "
        f"{PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} (1 row) "
        f"[run_id={run_id}]"
    )


def main():
    print("[START] COST PREDICTION PIPELINE")
    model = load_model()
    claims = load_claims_data()
    preds = predict_costs(model, claims)
    monthly = aggregate_monthly(preds)
    save_predictions(preds, monthly)
    print("[SUMMARY] Estimated monthly budget (next period):")
    print(monthly.head())

    # calculate KPIs and print with explanatory comments
    kpis = calculate_kpis(preds)
    save_predictions_to_database(preds, kpis)
    print("\nKEY PERFORMANCE INDICATORS (KPIs):")
    print("Predicted Claims Budget:")
    print(f"    {kpis['estimated_monthly_budget']:.2f}")
    print("average_cost_per_claim:")
    print(f"    {kpis['average_cost_per_claim']:.2f}")
    print("High-Cost Claim Risk Rate:")
    print(f"    {kpis['high_cost_rate']:.2%}")
    print("budget_deviation_risk:")
    if pd.notna(kpis['budget_deviation_risk']):
        print(f"    {kpis['budget_deviation_risk']:.2%}")
    else:
        print("    N/A")

    print("COST PREDICTION PIPELINE COMPLETED")


if __name__ == "__main__":
    main()
