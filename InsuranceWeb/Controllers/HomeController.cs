using System.Diagnostics;
using InsuranceWeb.Data;
using InsuranceWeb.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    /// <summary>
    /// Home/Dashboard controller - accessible to Manager and Analyst roles
    /// </summary>
    [Authorize]
    public class HomeController : Controller
    {
        private readonly AppDbContext _db;

        public HomeController(AppDbContext db) => _db = db;

        public async Task<IActionResult> Index()
        {
            var vm = new HomeOverviewViewModel();

            vm.DelaySummary = await _db.ClaimDelayRunSummaries
                .OrderByDescending(x => x.ScoredAt)
                .AsNoTracking()
                .FirstOrDefaultAsync();

            vm.CostSummary = await _db.ClaimCostRunSummaries
                .OrderByDescending(x => x.ScoredAt)
                .AsNoTracking()
                .FirstOrDefaultAsync();

            vm.FraudSummary = await _db.ClaimFraudSummaries
                .OrderByDescending(x => x.ScoredAt)
                .AsNoTracking()
                .FirstOrDefaultAsync();

            vm.ForecastSummary = await _db.ClaimForecastSummaries
                .OrderByDescending(x => x.GeneratedAt)
                .AsNoTracking()
                .FirstOrDefaultAsync();

            if (vm.ForecastSummary != null)
            {
                vm.ForecastMonths = await _db.ClaimForecastMonthlies
                    .Where(x => x.ForecastRunId == vm.ForecastSummary.ForecastRunId)
                    .OrderBy(x => x.Period)
                    .AsNoTracking()
                    .ToListAsync();
            }

            return View(vm);
        }

        [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
        public IActionResult Error()
        {
            return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
        }
    }
}
