using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Data.SqlClient;
using System.Data;
using System.Globalization;

namespace InsuranceWeb.Controllers
{
    [Authorize(Roles = "Manager")]
    public class DataUploadController : Controller
    {
        private readonly IConfiguration _config;
        private readonly ILogger<DataUploadController> _logger;

        // Allowed tables and their schema
        private static readonly Dictionary<string, string[]> AllowedTables = new()
        {
            ["Clients"] = new[] {
                "Client_ID", "Nom", "Prénom", "Genre", "Age", "Niveau_Professionnel",
                "Revenu_Annuel", "Score_Credit", "Gouvernorat", "Ville",
                "Nb_Retards_Paiement", "Nb_Infractions_Majeures", "Points_Permis_Retires",
                "Participe_Conduite_Responsable", "Entretien_Regulier", "Vehicule_Peu_Polluant",
                "Engagement_Securite_Routiere", "Incidents_Paiement_Assureur", "Historique_Dettes",
                "Changement_Frequent_Assureur", "Nombre_Enfants", "Driving_Behavior",
                "Num_Contracts_Target", "Risque_Comportemental", "Risque_RSE",
                "Risque_Financier", "Risque_Fraude", "Risque_Global"
            },
            ["Vehicules"] = new[] {
                "Vehicle_ID", "Contract_ID", "Type_Vehicule", "Marque", "Modele",
                "Annee_Modele", "Puissance_Fiscale", "Kilometrage_Actuel",
                "Valeur_Vehicule", "Immatriculation", "Usage_Vehicule"
            },
            ["Polices_Assurance"] = new[] {
                "Contract_ID", "Client_ID", "Date_Debut_Contrat", "Date_Fin_Contrat",
                "Type_Couverture", "Prime_Assurance_Annuelle",
                "Nb_Sinistres_Precedents", "Delai_Souscription_Sinistre_Jours"
            },
            ["Sinistres"] = new[] {
                "Claim_ID", "Contract_ID", "Client_ID", "Vehicle_ID",
                "Date_Sinistre_Claim", "Type_Sinistre_Claim", "Description_Sinistre_Claim",
                "Montant_Estime_Dommage_Claim", "Montant_Indemnisation_Claim",
                "Est_Frauduleux_Claim", "Statut_Sinistre_Claim",
                "Incoherence_Dommages", "Nature_Sinistre_Consistante",
                "Date_Debut_Contrat", "Date_Fin_Contrat", "Type_Couverture",
                "Date_Cloture_Claim", "Duree_Traitement_Jours",
                "Duree_Traitement_Heures", "SLA_Jours", "Is_Delayed"
            },
            ["addon_sinistres"] = new[] {
                "Claim_ID", "Contract_ID", "Client_ID", "Vehicle_ID",
                "Date_Sinistre_Claim", "Type_Sinistre_Claim", "Description_Sinistre_Claim",
                "Montant_Estime_Dommage_Claim", "Montant_Indemnisation_Claim",
                "Est_Frauduleux_Claim", "Statut_Sinistre_Claim",
                "Incoherence_Dommages", "Nature_Sinistre_Consistante",
                "Date_Cloture_Claim", "Duree_Traitement_Jours",
                "Duree_Traitement_Heures", "SLA_Jours", "Is_Delayed"
            }
        };

        public DataUploadController(IConfiguration config, ILogger<DataUploadController> logger)
        {
            _config = config;
            _logger = logger;
        }

