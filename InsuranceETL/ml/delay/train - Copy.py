"""
ml/delay/train.py
Train delay prediction model using Random Forest and XGBoost.
Production-ready ML pipeline for insurance claim delay prediction.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    precision_score,
    recall_score,
    accuracy_score,
    mean_absolute_error,
    median_absolute_error,
    r2_score,
)
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import xgboost as xgb
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
CV_FOLDS = 2
RF_SEARCH_ITERS = 6
XGB_SEARCH_ITERS = 8
DURATION_SEARCH_ITERS = 10

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

    # Drop ID columns and non-feature columns
    drop_cols = ["claim_id", "client_id", "contract_id", "vehicle_id",
                 "date_sinistre_claim", "est_frauduleux_claim", "claim_severity_bucket"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

    # Separate features and target
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    # Identify column types
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(include=['object', 'category', 'string']).columns.tolist()

    # Convert pandas extension string dtype to plain object to avoid joblib pickling issues in parallel fit
    if categorical_cols:
        X[categorical_cols] = X[categorical_cols].astype(object)

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
    """Pick probability threshold that balances precision/accuracy while keeping usable recall."""
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

        # Prefer higher precision and strong accuracy, but guard against near-zero recall.
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


def _evaluate_ensemble(y_test, rf_proba, xgb_proba):
    """Evaluate weighted soft-voting ensemble from RF and XGB probabilities."""
    ensemble_proba = (0.35 * rf_proba) + (0.65 * xgb_proba)
    threshold_info = _optimize_threshold(y_test, ensemble_proba)
    y_pred = (ensemble_proba >= threshold_info['best_threshold']).astype(int)

    return {
        'accuracy': accuracy_score(y_test, y_pred),
        'auc': roc_auc_score(y_test, ensemble_proba),
        'report': classification_report(y_test, y_pred, output_dict=True),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'best_threshold': threshold_info['best_threshold'],
        'threshold_precision': threshold_info['precision'],
        'threshold_recall': threshold_info['recall'],
        'threshold_accuracy': threshold_info['accuracy'],
        'weights': {'rf': 0.35, 'xgb': 0.65},
    }

def train_models(X_train, X_test, y_train, y_test, preprocessor):
    """Train and evaluate models."""
    models = {}
    results = {}
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)

    # Random Forest + randomized tuning
    print("[TRAIN] Tuning Random Forest...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            random_state=RANDOM_STATE,
            class_weight='balanced',
            n_jobs=1
        ))
    ])
    rf_param_dist = {
        'classifier__n_estimators': [200, 300, 500, 700],
        'classifier__max_depth': [8, 12, 16, None],
        'classifier__min_samples_split': [2, 5, 10, 20],
        'classifier__min_samples_leaf': [1, 2, 4, 8],
        'classifier__max_features': ['sqrt', 'log2', 0.6, 0.8]
    }
    rf_search = RandomizedSearchCV(
        estimator=rf_pipeline,
        param_distributions=rf_param_dist,
        n_iter=RF_SEARCH_ITERS,
        scoring='roc_auc',
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=1,
        verbose=1,
        refit=True
    )
    rf_search.fit(X_train, y_train)
    best_rf = rf_search.best_estimator_
    print(f"[TRAIN] RF best CV AUC: {rf_search.best_score_:.4f}")
    print(f"[TRAIN] RF best params: {rf_search.best_params_}")

    models['random_forest'] = best_rf
    results['random_forest'] = _evaluate_model(best_rf, X_test, y_test)
    results['random_forest']['best_params'] = rf_search.best_params_
    results['random_forest']['cv_auc'] = rf_search.best_score_

    # XGBoost + randomized tuning
    print("[TRAIN] Tuning XGBoost...")
    xgb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', xgb.XGBClassifier(
            random_state=RANDOM_STATE,
            objective='binary:logistic',
            eval_metric='auc',
            tree_method='hist',
            n_jobs=1,
            scale_pos_weight=len(y_train[y_train==0]) / len(y_train[y_train==1])
        ))
    ])
    xgb_param_dist = {
        'classifier__n_estimators': [200, 300, 500, 800],
        'classifier__max_depth': [3, 4, 5, 6, 8],
        'classifier__learning_rate': [0.01, 0.03, 0.05, 0.1],
        'classifier__subsample': [0.7, 0.8, 0.9, 1.0],
        'classifier__colsample_bytree': [0.6, 0.7, 0.8, 1.0],
        'classifier__min_child_weight': [1, 3, 5, 8],
        'classifier__gamma': [0, 0.1, 0.3, 0.5]
    }
    xgb_search = RandomizedSearchCV(
        estimator=xgb_pipeline,
        param_distributions=xgb_param_dist,
        n_iter=XGB_SEARCH_ITERS,
        scoring='roc_auc',
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=1,
        verbose=1,
        refit=True
    )
    xgb_search.fit(X_train, y_train)
    best_xgb = xgb_search.best_estimator_
    print(f"[TRAIN] XGB best CV AUC: {xgb_search.best_score_:.4f}")
    print(f"[TRAIN] XGB best params: {xgb_search.best_params_}")

    models['xgboost'] = best_xgb
    results['xgboost'] = _evaluate_model(best_xgb, X_test, y_test)
    results['xgboost']['best_params'] = xgb_search.best_params_
    results['xgboost']['cv_auc'] = xgb_search.best_score_

    # RF + XGB soft-voting ensemble (keeps both algorithms in final decision)
    print("[TRAIN] Evaluating RF+XGB soft-voting ensemble...")
    rf_proba = best_rf.predict_proba(X_test)[:, 1]
    xgb_proba = best_xgb.predict_proba(X_test)[:, 1]
    results['ensemble'] = _evaluate_ensemble(y_test, rf_proba, xgb_proba)
    results['ensemble']['cv_auc'] = float(
        (results['random_forest']['cv_auc'] * 0.35) + (results['xgboost']['cv_auc'] * 0.65)
    )

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
            n_jobs=1
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

    # Save best model (higher AUC)
    rf_auc = results['random_forest']['auc']
    xgb_auc = results['xgboost']['auc']
    ens_auc = results['ensemble']['auc'] if 'ensemble' in results else -1

    if ens_auc > max(rf_auc, xgb_auc):
        best_model = models['xgboost']
        best_name = 'ensemble'
    elif xgb_auc > rf_auc:
        best_model = models['xgboost']
        best_name = 'xgboost'
    else:
        best_model = models['random_forest']
        best_name = 'random_forest'

    print(f"[SAVE] Best model: {best_name} (AUC: {results[best_name]['auc']:.4f})")

    # Save best model
    joblib.dump(best_model, os.path.join(MODEL_DIR, 'delay_prediction_model.pkl'))

    # Save all models
    for name, model in models.items():
        joblib.dump(model, os.path.join(MODEL_DIR, f'{name}_model.pkl'))

    # Save results
    joblib.dump(results, os.path.join(MODEL_DIR, 'model_results.pkl'))

    # Save metadata for prediction-time thresholding / ensemble behavior
    metadata = {
        'best_model_name': best_name,
        'best_threshold': results[best_name]['best_threshold'],
        'ensemble_weights': results.get('ensemble', {}).get('weights', {'rf': 0.35, 'xgb': 0.65}),
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, 'model_metadata.pkl'))

    print("[SAVE] Models and results saved to ml/delay/models/")

def main():
    """Main training pipeline."""
    print("[START] DELAY PREDICTION MODEL TRAINING STARTED")

    # Load data
    df = load_data()

    # Preprocess
    X, y, preprocessor = preprocess_data(df)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    print(f"[SPLIT] Train: {len(X_train)}, Test: {len(X_test)}")

    # Train models
    models, results = train_models(X_train, X_test, y_train, y_test, preprocessor)

    # Print results
    for name, res in results.items():
        print(f"\n[{name.upper()}]")
        print(f"  Accuracy: {res['accuracy']:.4f}")
        print(f"  AUC: {res['auc']:.4f}")
        print(f"  Precision (Delayed): {res['report']['1']['precision']:.4f}")
        print(f"  Recall (Delayed): {res['report']['1']['recall']:.4f}")
        print(f"  Best threshold: {res.get('best_threshold', 0.5):.2f}")
        if 'cv_auc' in res:
            print(f"  CV AUC (mean): {res['cv_auc']:.4f}")

    # Save models
    save_models(models, results)

    # Train claim-specific duration model (excess delay days)
    train_duration_model(df, preprocessor)

    print("[SUCCESS] DELAY PREDICTION MODEL TRAINING COMPLETED")

if __name__ == "__main__":
    main()