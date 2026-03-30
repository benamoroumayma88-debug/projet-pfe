using InsuranceWeb.Data;
using InsuranceWeb.Models;
using InsuranceWeb.Utilities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    /// <summary>
    /// Fraud Predictions controller - accessible to Manager and Fraud Agent roles
    /// Fraud Agents can only view, Managers can view and modify
    /// </summary>
    [Authorize(Roles = "Manager,Business Analyst")]
    public class FraudPredictionsController : Controller
    {
        private readonly AppDbContext _db;
        private const int PageSize = 20;

        public FraudPredictionsController(AppDbContext db) => _db = db;

        public async Task<IActionResult> Index(
            string? runId, string? riskLevel, string? claimId,
            bool flaggedOnly = false, int page = 1)
        {
            var availableRuns = await _db.ClaimFraudPredictions
                .Select(x => x.PredictionRunId)
                .Distinct()
                .OrderByDescending(x => x)
                .ToListAsync();
            var runList = availableRuns.Where(r => r != null).Cast<string>().ToList();

            if (string.IsNullOrEmpty(runId) && runList.Any())
                runId = runList.First();

            // Summary
            ClaimFraudSummary? summary = null;
            if (!string.IsNullOrEmpty(runId))
            {
                summary = await _db.ClaimFraudSummaries
                    .Where(x => x.PredictionRunId == runId)
                    .AsNoTracking()
                    .FirstOrDefaultAsync();
            }

            // Priority cases
            var topRisk = new List<ClaimFraudPriorityCase>();
            var critical = new List<ClaimFraudPriorityCase>();
            if (!string.IsNullOrEmpty(runId))
            {
                topRisk = await _db.ClaimFraudPriorityCases
                    .Where(x => x.PredictionRunId == runId && x.PriorityListType == "TOP_20_RISK")
                    .OrderBy(x => x.PriorityRank)
                    .AsNoTracking()
                    .ToListAsync();

                critical = await _db.ClaimFraudPriorityCases
                    .Where(x => x.PredictionRunId == runId && x.PriorityListType == "CRITICAL_TO_MONITOR")
                    .OrderBy(x => x.PriorityRank)
                    .AsNoTracking()
                    .ToListAsync();
            }

            // Predictions
            var query = _db.ClaimFraudPredictions.AsNoTracking();
            if (!string.IsNullOrEmpty(runId))
                query = query.Where(x => x.PredictionRunId == runId);
            if (!string.IsNullOrEmpty(riskLevel))
                query = query.Where(x => x.RiskLevel == riskLevel);
            if (!string.IsNullOrEmpty(claimId))
                query = query.Where(x => x.ClaimId!.Contains(claimId));
            if (flaggedOnly)
                query = query.Where(x => x.PredictedFraud == 1);

            var totalCount = await query.CountAsync();
            var claims = await query
                .OrderByDescending(x => x.FraudProbability)
                .Skip((page - 1) * PageSize)
                .Take(PageSize)
                .ToListAsync();

            var vm = new FraudDashboardViewModel
            {
                Summary = summary,
                Claims = claims,
                TopRiskCases = topRisk,
                CriticalCases = critical,
                PageNumber = page,
                PageSize = PageSize,
                TotalCount = totalCount,
                TotalPages = (int)Math.Ceiling(totalCount / (double)PageSize),
                SelectedRunId = runId,
                SelectedRiskLevel = riskLevel,
                SearchClaimId = claimId,
                FlaggedOnly = flaggedOnly,
                AvailableRunIds = runList,
            };

            return View(vm);
        }
    }
}
