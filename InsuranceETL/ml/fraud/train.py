"""
ml/fraud/train.py
Train fraud detection models: XGBoost and LightGBM.
Both are trained with tuned hyperparameters, compared side by side,
and the winner is saved as the production model.
"""

from __future__ import annotations

import json
import os
import sys
import importlib
from datetime import datetime
from typing import Dict, Tuple, Any, List

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import time

# Optional gradient boosting models (keep training robust even if unavailable)
try:
    xgb = importlib.import_module("xgboost")
except Exception:  # pragma: no cover
    xgb = None

try:
    lgb = importlib.import_module("lightgbm")
except Exception:  # pragma: no cover
    lgb = None


project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table


MODEL_DIR = "ml/fraud/models"
DATA_TABLE = "ml.ml_claim"
TARGET_COL = "est_frauduleux_claim"
TEST_SIZE = 0.2
RANDOM_STATE = 42
MIN_PRECISION_TARGET = 0.40
MIN_RECALL_TARGET = 0.30
MAX_INVESTIGATION_RATE = 0.20

# Agent cost calculation (Tunisia - TND)
AGENT_MONTHLY_SALARY = 3000.0  # TND
AGENT_MONTHLY_WORKING_HOURS = 160.0  # hours
AGENT_HOURLY_RATE = AGENT_MONTHLY_SALARY / AGENT_MONTHLY_WORKING_HOURS  # TND/hour
BASE_INVESTIGATION_HOURS = 1.5  # baseline hours for any fraudulent case
MAX_INVESTIGATION_HOURS = 7.5  # maximum hours for highest risk cases


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


def load_data() -> pd.DataFrame:
    print("[LOAD] Loading ML dataset from database...")
    df = extract_table(DATA_TABLE)
    print(f"[LOAD] Loaded {len(df)} rows with {len(df.columns)} columns")
    return df


def preprocess_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, ColumnTransformer, Dict[str, Any]]:
    df = df[df[TARGET_COL].notna()].copy()
    df[TARGET_COL] = df[TARGET_COL].astype(int)

    fraud_count = int(df[TARGET_COL].sum())
    fraud_rate = (fraud_count / len(df)) * 100 if len(df) else 0
    print(f"[PREPROCESS] Fraud rate: {fraud_count}/{len(df)} ({fraud_rate:.2f}%)")

    leakage_or_non_feature_cols = [
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
    ]

    X = df.drop(columns=[TARGET_COL] + [c for c in leakage_or_non_feature_cols if c in df.columns], errors="ignore")
    y = df[TARGET_COL]

    numeric_cols = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

    print(f"[PREPROCESS] Numeric features: {len(numeric_cols)} | Categorical features: {len(categorical_cols)}")

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]),
                numeric_cols,
            ),
            (
                "cat",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, max_categories=12)),
                ]),
                categorical_cols,
            ),
        ],
        remainder="drop",
    )

    amount_col = _find_amount_column(df)
    avg_claim_amount = float(df[amount_col].fillna(0).mean()) if amount_col else 0.0
    avg_fraud_amount = float(df.loc[df[TARGET_COL] == 1, amount_col].fillna(0).mean()) if amount_col else avg_claim_amount

    dataset_profile = {
        "n_rows": int(len(df)),
        "fraud_count": fraud_count,
        "fraud_rate": fraud_rate,
        "amount_column": amount_col,
        "avg_claim_amount": avg_claim_amount,
        "avg_fraud_amount": avg_fraud_amount,
    }

    return X, y, preprocessor, dataset_profile


def _threshold_metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float) -> Dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    specificity = tn / (tn + fp) if (tn + fp) else 0.0

    return {
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "specificity": float(specificity),
    }


def _estimate_case_hours(fraud_probability: float) -> float:
    """Estimate hours to investigate case based on fraud probability.
    Higher probability = more complex investigation = more hours.
    """
    return BASE_INVESTIGATION_HOURS + (fraud_probability * (MAX_INVESTIGATION_HOURS - BASE_INVESTIGATION_HOURS))


