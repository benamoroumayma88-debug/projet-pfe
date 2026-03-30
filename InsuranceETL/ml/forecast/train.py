"""
ml/forecast/train.py
----------------------------------------------------------------
Trains SARIMA time-series forecasting models for 5 business KPIs.

KPIs trained:
  1. claim_volume        – monthly claim count
  2. total_indemnisation – monthly total payout (TND)
  3. delay_rate          – monthly proportion of delayed claims (0-1)
  4. fraud_rate          – monthly proportion of fraudulent claims (0-1)
  5. avg_claim_amount    – monthly average claim amount (TND)

For each KPI the routine:
  • builds a clean monthly time series from ml.ml_claim
  • runs an ADF stationarity test
  • grid-searches a set of SARIMA candidate orders, selects best by AIC
  • evaluates on a 3-month hold-out (MAE, MAPE, RMSE)
  • saves the fitted model + series + metadata with joblib
  • persists a JSON manifest for predict.py to read

Usage:
  python ml/forecast/train.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import datetime
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.extract import extract_table

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
MODEL_DIR           = "ml/forecast/models"
DATA_SOURCE         = "ml.ml_claim"
HOLDOUT_MONTHS      = 3       # months kept out for evaluation
MIN_MONTHS_REQUIRED = 12      # minimum history to train
SEASONAL_PERIOD     = 12      # annual seasonality
FORECAST_HORIZON    = 6       # months ahead to forecast later

# SARIMA candidate orders: (p,d,q) × (P,D,Q,s)
# Ordered from simple to complex – first AIC winner wins
SARIMA_CANDIDATES: List[Tuple] = [
    ((1, 1, 1), (1, 1, 1, 12)),   # classic seasonal
    ((0, 1, 1), (0, 1, 1, 12)),   # MA seasonal
    ((1, 1, 0), (1, 1, 0, 12)),   # AR seasonal
    ((2, 1, 2), (1, 0, 1, 12)),   # richer seasonal
    ((1, 1, 1), (0, 0, 0,  0)),   # plain ARIMA (no season)
    ((0, 1, 1), (0, 0, 0,  0)),   # simple MA
    ((0, 1, 0), (0, 0, 0,  0)),   # random walk
]

# KPI definitions: how to aggregate from the raw ML table
KPI_DEFINITIONS: Dict[str, Dict] = {
    "claim_volume": {
        "agg": "count",
        "col": "claim_id",
        "description": "Monthly number of new claims",
        "unit": "claims",
    },
    "total_indemnisation": {
        "agg": "sum",
        "col": "montant_indemnisation_claim",
        "description": "Monthly total indemnisation payout (TND)",
        "unit": "TND",
    },
    "delay_rate": {
        "agg": "mean",
        "col": "is_delayed",
        "description": "Monthly proportion of delayed claims (0-1)",
        "unit": "rate",
    },
    "fraud_rate": {
        "agg": "mean",
        "col": "est_frauduleux_claim",
        "description": "Monthly proportion of fraudulent claims (0-1)",
        "unit": "rate",
    },
    "avg_claim_amount": {
        "agg": "mean",
        "col": "montant_indemnisation_claim",
        "description": "Monthly average claim amount (TND)",
        "unit": "TND",
    },
}


# ─────────────────────────────────────────────────────────
# Data loading & aggregation
# ─────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    print("[LOAD] Loading claims data from ml.ml_claim ...")
    df = extract_table(DATA_SOURCE)
    print(f"[LOAD] {len(df):,} rows | {len(df.columns)} columns")
    return df


def build_monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate the claim-level dataframe into a monthly time series
    with one column per KPI.
    """
    df = df.copy()

    # Parse date
    df["date_sinistre_claim"] = pd.to_datetime(df["date_sinistre_claim"], errors="coerce")
    df = df.dropna(subset=["date_sinistre_claim"])
    df["period"] = df["date_sinistre_claim"].dt.to_period("M")

    # Coerce numeric columns
    for col in ["montant_indemnisation_claim", "is_delayed", "est_frauduleux_claim"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    aggs: Dict[str, pd.Series] = {}
    for kpi, defn in KPI_DEFINITIONS.items():
        col = defn["col"]
        method = defn["agg"]

        if col not in df.columns:
            print(f"  [SKIP] Column '{col}' not found for KPI '{kpi}'")
            continue

        if method == "count":
            aggs[kpi] = df.groupby("period")[col].count()
        elif method == "sum":
            aggs[kpi] = df.groupby("period")[col].sum()
        elif method == "mean":
            aggs[kpi] = df.groupby("period")[col].mean()

    if not aggs:
        raise RuntimeError("No KPI could be built – check column names in ml.ml_claim")

    monthly = pd.DataFrame(aggs)
    monthly.index = monthly.index.to_timestamp()
    monthly = monthly.sort_index()

    # Reindex to fill any missing calendar months via linear interpolation
    full_range = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    monthly = monthly.reindex(full_range).interpolate(method="linear")

    print(
        f"[AGGREGATE] {len(monthly)} months of history  "
        f"({monthly.index[0].strftime('%Y-%m')} → {monthly.index[-1].strftime('%Y-%m')})"
    )
    return monthly


# ─────────────────────────────────────────────────────────
# Stationarity check
# ─────────────────────────────────────────────────────────
def check_stationarity(series: pd.Series, name: str) -> bool:
    try:
        result = adfuller(series.dropna(), autolag="AIC")
        p_val = result[1]
        stationary = p_val < 0.05
        label = "stationary ✓" if stationary else "non-stationary (will diff)"
        print(f"    ADF p={p_val:.4f}  → {label}")
        return stationary
    except Exception:
        return False


# ─────────────────────────────────────────────────────────
# SARIMA grid search
# ─────────────────────────────────────────────────────────
def fit_best_sarima(
    series: pd.Series,
    name: str,
    n_holdout: int,
) -> Tuple[Any, Dict]:
    """
    Try all SARIMA candidates on the training portion, return the
    fitted model with the lowest AIC together with evaluation metrics.
    """
    train = series.iloc[:-n_holdout] if n_holdout > 0 else series
    test  = series.iloc[-n_holdout:]  if n_holdout > 0 else pd.Series(dtype=float)

    best_aic   = np.inf
    best_model = None
    best_order: Tuple     = (1, 1, 1)
    best_seasonal: Tuple  = (0, 0, 0, 0)

    for order, seasonal_order in SARIMA_CANDIDATES:
        try:
            use_seasonal = seasonal_order[3] > 0
            model = SARIMAX(
                train,
                order=order,
                seasonal_order=seasonal_order if use_seasonal else (0, 0, 0, 0),
                trend="n",
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fitted = model.fit(disp=False, maxiter=300)

            if fitted.aic < best_aic:
                best_aic      = fitted.aic
                best_model    = fitted
                best_order    = order
                best_seasonal = seasonal_order

        except Exception:
            continue

    # Hard fallback – plain ARIMA(1,1,0)
    if best_model is None:
        model = SARIMAX(
            train, order=(1, 1, 0), trend="n",
            enforce_stationarity=False, enforce_invertibility=False,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            best_model    = model.fit(disp=False, maxiter=300)
        best_order    = (1, 1, 0)
        best_seasonal = (0, 0, 0, 0)
        best_aic      = best_model.aic

    # Evaluate on hold-out
    metrics: Dict = {}
    if len(test) > 0:
        try:
            fc = best_model.forecast(steps=len(test))
            actual = test.values
            predicted = fc.values
            mae  = float(np.mean(np.abs(actual - predicted)))
            mape = float(np.mean(np.abs((actual - predicted) / (np.abs(actual) + 1e-9))) * 100)
            rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
            metrics = {
                "mae": round(mae, 4),
                "mape_pct": round(mape, 2),
                "rmse": round(rmse, 4),
                "holdout_months": n_holdout,
            }
        except Exception:
            metrics = {}

    print(
        f"    Best order: ARIMA{best_order}×{best_seasonal}  "
        f"AIC={best_aic:.1f}  "
        f"MAPE={metrics.get('mape_pct', 'N/A')}"
    )
    return best_model, {
        "order":          best_order,
        "seasonal_order": best_seasonal,
        "aic":            float(best_aic),
        "metrics":        metrics,
    }


# ─────────────────────────────────────────────────────────
# Main training loop
# ─────────────────────────────────────────────────────────
def train_all_models(monthly: pd.DataFrame) -> Dict:
    os.makedirs(MODEL_DIR, exist_ok=True)

    n_months   = len(monthly)
    n_holdout  = HOLDOUT_MONTHS if n_months >= MIN_MONTHS_REQUIRED + HOLDOUT_MONTHS else max(1, n_months // 5)

    print(
        f"\n[TRAIN] {n_months} months of history  |  {n_holdout}-month hold-out  |  "
        f"{len(SARIMA_CANDIDATES)} SARIMA candidates per KPI\n"
    )

    results: Dict = {}

    for kpi, defn in KPI_DEFINITIONS.items():
        if kpi not in monthly.columns:
            continue

        series = monthly[kpi].copy().fillna(monthly[kpi].median())

        print(f"[KPI] {kpi}  ({defn['description']})")
        print(f"    mean={series.mean():.2f}  std={series.std():.2f}  min={series.min():.2f}  max={series.max():.2f}")
        check_stationarity(series, kpi)

        try:
            model, meta = fit_best_sarima(series, kpi, n_holdout)

            model_path = os.path.join(MODEL_DIR, f"{kpi}_sarima.pkl")
            joblib.dump({"model": model, "series": series, "meta": meta}, model_path)

            results[kpi] = {
                "model_path":  model_path,
                "meta":        meta,
                "n_months":    n_months,
                "last_date":   series.index[-1].strftime("%Y-%m-%d"),
                "mean_value":  float(series.mean()),
                "std_value":   float(series.std()),
                "unit":        defn["unit"],
                "description": defn["description"],
            }
            print(f"    Saved → {model_path}\n")

        except Exception as exc:
            print(f"    ERROR training {kpi}: {exc}\n")

    return results


def save_training_metadata(results: Dict, monthly: pd.DataFrame) -> None:
    def _convert(obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return str(obj)

    meta_path = os.path.join(MODEL_DIR, "training_metadata.json")
    metadata = {
        "trained_at":             datetime.now().isoformat(),
        "data_source":            DATA_SOURCE,
        "months_of_history":      len(monthly),
        "date_range": {
            "from": monthly.index[0].strftime("%Y-%m-%d"),
            "to":   monthly.index[-1].strftime("%Y-%m-%d"),
        },
        "kpis_trained":           list(results.keys()),
        "forecast_horizon_months": FORECAST_HORIZON,
        "seasonal_period":         SEASONAL_PERIOD,
        "model_results":           results,
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=_convert)
    print(f"[SAVE] Training manifest → {meta_path}")


# ─────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 65)
    print("  INSURANCE CLAIMS FORECASTING – SARIMA TRAINING")
    print("=" * 65)

    df = load_data()

    if "date_sinistre_claim" not in df.columns:
        print("[ERROR] 'date_sinistre_claim' column is missing from ml.ml_claim")
        return

    monthly = build_monthly_series(df)

    if len(monthly) < 6:
        print(f"[ERROR] Only {len(monthly)} months of data – minimum 6 required.")
        return

    results = train_all_models(monthly)
    save_training_metadata(results, monthly)

    print("\n" + "=" * 65)
    print(f"  DONE – {len(results)} SARIMA model(s) trained and saved.")
    print("  Next step: run  python ml/forecast/predict.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
