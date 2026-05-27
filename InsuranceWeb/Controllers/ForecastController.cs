using InsuranceWeb.Data;
using InsuranceWeb.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    /// <summary>
    /// Forecast controller - accessible to Manager and Business Analyst roles
    /// Analysts can only view, Managers can view and modify
    /// </summary>
    [Authorize(Roles = "Manager,Business Analyst")]
    public class ForecastController : Controller
    {
        private readonly AppDbContext _db;

        public ForecastController(AppDbContext db) => _db = db;

        public async Task<IActionResult> Index(string? runId)
        {
            var availableRuns = await _db.ClaimForecastSummaries
                .Select(x => x.ForecastRunId)
                .Distinct()
                .OrderByDescending(x => x)
                .ToListAsync();
            var runList = availableRuns.Where(r => r != null).Cast<string>().ToList();

            if (string.IsNullOrEmpty(runId) && runList.Any())
                runId = runList.First();

            ClaimForecastSummary? summary = null;
            var months = new List<ClaimForecastMonthly>();
            var alerts = new List<ClaimForecastAlert>();

            if (!string.IsNullOrEmpty(runId))
            {
                summary = await _db.ClaimForecastSummaries
                    .Where(x => x.ForecastRunId == runId)
                    .AsNoTracking()
                    .FirstOrDefaultAsync();

                months = await _db.ClaimForecastMonthlies
                    .Where(x => x.ForecastRunId == runId)
                    .OrderBy(x => x.Period)
                    .AsNoTracking()
                    .ToListAsync();

                alerts = await _db.ClaimForecastAlerts
                    .Where(x => x.ForecastRunId == runId)
                    .OrderBy(x => x.Period)
                    .ThenByDescending(x => x.AlertLevel)
                    .AsNoTracking()
                    .ToListAsync();
            }

            var vm = new ForecastDashboardViewModel
            {
                Summary = summary,
                MonthlyForecasts = months,
                Alerts = alerts,
                SelectedRunId = runId,
                AvailableRunIds = runList,
            };

            return View(vm);
        }

        public async Task<IActionResult> Alerts(string? runId)
        {
            var availableRuns = await _db.ClaimForecastSummaries
                .Select(x => x.ForecastRunId)
                .Distinct()
                .OrderByDescending(x => x)
                .ToListAsync();
            var runList = availableRuns.Where(r => r != null).Cast<string>().ToList();

            if (string.IsNullOrEmpty(runId) && runList.Any())
                runId = runList.First();

            ClaimForecastSummary? summary = null;
            var alerts = new List<ClaimForecastAlert>();

            if (!string.IsNullOrEmpty(runId))
            {
                summary = await _db.ClaimForecastSummaries
                    .Where(x => x.ForecastRunId == runId)
                    .AsNoTracking()
                    .FirstOrDefaultAsync();

                alerts = await _db.ClaimForecastAlerts
                    .Where(x => x.ForecastRunId == runId)
                    .OrderBy(x => x.Period)
                    .ThenByDescending(x => x.AlertLevel)
                    .AsNoTracking()
                    .ToListAsync();
            }

            var vm = new ForecastDashboardViewModel
            {
                Summary = summary,
                Alerts = alerts,
                SelectedRunId = runId,
                AvailableRunIds = runList,
            };

            return View(vm);
        }
    }
}