def _optimize_threshold(
    y_true: pd.Series,
    y_prob: np.ndarray,
    avg_fraud_amount: float,
    prevented_loss_ratio: float = 0.70,
    min_precision_target: float = MIN_PRECISION_TARGET,
    min_recall_target: float = MIN_RECALL_TARGET,
    max_investigation_rate: float = MAX_INVESTIGATION_RATE,
) -> Dict[str, Any]:
    thresholds = np.linspace(0.10, 0.90, 33)
    candidates: List[Dict[str, Any]] = []

    for threshold in thresholds:
        metric = _threshold_metrics(y_true, y_prob, threshold)
        tp = metric["tp"]
        fp = metric["fp"]
        fn = metric["fn"]
        flagged_indices = (y_prob >= threshold)
        flagged_predictions = y_prob[flagged_indices]
        flagged_count = flagged_indices.sum()
        investigation_rate = flagged_count / len(y_true) if len(y_true) else 0.0

        # Calculate review cost based on estimated hours per case
        estimated_flagged_hours = sum(_estimate_case_hours(p) for p in flagged_predictions) if len(flagged_predictions) > 0 else 0.0
        review_cost = estimated_flagged_hours * AGENT_HOURLY_RATE

        prevented_loss = tp * avg_fraud_amount * prevented_loss_ratio
        residual_loss = fn * avg_fraud_amount
        net_value = prevented_loss - review_cost

        metric.update(
            {
                "prevented_loss": float(prevented_loss),
                "estimated_investigation_hours": float(estimated_flagged_hours),
                "review_cost": float(review_cost),
                "residual_loss": float(residual_loss),
                "net_value": float(net_value),
                "flagged_count": int(flagged_count),
                "investigation_rate": float(investigation_rate),
            }
        )
        candidates.append(metric)

    precision_first_pool = [
        c
        for c in candidates
        if (
            c["precision"] >= min_precision_target
            and c["recall"] >= min_recall_target
            and c["investigation_rate"] <= max_investigation_rate
        )
    ]

    balanced_pool = [
        c
        for c in candidates
        if c["recall"] >= 0.70 and c["precision"] >= 0.20
    ]

    selected_pool = precision_first_pool if precision_first_pool else candidates
    precision_first = max(selected_pool, key=lambda c: (c["precision"], c["net_value"], c["f1_score"]))

    balanced_selected = balanced_pool if balanced_pool else candidates
    balanced = max(balanced_selected, key=lambda c: (c["net_value"], c["f1_score"]))

    return {
        "recommended_threshold": float(precision_first["threshold"]),
        "recommended_metrics": precision_first,
        "operating_points": {
            "precision_first": precision_first,
            "balanced": balanced,
        },
        "threshold_scan": candidates,
        "assumptions": {
            "currency": "TND (Tunisian Dinar)",
            "agent_monthly_salary": AGENT_MONTHLY_SALARY,
            "agent_monthly_working_hours": AGENT_MONTHLY_WORKING_HOURS,
            "agent_hourly_rate": AGENT_HOURLY_RATE,
            "base_investigation_hours": BASE_INVESTIGATION_HOURS,
            "max_investigation_hours": MAX_INVESTIGATION_HOURS,
            "prevented_loss_ratio": prevented_loss_ratio,
            "avg_fraud_amount": float(avg_fraud_amount),
            "min_precision_target": min_precision_target,
            "min_recall_target": min_recall_target,
            "max_investigation_rate": max_investigation_rate,
        },
    }


def evaluate_model(y_test: pd.Series, y_prob: np.ndarray) -> Dict[str, Any]:
    p, r, _ = precision_recall_curve(y_test, y_prob)
    pr_auc = auc(r, p)

    default_metrics = _threshold_metrics(y_test, y_prob, threshold=0.5)
    default_pred = (y_prob >= 0.5).astype(int)

    return {
        "auc": float(roc_auc_score(y_test, y_prob)),
        "pr_auc": float(pr_auc),
        "default_threshold_metrics": default_metrics,
        "classification_report": classification_report(y_test, default_pred, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, default_pred).tolist(),
    }


