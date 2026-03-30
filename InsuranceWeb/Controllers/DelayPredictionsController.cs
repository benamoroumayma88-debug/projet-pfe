using InsuranceWeb.Data;
using InsuranceWeb.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    /// <summary>
    /// Delay Predictions controller - accessible to Manager and Business Analyst roles
    /// Analysts can only view, Managers can view and modify
    /// </summary>
    [Authorize(Roles = "Manager,Business Analyst")]
    public class DelayPredictionsController : Controller
    {
        private readonly AppDbContext _db;
        private const int PageSize = 20;

        public DelayPredictionsController(AppDbContext db)
        {
            _db = db;
        }

        public async Task<IActionResult> Index(
            string? runId,
            string? riskLevel,
            string? claimId,
            bool delayedOnly = false,
            int page = 1)
        {
            var availableRuns = await _db.ClaimDelayPredictions
                .Select(x => x.PredictionRunId)
                .Distinct()
                .OrderByDescending(x => x)
                .ToListAsync();

            var runList = availableRuns.Where(r => r != null).Cast<string>().ToList();

            // Default to the latest run
            if (string.IsNullOrEmpty(runId) && runList.Any())
                runId = runList.First();

            var query = _db.ClaimDelayPredictions.AsNoTracking();

            if (!string.IsNullOrEmpty(runId))
                query = query.Where(x => x.PredictionRunId == runId);

            if (!string.IsNullOrEmpty(riskLevel))
                query = query.Where(x => x.RiskLevel == riskLevel);

            if (!string.IsNullOrEmpty(claimId))
                query = query.Where(x => x.ClaimId == claimId);

            if (delayedOnly)
                query = query.Where(x => x.PredictedDelayed);

            // Load run summary
            ClaimDelayRunSummary? summary = null;
            if (!string.IsNullOrEmpty(runId))
            {
                summary = await _db.ClaimDelayRunSummaries
                    .Where(x => x.PredictionRunId == runId)
                    .AsNoTracking()
                    .FirstOrDefaultAsync();
            }

            var totalCount = await query.CountAsync();

            var claims = await query
                .OrderByDescending(x => x.DelayProbability)
                .Skip((page - 1) * PageSize)
                .Take(PageSize)
                .ToListAsync();

            var vm = new DelayPredictionsViewModel
            {
                Summary          = summary,
                Claims           = claims,
                PageNumber       = page,
                PageSize         = PageSize,
                TotalCount       = totalCount,
                TotalPages       = (int)Math.Ceiling(totalCount / (double)PageSize),
                SelectedRunId    = runId,
                SelectedRiskLevel = riskLevel,
                SearchClaimId    = claimId,
                DelayedOnly      = delayedOnly,
                AvailableRunIds  = runList
            };

            return View(vm);
        }
    }
}
