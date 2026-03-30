using InsuranceWeb.Data;
using InsuranceWeb.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    /// <summary>
    /// Cost Predictions controller - accessible to Manager and Business Analyst roles
    /// Analysts can only view, Managers can view and modify
    /// </summary>
    [Authorize(Roles = "Manager,Business Analyst")]
    public class CostPredictionsController : Controller
    {
        private readonly AppDbContext _db;
        private const int PageSize = 20;

        public CostPredictionsController(AppDbContext db) => _db = db;

        public async Task<IActionResult> Index(
            string? runId, string? riskLevel, string? claimId, int page = 1)
        {
            var availableRuns = await _db.ClaimCostPredictions
                .Select(x => x.PredictionRunId)
                .Distinct()
                .OrderByDescending(x => x)
                .ToListAsync();
            var runList = availableRuns.Where(r => r != null).Cast<string>().ToList();

            if (string.IsNullOrEmpty(runId) && runList.Any())
                runId = runList.First();

            // Get run summary
            ClaimCostRunSummary? summary = null;
            if (!string.IsNullOrEmpty(runId))
            {
                summary = await _db.ClaimCostRunSummaries
                    .Where(x => x.PredictionRunId == runId)
                    .AsNoTracking()
                    .FirstOrDefaultAsync();
            }

            // Filter predictions
            var query = _db.ClaimCostPredictions.AsNoTracking();
            if (!string.IsNullOrEmpty(runId))
                query = query.Where(x => x.PredictionRunId == runId);
            if (!string.IsNullOrEmpty(riskLevel))
                query = query.Where(x => x.CostRiskLevel == riskLevel);
            if (!string.IsNullOrEmpty(claimId))
                query = query.Where(x => x.ClaimId!.Contains(claimId));

            var totalCount = await query.CountAsync();
            var claims = await query
                .OrderByDescending(x => x.PredictedCost)
                .Skip((page - 1) * PageSize)
                .Take(PageSize)
                .ToListAsync();

            // Risk distribution for the selected run
            int highCount = 0, medCount = 0, lowCount = 0;
            if (!string.IsNullOrEmpty(runId))
            {
                var runQuery = _db.ClaimCostPredictions.Where(x => x.PredictionRunId == runId);
                highCount = await runQuery.CountAsync(x => x.CostRiskLevel == "High");
                medCount = await runQuery.CountAsync(x => x.CostRiskLevel == "Medium");
                lowCount = await runQuery.CountAsync(x => x.CostRiskLevel == "Low");
            }

            var vm = new CostDashboardViewModel
            {
                Summary = summary,
                Claims = claims,
                PageNumber = page,
                PageSize = PageSize,
                TotalCount = totalCount,
                TotalPages = (int)Math.Ceiling(totalCount / (double)PageSize),
                SelectedRunId = runId,
                SelectedRiskLevel = riskLevel,
                SearchClaimId = claimId,
                AvailableRunIds = runList,
                HighCostCount = highCount,
                MediumCostCount = medCount,
                LowCostCount = lowCount,
            };

            return View(vm);
        }
    }
}
