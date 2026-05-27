# Production Data Ingestion & ETL Workflow

## Overview
Weekly or monthly, managers export new data from operational systems as 4 CSV files:
- `clients.csv` - new or updated client profiles
- `policies.csv` - new or updated insurance policies  
- `vehicles.csv` - new or updated vehicle records
- `claims.csv` - new claim incidents

This guide shows how to **append** these to existing raw data and regenerate ML-ready datasets.

---

## Workflow Steps

### 1. Data Arrives (Weekly/Monthly)
Managers place CSV files in a shared folder, e.g., `/data/weekly_batch/2026-02-25/`

CSV Schema (must match dbo.* columns):

**clients.csv**
- client_id, nom, prenom, genre, age, revenu_annuel, score_credit, ... (34 total columns)

**policies.csv**
- contract_id, client_id, date_debut_contrat, type_couverture, prime_assurance_annuelle, ... (10 cols)

**vehicles.csv**
- vehicle_id, contract_id, type_vehicule, marque, modele, valeur_vehicule, ... (14 cols)

**claims.csv**
- claim_id, contract_id, client_id, vehicle_id, date_sinistre_claim, montant_estime_dommage_claim, statut_sinistre_claim, is_delayed, ... (21 cols)

### 2. Validate & Ingest (Admin/Data Team)

**Dry-run preview (no writes):**
```bash
cd c:\Projet PFE\InsuranceETL
python etl/ingest_new_data.py \
  --clients /path/to/clients.csv \
  --policies /path/to/policies.csv \
  --vehicles /path/to/vehicles.csv \
  --claims /path/to/claims.csv \
  --dry-run
```

Review output for:
- Row counts
- Missing/extra columns (script auto-fills missing, drops extra)
- Type validation warnings
- First 3 rows preview

**Live ingest (appends to dbo.*):**
```bash
python etl/ingest_new_data.py \
  --clients /path/to/clients.csv \
  --policies /path/to/policies.csv \
  --vehicles /path/to/vehicles.csv \
  --claims /path/to/claims.csv
```

Output:
```
[INGEST] /path/to/clients.csv -> dbo.Clients
  New data: 5000 rows, 34 columns
  Existing table: 10000 rows
  [SUCCESS] Inserted 5000 rows

[INGEST] /path/to/policies.csv -> dbo.Polices_Assurance
  New data: 8000 rows, 10 columns
  Existing table: 17509 rows
  [SUCCESS] Inserted 8000 rows

[INGEST] /path/to/vehicles.csv -> dbo.Vehicules
  New data: 8000 rows, 14 columns
  Existing table: 17509 rows
  [SUCCESS] Inserted 8000 rows

[INGEST] /path/to/claims.csv -> dbo.Sinistres
  New data: 6000 rows, 21 columns
  Existing table: 5252 rows
  [SUCCESS] Inserted 6000 rows

SUMMARY: 27000 total rows ingested
Next step: run `python main.py` to trigger ETL pipeline
```

### 3. Run ETL Pipeline (Auto-cleans & Transforms)

```bash
python main.py
```

This will:
1. **Extract** all raw data from dbo.* (now includes both old + new)
2. **Transform** via staging layer (stg.*): clean, normalize, deduplicate
3. **Load** into data warehouse (dw.*) & ML layer (ml.ml_claim)
4. Regenerate ml.ml_claim with fresh feature engineering

Output:
```
INSURANCE ETL PIPELINE STARTED
[EXTRACT] Reading table: dbo.Clients
[EXTRACT] 15000 rows loaded from dbo.Clients (was 10000, +5000 new)
...
[TRANSFORM] Done ✅
{'clean_rows': {'clients': 15000, 'policies': 25509, 'vehicles': 25509, 'claims': 11252}, ...}
[ML] ml_claim rows: 11000 (was 5252, +5748 new)
[LOAD] Done ✅
```

### 4. Retrain ML Models (Optional but Recommended)

After ingesting significant new data (e.g., 5k+ claims), retrain models:

```bash
python ml/delay/train.py
```

