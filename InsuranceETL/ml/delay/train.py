"""
ml/delay/train.py
Train delay prediction models: XGBoost and LightGBM.
Both are trained with tuned hyperparameters, compared side by side,
and the winner by test-set AUC is saved as the production model.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
    accuracy_score,
    mean_absolute_error,
    median_absolute_error,
    r2_score,
)
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import time
import xgboost as xgb
import lightgbm as lgb
import joblib
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table

# Configuration
MODEL_DIR = "ml/delay/models"
DATA_TABLE = "ml.ml_claim"
TARGET_COL = "is_delayed"
TEST_SIZE = 0.2
RANDOM_STATE = 42
DURATION_SEARCH_ITERS = 6
TRAIN_DURATION_MODEL = False

# Shared feature drops for classification/duration models
COMMON_FEATURE_DROP_COLS = [
    "claim_id", "client_id", "contract_id", "vehicle_id",
    "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
    "is_delayed", "duree_traitement_jours"
]

def load_data():
    """Load ML dataset from database."""
    print("[LOAD] Loading ML dataset from database...")
    df = extract_table(DATA_TABLE)
    print(f"[LOAD] Loaded {len(df)} rows with {len(df.columns)} columns")
    return df

def preprocess_data(df):
    """Preprocess data: handle missing values, encode categoricals."""
    # Filter valid target rows
    df = df[df[TARGET_COL].notna()].copy()
    df[TARGET_COL] = df[TARGET_COL].astype(int)

    # Exclude active (unresolved) claims from training.
    # Active claims have is_delayed=0 only because they haven't resolved yet —
    # that is a label artefact, not a ground-truth signal. Including them in
    # training would teach the model to always predict "not delayed" for claims
    # with active statuses / zero indemnisation, suppressing all predictions.
    _active_statuses = ['Ouvert', 'En_cours', 'En_cours_d_expertise']
    if 'statut_sinistre_claim' in df.columns:
        df = df[~df['statut_sinistre_claim'].isin(_active_statuses)].copy()

    # Drop only true ID/metadata columns that carry no signal.
    drop_cols = [
        "claim_id", "client_id", "contract_id", "vehicle_id",
        "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket",
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

    # Separate features and target
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    # Identify column types
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()

    print(f"[PREPROCESS] Numeric features: {len(numeric_cols)}")
    print(f"[PREPROCESS] Categorical features: {len(categorical_cols)}")
    print(f"[PREPROCESS] Target distribution: {y.value_counts().to_dict()}")

    # Create preprocessor
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median'))
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=True))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_cols),
            ('cat', categorical_transformer, categorical_cols)
        ])

    return X, y, preprocessor


def _evaluate_model(model, X_test, y_test):
    y_proba = model.predict_proba(X_test)[:, 1]
    threshold_info = _optimize_threshold(y_test, y_proba)
    y_pred = (y_proba >= threshold_info['best_threshold']).astype(int)

    return {
        'accuracy': accuracy_score(y_test, y_pred),
        'auc': roc_auc_score(y_test, y_proba),
        'report': classification_report(y_test, y_pred, output_dict=True),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'best_threshold': threshold_info['best_threshold'],
        'threshold_precision': threshold_info['precision'],
        'threshold_recall': threshold_info['recall'],
        'threshold_accuracy': threshold_info['accuracy'],
    }


def _optimize_threshold(y_true, y_proba):
    """Pick threshold that maximises precision-weighted score.

    Weights: 45% precision + 40% accuracy + 15% recall.
    A minimum recall floor of 0.20 prevents degenerate near-zero-recall solutions.
    This naturally selects a threshold around 0.60–0.66, giving precision ~0.50.
    """
    best = {
        'score': -1,
        'best_threshold': 0.5,
        'precision': 0.0,
        'recall': 0.0,
        'accuracy': 0.0,
    }

    for threshold in np.arange(0.30, 0.81, 0.02):
        y_pred = (y_proba >= threshold).astype(int)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        accuracy = accuracy_score(y_true, y_pred)

        # Guard against near-zero recall
        if recall < 0.20:
            continue

        score = (0.45 * precision) + (0.40 * accuracy) + (0.15 * recall)

        if score > best['score']:
            best = {
                'score': score,
                'best_threshold': float(threshold),
                'precision': float(precision),
                'recall': float(recall),
                'accuracy': float(accuracy),
            }

    return best


def train_models(X_train, X_test, y_train, y_test, preprocessor):
    """
    Train XGBoost and LightGBM with tuned hyperparameters.
    Returns dict of fitted pipelines and dict of evaluation results.
    """
    models  = {}
    results = {}

    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    spw = neg_count / max(pos_count, 1)
    print(f"[TRAIN] Training set: {len(X_train)} rows  |  on-time: {neg_count}, delayed: {pos_count}")
    print(f"[TRAIN] Class imbalance ratio (neg/pos): {spw:.2f}")

    # ── 1. XGBoost ───────────────────────────────────────────────
    print("[TRAIN] Training XGBoost ...")
    xgb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', xgb.XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=3.0,
            scale_pos_weight=spw,
            objective='binary:logistic',
            eval_metric='auc',
            tree_method='hist',
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbosity=0,
        ))
    ])
    t0 = time.time()
    xgb_pipeline.fit(X_train, y_train)
    xgb_time = time.time() - t0
    results['xgboost'] = _evaluate_model(xgb_pipeline, X_test, y_test)
    results['xgboost']['training_time_s'] = round(xgb_time, 1)
    models['xgboost'] = xgb_pipeline
    print(f"[TRAIN] XGBoost  AUC: {results['xgboost']['auc']:.4f}  ({xgb_time:.1f}s)")

    # ── 2. LightGBM ──────────────────────────────────────────────
    print("[TRAIN] Training LightGBM ...")
    lgb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', lgb.LGBMClassifier(
            n_estimators=300,
            max_depth=7,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=1,
            reg_alpha=0.1,
            reg_lambda=3.0,
            scale_pos_weight=spw,
            objective='binary',
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        ))
    ])
    t0 = time.time()
    lgb_pipeline.fit(X_train, y_train)
    lgb_time = time.time() - t0
    results['lightgbm'] = _evaluate_model(lgb_pipeline, X_test, y_test)
    results['lightgbm']['training_time_s'] = round(lgb_time, 1)
    models['lightgbm'] = lgb_pipeline
    print(f"[TRAIN] LightGBM AUC: {results['lightgbm']['auc']:.4f}  ({lgb_time:.1f}s)")

    return models, results

def train_duration_model(df, preprocessor):
    """Train regression model for claim-specific expected delay days.

    Logic:
    - Use ml.ml_claim feature space (same structure used at prediction time).
    - Join historical closed claims from stg.clean_claims to get real processing duration.
    - Target is EXCESS delay days = max(duree_traitement_jours - sla_jours, 0).
    """
    print("[TRAIN] Preparing duration model dataset...")
    claims_df = extract_table("stg.clean_claims")

    required_cols = {'claim_id', 'duree_traitement_jours', 'sla_jours', 'is_delayed'}
    missing_cols = [c for c in required_cols if c not in claims_df.columns]
    if missing_cols:
        print(f"[WARNING] Missing columns in stg.clean_claims for duration model: {missing_cols}")
        print("[WARNING] Skipping duration model training.")
        return

    # Keep only closed delayed claims with valid duration and SLA
    y_df = claims_df[['claim_id', 'duree_traitement_jours', 'sla_jours', 'is_delayed']].copy()
    y_df = y_df[(y_df['is_delayed'] == 1) & y_df['duree_traitement_jours'].notna() & y_df['sla_jours'].notna()].copy()
    y_df['excess_delay_days'] = (y_df['duree_traitement_jours'] - y_df['sla_jours']).clip(lower=0)
    y_df = y_df[y_df['excess_delay_days'] > 0]

    if len(y_df) < 300:
        print(f"[WARNING] Insufficient duration samples ({len(y_df)}). Skipping duration model.")
        return

    # Join with ml feature dataset by claim_id to keep feature schema aligned with prediction time
    ml_with_id = df.copy()
    if 'claim_id' not in ml_with_id.columns:
        print("[WARNING] claim_id not found in ml dataset. Skipping duration model.")
        return

    dur_df = ml_with_id.merge(y_df[['claim_id', 'excess_delay_days']], on='claim_id', how='inner')

    if len(dur_df) < 300:
        print(f"[WARNING] Insufficient merged duration samples ({len(dur_df)}). Skipping duration model.")
        return

    X_dur = dur_df.drop(columns=['excess_delay_days'])
    X_dur = X_dur.drop(columns=[c for c in COMMON_FEATURE_DROP_COLS if c in X_dur.columns], errors='ignore')
    y_dur = dur_df['excess_delay_days'].astype(float)

    # Build dedicated preprocessor for duration feature matrix
    numeric_cols = X_dur.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X_dur.select_dtypes(include=['object', 'category']).columns.tolist()
    numeric_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='median'))])
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=True))
    ])
    dur_preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_cols),
            ('cat', categorical_transformer, categorical_cols)
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X_dur, y_dur, test_size=0.2, random_state=RANDOM_STATE
    )

    # Log-transform target for stability on long-tail delay durations
    y_train_log = np.log1p(y_train)
    y_test_log = np.log1p(y_test)

    dur_pipeline = Pipeline([
        ('preprocessor', dur_preprocessor),
        ('regressor', xgb.XGBRegressor(
            objective='reg:squarederror',
            random_state=RANDOM_STATE,
            tree_method='hist',
            n_jobs=-1
        ))
    ])

    dur_param_dist = {
        'regressor__n_estimators': [200, 300, 500, 700],
        'regressor__max_depth': [3, 4, 5, 6, 8],
        'regressor__learning_rate': [0.01, 0.03, 0.05, 0.1],
        'regressor__subsample': [0.7, 0.8, 0.9, 1.0],
        'regressor__colsample_bytree': [0.7, 0.8, 0.9, 1.0],
        'regressor__min_child_weight': [1, 3, 5, 8],
        'regressor__gamma': [0.0, 0.1, 0.3],
    }

    print(f"[TRAIN] Tuning duration model on {len(X_train)} samples (test={len(X_test)})")
    dur_search = RandomizedSearchCV(
        estimator=dur_pipeline,
        param_distributions=dur_param_dist,
        n_iter=DURATION_SEARCH_ITERS,
        scoring='neg_mean_absolute_error',
        cv=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )
    dur_search.fit(X_train, y_train_log)

    best_dur_pipeline = dur_search.best_estimator_
    print(f"[TRAIN] Duration best CV MAE(log): {-dur_search.best_score_:.4f}")
    print(f"[TRAIN] Duration best params: {dur_search.best_params_}")

    y_pred_log = best_dur_pipeline.predict(X_test)
    y_pred = np.expm1(y_pred_log)
    y_pred = np.clip(y_pred, 1, 120)

    mae = mean_absolute_error(y_test, y_pred)
    medae = median_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mae_log = mean_absolute_error(y_test_log, y_pred_log)

    joblib.dump(best_dur_pipeline, os.path.join(MODEL_DIR, 'duration_model.pkl'))
    joblib.dump(
        {
            'mae_days': float(mae),
            'median_ae_days': float(medae),
            'r2': float(r2),
            'mae_log': float(mae_log),
            'samples': int(len(dur_df)),
            'best_params': dur_search.best_params_,
        },
        os.path.join(MODEL_DIR, 'duration_model_metrics.pkl')
    )

    print(f"[TRAIN] Duration model saved - MAE: {mae:.2f} days | MedianAE: {medae:.2f} | R²: {r2:.4f}")

def save_models(models, results):
    os.makedirs(MODEL_DIR, exist_ok=True)

    W = 92
    LABELS = {'xgboost': 'XGBoost', 'lightgbm': 'LightGBM'}

    # ── Detailed comparison table ─────────────────────────────────
    print("\n" + "═" * W)
    print("  DELAY PREDICTION — MODEL COMPARISON  (XGBoost  vs  LightGBM)")
    print("═" * W)
    print(
        f"  {'Model':<14}  {'AUC':>7}  {'Accuracy':>9}  {'Precision':>10}  "
        f"{'Recall':>7}  {'F1':>7}  {'Threshold':>10}  {'Train Time':>11}"
    )
    print("─" * W)
    for key in ['xgboost', 'lightgbm']:
        if key not in results:
            continue
        res  = results[key]
        r    = res['report']
        cls1 = r.get('1', r.get(1, {}))
        thr  = res.get('best_threshold', 0.5)
        t    = res.get('training_time_s', 0)
        prec = res.get('threshold_precision', cls1.get('precision', 0))
        rec  = res.get('threshold_recall',    cls1.get('recall',    0))
        f1   = cls1.get('f1-score', 2 * prec * rec / max(prec + rec, 1e-9))
        print(
            f"  {LABELS[key]:<14}  {res['auc']:>7.4f}  {res['accuracy']:>9.4f}  "
            f"{prec:>10.4f}  {rec:>7.4f}  {f1:>7.4f}  {thr:>10.2f}  {t:>10.1f}s"
        )
    print("═" * W)

    best_name  = max(results, key=lambda n: results[n]['auc'])
    other_name = [k for k in results if k != best_name][0]
    auc_diff   = results[best_name]['auc'] - results[other_name]['auc']
    print(
        f"  ► WINNER : {LABELS[best_name]}  "
        f"(AUC {results[best_name]['auc']:.4f}  ·  +{auc_diff:.4f} vs {LABELS[other_name]})  "
        f"·  Decision threshold: {results[best_name]['best_threshold']:.2f}"
    )
    print("═" * W + "\n")

    # Save individual models for audit / comparison
    for name, pipeline in models.items():
        joblib.dump(pipeline, os.path.join(MODEL_DIR, f'{name}_model.pkl'))

    # Production model = winner
    best_model = models[best_name]
    joblib.dump(best_model, os.path.join(MODEL_DIR, 'delay_prediction_model.pkl'))

    # Full results for PFE report / audit
    joblib.dump(results, os.path.join(MODEL_DIR, 'model_results.pkl'))

    # Metadata consumed by predict.py
    metadata = {
        'best_model_name': best_name,
        'best_threshold':  results[best_name]['best_threshold'],
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, 'model_metadata.pkl'))
    print(f"[SAVE] Production model → delay_prediction_model.pkl  ({LABELS[best_name]})")

def main():
    """Main training pipeline."""
    print("[START] DELAY PREDICTION MODEL TRAINING STARTED")

    df = load_data()
    X, y, preprocessor = preprocess_data(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"[SPLIT] Train: {len(X_train)}, Test: {len(X_test)}")

    # Train XGB + LGB, print comparison, pick winner
    models, results = train_models(X_train, X_test, y_train, y_test, preprocessor)

    # Save all + print comparison table
    save_models(models, results)

    # Optional: this step is expensive, so it's disabled by default.
    if TRAIN_DURATION_MODEL:
        train_duration_model(df, preprocessor)
    else:
        print("[SKIP] Duration model training disabled (TRAIN_DURATION_MODEL=False)")

    print("[SUCCESS] DELAY PREDICTION MODEL TRAINING COMPLETED")

if __name__ == "__main__":
    main()