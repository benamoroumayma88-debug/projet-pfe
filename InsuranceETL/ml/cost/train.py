"""
ml/cost/train.py
Train regression model to predict claim cost amounts.
This model is intended to estimate monthly costs that should be
reserved for incoming claims.  It uses the unified `claim_cost`
column produced by the ETL pipeline and trains XGBoost and LightGBM
regressors, saving the best performing model.
"""

import pandas as pd
import numpy as np
import os
import sys
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    mean_squared_error,
    roc_auc_score,
    precision_score,
    accuracy_score,
)
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import time
import xgboost as xgb
import lightgbm as lgb

# adjust path to import extract_table from ETL
# ensure the repository root is on sys.path when running this file directly.
# Climb two directories from this file: cost -> ml -> InsuranceETL.
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from etl.extract import extract_table

# Configuration
MODEL_DIR = "ml/cost/models"
DATA_TABLE = "ml.ml_claim"
TARGET_COL = "claim_cost"    # unified target created in ml_builders
TEST_SIZE = 0.2
RANDOM_STATE = 42
CLOSED_STATUSES = ['Clos_avec_indemnisation', 'Clos_sans_indemnisation', 'Refusé']
SKIP_RF = True  # when True, only XGBoost + LightGBM are trained for cost model


def load_data():
    """Load ML dataset from database and filter for rows with cost labels."""
    print("[LOAD] Loading ML dataset from database...")
    df = extract_table(DATA_TABLE)
    print(f"[LOAD] Loaded {len(df)} rows with {len(df.columns)} columns")
    return df


def preprocess_data(df):
    """Prepare features and target for regression.
    Drops rows where the cost target is missing and separates features.

    If the unified target column is absent, try to construct it using the raw
    indemnisation or estimated damage amounts so that the training script can
    still run on older ETL outputs or ad-hoc datasets.
    """
    # filter for closed claims only
    if 'statut_sinistre_claim' in df.columns:
        df = df[df['statut_sinistre_claim'].isin(CLOSED_STATUSES)].copy()
        print(f"[PREPROCESS] Filtered to {len(df)} closed claims")
    else:
        print("[WARNING] status column missing; using all claims for training")

    # ensure target column exists
    if TARGET_COL not in df.columns:
        print(f"[PREPROCESS] warning: {TARGET_COL} not found, attempting fallback")
        if "montant_indemnisation_claim" in df.columns:
            df[TARGET_COL] = df["montant_indemnisation_claim"].copy()
        elif "montant_estime_dommage_claim" in df.columns:
            df[TARGET_COL] = df["montant_estime_dommage_claim"].copy()
        else:
            raise KeyError(f"{TARGET_COL} is missing and no fallback columns are available")

    # cost target must be numeric
    df = df[df[TARGET_COL].notna()].copy()
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")

    if df.empty:
        raise ValueError("No rows with cost target available for training")

    # drop identifiers and leakage columns
    drop_cols = [
        "claim_id", "client_id", "contract_id", "vehicle_id",
        "date_sinistre_claim", "est_frauduleux_claim",
        # severity bucket is derived directly from cost; leaking it would make
        # the prediction trivial.
        "claim_severity_bucket",
        # also drop the raw cost columns since we use the unified target
        "montant_indemnisation_claim", "montant_estime_dommage_claim",
        "montant_indemnisation", "montant_estime"
    ]
    # ensure the target column is not used as a feature (data leakage)
    if TARGET_COL in df.columns:
        drop_cols.append(TARGET_COL)

    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    y = df[TARGET_COL]

    # identify numeric/categorical columns
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()

    print(f"[PREPROCESS] Preparing {len(numeric_cols)} numeric and {len(categorical_cols)} categorical features")
    print(f"[PREPROCESS] Target distribution: count={len(y)}, mean={y.mean():.2f}, std={y.std():.2f}")

    # create preprocessing pipeline
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer(transformers=[
        ('num', numeric_transformer, numeric_cols),
        ('cat', categorical_transformer, categorical_cols)
    ])

    return X, y, preprocessor


