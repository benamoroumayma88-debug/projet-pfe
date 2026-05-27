namespace InsuranceWeb.Models
{
    public class DelayPredictionsViewModel
    {
        public ClaimDelayRunSummary? Summary { get; set; }
        public List<ClaimDelayPrediction> Claims { get; set; } = new();
        public int PageNumber { get; set; }
        public int PageSize { get; set; }
        public int TotalCount { get; set; }
        public int TotalPages { get; set; }

        // Active filters
        public string? SelectedRunId { get; set; }
        public string? SelectedRiskLevel { get; set; }
        public string? SearchClaimId { get; set; }
        public bool DelayedOnly { get; set; }

        // Dropdown data
        public List<string> AvailableRunIds { get; set; } = new();

        public bool HasPreviousPage => PageNumber > 1;
        public bool HasNextPage => PageNumber < TotalPages;
    }
}
