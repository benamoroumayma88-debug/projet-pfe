namespace InsuranceWeb.Models
{
    // ─── Cost ──────────────────────────────────────
    public class CostDashboardViewModel
    {
        public ClaimCostRunSummary? Summary { get; set; }
        public List<ClaimCostPrediction> Claims { get; set; } = new();
        public int PageNumber { get; set; }
        public int PageSize { get; set; }
        public int TotalCount { get; set; }
        public int TotalPages { get; set; }
        public string? SelectedRunId { get; set; }
        public string? SelectedRiskLevel { get; set; }
        public string? SearchClaimId { get; set; }
        public List<string> AvailableRunIds { get; set; } = new();
        public bool HasPreviousPage => PageNumber > 1;
        public bool HasNextPage => PageNumber < TotalPages;

        // Chart data
        public int HighCostCount { get; set; }
        public int MediumCostCount { get; set; }
        public int LowCostCount { get; set; }
    }

    // ─── Fraud ─────────────────────────────────────
    public class FraudDashboardViewModel
    {
        public ClaimFraudSummary? Summary { get; set; }
        public List<ClaimFraudPrediction> Claims { get; set; } = new();
        public List<ClaimFraudPriorityCase> TopRiskCases { get; set; } = new();
        public List<ClaimFraudPriorityCase> CriticalCases { get; set; } = new();
        public int PageNumber { get; set; }
        public int PageSize { get; set; }
        public int TotalCount { get; set; }
        public int TotalPages { get; set; }
        public string? SelectedRunId { get; set; }
        public string? SelectedRiskLevel { get; set; }
        public string? SearchClaimId { get; set; }
        public bool FlaggedOnly { get; set; }
        public List<string> AvailableRunIds { get; set; } = new();
        public bool HasPreviousPage => PageNumber > 1;
        public bool HasNextPage => PageNumber < TotalPages;
    }

    // ─── Forecast ──────────────────────────────────
    public class ForecastDashboardViewModel
    {
        public ClaimForecastSummary? Summary { get; set; }
        public List<ClaimForecastMonthly> MonthlyForecasts { get; set; } = new();
        public List<ClaimForecastAlert> Alerts { get; set; } = new();
        public string? SelectedRunId { get; set; }
        public List<string> AvailableRunIds { get; set; } = new();
    }

    // ─── Home Overview ─────────────────────────────
    public class HomeOverviewViewModel
    {
        // Delay
        public ClaimDelayRunSummary? DelaySummary { get; set; }
        // Cost
        public ClaimCostRunSummary? CostSummary { get; set; }
        // Fraud
        public ClaimFraudSummary? FraudSummary { get; set; }
        // Forecast
        public ClaimForecastSummary? ForecastSummary { get; set; }
        public List<ClaimForecastMonthly> ForecastMonths { get; set; } = new();

        public bool HasDelay => DelaySummary != null;
        public bool HasCost => CostSummary != null;
        public bool HasFraud => FraudSummary != null;
        public bool HasForecast => ForecastSummary != null;
    }
}
