namespace InsuranceWeb.Models
{
    public class PredictionRunSummaryViewModel
    {
        public List<PredictionRunSummary> PredictionRuns { get; set; } = new();
    }

    public class PredictionRunSummary
    {
        public string RunId { get; set; } = string.Empty;
        public DateTime? RunDate { get; set; }
        public int TotalClaims { get; set; }
        public int DelayedCount { get; set; }
        public int HighRiskCount { get; set; }
        public double TotalEstimatedCostImpact { get; set; }
        public double DelayedPercentage => TotalClaims > 0 ? Math.Round((DelayedCount / (double)TotalClaims) * 100, 1) : 0;
        public double HighRiskPercentage => TotalClaims > 0 ? Math.Round((HighRiskCount / (double)TotalClaims) * 100, 1) : 0;
    }
}