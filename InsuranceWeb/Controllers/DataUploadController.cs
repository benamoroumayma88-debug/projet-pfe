using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Data.SqlClient;
using System.Data;
using System.Diagnostics;
using System.Globalization;
using System.Text;

namespace InsuranceWeb.Controllers
{
    [Authorize(Roles = "Manager")]
    public class DataUploadController : Controller
    {
        private readonly IConfiguration _config;
        private readonly ILogger<DataUploadController> _logger;

        // ── Pipeline tracking (single-server) ──
        private static readonly object _pipelineLock = new();
        private static Process? _runningPipeline;
        private static string _pipelineStatus = "idle"; // idle | running | completed | failed
        private static string _pipelineOutput = "";
        private static DateTime? _pipelineStartTime;
        private static DateTime? _pipelineEndTime;

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

                // Trigger the ETL + ML pipeline in the background
                var pipelineTriggered = TriggerPipeline();

                ViewBag.Success = $"Successfully uploaded {insertedCount} rows to {targetTable}.";
                if (pipelineTriggered)
                {
                    ViewBag.PipelineTriggered = true;
                    ViewBag.Success += " The ETL & ML pipeline has been triggered in the background.";
                }
                else
                {
                    ViewBag.PipelineAlreadyRunning = true;
                    ViewBag.Success += " A pipeline is already running — it will pick up the new data.";
                }

                return View("Index");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "CSV upload failed for table {Table}", targetTable);
                ViewBag.Error = $"Upload failed: {ex.Message}";
                return View("Index");
            }
        }

        /// <summary>
        /// AJAX endpoint: returns current pipeline status as JSON.
        /// </summary>
        [HttpGet]
        public IActionResult PipelineStatus()
        {
            lock (_pipelineLock)
            {
                return Json(new
                {
                    status = _pipelineStatus,
                    output = _pipelineOutput,
                    startTime = _pipelineStartTime?.ToString("yyyy-MM-dd HH:mm:ss"),
                    endTime = _pipelineEndTime?.ToString("yyyy-MM-dd HH:mm:ss"),
                    durationSeconds = _pipelineStartTime.HasValue
                        ? (int)((_pipelineEndTime ?? DateTime.Now) - _pipelineStartTime.Value).TotalSeconds
                        : 0
                });
            }
        }

        /// <summary>
        /// Launch auto_pipeline.py --force as a background process.
        /// Returns false if a pipeline is already running.
        /// </summary>
        private bool TriggerPipeline()
        {
            lock (_pipelineLock)
            {
                if (_pipelineStatus == "running" && _runningPipeline != null && !_runningPipeline.HasExited)
                {
                    _logger.LogInformation("Pipeline already running — skipping trigger.");
                    return false;
                }

                var pythonPath = _config["Pipeline:PythonPath"] ?? "python";
                var scriptPath = _config["Pipeline:ScriptPath"] ?? @"..\InsuranceETL\auto_pipeline.py";

                // Resolve relative to the web app's content root
                if (!Path.IsPathRooted(scriptPath))
                {
                    scriptPath = Path.GetFullPath(Path.Combine(
                        Directory.GetCurrentDirectory(), scriptPath));
                }

                _pipelineStatus = "running";
                _pipelineOutput = "";
                _pipelineStartTime = DateTime.Now;
                _pipelineEndTime = null;

                _logger.LogInformation("Triggering pipeline: {Python} {Script} --force",
                    pythonPath, scriptPath);
            }

            // Start outside the lock so it doesn't block
            var pythonExe = _config["Pipeline:PythonPath"] ?? "python";
            var script = _config["Pipeline:ScriptPath"] ?? @"..\InsuranceETL\auto_pipeline.py";
            if (!Path.IsPathRooted(script))
            {
                script = Path.GetFullPath(Path.Combine(
                    Directory.GetCurrentDirectory(), script));
            }

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{script}\" --force",
                WorkingDirectory = Path.GetDirectoryName(script),
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            psi.Environment["PYTHONIOENCODING"] = "utf-8";

            Task.Run(() =>
            {
                try
                {
                    var process = new Process { StartInfo = psi };
                    var output = new StringBuilder();

                    process.OutputDataReceived += (_, e) =>
                    {
                        if (e.Data != null)
                        {
                            lock (_pipelineLock) { _pipelineOutput += e.Data + "\n"; }
                        }
                    };
                    process.ErrorDataReceived += (_, e) =>
                    {
                        if (e.Data != null)
                        {
                            lock (_pipelineLock) { _pipelineOutput += "[ERR] " + e.Data + "\n"; }
                        }
                    };

                    process.Start();
                    lock (_pipelineLock) { _runningPipeline = process; }

                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();

                    lock (_pipelineLock)
                    {
                        _pipelineEndTime = DateTime.Now;
                        _pipelineStatus = process.ExitCode == 0 ? "completed" : "failed";
                        _runningPipeline = null;
                    }

                    _logger.LogInformation("Pipeline finished with exit code {Code}", process.ExitCode);
                }
                catch (Exception ex)
                {
                    lock (_pipelineLock)
                    {
                        _pipelineStatus = "failed";
                        _pipelineOutput += $"\n[FATAL] {ex.Message}\n";
                        _pipelineEndTime = DateTime.Now;
                        _runningPipeline = null;
                    }
                    _logger.LogError(ex, "Pipeline process failed");
                }
            });

            return true;
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
