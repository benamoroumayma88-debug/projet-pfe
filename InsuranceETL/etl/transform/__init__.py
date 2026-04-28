from typing import Dict, Any
import pandas as pd

from .clients import transform_clients
from .policies import transform_policies
from .vehicles import transform_vehicles
from .claims import transform_claims

from .dw_builders import (
    build_dim_client, build_dim_policy, build_dim_vehicle, build_dim_time, build_fact_claim
)
from .ml_builders import build_ml_claim_dataset


def transform_all(
    clients_raw: pd.DataFrame,
    policies_raw: pd.DataFrame,
    vehicles_raw: pd.DataFrame,
    claims_raw: pd.DataFrame
) -> Dict[str, Any]:

    clean_clients = transform_clients(clients_raw) if not clients_raw.empty else clients_raw
    clean_policies = transform_policies(policies_raw) if not policies_raw.empty else policies_raw
    clean_vehicles = transform_vehicles(vehicles_raw) if not vehicles_raw.empty else vehicles_raw
    clean_claims = transform_claims(claims_raw) if not claims_raw.empty else claims_raw

    if clean_clients.empty:
        print("[TRANSFORM] Warning: clean_clients is empty — dim_client will be skipped")
    if clean_policies.empty:
        print("[TRANSFORM] Warning: clean_policies is empty — dim_policy will be skipped")
    if clean_vehicles.empty:
        print("[TRANSFORM] Warning: clean_vehicles is empty — dim_vehicle will be skipped")
    if clean_claims.empty:
        print("[TRANSFORM] Warning: clean_claims is empty — fact_claim and ml_claim will be skipped")

    dim_client = build_dim_client(clean_clients) if not clean_clients.empty else pd.DataFrame()
    dim_policy = build_dim_policy(clean_policies) if not clean_policies.empty else pd.DataFrame()
    dim_vehicle = build_dim_vehicle(clean_vehicles) if not clean_vehicles.empty else pd.DataFrame()
    dim_time = build_dim_time(clean_policies, clean_claims)

    if not clean_claims.empty:
        fact_claim = build_fact_claim(clean_claims, clean_policies, clean_clients, clean_vehicles)
        ml_claim = build_ml_claim_dataset(
            clean_clients, clean_policies, clean_vehicles, clean_claims
        )
    else:
        fact_claim = pd.DataFrame()
        ml_claim = pd.DataFrame()

    return {
        "clean_clients": clean_clients,
        "clean_policies": clean_policies,
        "clean_vehicles": clean_vehicles,
        "clean_claims": clean_claims,

        "dim_client": dim_client,
        "dim_policy": dim_policy,
        "dim_vehicle": dim_vehicle,
        "dim_time": dim_time,
        "fact_claim": fact_claim,

        "ml_claim": ml_claim,
    }
