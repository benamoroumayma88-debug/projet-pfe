from etl.extract import extract_table

tables = [
    'dbo.Sinistres',
    'stg.clean_clients',
    'stg.clean_policies',
    'stg.clean_vehicles',
    'stg.clean_claims',
    'dw.fact_claim',
    'ml.ml_claim'
]

for t in tables:
    try:
        df = extract_table(t)
        print(f"{t}: rows={len(df):,} cols={len(df.columns)}")
        print(f"  sample cols: {df.columns.tolist()[:10]}")
    except Exception as e:
        print(f"{t}: ERROR -> {e}")

# Active status breakdown in ml.ml_claim
try:
    ml = extract_table('ml.ml_claim')
    if 'statut_sinistre_claim' in ml.columns:
        counts = ml['statut_sinistre_claim'].value_counts(dropna=False).to_dict()
        print('\nml.ml_claim statut_sinistre_claim counts:')
        for k,v in counts.items():
            print(f"  {k}: {v}")
        active = sum(counts.get(s,0) for s in ['Ouvert','En_cours','En_cours_d_expertise','En_cours_d_expertise','En_cours'])
        print(f"Total active claims (estimated): {active}")
    else:
        print('\nml.ml_claim has no statut_sinistre_claim column')
except Exception as e:
    print(f"ml.ml_claim ERROR -> {e}")
