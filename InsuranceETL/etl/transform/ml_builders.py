# etl/transform/ml_builders.py
"""
ML feature builder.

Builds the unified ml.ml_claim dataset by reading from the data warehouse
tables (dw.dim_client, dw.dim_policy, dw.dim_vehicle, dw.fact_claim).
This eliminates the redundant stg.* intermediate layer — the DW IS the
clean data store, and ML features are derived from it.
"""
import numpy as np
import pandas as pd
from ..common import clip_outliers


def build_ml_claim_dataset(dim_client, dim_policy, dim_vehicle, fact_claim):
    """Build the unified ML feature dataset from data warehouse tables."""
    base = fact_claim.copy()

    # -------------------------
    # Target for delay model
    # -------------------------
    # Keep ALL claims (active and closed) for the ML dataset.
    # Active claims will have is_delayed=NA and can be scored with predictions.
    # Closed claims with delay labels can be used for model training.
    if "is_delayed" not in base.columns:
        base["is_delayed"] = pd.NA
    base["is_delayed"] = base["is_delayed"].astype("Int64")

    # -------------------------
    # Claim status (for filtering active vs closed claims)
    # -------------------------
    if "statut_sinistre_claim" not in base.columns:
        base["statut_sinistre_claim"] = "Unknown"

    # -------------------------
    # Merge policy features
    # -------------------------
    policy_feats = [
        "contract_id",
        "type_couverture",
        "prime_assurance_annuelle",
        "nb_sinistres_precedents",
        "delai_souscription_sinistre_jours",
        "policy_duration_days",
        "policy_tenure_bucket",
        "date_debut_contrat",
    ]
    policy_feats = [c for c in policy_feats if c in dim_policy.columns]
    if policy_feats:
        base = base.merge(
            dim_policy[policy_feats].drop_duplicates(subset=["contract_id"]),
            on="contract_id", how="left"
        )

    # -------------------------
    # Merge client features
    # -------------------------
    client_feats = [
        "client_id", "age", "age_group", "genre",
        "revenu_annuel", "income_band",
        "score_credit", "credit_band",
        "nb_retards_paiement", "nb_infractions_majeures", "points_permis_retires",
        "driving_risk_score", "financial_stress_score", "responsible_behavior_score",
        "risque_comportemental", "risque_rse", "risque_financier", "risque_fraude", "risque_global",
        "changement_frequent_assureur",
        "nombre_enfants",
    ]
    client_feats = [c for c in client_feats if c in dim_client.columns]
    if client_feats:
        base = base.merge(
            dim_client[client_feats].drop_duplicates(subset=["client_id"]),
            on="client_id", how="left"
        )

    # -------------------------
    # Merge vehicle features
    # -------------------------
    vehicle_feats = [
        "vehicle_id", "type_vehicule", "marque", "modele", "usage_vehicule",
        "vehicle_age", "valeur_vehicule", "vehicle_value_band",
        "kilometrage_actuel", "mileage_per_year", "puissance_fiscale",
    ]
    vehicle_feats = [c for c in vehicle_feats if c in dim_vehicle.columns]
    if vehicle_feats:
        base = base.merge(
            dim_vehicle[vehicle_feats].drop_duplicates(subset=["vehicle_id"]),
            on="vehicle_id", how="left"
        )

    # -------------------------
    # Claim-level derived features
    # -------------------------
    if "prime_assurance_annuelle" in base.columns and "valeur_vehicule" in base.columns:
        denom = base["valeur_vehicule"].replace(0, np.nan)
        base["premium_to_value_ratio"] = base["prime_assurance_annuelle"] / denom
        base["premium_to_value_ratio"] = clip_outliers(base["premium_to_value_ratio"])

    if "date_sinistre_claim" in base.columns:
        dt = pd.to_datetime(base["date_sinistre_claim"], errors="coerce")
        base["claim_year"] = dt.dt.year
        base["claim_month"] = dt.dt.month
        base["claim_quarter"] = dt.dt.quarter
        base["claim_dayofweek"] = dt.dt.dayofweek
        base["claim_hour"] = dt.dt.hour

    # -------------------------
    # LEAKAGE CONTROL
    # -------------------------
    # When predicting delay at claim creation time, drop anything that
    # directly encodes closure or processing duration.
    predict_at_opening = True
    if predict_at_opening:
        leakage_cols = [
            "date_cloture_claim",
            "duree_traitement_jours",
            "duree_traitement_heures",
        ]
        base = base.drop(columns=[c for c in leakage_cols if c in base.columns], errors="ignore")

    ml_claim = base.copy()
    ml_claim = ml_claim.drop(columns=["description_sinistre_claim"], errors="ignore")

    critical_cols = ["sla_jours", "is_delayed"]
    missing = [col for col in critical_cols if col not in ml_claim.columns]
    if missing:
        print(f"[WARNING] ML dataset missing critical columns: {missing}")
        print(f"[WARNING] Available columns: {list(ml_claim.columns)}")

    return ml_claim.reset_index(drop=True)