This will:
- Load fresh ml.ml_claim (now with more labeled examples)
- Recompute feature distributions
- Retrain Random Forest + XGBoost
- Save updated models to `ml/delay/models/`

Expected improvements:
- More closed claims = more trained labels (is_delayed=1/0)
- Larger dataset → lower AUC variance, more stable precision/recall
- New patterns captured from recent data

### 5. Generate Updated Dashboard

```bash
python ml/delay/predict.py
```

Pulls latest predictions on active claims (statut_sinistre_claim = Ouvert/En_cours):
- Filters active claims only
- Scores each for delay risk
- Outputs `ml/delay/dashboard_insights.json` 

---

## Scheduling Example (Weekly Cadence)

| Day | Time | Task | Owner |
|-----|------|------|-------|
| Mon | 6 AM | New data arrives in /data/weekly/ | Ops team |
| Mon | 7 AM | `python etl/ingest_new_data.py --dry-run` | Data analyst |
| Mon | 8 AM | Review preview, validate | Data analyst |
| Mon | 9 AM | `python etl/ingest_new_data.py` (live) | Data engineer |
| Mon | 10 AM | `python main.py` (ETL) | Automated (cron) |
| Mon | 11 AM | `python ml/delay/train.py` (if >5k new claims) | Automated (cron) |
| Mon | 12 PM | `python ml/delay/predict.py` (dashboard) | Automated (cron) |
| Mon | 1 PM | Dashboards refresh; managers can view | Managers |

---

## Schema Mapping Reference

### Raw Tables (dbo.*)
- **dbo.Clients** (18 cols): master client registry
- **dbo.Polices_Assurance** (10 cols): insurance contracts per client
- **dbo.Vehicules** (14 cols): vehicles covered per contract
- **dbo.Sinistres** (21 cols): claim incidents per contract

### Staging Tables (stg.*)
After ETL transform, raw data moves to normalized staging:
- **stg.clean_clients** (34 cols): enriched with risk scores
- **stg.clean_policies** (10 cols): normalized, deduplicated
- **stg.clean_vehicles** (14 cols): cleaned values, standardized
- **stg.clean_claims** (21 cols): standardized dates, status normalization

### Data Warehouse (dw.*)
Dimensional/fact tables for analytics:
- **dw.dim_client** (34 cols)
- **dw.dim_policy** (10 cols)
- **dw.dim_vehicle** (14 cols)
- **dw.dim_time** (time dimension, auto-generated)
- **dw.fact_claim** (34 cols): fact table, merged with dimensions

### ML Ready (ml.*)
- **ml.ml_claim** (60 cols): unified feature matrix
  - All claims with client/policy/vehicle features merged
  - 36 numeric + 13 categorical + 11 label/metadata columns
  - Ready for scikit-learn pipelines

---

## Error Handling & Rollback

If ingestion fails mid-way:

```bash
# 1. Check error messages
python etl/ingest_new_data.py --dry-run  # see what failed

# 2. If data was partially inserted, manually delete from dbo.* 
# (SQL Server Management Studio or sqlcmd):
DELETE FROM dbo.Sinistres WHERE claim_id LIKE 'SYN-%'

# 3. Fix CSV (correct schema, types, missing values)

# 4. Retry ingest
python etl/ingest_new_data.py --claims /path/to/fixed/claims.csv
```

---

## Key Points

✅ **Append, never replace** - ingest script uses INSERT (not TRUNCATE)
✅ **Schema validation** - auto-fills missing cols, drops extras, type-casts
✅ **Idempotent ETL** - running main.py multiple times is safe (deduplicates on claim_id)
✅ **Cascading refresh** - one ingest triggers stg → dw → ml layers
✅ **Model updates** - retrain ML models periodically for drift correction
✅ **Production-ready** - can be scheduled in cron / SQL Server Agent / Azure Data Factory

---

## Next Steps

1. Place your ChatGPT-generated CSV files in a folder
2. Run `python etl/ingest_new_data.py --dry-run` to preview
3. Run live ingest (see step 2 above)
4. Run `python main.py` to regenerate all layers
5. Retrain ML models & refresh dashboard

Questions? Check `etl/ingest_new_data.py` docstring or reach out.
