"""
ml/forecast/predict.py
────────────────────────────────────────────────────────────────
Loads trained SARIMA models and generates a 6-month forward forecast
with production-grade business KPIs and actionable manager insights.

Seasonality design
──────────────────
Tunisia-specific monthly multipliers are ALWAYS applied (not only
when the SARIMA output is flat).  This guarantees meaningful
month-to-month variation matching real Tunisian seasonal patterns:

  Summer (Jun–Aug)  → peak vehicle use, school breaks, road trips
  Sep               → back-to-school, young new drivers
  Oct–Nov           → Autumn rains, deteriorating road conditions
  Feb               → lowest activity quarter

Volume anchoring
────────────────
Raw SARIMA volume forecasts are anchored to the recent 12-month
historical mean so that forecasts stay coherent with the current
operating baseline (~1 400 active claims / 19 agents).  If SARIMA
outputs > 1.5× historical mean the values are scaled back to
1.1× historical mean to prevent inflated staffing numbers.

8 Business KPIs per forecast month
───────────────────────────────────
  1.  Claim Volume Forecast          → staffing decisions
  2.  Total Indemnisation Budget      → budget planning
  3.  Expected Delayed Claims         → SLA violation risk
  4.  Expected Fraud Exposure (TND)   → fraud prevention budget
  5.  Required Agent Count            → HR planning
  6.  Net Savings Potential (TND)     → ROI of early interventions
  7.  Workload Index                  → operational efficiency
  8.  Budget Variance vs Rolling Avg  → financial control

Usage:
  python ml/forecast/predict.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import warnings
from datetime import datetime
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from etl.db_connection import get_connection
from etl.load import load_table
from etl.extract import extract_table

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
MODEL_DIR        = "ml/forecast/models"
OUTPUT_DIR       = "ml/forecast"
DASHBOARD_FILE   = "dashboard_insights.json"
FORECAST_HORIZON = 6   # months ahead

PREDICTIONS_SCHEMA = "ml"
MONTHLY_TABLE      = "claim_forecast_monthly"
SUMMARY_TABLE      = "claim_forecast_summary"
ALERTS_TABLE       = "claim_forecast_alerts"

DATA_TABLE      = "ml.ml_claim"
ACTIVE_STATUSES = ["Ouvert", "En_cours", "En_cours_d_expertise"]

# ── Business constants (TND – Tunisian Dinar) ────────────
AGENT_MONTHLY_SALARY          = 3_000.0   # TND
AGENT_MONTHLY_CAPACITY        = 80        # claims per agent per month
DELAY_COST_PER_CLAIM          = 1_200.0   # TND: penalty + rework per delayed claim
FRAUD_RECOVERY_RATE           = 0.35      # 35 % of fraud amount recoverable if caught early
INVESTIGATION_COST_PER_CLAIM  = 150.0     # TND: cost to investigate one suspicious claim
EARLY_INTERVENTION_EFFICIENCY = 0.40      # 40 % of delay costs avoidable with early action

# ── Operational baselines (anchored to current model outputs) ─
# These reflect actual current portfolio: ~1 400 active claims, ~19 agents
BASELINE_AGENTS      = 19      # from delay model recommended_agents
BASELINE_DELAY_RATE  = 0.35    # ~35 % of active claims are delayed
BASELINE_FRAUD_RATE  = 0.10    # ~10 % of active claims flagged as fraud
VOLUME_ANCHOR_FACTOR = 1.5     # if SARIMA mean > this × historical mean → scale down
VOLUME_SCALE_TARGET  = 1.1     # scale back to this × historical mean

# ── Alert thresholds ─────────────────────────────────────
VOLUME_SURGE_THRESHOLD   = 0.20   # >20 % above rolling mean
DELAY_RATE_WARNING       = 0.25   # >25 %  → HIGH
DELAY_RATE_CRITICAL      = 0.40   # >40 %  → CRITICAL
FRAUD_RATE_WARNING       = 0.05   # >5 %   → HIGH alert
BUDGET_OVERSHOOT_PCT     = 0.15   # >15 % above recent avg → MEDIUM alert

# ── Tunisia seasonal multipliers (always applied) ─────────────
# Values represent factor relative to annual mean = 1.0
# Volume multipliers – how many more/fewer claims vs annual average
_SEASONAL_VOLUME: Dict[int, float] = {
    1: 0.85,   # Jan – post-holiday, moderate
    2: 0.75,   # Feb – lowest month
    3: 0.88,   # Mar – slow start
    4: 1.05,   # Apr – spring traffic pickup
    5: 1.10,   # May – public holiday spikes
    6: 1.25,   # Jun – summer begins, student drivers
    7: 1.40,   # Jul – peak: vacation travel, max risk
    8: 1.35,   # Aug – vacation peak still high
    9: 1.20,   # Sep – back-to-school, young drivers
    10: 1.10,  # Oct – autumn rains, road accidents rise
    11: 1.00,  # Nov – rain season in full effect
    12: 0.90,  # Dec – winter, year-end slowdown
}

# Delay rate multipliers – some months have more delays (rain, summer chaos)
_SEASONAL_DELAY: Dict[int, float] = {
    1: 1.00, 2: 0.90, 3: 0.95, 4: 1.05, 5: 1.10,
    6: 1.20, 7: 1.30, 8: 1.25, 9: 1.15, 10: 1.15, 11: 1.10, 12: 1.05,
}

# Fraud rate multipliers – higher in peak claim months (more volume = more opportunity)
_SEASONAL_FRAUD: Dict[int, float] = {
    1: 0.90, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.05,
    6: 1.15, 7: 1.25, 8: 1.20, 9: 1.10, 10: 1.05, 11: 1.00, 12: 0.95,
}

# ── Tunisia seasonal context (manager-facing labels) ─────
_SEASONAL_NOTE: Dict[int, str] = {
    1:  "Post-holiday: Moderate activity, stable claims",
    2:  "Low season: Quietest month – good for staff training",
    3:  "Pre-summer preparation: Activity starts rising",
    4:  "Spring traffic surge: Road accidents increase",
    5:  "May public holidays: Traffic spike risk",
    6:  "Summer begins: Student drivers, vacation travel → surge",
    7:  "Peak summer: Maximum vehicle usage – highest risk month",
    8:  "Vacation peak: Cross-country travel → high claim risk",
    9:  "Back-to-school: New young drivers, accident risk elevated",
    10: "Autumn rains begin: Road condition deterioration",
    11: "Rain season: Accident risk intensifies",
    12: "Year-end: Winter conditions, year-close review",
}


# ─────────────────────────────────────────────────────────
# Forecast anchor: detect latest active-claim month
# ─────────────────────────────────────────────────────────
def _infer_forecast_anchor() -> pd.Timestamp | None:
    """
    Load active claims from ml.ml_claim and return the month-start timestamp
    of the LATEST date_sinistre_claim.  The forecast horizon is then set to
    start from the month AFTER this anchor, so:

      Latest active claim   →  Forecast window
      ───────────────────      ───────────────────────────────────────
      January  2026        →  Feb Mar Apr May Jun Jul 2026
      March    2026        →  Apr May Jun Jul Aug Sep 2026
      April    2026        →  May Jun Jul Aug Sep Oct 2026   ← current case

    If no active claims are found, returns None and the SARIMA training-series
    end date is used as fallback (original behaviour).
    """
    try:
        df = extract_table(DATA_TABLE)
        if "statut_sinistre_claim" in df.columns:
            df = df[df["statut_sinistre_claim"].isin(ACTIVE_STATUSES)]
        if df.empty:
            print("[ANCHOR] No active claims found — using SARIMA training series end.")
            return None

        date_col = "date_sinistre_claim"
        if date_col not in df.columns:
            print("[ANCHOR] date_sinistre_claim column missing — using SARIMA training series end.")
            return None

        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if dates.empty:
            return None

        latest = dates.max()
        # anchor = the month-start of the latest active claim month
        anchor = pd.Timestamp(year=latest.year, month=latest.month, day=1)
        print(
            f"[ANCHOR] Latest active claim: {latest.strftime('%Y-%m-%d')} → "
            f"anchor month = {anchor.strftime('%B %Y')}  → "
            f"forecast starts {(anchor + pd.offsets.MonthBegin(1)).strftime('%B %Y')}"
        )
        return anchor
    except Exception as exc:
        print(f"[ANCHOR] Could not load active claims ({exc}) — using SARIMA end date.")
        return None


# ─────────────────────────────────────────────────────────
# Model loading
# ─────────────────────────────────────────────────────────
def load_models() -> Dict[str, Any]:
    meta_path = os.path.join(MODEL_DIR, "training_metadata.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"No training manifest found at {meta_path}. "
            "Run  python ml/forecast/train.py  first."
        )

    with open(meta_path, encoding="utf-8") as f:
        training_meta = json.load(f)

    models: Dict[str, Any] = {"_meta": training_meta}

    for kpi in training_meta.get("kpis_trained", []):
        model_path = os.path.join(MODEL_DIR, f"{kpi}_sarima.pkl")
        if os.path.exists(model_path):
            bundle = joblib.load(model_path)
            models[kpi] = bundle
            order    = bundle["meta"]["order"]
            seasonal = bundle["meta"]["seasonal_order"]
            mape     = bundle["meta"].get("metrics", {}).get("mape_pct", "N/A")
            print(f"  [LOAD] {kpi:25s}  ARIMA{order}×{seasonal}  MAPE={mape}")
        else:
            print(f"  [MISSING] {kpi}: model file not found")

    print(f"  └── {len(models) - 1} model(s) loaded\n")
    return models


# ─────────────────────────────────────────────────────────
# Forecast generation
# ─────────────────────────────────────────────────────────
def generate_forecasts(models: Dict, horizon: int) -> pd.DataFrame:
    """
    1. Run SARIMA forecast for each KPI.
    2. Anchor the forecast START month to the latest active-claim month
       (loaded live from ml.ml_claim) so the window auto-shifts every time
       new sinistres are injected.  Falls back to the SARIMA series end date
       if no active claims are found.
    3. ALWAYS apply Tunisia seasonal multipliers for volume, delay_rate, fraud_rate.
    4. Apply physical constraints (clip rates to [0,1], volumes to ≥0).
    """

    # ── Determine forecast start date ────────────────────────────────────
    # Priority 1: live anchor from active claims (data-driven, always current)
    live_anchor = _infer_forecast_anchor()

    # Priority 2: SARIMA training series end date (original fallback)
    sarima_last: pd.Timestamp | None = None
    for kpi, bundle in models.items():
        if kpi == "_meta":
            continue
        try:
            sarima_last = pd.to_datetime(bundle["series"].index[-1])
            break
        except Exception:
            continue

    if live_anchor is not None:
        # Use whichever is later: the live data anchor or the SARIMA end
        if sarima_last is not None and sarima_last > live_anchor:
            last_date = sarima_last
            print(
                f"[ANCHOR] SARIMA series ends {sarima_last.strftime('%Y-%m')} which is "
                f"after live anchor {live_anchor.strftime('%Y-%m')} — using SARIMA end."
            )
        else:
            last_date = live_anchor
    elif sarima_last is not None:
        last_date = sarima_last
    else:
        last_date = datetime.now().replace(day=1) - pd.DateOffset(months=1)
        print("[ANCHOR] No date reference found — using last month as fallback.")

    forecast_dates = pd.date_range(
        last_date + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"
    )
    print(
        f"[FORECAST] Horizon: {forecast_dates[0].strftime('%Y-%m')} → "
        f"{forecast_dates[-1].strftime('%Y-%m')}\n"
    )

    point_forecasts: Dict[str, np.ndarray] = {}

    for kpi, bundle in models.items():
        if kpi == "_meta":
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fc_values = bundle["model"].forecast(steps=horizon).values.astype(float)

            fc_values = np.clip(fc_values, 0.0, None)

            # ── Volume anchoring ───────────────────────────────────
            if kpi == "claim_volume":
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                if hist_mean > 0:
                    fc_mean = float(fc_values.mean())
                    if fc_mean > VOLUME_ANCHOR_FACTOR * hist_mean:
                        scale = (VOLUME_SCALE_TARGET * hist_mean) / fc_mean
                        fc_values = fc_values * scale
                        print(
                            f"  [ANCHOR] {kpi}: raw mean {fc_mean:.1f} > {VOLUME_ANCHOR_FACTOR}× "
                            f"hist mean {hist_mean:.1f} → scaled by {scale:.3f}"
                        )

            # ── Always apply Tunisia seasonal multipliers ──────────
            if kpi == "claim_volume":
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                seasonal_factors = np.array([_SEASONAL_VOLUME[d.month] for d in forecast_dates])
                # Normalise so the mean multiplier doesn't inflate the total
                seasonal_factors = seasonal_factors / float(seasonal_factors.mean())
                fc_values = fc_values * seasonal_factors
                # ── Hard per-month clamp: each month stays within ±40% of recent avg.
                # This prevents individual SARIMA outlier months even when the overall
                # mean is reasonable (e.g. 171 one month, 2997 the next is impossible).
                if hist_mean > 0:
                    fc_values = np.clip(fc_values, hist_mean * 0.60, hist_mean * 1.45)

            elif kpi == "total_indemnisation":
                # Clamp each month to ±45% of recent 12-month average
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                if hist_mean > 0:
                    fc_values = np.clip(fc_values, hist_mean * 0.55, hist_mean * 1.50)

            elif kpi == "avg_claim_amount":
                # Clamp to ±40% of recent average
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                if hist_mean > 0:
                    fc_values = np.clip(fc_values, hist_mean * 0.60, hist_mean * 1.40)

            elif kpi == "delay_rate":
                seasonal_factors = np.array([_SEASONAL_DELAY[d.month] for d in forecast_dates])
                seasonal_factors = seasonal_factors / float(seasonal_factors.mean())
                fc_values = fc_values * seasonal_factors
                # Clamp relative to the series' own historical mean (not a fixed constant)
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean_d = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                fc_values = np.clip(fc_values, hist_mean_d * 0.65, hist_mean_d * 1.50)

            elif kpi == "fraud_rate":
                seasonal_factors = np.array([_SEASONAL_FRAUD[d.month] for d in forecast_dates])
                seasonal_factors = seasonal_factors / float(seasonal_factors.mean())
                fc_values = fc_values * seasonal_factors
                series = bundle.get("series", pd.Series(dtype=float))
                hist_mean_f = float(series.iloc[-12:].mean()) if len(series) >= 12 else float(series.mean())
                fc_values = np.clip(fc_values, hist_mean_f * 0.65, hist_mean_f * 1.50)

            # Final physical constraints
            if kpi in ("delay_rate", "fraud_rate"):
                fc_values = np.clip(fc_values, 0.0, 1.0)
            else:
                fc_values = np.clip(fc_values, 0.0, None)

            point_forecasts[kpi] = fc_values
            print(f"  {kpi:25s} range [{fc_values.min():.2f} – {fc_values.max():.2f}]")

        except Exception as exc:
            print(f"  {kpi:25s} ERROR: {exc}")

    return pd.DataFrame(point_forecasts, index=forecast_dates)


# ─────────────────────────────────────────────────────────
# Business KPI computation
# ─────────────────────────────────────────────────────────
def _baselines(models: Dict) -> Dict[str, Dict]:
    """Compute historical baselines for each KPI from training series."""
    bl: Dict[str, Dict] = {}
    for kpi, bundle in models.items():
        if kpi == "_meta":
            continue
        try:
            s = bundle["series"]
            bl[kpi] = {
                "mean":        float(s.mean()),
                "std":         float(s.std()),
                "last_3m_avg": float(s.iloc[-3:].mean()),
                "last_12m_avg": float(s.iloc[-12:].mean()) if len(s) >= 12 else float(s.mean()),
            }
        except Exception:
            bl[kpi] = {"mean": 0, "std": 0, "last_3m_avg": 0, "last_12m_avg": 0}
    return bl


def compute_business_kpis(
    forecasts: pd.DataFrame,
    models: Dict,
) -> List[Dict]:
    baselines = _baselines(models)
    monthly_kpis: List[Dict] = []

    # Historical volume mean used for workload / surge detection
    hist_vol_mean = baselines.get("claim_volume", {}).get("last_12m_avg", 100.0)

    for dt in forecasts.index:
        row = forecasts.loc[dt]

        # ── Core forecast values ──────────────────────────
        vol        = max(float(row.get("claim_volume",       100.0)), 0.0)
        total_cost = max(float(row.get("total_indemnisation", vol * 800)), 0.0)
        delay_rate = float(np.clip(row.get("delay_rate",  BASELINE_DELAY_RATE), 0.0, 1.0))
        fraud_rate = float(np.clip(row.get("fraud_rate",  BASELINE_FRAUD_RATE), 0.0, 1.0))
        avg_amount = max(float(row.get("avg_claim_amount", total_cost / max(vol, 1))), 0.0)

        # ── Derived KPIs ──────────────────────────────────

        # 1. Expected delayed & fraudulent claims
        expected_delays       = vol * delay_rate
        expected_fraud_cases  = vol * fraud_rate
        expected_fraud_exposure = expected_fraud_cases * avg_amount

        # 2. Staffing – anchored to BASELINE_AGENTS, scaled ±5 with volume multiplier
        #    Volume multiplier = vol / hist_vol_mean (how much busier vs usual)
        vol_ratio = vol / max(hist_vol_mean, 1.0)
        recommended_agents = int(
            np.clip(
                round(BASELINE_AGENTS * vol_ratio),
                max(1, BASELINE_AGENTS - 7),   # never drop below baseline - 7
                BASELINE_AGENTS + 10,           # never spike above baseline + 10
            )
        )
        staffing_cost = recommended_agents * AGENT_MONTHLY_SALARY

        # 3. Delay cost & savings
        total_delay_cost       = expected_delays * DELAY_COST_PER_CLAIM
        preventable_delay_cost = total_delay_cost * EARLY_INTERVENTION_EFFICIENCY

        # 4. Fraud savings
        fraud_prevention_savings = expected_fraud_exposure * FRAUD_RECOVERY_RATE
        investigation_cost       = expected_fraud_cases * INVESTIGATION_COST_PER_CLAIM
        net_fraud_savings        = max(0.0, fraud_prevention_savings - investigation_cost)

        # 5. Total net savings potential (KPI 6)
        net_savings_potential = preventable_delay_cost + net_fraud_savings

        # 6. ROI
        intervention_cost = investigation_cost + (recommended_agents * 300)
        intervention_roi  = (net_savings_potential / max(intervention_cost, 1)) * 100

        # 7. Budget variance vs last-12m rolling average
        baseline_cost       = baselines.get("total_indemnisation", {}).get("last_12m_avg", total_cost)
        budget_variance_pct = ((total_cost - baseline_cost) / max(baseline_cost, 1)) * 100

        # 8. Workload index – fraction of capacity used
        workload_index = vol / max(recommended_agents * AGENT_MONTHLY_CAPACITY, 1)

        # ── Risk level ────────────────────────────────────
        if delay_rate >= DELAY_RATE_CRITICAL or fraud_rate >= FRAUD_RATE_WARNING * 2:
            risk_level = "CRITICAL"
        elif delay_rate >= DELAY_RATE_WARNING or fraud_rate >= FRAUD_RATE_WARNING:
            risk_level = "HIGH"
        elif delay_rate >= DELAY_RATE_WARNING * 0.65:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # ── Volume surge detection ────────────────────────
        baseline_vol      = baselines.get("claim_volume", {}).get("last_3m_avg", vol)
        volume_surge_pct  = ((vol - baseline_vol) / max(baseline_vol, 1)) * 100
        is_surge          = volume_surge_pct > VOLUME_SURGE_THRESHOLD * 100

        # ── Alerts ───────────────────────────────────────
        month_label = dt.strftime("%B %Y")
        alerts: List[Dict] = []

        if is_surge:
            extra_agents = max(0, recommended_agents - BASELINE_AGENTS)
            alerts.append({
                "level": "HIGH",
                "type":  "VOLUME_SURGE",
                "message": (
                    f"Claim surge expected in {month_label} (+{volume_surge_pct:.0f}% vs recent avg). "
                    f"Recommend {extra_agents} additional agent(s) above baseline."
                ),
            })

        if delay_rate >= DELAY_RATE_CRITICAL:
            alerts.append({
                "level": "CRITICAL",
                "type":  "DELAY_RISK",
                "message": (
                    f"Critical delay rate forecast: {delay_rate*100:.0f}% in {month_label}. "
                    "Immediate SLA process review and fast-track queue activation required."
                ),
            })
        elif delay_rate >= DELAY_RATE_WARNING:
            alerts.append({
                "level": "HIGH",
                "type":  "DELAY_RISK",
                "message": (
                    f"High delay rate forecast: {delay_rate*100:.0f}% in {month_label}. "
                    "Intensify SLA monitoring and assign senior handlers to flagged cases."
                ),
            })

        if fraud_rate >= FRAUD_RATE_WARNING:
            investigators_needed = max(1, int(np.ceil(expected_fraud_cases / 5)))
            alerts.append({
                "level": "HIGH",
                "type":  "FRAUD_RISK",
                "message": (
                    f"Elevated fraud rate forecast: {fraud_rate*100:.1f}% ({expected_fraud_cases:.0f} cases) "
                    f"in {month_label}. Deploy {investigators_needed} fraud investigator(s)."
                ),
            })

        if budget_variance_pct > BUDGET_OVERSHOOT_PCT * 100:
            alerts.append({
                "level": "MEDIUM",
                "type":  "BUDGET_ALERT",
                "message": (
                    f"Indemnisation costs forecast +{budget_variance_pct:.0f}% above recent average "
                    f"in {month_label}. Review reserve allocation."
                ),
            })

        # ── Manager recommendations ───────────────────────
        recommendations: List[str] = []

        if net_savings_potential > 5_000:
            recommendations.append(
                f"Early intervention this month could prevent up to "
                f"{int(net_savings_potential / 1_000)}K TND in losses."
            )
        if expected_delays > 10:
            recommendations.append(
                f"Pre-assign {int(expected_delays)} high-risk claims to fast-track handlers."
            )
        if expected_fraud_cases > 3:
            recommendations.append(
                f"Flag {int(np.ceil(expected_fraud_cases))} suspected fraud dossiers for proactive investigation."
            )
        if workload_index > 0.85:
            recommendations.append(
                f"Agent workload at {workload_index*100:.0f}% capacity – consider temporary staffing."
            )
        if budget_variance_pct < -10:
            recommendations.append(
                "Claims activity lower than average – opportunity to accelerate pending backlog."
            )

        monthly_kpis.append({
            "month":            month_label,
            "period":           dt.strftime("%Y-%m"),
            "year":             int(dt.year),
            "month_number":     int(dt.month),
            "seasonal_context": _SEASONAL_NOTE.get(dt.month, ""),

            # Core forecasts
            "forecast": {
                "claim_volume":               round(vol, 1),
                "total_indemnisation_tnd":    round(total_cost, 2),
                "delay_rate_pct":             round(delay_rate * 100, 1),
                "fraud_rate_pct":             round(fraud_rate * 100, 2),
                "avg_claim_amount_tnd":       round(avg_amount, 2),
            },

            # 8 Business KPIs
            "business_kpis": {
                "expected_delayed_claims":        round(expected_delays, 1),
                "expected_fraud_cases":           round(expected_fraud_cases, 1),
                "expected_fraud_exposure_tnd":    round(expected_fraud_exposure, 2),
                "recommended_agents":             recommended_agents,
                "staffing_cost_tnd":              round(staffing_cost, 2),
                "total_delay_cost_tnd":           round(total_delay_cost, 2),
                "preventable_delay_cost_tnd":     round(preventable_delay_cost, 2),
                "net_fraud_savings_tnd":          round(net_fraud_savings, 2),
                "net_savings_potential_tnd":      round(net_savings_potential, 2),
                "intervention_roi_pct":           round(intervention_roi, 1),
                "budget_variance_pct":            round(budget_variance_pct, 1),
                "workload_index":                 round(workload_index, 3),
            },

            "risk_level":       risk_level,
            "volume_surge_pct": round(volume_surge_pct, 1),
            "is_surge_month":   bool(is_surge),
            "alerts":           alerts,
            "recommendations":  recommendations,
        })

    return monthly_kpis


# ─────────────────────────────────────────────────────────
# Portfolio summary
# ─────────────────────────────────────────────────────────
def compute_portfolio_summary(monthly_kpis: List[Dict]) -> Dict:
    if not monthly_kpis:
        return {}

    total_volume   = sum(m["forecast"]["claim_volume"]            for m in monthly_kpis)
    total_cost     = sum(m["forecast"]["total_indemnisation_tnd"]  for m in monthly_kpis)
    avg_delay_rate = float(np.mean([m["forecast"]["delay_rate_pct"] for m in monthly_kpis]))
    avg_fraud_rate = float(np.mean([m["forecast"]["fraud_rate_pct"] for m in monthly_kpis]))
    total_delays   = sum(m["business_kpis"]["expected_delayed_claims"]    for m in monthly_kpis)
    total_fraud_ex = sum(m["business_kpis"]["expected_fraud_exposure_tnd"] for m in monthly_kpis)
    total_savings  = sum(m["business_kpis"]["net_savings_potential_tnd"]   for m in monthly_kpis)
    avg_agents     = float(np.mean([m["business_kpis"]["recommended_agents"] for m in monthly_kpis]))

    peak_vol_month   = max(monthly_kpis, key=lambda m: m["forecast"]["claim_volume"])
    peak_delay_month = max(monthly_kpis, key=lambda m: m["forecast"]["delay_rate_pct"])
    peak_cost_month  = max(monthly_kpis, key=lambda m: m["forecast"]["total_indemnisation_tnd"])

    high_risk_months = [m["month"] for m in monthly_kpis if m["risk_level"] in ("CRITICAL", "HIGH")]
    surge_months     = [m["month"] for m in monthly_kpis if m["is_surge_month"]]
    all_alerts       = [a for m in monthly_kpis for a in m["alerts"]]

    return {
        "horizon_months":                 len(monthly_kpis),
        "total_forecast_period":          f"{monthly_kpis[0]['period']} → {monthly_kpis[-1]['period']}",
        "total_expected_claims":          round(total_volume),
        "total_expected_cost_tnd":        round(total_cost, 2),
        "avg_monthly_delay_rate_pct":     round(avg_delay_rate, 1),
        "avg_monthly_fraud_rate_pct":     round(avg_fraud_rate, 2),
        "total_expected_delays":          round(total_delays),
        "total_fraud_exposure_tnd":       round(total_fraud_ex, 2),
        "total_net_savings_potential_tnd": round(total_savings, 2),
        "avg_agents_needed_per_month":    round(avg_agents, 1),
        "peak_volume_month":              peak_vol_month["month"],
        "peak_volume_claims":             round(peak_vol_month["forecast"]["claim_volume"]),
        "peak_delay_month":               peak_delay_month["month"],
        "peak_delay_rate_pct":            round(peak_delay_month["forecast"]["delay_rate_pct"], 1),
        "peak_cost_month":                peak_cost_month["month"],
        "peak_cost_tnd":                  round(peak_cost_month["forecast"]["total_indemnisation_tnd"], 2),
        "high_risk_months":               high_risk_months,
        "surge_expected_months":          surge_months,
        "total_alerts":                   len(all_alerts),
        "critical_alerts":                sum(1 for a in all_alerts if a["level"] == "CRITICAL"),
        "high_alerts":                    sum(1 for a in all_alerts if a["level"] == "HIGH"),
        "strategic_insight":              _build_strategic_insight(
            avg_delay_rate, avg_fraud_rate, total_volume,
            total_cost, total_savings, surge_months, high_risk_months,
        ),
    }


def _build_strategic_insight(
    delay_rate: float,
    fraud_rate: float,
    volume: float,
    cost: float,
    savings: float,
    surge_months: List[str],
    high_risk_months: List[str],
) -> str:
    parts: List[str] = []
    if surge_months:
        parts.append(
            f"Volume surges forecast in {', '.join(surge_months)} – proactive staffing strongly recommended."
        )
    if high_risk_months:
        parts.append(
            f"High-risk periods: {', '.join(high_risk_months)}. Escalate monitoring and resource allocation."
        )
    if delay_rate > DELAY_RATE_WARNING * 100:
        parts.append(
            f"Sustained delay rate of {delay_rate:.0f}% requires structural process optimisation across the horizon."
        )
    if fraud_rate > FRAUD_RATE_WARNING * 100:
        parts.append(
            f"Elevated fraud index ({fraud_rate:.1f}%) warrants enhanced investigation protocols."
        )
    if savings > 30_000:
        parts.append(
            f"Proactive interventions could prevent up to {int(savings / 1_000)}K TND in losses over 6 months – ROI positive."
        )
    if not parts:
        parts.append(
            "Operations appear stable over the forecast horizon. Maintain current protocols and leverage quiet periods for staff training."
        )
    return "  ".join(parts)


# ─────────────────────────────────────────────────────────
# Console output
# ─────────────────────────────────────────────────────────
def print_forecast_report(monthly_kpis: List[Dict], summary: Dict) -> None:
    W = 80
    print("\n" + "═" * W)
    print("  INSURANCE CLAIMS – 6-MONTH STRATEGIC FORECAST REPORT")
    print(f"  Period : {summary.get('total_forecast_period', '')}")
    print(f"  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * W)

    # Monthly table
    header = (
        f"{'Month':<18} {'Claims':>7} {'Cost(KTND)':>11} "
        f"{'Delay%':>8} {'Fraud%':>7} {'Agents':>7} {'Savings(KTND)':>14} {'Risk':<10}"
    )
    print("\n" + header)
    print("─" * W)
    for m in monthly_kpis:
        f  = m["forecast"]
        b  = m["business_kpis"]
        surge_flag = " ▲" if m["is_surge_month"] else "  "
        print(
            f"{m['month']:<18} {f['claim_volume']:>7.0f} {f['total_indemnisation_tnd']/1_000:>11.1f} "
            f"{f['delay_rate_pct']:>8.1f} {f['fraud_rate_pct']:>7.2f} "
            f"{b['recommended_agents']:>7} {b['net_savings_potential_tnd']/1_000:>14.1f} "
            f"{m['risk_level']:<8}{surge_flag}"
        )

    print("─" * W)
    print(f"  {'TOTAL / AVG':<16} {summary['total_expected_claims']:>7.0f} "
          f"{summary['total_expected_cost_tnd']/1_000:>11.1f} "
          f"{summary['avg_monthly_delay_rate_pct']:>8.1f} "
          f"{summary['avg_monthly_fraud_rate_pct']:>7.2f} "
          f"{summary['avg_agents_needed_per_month']:>7.1f} "
          f"{summary['total_net_savings_potential_tnd']/1_000:>14.1f}")

    # KPI highlights
    print("\n" + "─" * W)
    print("  KEY PERFORMANCE INDICATORS (6-MONTH CUMULATIVE)")
    print("─" * W)
    kpis = [
        ("Total Expected Claims",            f"{summary['total_expected_claims']:,.0f}"),
        ("Total Expected Cost",              f"{summary['total_expected_cost_tnd']/1_000:,.1f} K TND"),
        ("Total Expected Delays",            f"{summary['total_expected_delays']:,.0f} claims"),
        ("Total Fraud Exposure",             f"{summary['total_fraud_exposure_tnd']/1_000:,.1f} K TND"),
        ("Net Savings Potential",            f"{summary['total_net_savings_potential_tnd']/1_000:,.1f} K TND"),
        ("Peak Volume Month",                summary["peak_volume_month"]),
        ("Peak Delay Month",                 f"{summary['peak_delay_month']} ({summary['peak_delay_rate_pct']}%)"),
        ("High-Risk Months",                 ", ".join(summary["high_risk_months"]) or "None"),
        ("Volume Surge Months",              ", ".join(summary["surge_expected_months"]) or "None"),
        ("Total Alerts",                     f"{summary['total_alerts']} ({summary['critical_alerts']} critical, {summary['high_alerts']} high)"),
    ]
    for label, value in kpis:
        print(f"  {label:<35} {value}")

    # Alerts
    print("\n" + "─" * W)
    print("  AUTOMATED ALERTS")
    print("─" * W)
    has_alerts = False
    for m in monthly_kpis:
        for alert in m["alerts"]:
            has_alerts = True
            print(f"  [{alert['level']:<8}] {m['month']}: {alert['message']}")
    if not has_alerts:
        print("  No alerts for the forecast horizon.")

    # Strategic insight
    print("\n" + "─" * W)
    print("  STRATEGIC INSIGHT FOR MANAGEMENT")
    print("─" * W)
    for sentence in summary.get("strategic_insight", "").split("  "):
        if sentence.strip():
            print(f"  • {sentence.strip()}")

    print("\n" + "═" * W)


# ─────────────────────────────────────────────────────────
# Dashboard export
# ─────────────────────────────────────────────────────────
def save_dashboard_insights(
    monthly_kpis: List[Dict],
    summary: Dict,
    models: Dict,
) -> Dict[str, Any]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, DASHBOARD_FILE)

    # Flat table for Power BI (one row per forecast month)
    flat_rows: List[Dict] = []
    for m in monthly_kpis:
        row: Dict = {
            "period":           m["period"],
            "month":            m["month"],
            "year":             m["year"],
            "month_number":     m["month_number"],
            "seasonal_context": m["seasonal_context"],
            "risk_level":       m["risk_level"],
            "is_surge_month":   m["is_surge_month"],
            "volume_surge_pct": m["volume_surge_pct"],
            "alert_count":      len(m["alerts"]),
            "alert_messages":   " | ".join(a["message"] for a in m["alerts"])[:255],
            "recommendations":  " | ".join(m["recommendations"]),
        }
        row.update({f"forecast_{k}": v for k, v in m["forecast"].items()})
        row.update({f"kpi_{k}": v for k, v in m["business_kpis"].items()})
        flat_rows.append(row)

    training_meta = models.get("_meta", {})

    insights = {
        "run_timestamp":         datetime.now().isoformat(),
        "model_trained_at":      training_meta.get("trained_at", "unknown"),
        "data_source":           training_meta.get("data_source", "ml.ml_claim"),
        "training_history_months": training_meta.get("months_of_history", 0),
        "forecast_horizon_months": FORECAST_HORIZON,
        "currency":              "TND (Tunisian Dinar)",
        "summary":               summary,
        "monthly_details":       monthly_kpis,
        "flat_table":            flat_rows,
        "model_performance": {
            kpi: bundle.get("meta", {}).get("metrics", {})
            for kpi, bundle in models.items()
            if kpi != "_meta"
        },
        "business_assumptions": {
            "agent_monthly_salary_tnd":          AGENT_MONTHLY_SALARY,
            "agent_monthly_capacity_claims":     AGENT_MONTHLY_CAPACITY,
            "delay_cost_per_claim_tnd":          DELAY_COST_PER_CLAIM,
            "fraud_recovery_rate_pct":           FRAUD_RECOVERY_RATE * 100,
            "investigation_cost_per_claim_tnd":  INVESTIGATION_COST_PER_CLAIM,
            "early_intervention_efficiency_pct": EARLY_INTERVENTION_EFFICIENCY * 100,
        },
    }

    def _convert(obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, np.bool_): return bool(obj)
        return str(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, default=_convert)

    print(f"[SAVE] Dashboard insights → {output_path}")
    return insights


def _build_sql_payloads(insights: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    run_id = datetime.now().strftime("FCST-%Y%m%d-%H%M%S")
    generated_at = datetime.now()

    monthly_details = insights.get("monthly_details", [])
    summary = insights.get("summary", {})

    monthly_rows: List[Dict[str, Any]] = []
    alert_rows: List[Dict[str, Any]] = []
    for m in monthly_details:
        forecast = m.get("forecast", {})
        kpis = m.get("business_kpis", {})
        alerts = m.get("alerts", [])

        monthly_rows.append({
            "forecast_record_id": str(uuid.uuid4()),
            "forecast_run_id": run_id,
            "generated_at": generated_at,
            "period": m.get("period"),
            "month": m.get("month"),
            "year": int(m.get("year", 0) or 0),
            "month_number": int(m.get("month_number", 0) or 0),
            "seasonal_context": m.get("seasonal_context", ""),
            "risk_level": m.get("risk_level", ""),
            "is_surge_month": bool(m.get("is_surge_month", False)),
            "volume_surge_pct": float(m.get("volume_surge_pct", 0.0) or 0.0),
            "alert_count": int(len(alerts)),
            "alert_messages": " | ".join(a.get("message", "") for a in alerts)[:255],
            "recommendations": " | ".join(m.get("recommendations", [])),
            "forecast_claim_volume": float(forecast.get("claim_volume", 0.0) or 0.0),
            "forecast_total_indemnisation_tnd": float(forecast.get("total_indemnisation_tnd", 0.0) or 0.0),
            "forecast_delay_rate_pct": float(forecast.get("delay_rate_pct", 0.0) or 0.0),
            "forecast_fraud_rate_pct": float(forecast.get("fraud_rate_pct", 0.0) or 0.0),
            "forecast_avg_claim_amount_tnd": float(forecast.get("avg_claim_amount_tnd", 0.0) or 0.0),
            "kpi_expected_delayed_claims": float(kpis.get("expected_delayed_claims", 0.0) or 0.0),
            "kpi_expected_fraud_cases": float(kpis.get("expected_fraud_cases", 0.0) or 0.0),
            "kpi_expected_fraud_exposure_tnd": float(kpis.get("expected_fraud_exposure_tnd", 0.0) or 0.0),
            "kpi_recommended_agents": int(kpis.get("recommended_agents", 0) or 0),
            "kpi_staffing_cost_tnd": float(kpis.get("staffing_cost_tnd", 0.0) or 0.0),
            "kpi_total_delay_cost_tnd": float(kpis.get("total_delay_cost_tnd", 0.0) or 0.0),
            "kpi_preventable_delay_cost_tnd": float(kpis.get("preventable_delay_cost_tnd", 0.0) or 0.0),
            "kpi_net_fraud_savings_tnd": float(kpis.get("net_fraud_savings_tnd", 0.0) or 0.0),
            "kpi_net_savings_potential_tnd": float(kpis.get("net_savings_potential_tnd", 0.0) or 0.0),
            "kpi_intervention_roi_pct": float(kpis.get("intervention_roi_pct", 0.0) or 0.0),
            "kpi_budget_variance_pct": float(kpis.get("budget_variance_pct", 0.0) or 0.0),
            "kpi_workload_index": float(kpis.get("workload_index", 0.0) or 0.0),
        })

        for a in alerts:
            alert_rows.append({
                "alert_record_id": str(uuid.uuid4()),
                "forecast_run_id": run_id,
                "generated_at": generated_at,
                "period": m.get("period"),
                "month": m.get("month"),
                "risk_level": m.get("risk_level", ""),
                "alert_level": a.get("level", ""),
                "alert_type": a.get("type", ""),
                "alert_message": a.get("message", ""),
                "is_surge_month": bool(m.get("is_surge_month", False)),
            })

    summary_row = {
        "summary_record_id": str(uuid.uuid4()),
        "forecast_run_id": run_id,
        "generated_at": generated_at,
        "model_trained_at": insights.get("model_trained_at", "unknown"),
        "data_source": insights.get("data_source", "ml.ml_claim"),
        "training_history_months": int(insights.get("training_history_months", 0) or 0),
        "forecast_horizon_months": int(insights.get("forecast_horizon_months", 0) or 0),
        "currency": insights.get("currency", "TND (Tunisian Dinar)"),
        "total_forecast_period": summary.get("total_forecast_period", ""),
        "total_expected_claims": float(summary.get("total_expected_claims", 0.0) or 0.0),
        "total_expected_cost_tnd": float(summary.get("total_expected_cost_tnd", 0.0) or 0.0),
        "avg_monthly_delay_rate_pct": float(summary.get("avg_monthly_delay_rate_pct", 0.0) or 0.0),
        "avg_monthly_fraud_rate_pct": float(summary.get("avg_monthly_fraud_rate_pct", 0.0) or 0.0),
        "total_expected_delays": float(summary.get("total_expected_delays", 0.0) or 0.0),
        "total_fraud_exposure_tnd": float(summary.get("total_fraud_exposure_tnd", 0.0) or 0.0),
        "total_net_savings_potential_tnd": float(summary.get("total_net_savings_potential_tnd", 0.0) or 0.0),
        "avg_agents_needed_per_month": float(summary.get("avg_agents_needed_per_month", 0.0) or 0.0),
        "peak_volume_month": summary.get("peak_volume_month", ""),
        "peak_volume_claims": float(summary.get("peak_volume_claims", 0.0) or 0.0),
        "peak_delay_month": summary.get("peak_delay_month", ""),
        "peak_delay_rate_pct": float(summary.get("peak_delay_rate_pct", 0.0) or 0.0),
        "peak_cost_month": summary.get("peak_cost_month", ""),
        "peak_cost_tnd": float(summary.get("peak_cost_tnd", 0.0) or 0.0),
        "high_risk_months": " | ".join(summary.get("high_risk_months", [])),
        "surge_expected_months": " | ".join(summary.get("surge_expected_months", [])),
        "total_alerts": int(summary.get("total_alerts", 0) or 0),
        "critical_alerts": int(summary.get("critical_alerts", 0) or 0),
        "high_alerts": int(summary.get("high_alerts", 0) or 0),
        "strategic_insight": summary.get("strategic_insight", ""),
    }

    return {
        "run_id": run_id,
        "monthly": pd.DataFrame(monthly_rows),
        "summary": pd.DataFrame([summary_row]),
        "alerts": pd.DataFrame(alert_rows),
    }


def save_forecast_to_database(insights: Dict[str, Any]) -> None:
    payload = _build_sql_payloads(insights)
    conn = get_connection()
    try:
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=MONTHLY_TABLE,
            df=payload["monthly"],
            mode="replace",
            primary_key=None,
        )
        load_table(
            conn=conn,
            schema=PREDICTIONS_SCHEMA,
            table=SUMMARY_TABLE,
            df=payload["summary"],
            mode="replace",
            primary_key=None,
        )
        if not payload["alerts"].empty:
            load_table(
                conn=conn,
                schema=PREDICTIONS_SCHEMA,
                table=ALERTS_TABLE,
                df=payload["alerts"],
                mode="replace",
                primary_key=None,
            )
    finally:
        conn.close()

    print(
        f"[SAVE] SQL forecast saved: {PREDICTIONS_SCHEMA}.{MONTHLY_TABLE} ({len(payload['monthly'])} rows), "
        f"{PREDICTIONS_SCHEMA}.{SUMMARY_TABLE} ({len(payload['summary'])} row), "
        f"{PREDICTIONS_SCHEMA}.{ALERTS_TABLE} ({len(payload['alerts'])} rows) "
        f"[run_id={payload['run_id']}]"
    )


# ─────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 65)
    print("  INSURANCE CLAIMS FORECASTING – PREDICTION & KPI REPORT")
    print("=" * 65 + "\n")

    # _infer_forecast_anchor() is called inside generate_forecasts() and will
    # print the detected anchor + forecast window.  No manual date config needed.
    models        = load_models()
    forecasts     = generate_forecasts(models, FORECAST_HORIZON)
    monthly_kpis  = compute_business_kpis(forecasts, models)
    summary       = compute_portfolio_summary(monthly_kpis)

    print_forecast_report(monthly_kpis, summary)
    insights = save_dashboard_insights(monthly_kpis, summary, models)
    save_forecast_to_database(insights)

    print("\n[DONE] Forecasting complete!")


if __name__ == "__main__":
    main()