def train_models(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    preprocessor: ColumnTransformer,
    dataset_profile: Dict[str, Any],
) -> Tuple[Dict[str, Pipeline], Dict[str, Dict[str, Any]]]:
    models: Dict[str, Pipeline] = {}
    results: Dict[str, Dict[str, Any]] = {}

    positives = int((y_train == 1).sum())
    negatives = int((y_train == 0).sum())
    imbalance_ratio = (negatives / positives) if positives else 1.0

    print(f"[TRAIN] Class imbalance ratio (neg/pos): {imbalance_ratio:.2f}")

    candidate_models: Dict[str, Any] = {}

    if xgb is not None:
        candidate_models["xgboost"] = xgb.XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=RANDOM_STATE,
            scale_pos_weight=imbalance_ratio,
            eval_metric="logloss",
            n_jobs=-1,
        )
    else:
        print("[WARNING] XGBoost not available — skipping")

    if lgb is not None:
        candidate_models["lightgbm"] = lgb.LGBMClassifier(
            n_estimators=250,
            max_depth=7,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=RANDOM_STATE,
            scale_pos_weight=imbalance_ratio,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        print("[WARNING] LightGBM not available — skipping")

    for model_name, estimator in candidate_models.items():
        print(f"[TRAIN] Training {model_name}...")
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", estimator),
        ])

        t0 = time.time()
        pipeline.fit(X_train, y_train)
        train_time = time.time() - t0
        y_prob = pipeline.predict_proba(X_test)[:, 1]

        model_eval = evaluate_model(y_test, y_prob)
        threshold_bundle = _optimize_threshold(
            y_test,
            y_prob,
            avg_fraud_amount=max(dataset_profile["avg_fraud_amount"], 1.0),
        )

        optimized = threshold_bundle["operating_points"]["precision_first"]
        balanced = threshold_bundle["operating_points"]["balanced"]

        selection_score = (
            (model_eval["auc"] * 0.35)
            + (optimized["recall"] * 0.35)
            + (optimized["precision"] * 0.20)
            + (optimized["f1_score"] * 0.10)
        )

        results[model_name] = {
            **model_eval,
            "optimized_threshold": threshold_bundle,
            "selection_score": float(selection_score),
            "training_time_s": round(train_time, 1),
        }
        models[model_name] = pipeline

        print(
            f"  AUC={model_eval['auc']:.4f} | PR-AUC={model_eval['pr_auc']:.4f} | Time={train_time:.1f}s | "
            f"Threshold={optimized['threshold']:.2f} | Recall={optimized['recall']:.3f} | "
            f"Precision={optimized['precision']:.3f} | NetValue={optimized['net_value']:.2f} TND | "
            f"Hours={optimized['estimated_investigation_hours']:.1f} | QueueRate={optimized['investigation_rate']:.3f}"
        )
        print(
            f"  BalancedPoint -> Threshold={balanced['threshold']:.2f}, "
            f"Recall={balanced['recall']:.3f}, Precision={balanced['precision']:.3f}, "
            f"NetValue={balanced['net_value']:.2f} TND, Hours={balanced['estimated_investigation_hours']:.1f}"
        )

    return models, results


def get_feature_importance(model: Pipeline) -> Dict[str, Any]:
    try:
        classifier = model.named_steps["classifier"]
        if not hasattr(classifier, "feature_importances_"):
            return {"feature_names": [], "importances": []}

        preprocessor = model.named_steps["preprocessor"]
        feature_names = preprocessor.get_feature_names_out()
        importances = classifier.feature_importances_

        top_idx = np.argsort(importances)[::-1][:20]
        return {
            "feature_names": [str(feature_names[i]) for i in top_idx],
            "importances": [float(importances[i]) for i in top_idx],
        }
    except Exception:
        return {"feature_names": [], "importances": []}


