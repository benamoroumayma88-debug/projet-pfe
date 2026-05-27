# Removes all TST-* test claims from the database so the same CSV
# can be re-uploaded (e.g. during a presentation demo).
#
# Deletes from:
#   • dbo.Sinistres   (raw upload destination)
#   • dw.fact_claim   (data warehouse)
#   • ml.ml_claim     (ML feature dataset)
#
# Prediction tables (ml.claim_*_predictions) are NOT touched — those get
# fully replaced on each ML run via mode="replace".

$conn = New-Object System.Data.SqlClient.SqlConnection 'Server=(localdb)\MSSQLLocalDB;Database=InsuranceBI;Trusted_Connection=True;TrustServerCertificate=True;'
$conn.Open()

$targets = @(
    @{ Table='dbo.Sinistres'; IdCol='Claim_ID' },
    @{ Table='dw.fact_claim'; IdCol='claim_id' },
    @{ Table='ml.ml_claim';   IdCol='claim_id' }
)

foreach ($t in $targets) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "IF OBJECT_ID(N'$($t.Table)', N'U') IS NOT NULL SELECT 1 ELSE SELECT 0"
    $exists = $cmd.ExecuteScalar()
    if ($exists -ne 1) {
        Write-Host ("SKIP {0,-20} (table not found)" -f $t.Table) -ForegroundColor DarkGray
        continue
    }

    $cmd.CommandText = "DELETE FROM $($t.Table) WHERE [$($t.IdCol)] LIKE 'TST-%'"
    $deleted = $cmd.ExecuteNonQuery()
    Write-Host ("OK   {0,-20} {1,4} TST-* row(s) deleted" -f $t.Table, $deleted) -ForegroundColor Green
}

$conn.Close()
Write-Host "`nCleanup done. You can re-upload TestClaims_50.csv now." -ForegroundColor Cyan
