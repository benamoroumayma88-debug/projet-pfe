# Generates a 50-row Sinistres CSV with VALID foreign keys and NO empty cells.
# Every claim is generated as a CLOSED claim with realistic closure data so
# every one of the 18 columns gets a non-empty value.
#
# Output: c:\Projet PFE\TestClaims_50.csv

$outFile = 'C:\Projet PFE\TestClaims_50.csv'

# ── Query 50 random valid (contract, client, vehicle) combinations ──
$conn = New-Object System.Data.SqlClient.SqlConnection 'Server=(localdb)\MSSQLLocalDB;Database=InsuranceBI;Trusted_Connection=True;TrustServerCertificate=True;'
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandText = @"
SELECT TOP 50 p.Contract_ID, p.Client_ID, v.Vehicle_ID
FROM dbo.Polices_Assurance p
INNER JOIN dbo.Vehicules v ON v.Contract_ID = p.Contract_ID
WHERE p.Client_ID IN (SELECT Client_ID FROM dbo.Clients)
ORDER BY NEWID()
"@
$r = $cmd.ExecuteReader()
$combos = New-Object System.Collections.ArrayList
while ($r.Read()) {
    [void]$combos.Add(@{
        Contract  = $r['Contract_ID']
        Client    = $r['Client_ID']
        Vehicle   = $r['Vehicle_ID']
    })
}
$r.Close()
$conn.Close()

Write-Host "Pulled $($combos.Count) valid FK combinations from DB" -ForegroundColor Cyan

# ── Claim type catalog (descriptions without commas to avoid CSV escape issues) ──
$catalog = @(
    @{ Type='Accident'; SLA=30; Desc=@(
        'Collision laterale moderee','Collision par arriere moderee','Collision frontale grave',
        'Collision mineure en stationnement','Accrochage leger','Leger frottement',
        'Accident multiple impliquant plusieurs vehicules','Sortie de route sans renversement grave'
    )},
    @{ Type='Responsabilite civile'; SLA=25; Desc=@(
        'Dommage corporel leger a un tiers',
        'Dommage corporel tres leger a un tiers',
        'Dommage materiel grave a des tiers',
        'Dommage materiel modere a un autre vehicule',
        'Dommage materiel leger a un autre vehicule',
        'Collision grave avec pieton ou cycliste'
    )},
    @{ Type='Bris de glace'; SLA=15; Desc=@(
        'Bris vitre laterale','Bris total pare-brise','Fissure legere pare-brise','Impact pare-brise reparable'
    )},
    @{ Type='Incendie'; SLA=30; Desc=@('Incendie partiel du moteur','Debut incendie eteint rapidement')},
    @{ Type='Vol'; SLA=20; Desc=@('Vol partiel accessoires ou pieces','Vol total du vehicule')},
    @{ Type='Catastrophe naturelle'; SLA=25; Desc=@('Inondation partielle','Glissement de terrain sur vehicule','Grele importante')}
)

# Closed-claim statuses (every row is a closed claim so all columns are filled)
$closedStatuses = @('Clos_avec_indemnisation','Clos_sans_indemnisation','Cloture')

$rnd = New-Object System.Random

function New-ClaimId {
    $hex = -join (1..8 | ForEach-Object { '{0:X}' -f $rnd.Next(0,16) })
    "TST-$hex"
}

# ── Build CSV rows ──
$rows = New-Object System.Collections.ArrayList
[void]$rows.Add('Claim_ID,Contract_ID,Client_ID,Vehicle_ID,Date_Sinistre_Claim,Type_Sinistre_Claim,Description_Sinistre_Claim,Montant_Estime_Dommage_Claim,Montant_Indemnisation_Claim,Est_Frauduleux_Claim,Statut_Sinistre_Claim,Incoherence_Dommages,Nature_Sinistre_Consistante,Date_Cloture_Claim,Duree_Traitement_Jours,Duree_Traitement_Heures,SLA_Jours,Is_Delayed')

foreach ($c in $combos) {
    $cat = $catalog[$rnd.Next(0, $catalog.Count)]
    $desc = $cat.Desc[$rnd.Next(0, $cat.Desc.Count)]

    # Opening date: random in April 2026 only (so closures land in April-May)
    $day = $rnd.Next(1, 31)
    $hour = $rnd.Next(6, 23)
    $minute = $rnd.Next(0, 60)
    $openDate = (Get-Date '2026-04-01').AddDays($day - 1).AddHours($hour).AddMinutes($minute)

    # Damage estimate
    $estimate = switch ($cat.Type) {
        'Bris de glace' { $rnd.Next(200, 2000) }
        'Vol'           { $rnd.Next(5000, 70000) }
        default         { $rnd.Next(500, 50000) }
    }

    # Closure: random duration from (SLA - 5) to (SLA + 10) days
    $duration = $rnd.Next([Math]::Max(1, $cat.SLA - 5), $cat.SLA + 11)
    $closeDate = $openDate.AddDays($duration).AddHours($rnd.Next(0, 8))
    $hours = [Math]::Round(($closeDate - $openDate).TotalHours, 1)

    # Is the claim delayed?
    $isDelayed = if ($duration -gt $cat.SLA) { 1 } else { 0 }

    # Indemnisation: paid = 50%-100% of estimate (or 0 if "Clos_sans_indemnisation")
    $status = $closedStatuses[$rnd.Next(0, $closedStatuses.Count)]
    $indemnisation = if ($status -eq 'Clos_sans_indemnisation') {
        0
    } else {
        [Math]::Round($estimate * (0.5 + ($rnd.NextDouble() * 0.5)), 2)
    }

    # 5% fraud rate
    $fraud = ($rnd.Next(0, 100) -lt 5)
    $incoherence = $fraud
    $natureConsistente = -not $fraud

    # Quote description (handles parentheses safely; no commas in catalog anyway)
    $descQuoted = '"' + ($desc -replace '"','""') + '"'

    $openStr = $openDate.ToString('yyyy-MM-dd HH:mm:ss')
    $closeStr = $closeDate.ToString('yyyy-MM-dd HH:mm:ss')

    $line = "$(New-ClaimId),$($c.Contract),$($c.Client),$($c.Vehicle),$openStr,$($cat.Type),$descQuoted,$estimate,$indemnisation,$fraud,$status,$incoherence,$natureConsistente,$closeStr,$duration,$hours,$($cat.SLA),$isDelayed"
    [void]$rows.Add($line)
}

[System.IO.File]::WriteAllLines($outFile, $rows, [System.Text.UTF8Encoding]::new($false))

Write-Host "Wrote $($rows.Count - 1) test claim rows to: $outFile" -ForegroundColor Green
Write-Host "Every column is filled. Claim_IDs prefixed 'TST-' for easy cleanup." -ForegroundColor DarkCyan