        public IActionResult Index()
        {
            ViewBag.Tables = AllowedTables.Keys.ToList();
            return View();
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        [RequestSizeLimit(50_000_000)] // 50 MB
        public async Task<IActionResult> Upload(IFormFile csvFile, string targetTable)
        {
            ViewBag.Tables = AllowedTables.Keys.ToList();

            if (csvFile == null || csvFile.Length == 0)
            {
                ViewBag.Error = "Please select a CSV file to upload.";
                return View("Index");
            }

            if (!Path.GetExtension(csvFile.FileName).Equals(".csv", StringComparison.OrdinalIgnoreCase))
            {
                ViewBag.Error = "Only CSV files are allowed.";
                return View("Index");
            }

            if (string.IsNullOrEmpty(targetTable) || !AllowedTables.ContainsKey(targetTable))
            {
                ViewBag.Error = "Please select a valid target table.";
                return View("Index");
            }

            try
            {
                var expectedColumns = AllowedTables[targetTable];
                var rows = new List<string[]>();
                string[] csvHeaders;

                using (var reader = new StreamReader(csvFile.OpenReadStream()))
                {
                    var headerLine = await reader.ReadLineAsync();
                    if (string.IsNullOrWhiteSpace(headerLine))
                    {
                        ViewBag.Error = "CSV file is empty or has no header row.";
                        return View("Index");
                    }

                    csvHeaders = ParseCsvLine(headerLine);

                    // Validate that CSV headers match expected columns
                    var missingColumns = expectedColumns
                        .Where(ec => !csvHeaders.Any(ch => ch.Equals(ec, StringComparison.OrdinalIgnoreCase)))
                        .ToList();

                    if (missingColumns.Count > 0)
                    {
                        ViewBag.Error = $"CSV is missing required columns: {string.Join(", ", missingColumns)}";
                        ViewBag.ExpectedColumns = expectedColumns;
                        return View("Index");
                    }

                    // Read all data rows
                    string? line;
                    int lineNum = 1;
                    while ((line = await reader.ReadLineAsync()) != null)
                    {
                        lineNum++;
                        if (string.IsNullOrWhiteSpace(line)) continue;
                        var values = ParseCsvLine(line);
                        if (values.Length != csvHeaders.Length)
                        {
                            ViewBag.Error = $"Row {lineNum} has {values.Length} columns but header has {csvHeaders.Length}.";
                            return View("Index");
                        }
                        rows.Add(values);
                    }
                }

                if (rows.Count == 0)
                {
                    ViewBag.Error = "CSV file has no data rows.";
                    return View("Index");
                }

                // Build column index mapping (CSV column index -> expected column name)
                var columnMapping = new Dictionary<int, string>();
                for (int i = 0; i < csvHeaders.Length; i++)
                {
                    var matchedCol = expectedColumns
                        .FirstOrDefault(ec => ec.Equals(csvHeaders[i], StringComparison.OrdinalIgnoreCase));
                    if (matchedCol != null)
                    {
                        columnMapping[i] = matchedCol;
                    }
                }

                // Insert rows using parameterized queries
                var connString = _config.GetConnectionString("DefaultConnection");
                int insertedCount = 0;

                using var conn = new SqlConnection(connString);
                await conn.OpenAsync();

                // Use a transaction for atomicity
                using var transaction = conn.BeginTransaction();

                try
                {
                    foreach (var row in rows)
                    {
                        var columns = columnMapping.Values.ToList();
                        var paramNames = columns.Select((_, i) => $"@p{i}").ToList();

                        // Table name is from our whitelist, safe to interpolate
                        var sql = $"INSERT INTO dbo.[{targetTable}] ([{string.Join("], [", columns)}]) VALUES ({string.Join(", ", paramNames)})";

                        using var cmd = new SqlCommand(sql, conn, transaction);
                        for (int i = 0; i < columns.Count; i++)
                        {
                            var csvIndex = columnMapping.First(kv => kv.Value == columns[i]).Key;
                            var value = row[csvIndex];
                            cmd.Parameters.AddWithValue($"@p{i}", string.IsNullOrEmpty(value) ? DBNull.Value : (object)value);
                        }

                        await cmd.ExecuteNonQueryAsync();
                        insertedCount++;
                    }

                    transaction.Commit();
                }
                catch
                {
                    transaction.Rollback();
                    throw;
                }

                _logger.LogInformation("User {User} uploaded {Count} rows to {Table}",
                    User.FindFirst("Login")?.Value, insertedCount, targetTable);

                ViewBag.Success = $"Successfully uploaded {insertedCount} rows to {targetTable}.";
                return View("Index");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "CSV upload failed for table {Table}", targetTable);
                ViewBag.Error = $"Upload failed: {ex.Message}";
                return View("Index");
            }
        }

        [HttpGet]
        public IActionResult GetTableColumns(string table)
        {
            if (string.IsNullOrEmpty(table) || !AllowedTables.ContainsKey(table))
                return Json(new string[0]);

            return Json(AllowedTables[table]);
        }

        private static string[] ParseCsvLine(string line)
        {
            var fields = new List<string>();
            bool inQuotes = false;
            var field = new System.Text.StringBuilder();

            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (inQuotes)
                {
                    if (c == '"')
                    {
                        if (i + 1 < line.Length && line[i + 1] == '"')
                        {
                            field.Append('"');
                            i++;
                        }
                        else
                        {
                            inQuotes = false;
                        }
                    }
                    else
                    {
                        field.Append(c);
                    }
                }
                else
                {
                    if (c == '"')
                    {
                        inQuotes = true;
                    }
                    else if (c == ',' || c == ';')
                    {
                        fields.Add(field.ToString().Trim());
                        field.Clear();
                    }
                    else
                    {
                        field.Append(c);
                    }
                }
            }

            fields.Add(field.ToString().Trim());
            return fields.ToArray();
        }
    }
}