def save_artifacts(
    models: Dict[str, Pipeline],
    results: Dict[str, Dict[str, Any]],
    dataset_profile: Dict[str, Any],
) -> Tuple[str, Pipeline]:
    os.makedirs(MODEL_DIR, exist_ok=True)

    W = 100
    LABELS = {'xgboost': 'XGBoost', 'lightgbm': 'LightGBM'}

    # ── Detailed comparison table ─────────────────────────────────
    print("\n" + "═" * W)
    print("  FRAUD DETECTION — MODEL COMPARISON  (XGBoost  vs  LightGBM)")
    print("═" * W)
    print(
        f"  {'Model':<14}  {'AUC':>7}  {'PR-AUC':>7}  {'Accuracy':>9}  "
        f"{'Precision':>10}  {'Recall':>7}  {'F1':>7}  {'Threshold':>10}  {'Train Time':>11}"
    )
    print("─" * W)
    for key in ['xgboost', 'lightgbm']:
        if key not in results:
            continue
        res  = results[key]
        opt  = res["optimized_threshold"]["operating_points"]["precision_first"]
        t    = res.get("training_time_s", 0)
        cr   = res.get("classification_report", {})
        cls1 = cr.get("1", cr.get(1, {}))
        acc  = cls1.get("support", 0)   # placeholder fallback
        # accuracy from default threshold report
        acc_val = res.get("default_threshold_metrics", {}).get("tp", 0)
        # use weighted avg accuracy approximation
        wa  = cr.get("accuracy", cr.get("weighted avg", {}).get("f1-score", 0))
        print(
            f"  {LABELS.get(key, key):<14}  {res['auc']:>7.4f}  {res['pr_auc']:>7.4f}  {wa:>9.4f}  "
            f"{opt['precision']:>10.4f}  {opt['recall']:>7.4f}  {opt['f1_score']:>7.4f}  "
            f"{opt['threshold']:>10.2f}  {t:>10.1f}s"
        )
    print("═" * W)

    best_name = max(results.keys(), key=lambda name: results[name]["selection_score"])
    if len(results) >= 2:
        other_name = [k for k in results if k != best_name][0]
        auc_diff   = results[best_name]["auc"] - results[other_name]["auc"]
        print(
            f"  ► WINNER : {LABELS.get(best_name, best_name)}  "
            f"(AUC {results[best_name]['auc']:.4f}  ·  +{auc_diff:.4f} vs {LABELS.get(other_name, other_name)})  "
            f"·  Threshold: {results[best_name]['optimized_threshold']['recommended_threshold']:.2f}"
        )
    else:
        print(f"  ► WINNER : {LABELS.get(best_name, best_name)}")
    print("═" * W + "\n")

    best_model     = models[best_name]
    best_model_path = os.path.join(MODEL_DIR, "fraud_detection_model.pkl")
    joblib.dump(best_model, best_model_path)

    for model_name, pipeline in models.items():
        joblib.dump(pipeline, os.path.join(MODEL_DIR, f"fraud_{model_name}_model.pkl"))

    feature_importance = get_feature_importance(best_model)

    training_results = {
        "training_date":     datetime.now().isoformat(),
        "best_model":        best_name,
        "dataset_profile":   dataset_profile,
        "feature_importance": feature_importance,
        "results":           results,
        "config": {
            "data_table":     DATA_TABLE,
            "target_column":  TARGET_COL,
            "test_size":      TEST_SIZE,
            "random_state":   RANDOM_STATE,
        },
    }

    with open(os.path.join(MODEL_DIR, "training_results.json"), "w", encoding="utf-8") as f:
        json.dump(training_results, f, indent=2, default=str)

    print(f"[SAVE] Production model → fraud_detection_model.pkl  ({LABELS.get(best_name, best_name)})")
    print(f"[SAVE] Training metadata → {os.path.join(MODEL_DIR, 'training_results.json')}")

    return best_name, best_model


def main() -> None:
    print("\n" + "=" * 70)
    print("INSURANCE FRAUD DETECTION - MODEL TRAINING")
    print("=" * 70)

    df = load_data()
    X, y, preprocessor, dataset_profile = preprocess_data(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(f"[SPLIT] Train={len(X_train)} | Test={len(X_test)}")

    models, results = train_models(X_train, X_test, y_train, y_test, preprocessor, dataset_profile)
    best_name, _ = save_artifacts(models, results, dataset_profile)

    best_threshold = results[best_name]["optimized_threshold"]["recommended_threshold"]
    best_metrics = results[best_name]["optimized_threshold"]["recommended_metrics"]

    print("\n[BUSINESS RECOMMENDATION]")
    print(f"  Investigate claims with fraud_probability >= {best_threshold:.2f}")
    print(f"  Expected Recall={best_metrics['recall']:.3f}, Precision={best_metrics['precision']:.3f}")
    print(f"  Expected Investigation Hours={best_metrics['estimated_investigation_hours']:.1f}h")
    print(f"  Expected Review Cost={best_metrics['review_cost']:.2f} TND")
    print(f"  Expected Net Value (test-set proxy)={best_metrics['net_value']:.2f} TND")
    print(f"  Expected Investigation Queue Rate={best_metrics['investigation_rate']:.3f}")

    print("\n" + "=" * 70)
    print("FRAUD MODEL TRAINING COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
