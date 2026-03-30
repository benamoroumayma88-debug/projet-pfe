"""
ml/delay/predict.py
Predict delays for claims and generate dashboard insights.
Production-ready prediction pipeline for insurance claim delay forecasting.
"""

import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime, timedelta
import uuid

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table
from etl.db_connection import get_connection
from etl.load import load_table

# Configuration
MODEL_PATH          = "ml/delay/models/delay_prediction_model.pkl"  # winner (RF or XGB)
MODEL_METADATA_PATH = "ml/delay/models/model_metadata.pkl"
DURATION_MODEL_PATH = "ml/delay/models/duration_model.pkl"
DATA_TABLE = "ml.ml_claim"
OUTPUT_DIR = "ml/delay"
DASHBOARD_FILE = "dashboard_data.csv"
PREDICTIONS_SCHEMA = "ml"
PREDICTIONS_TABLE = "claim_delay_predictions"
SUMMARY_TABLE = "claim_delay_run_summary"

def load_model():
    """Load the production delay model (winner of RF vs XGB comparison) and its metadata."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train.py first.")

    metadata = {'best_model_name': 'xgboost', 'best_threshold': 0.5}
    if os.path.exists(MODEL_METADATA_PATH):
        metadata.update(joblib.load(MODEL_METADATA_PATH))

    model_bundle = {
        'primary':  joblib.load(MODEL_PATH),
        'metadata': metadata,
    }

    print(f"[LOAD] Model: {metadata.get('best_model_name')}")
    print(f"[LOAD] Decision threshold: {metadata.get('best_threshold', 0.5):.2f}")
    return model_bundle

def load_duration_model():
    """Load trained duration prediction model."""
    if os.path.exists(DURATION_MODEL_PATH):
        model = joblib.load(DURATION_MODEL_PATH)
        print(f"[LOAD] Duration model loaded from {DURATION_MODEL_PATH}")
        return model
    else:
        print("[WARNING] Duration model not found. Using average duration.")
        return None


def _get_expected_input_columns(model):
    """Return columns expected by a fitted sklearn pipeline with a preprocessor."""
    expected = []
    if model is None:
        return expected
    # Model may be a Pipeline object
    preprocessor = None
    if hasattr(model, 'named_steps'):
        preprocessor = model.named_steps.get('preprocessor')
    elif hasattr(model, 'preprocessor'):
        preprocessor = model.preprocessor

    if preprocessor is None or not hasattr(preprocessor, 'transformers'):
        return expected

    for name, transformer, columns in preprocessor.transformers:
        if name == 'remainder':
            continue
        if isinstance(columns, str):
            expected.append(columns)
        elif isinstance(columns, (list, tuple, pd.Index, np.ndarray)):
            expected.extend(list(columns))
    return expected


def _ensure_expected_columns(X, model):
    expected = _get_expected_input_columns(model)
    X = X.copy()
    for col in expected:
        if col not in X.columns:
            X[col] = np.nan
    return X


def load_claims_data():
    """Load only ACTIVE claims for prediction."""
    print("[LOAD] Loading claims data for prediction...")
    
    # Load ML dataset
    ml_df = extract_table(DATA_TABLE)
    initial_count = len(ml_df)
    print(f"[LOAD] Loaded {initial_count} total records from {DATA_TABLE}")
    
    # Filter for active claims only
    active_statuses = ['Ouvert', 'En_cours', 'En_cours_d_expertise']
    
    if 'statut_sinistre_claim' in ml_df.columns:
        print(f"[DEBUG] Status column found. Unique values: {ml_df['statut_sinistre_claim'].unique()}")
        ml_df = ml_df[ml_df['statut_sinistre_claim'].isin(active_statuses)].copy()
        filtered_count = len(ml_df)
        closed_count = initial_count - filtered_count
        
        if filtered_count == 0:
            print(f"[WARNING] No active claims found after filtering! Using ALL claims as fallback.")
            # Reload without filtering
            ml_df = extract_table(DATA_TABLE)
            print(f"[LOAD] Using all {len(ml_df)} claims for prediction")
        else:
            print(f"[FILTER] Active: {filtered_count} | Closed (excluded): {closed_count}")
    else:
        print("[WARNING] Status column not found in ML dataset. Using ALL claims.")
    
    if len(ml_df) == 0:
        raise ValueError("No claims data available for prediction. Check database connection.")
    
    print(f"[LOAD] Processing {len(ml_df)} claims for prediction")
    return ml_df

def predict_delays(model, duration_model, df):
    """Predict delay probabilities and durations for claims."""
    if len(df) == 0:
        print("[ERROR] No claims available for prediction!")
        raise ValueError("Empty dataset - cannot make predictions")
    
    # Prepare features (same as training preprocessing)
    X = df.copy()

    # Drop non-feature columns (DO NOT drop statut_sinistre_claim - it's needed by the model)
    drop_cols = ["claim_id", "client_id", "contract_id", "vehicle_id",
                 "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
                 "is_delayed", "duree_traitement_jours"]
    X = X.drop(columns=[c for c in drop_cols if c in X.columns], errors='ignore')

    # Predict probabilities
    metadata = model.get('metadata', {})
    delay_proba = model['primary'].predict_proba(X)[:, 1]

    decision_threshold = float(metadata.get('best_threshold', 0.5))

    # Add predictions to dataframe
    df = df.copy()
    df['delay_probability'] = delay_proba

    # Classify risk levels
    df['risk_level'] = pd.cut(
        df['delay_probability'],
        bins=[0, 0.3, 0.7, 1.0],
        labels=['Low', 'Medium', 'High'],
        include_lowest=True
    )

    # Predict duration for likely delayed claims
    if duration_model is not None:
        high_risk_mask = df['delay_probability'] > decision_threshold
        if high_risk_mask.sum() > 0:
            X_high = X[high_risk_mask].copy()
            X_high = _ensure_expected_columns(X_high, duration_model)
            predicted_durations = duration_model.predict(X_high)
            # Duration model is trained on log1p(target), so map back to day scale
            predicted_durations = np.expm1(predicted_durations)
            # Keep estimates in a realistic operational range and integer day values
            predicted_durations = np.clip(predicted_durations, 1, 120)
            predicted_durations = np.rint(predicted_durations).astype(int)
            df.loc[high_risk_mask, 'predicted_delay_days'] = predicted_durations
            df['predicted_delay_days'] = df['predicted_delay_days'].fillna(0)
        else:
            df['predicted_delay_days'] = 0
    else:
        # Dynamic fallback: estimate excess delay days from probability + SLA context
        if 'sla_jours' in df.columns:
            sla = pd.to_numeric(df['sla_jours'], errors='coerce').fillna(20)
        else:
            sla = pd.Series(20, index=df.index)

        estimated_excess_days = ((df['delay_probability'] - decision_threshold).clip(lower=0) * (sla * 1.6 + 18)).round()
        estimated_excess_days = estimated_excess_days.clip(lower=1, upper=90)
        df['predicted_delay_days'] = np.where(df['delay_probability'] > decision_threshold, estimated_excess_days, 0)

    print(f"[PREDICT] Predictions completed for {len(df)} claims")
    print(f"Risk distribution: {df['risk_level'].value_counts().to_dict()}")

    return df

def calculate_dashboard_metrics(predictions_df, decision_threshold=0.5):
    """Calculate dashboard metrics from predictions."""
    metrics = {}

    # Risk counts
    risk_counts = predictions_df['risk_level'].value_counts()
    metrics['high_risk_count'] = int(risk_counts.get('High', 0))
    metrics['medium_risk_count'] = int(risk_counts.get('Medium', 0))
    metrics['low_risk_count'] = int(risk_counts.get('Low', 0))
    
    metrics['total_active_claims'] = len(predictions_df)

    # Estimated delayed claims (sum of probabilities)
    metrics['estimated_delayed_claims'] = float(predictions_df['delay_probability'].sum())

    # Estimated total delay days: sum of excess days across all predicted-delayed claims
    # Example: 115 delayed claims × avg 5.7 extra days = ~651 cumulative excess days
    delayed_days = predictions_df.loc[predictions_df['predicted_delay_days'] > 0, 'predicted_delay_days']
    metrics['estimated_total_delay_days'] = int(delayed_days.sum())
    metrics['avg_delay_days_per_delayed_claim'] = round(float(delayed_days.mean()), 1) if len(delayed_days) > 0 else 0.0
    metrics['avg_predicted_delay_days'] = float(predictions_df['predicted_delay_days'].mean())

    # Cost impact: sum of claim amounts for predicted delayed claims
    # Use montant_indemnisation_claim or montant_estime_dommage_claim
    cost_cols = ['montant_indemnisation_claim', 'montant_indemnisation', 'montant_estime_dommage_claim', 'montant_estime']
    cost_col = None
    for col in cost_cols:
        if col in predictions_df.columns:
            cost_col = col
            break

    if cost_col:
        # Cost impact = sum of amounts for claims predicted to be delayed
        delayed_mask = predictions_df['delay_probability'] > float(decision_threshold)
        metrics['estimated_cost_impact'] = float(predictions_df.loc[delayed_mask, cost_col].sum())
        metrics['avg_cost_per_delayed_claim'] = float(predictions_df.loc[delayed_mask, cost_col].mean())
    else:
        metrics['estimated_cost_impact'] = 0
        metrics['avg_cost_per_delayed_claim'] = 0

    # Staff recommendations
    # Industry benchmark: one adjuster handles ~170 routine claims per month.
    # Predicted-delayed claims require 2x more attention (re-assessment, follow-ups).
    # Formula:  base staff  = entire open portfolio / routine throughput   (≈ current headcount)
    #           extra staff = delayed-claim excess workload / routine throughput
    ROUTINE_THROUGHPUT = 170  # claims handled per adjuster per month
    predicted_delayed_count = int((predictions_df['delay_probability'] >= float(decision_threshold)).sum())
    on_time_count = metrics['total_active_claims'] - predicted_delayed_count
    # Delayed claims count double; on-time claims count normally
    total_weighted_workload = predicted_delayed_count * 2 + on_time_count * 1
    metrics['recommended_staff'] = max(1, int(np.ceil(total_weighted_workload / ROUTINE_THROUGHPUT)))
    metrics['predicted_delayed_count'] = predicted_delayed_count

    # Time-based projections (next month)
    current_month = datetime.now().month
    next_month = (datetime.now() + timedelta(days=30)).month
    metrics['projection_month'] = next_month

    print("[METRICS] Dashboard metrics calculated:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    return metrics


def build_prediction_records(predictions_df, decision_threshold=0.5, metadata=None):
    """Build claim-level prediction rows for SQL storage. Returns (df, run_id, scored_at)."""
    metadata = metadata or {}
    run_id = datetime.now().strftime("RUN-%Y%m%d-%H%M%S")
    scored_at = datetime.now()

    records_df = predictions_df.copy()

    # Row-level KPI flags
    records_df['predicted_delayed'] = (records_df['delay_probability'] >= float(decision_threshold)).astype(int)
    records_df['estimated_cost_impact_claim'] = 0.0
    for col in ['montant_indemnisation_claim', 'montant_indemnisation', 'montant_estime_dommage_claim', 'montant_estime']:
        if col in records_df.columns:
            records_df['estimated_cost_impact_claim'] = np.where(
                records_df['predicted_delayed'] == 1,
                pd.to_numeric(records_df[col], errors='coerce').fillna(0.0),
                0.0,
            )
            break

    # Keep columns useful for BI dashboards and operations
    base_cols = [
        'claim_id', 'client_id', 'contract_id', 'vehicle_id',
        'date_sinistre_claim', 'statut_sinistre_claim', 'type_sinistre_claim',
        'type_couverture', 'claim_severity_bucket',
        'montant_estime_dommage_claim', 'montant_indemnisation_claim', 'sla_jours'
    ]
    pred_cols = [
        'delay_probability', 'risk_level', 'predicted_delayed',
        'predicted_delay_days', 'estimated_cost_impact_claim'
    ]
    keep_cols = [c for c in base_cols + pred_cols if c in records_df.columns]
    records_df = records_df[keep_cols].copy()

    # Add scoring metadata per row so each run is traceable
    records_df.insert(0, 'prediction_record_id', [str(uuid.uuid4()) for _ in range(len(records_df))])
    records_df.insert(1, 'prediction_run_id', run_id)
    records_df.insert(2, 'scored_at', scored_at)
    records_df['decision_threshold'] = float(decision_threshold)
    records_df['model_mode'] = metadata.get('best_model_name', 'xgboost')
    records_df['prediction_month'] = int((datetime.now() + timedelta(days=30)).month)

    # Normalize text-like fields for SQL compatibility
    if 'risk_level' in records_df.columns:
        records_df['risk_level'] = records_df['risk_level'].astype(str)

    return records_df, run_id, scored_at


def save_predictions_to_database(predictions_df, decision_threshold=0.5, metadata=None):
    """Persist per-claim predictions into SQL Server for dashboard consumption."""
    records_df, run_id, scored_at = build_prediction_records(
        predictions_df,
        decision_threshold=decision_threshold,
        metadata=metadata,
    )

    conn = get_connection()
    try:
        # append mode keeps historical runs (weekly/monthly snapshots)
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=PREDICTIONS_TABLE,
            df=records_df,
            mode='append',
            primary_key=None,
        )
        print(f"[SAVE] SQL predictions saved to {PREDICTIONS_SCHEMA}.{PREDICTIONS_TABLE} ({len(records_df)} rows)")
    finally:
        conn.close()

    return run_id, scored_at

def build_run_summary(run_id, scored_at, metrics, metadata):
    """Build a single-row summary DataFrame for the current prediction run."""
    summary_row = {
        "summary_record_id":            str(uuid.uuid4()),
        "prediction_run_id":            run_id,
        "scored_at":                    scored_at,
        "model_name":                   metadata.get("best_model_name", "unknown"),
        "decision_threshold":           float(metadata.get("best_threshold", 0.5)),
        "total_active_claims":          int(metrics.get("total_active_claims", 0)),
        "predicted_delayed_count":      int(metrics.get("predicted_delayed_count", 0)),
        "high_risk_count":              int(metrics.get("high_risk_count", 0)),
        "medium_risk_count":            int(metrics.get("medium_risk_count", 0)),
        "low_risk_count":               int(metrics.get("low_risk_count", 0)),
        "estimated_delayed_claims":     float(metrics.get("estimated_delayed_claims", 0.0)),
        "estimated_total_delay_days":   int(metrics.get("estimated_total_delay_days", 0)),
        "avg_delay_days_per_claim":     float(metrics.get("avg_delay_days_per_delayed_claim", 0.0)),
        "estimated_cost_impact_tnd":    float(metrics.get("estimated_cost_impact", 0.0)),
        "avg_cost_per_delayed_claim":   float(metrics.get("avg_cost_per_delayed_claim", 0.0)),
        "recommended_staff":            int(metrics.get("recommended_staff", 0)),
        "projection_month":             int(metrics.get("projection_month", 0)),
    }
    return pd.DataFrame([summary_row])


def save_run_summary_to_database(run_id, scored_at, metrics, metadata):
    """Persist one aggregated summary row per prediction run to ml.claim_delay_run_summary."""
    summary_df = build_run_summary(run_id, scored_at, metrics, metadata)
    conn = get_connection()
    try:
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=SUMMARY_TABLE,
            df=summary_df,
            mode='append',
            primary_key=None,
        )
        print(f"[SAVE] Run summary saved to {PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} (1 row, run_id={run_id})")
    finally:
        conn.close()


def generate_dashboard_data(predictions_df, metrics):
    """Generate comprehensive dashboard data."""
    # Top high-risk claims
    high_risk_claims = predictions_df[predictions_df['risk_level'] == 'High'].copy()
    high_risk_claims = high_risk_claims.nlargest(10, 'delay_probability')

    # Select available columns for high-risk claims
    desired_cols = ['claim_id', 'delay_probability', 'montant_estime', 'montant_indemnisation',
                    'type_sinistre', 'client_id', 'contract_id', 'predicted_delay_days']
    available_cols = [c for c in desired_cols if c in high_risk_claims.columns]
    high_risk_data = high_risk_claims[available_cols].to_dict('records') if not high_risk_claims.empty else []

    # Claims by risk level with key info
    dashboard_data = {
        'summary': metrics,
        'high_risk_claims': high_risk_data,
        'risk_distribution': predictions_df['risk_level'].value_counts().to_dict(),
        'monthly_projection': {
            'month': metrics['projection_month'],
            'estimated_delays': metrics['estimated_delayed_claims'],
            'cost_impact': metrics['estimated_cost_impact'],
            'staff_needed': metrics['recommended_staff']
        }
    }

    return dashboard_data

def save_dashboard_data(dashboard_data):
    """Save dashboard data to file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save as JSON for dashboard consumption
    import json
    output_path = os.path.join(OUTPUT_DIR, 'dashboard_insights.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    # Also save predictions CSV
    predictions_path = os.path.join(OUTPUT_DIR, 'predictions.csv')
    dashboard_data['predictions'] = dashboard_data.pop('summary', {})  # For CSV
    # Actually, save the full predictions separately if needed

    print(f"[SAVE] Dashboard data saved to {output_path}")

def main():
    """Main prediction pipeline."""
    print("[START] DELAY PREDICTION & DASHBOARD GENERATION STARTED")

    try:
        # Load model and data
        model = load_model()
        metadata = model.get('metadata', {})
        decision_threshold = float(metadata.get('best_threshold', 0.5))
        duration_model = load_duration_model()
        claims_df = load_claims_data()

        # Make predictions
        predictions_df = predict_delays(model, duration_model, claims_df)

        # Calculate metrics
        metrics = calculate_dashboard_metrics(predictions_df, decision_threshold=decision_threshold)

        # Save claim-level predictions to SQL table for dashboards
        run_id, scored_at = save_predictions_to_database(
            predictions_df,
            decision_threshold=decision_threshold,
            metadata=metadata,
        )

        # Save one aggregated summary row for this run
        save_run_summary_to_database(run_id, scored_at, metrics, metadata)

        # Generate dashboard data
        dashboard_data = generate_dashboard_data(predictions_df, metrics)

        # Save results
        save_dashboard_data(dashboard_data)

        print("[SUCCESS] DELAY PREDICTION & DASHBOARD GENERATION COMPLETED")

        # Print key insights
        print("\n[INSIGHTS] KEY DASHBOARD INSIGHTS:")
        print(f"High-risk claims: {metrics['high_risk_count']}")
        print(f"Predicted delayed claims: {metrics['predicted_delayed_count']}")
        print(f"Estimated total delay days: {metrics['estimated_total_delay_days']:.0f}  (avg {metrics['avg_delay_days_per_delayed_claim']} days/delayed claim)")
        print(f"Estimated cost impact: ${metrics['estimated_cost_impact']:,.2f}")
        print(f"Recommended staff: {metrics['recommended_staff']}")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise

if __name__ == "__main__":
    main()
