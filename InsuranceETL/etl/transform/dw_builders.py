# etl/transform/dw_builders.py
"""
Data warehouse builders.

The DW tables (dw.dim_*, dw.fact_claim) ARE the cleaned data store —
they hold exactly the columns produced by the transform layer, deduplicated
on their natural keys. There is no separate stg.* layer: ml_builders reads
directly from these DW tables.
"""
import pandas as pd


def build_dim_client(clean_clients: pd.DataFrame) -> pd.DataFrame:
    """Client dimension = cleaned client data, deduplicated by client_id."""
    if "client_id" in clean_clients.columns:
        return clean_clients.drop_duplicates(subset=["client_id"]).reset_index(drop=True)
    return clean_clients.reset_index(drop=True)


def build_dim_policy(clean_policies: pd.DataFrame) -> pd.DataFrame:
    """Policy dimension = cleaned policy data, deduplicated by contract_id."""
    if "contract_id" in clean_policies.columns:
        return clean_policies.drop_duplicates(subset=["contract_id"]).reset_index(drop=True)
    return clean_policies.reset_index(drop=True)


def build_dim_vehicle(clean_vehicles: pd.DataFrame) -> pd.DataFrame:
    """Vehicle dimension = cleaned vehicle data, deduplicated by vehicle_id."""
    if "vehicle_id" in clean_vehicles.columns:
        return clean_vehicles.drop_duplicates(subset=["vehicle_id"]).reset_index(drop=True)
    return clean_vehicles.reset_index(drop=True)


def build_dim_time(policies: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """Time dimension built from all date columns across policies and claims."""
    dates = []
    for col in ["date_debut_contrat", "date_fin_contrat"]:
        if col in policies.columns:
            dates.append(policies[col])

    for col in ["date_sinistre_claim", "date_cloture_claim"]:
        if col in claims.columns:
            dates.append(claims[col])

    if not dates:
        return pd.DataFrame(columns=["date_key", "full_date", "year", "month", "day", "quarter", "week_of_year"])

    all_dates = pd.concat(dates, ignore_index=True).dropna()
    all_dates = pd.to_datetime(all_dates, errors="coerce").dropna().dt.normalize()
    all_dates = all_dates.drop_duplicates().sort_values()

    dim_time = pd.DataFrame({"full_date": all_dates})
    dim_time["date_key"] = dim_time["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim_time["year"] = dim_time["full_date"].dt.year
    dim_time["month"] = dim_time["full_date"].dt.month
    dim_time["day"] = dim_time["full_date"].dt.day
    dim_time["quarter"] = dim_time["full_date"].dt.quarter
    dim_time["week_of_year"] = dim_time["full_date"].dt.isocalendar().week.astype(int)
    return dim_time.reset_index(drop=True)


def build_fact_claim(clean_claims: pd.DataFrame) -> pd.DataFrame:
    """Claim fact = cleaned claim data, deduplicated by claim_id."""
    if "claim_id" in clean_claims.columns:
        return clean_claims.drop_duplicates(subset=["claim_id"]).reset_index(drop=True)
    return clean_claims.reset_index(drop=True)
