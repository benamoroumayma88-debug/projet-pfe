namespace InsuranceWeb.Models
{
    public class HomeDashboardViewModel
    {
        public string? LatestRunId { get; set; }
        public DateTime? LatestRunDate { get; set; }
        public int TotalClaimsScored { get; set; }
        public int PredictedDelayed { get; set; }
        public int OnTime { get; set; }
        public int HighRisk { get; set; }
        public int MediumRisk { get; set; }
        public int LowRisk { get; set; }
        public double AvgDelayProbabilityPct { get; set; }
        public double TotalEstimatedCostImpact { get; set; }
        public int AvgDelayDays { get; set; }
        public int RecommendedStaff { get; set; }
        public bool HasData => TotalClaimsScored > 0;
    }
}