def train_models(X_train, X_test, y_train, y_test, preprocessor):
    """Train and evaluate Random Forest / XGBoost / LightGBM regression algorithms."""
    models = {}
    results = {}
    threshold = y_train.median()
    y_test_binary = (y_test > threshold).astype(int)

    if SKIP_RF:
        print("[TRAIN] SKIP_RF=True, skipping RandomForestRegressor")
    else:
        print("[TRAIN] Training RandomForestRegressor...")
        rf_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ))
        ])
        t0 = time.time()
        rf_pipeline.fit(X_train, y_train)
        rf_time = time.time() - t0
        rf_pred = rf_pipeline.predict(X_test)
        rf_pred_binary = (rf_pred > threshold).astype(int)
        models['random_forest'] = rf_pipeline
        results['random_forest'] = {
            'mae': mean_absolute_error(y_test, rf_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, rf_pred)),
            'r2': r2_score(y_test, rf_pred),
            'auc': roc_auc_score(y_test_binary, rf_pred),
            'precision': precision_score(y_test_binary, rf_pred_binary, zero_division=0),
            'accuracy': accuracy_score(y_test_binary, rf_pred_binary),
            'training_time_s': round(rf_time, 1),
        }
        print(f"[TRAIN] RF done ({rf_time:.1f}s)")

    # XGBoost regressor
    print("[TRAIN] Training XGBRegressor...")
    xgb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE
        ))
    ])
    t0 = time.time()
    xgb_pipeline.fit(X_train, y_train)
    xgb_time = time.time() - t0
    xgb_pred = xgb_pipeline.predict(X_test)
    xgb_pred_binary = (xgb_pred > threshold).astype(int)
    models['xgboost'] = xgb_pipeline
    results['xgboost'] = {
        'mae': mean_absolute_error(y_test, xgb_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, xgb_pred)),
        'r2': r2_score(y_test, xgb_pred),
        'auc': roc_auc_score(y_test_binary, xgb_pred),
        'precision': precision_score(y_test_binary, xgb_pred_binary, zero_division=0),
        'accuracy': accuracy_score(y_test_binary, xgb_pred_binary),
        'training_time_s': round(xgb_time, 1),
    }
    print(f"[TRAIN] XGB done ({xgb_time:.1f}s)")

    # LightGBM regressor
    print("[TRAIN] Training LGBMRegressor...")
    lgb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=7,
            learning_rate=0.1,
            num_leaves=31,
            random_state=RANDOM_STATE,
            verbose=-1,
        ))
    ])
    t0 = time.time()
    lgb_pipeline.fit(X_train, y_train)
    lgb_time = time.time() - t0
    lgb_pred = lgb_pipeline.predict(X_test)
    lgb_pred_binary = (lgb_pred > threshold).astype(int)
    models['lightgbm'] = lgb_pipeline
    results['lightgbm'] = {
        'mae': mean_absolute_error(y_test, lgb_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, lgb_pred)),
        'r2': r2_score(y_test, lgb_pred),
        'auc': roc_auc_score(y_test_binary, lgb_pred),
        'precision': precision_score(y_test_binary, lgb_pred_binary, zero_division=0),
        'accuracy': accuracy_score(y_test_binary, lgb_pred_binary),
        'training_time_s': round(lgb_time, 1),
    }
    print(f"[TRAIN] LGB done ({lgb_time:.1f}s)")

    return models, results


def save_models(models, results):
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_labels = {
        'xgboost': 'XGBoost',
        'lightgbm': 'LightGBM',
    }
    if not SKIP_RF:
        model_labels['random_forest'] = 'Random Forest'

    # Side-by-side comparison table
    print("\n" + "="*100)
    print(f"  {'MODEL':<18} {'MAE':>10}  {'RMSE':>10}  {'R²':>8}  {'AUC':>8}  {'Precision':>10}  {'Accuracy':>10}  {'Time':>7}")
    print("-"*100)
    for key in ['random_forest', 'xgboost', 'lightgbm']:
        if key not in results:
            continue
        res = results[key]
        t = res.get('training_time_s', 0)
        print(
            f"  {model_labels[key]:<18} {res['mae']:>10.2f}  {res['rmse']:>10.2f}  "
            f"{res['r2']:>8.4f}  {res['auc']:>8.4f}  {res['precision']:>10.4f}  {res['accuracy']:>10.4f}  {t:>6.1f}s"
        )
    print("="*100)

    # choose best model by R² score (primary regression metric)
    candidate_keys = ['xgboost', 'lightgbm']
    if not SKIP_RF:
        candidate_keys.insert(0, 'random_forest')
    candidate_keys = [k for k in candidate_keys if k in results]

    best_name = max(candidate_keys, key=lambda k: results[k]['r2'])
    best_model = models[best_name]
    print(f"  >>> BEST MODEL: {model_labels[best_name]} (R²={results[best_name]['r2']:.4f}, AUC={results[best_name]['auc']:.4f})")
    print("="*90)

    joblib.dump(best_model, os.path.join(MODEL_DIR, 'cost_prediction_model.pkl'))
    for name, model in models.items():
        joblib.dump(model, os.path.join(MODEL_DIR, f"{name}_model.pkl"))
    joblib.dump(results, os.path.join(MODEL_DIR, 'model_results.pkl'))

    # Save metadata for predict.py
    metadata = {
        'best_model_name': best_name,
        'results_summary': {k: {m: round(v, 4) for m, v in res.items()} for k, res in results.items()},
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, 'model_metadata.pkl'))
    print(f"[SAVE] Models saved. Production model: cost_prediction_model.pkl ({model_labels[best_name]})")


def main():
    print(" COST PREDICTION MODEL TRAINING STARTED")
    df = load_data()
    X, y, preprocessor = preprocess_data(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    print(f"[SPLIT] Train: {len(X_train)}, Test: {len(X_test)}")
    models, results = train_models(X_train, X_test, y_train, y_test, preprocessor)
    save_models(models, results)
    print("COST PREDICTION MODEL TRAINING COMPLETED")


if __name__ == "__main__":
    main()
