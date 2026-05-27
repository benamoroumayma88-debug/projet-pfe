using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_cost_run_summary", Schema = "ml")]
    public class ClaimCostRunSummary
    {
        [Key]
        [Column("summary_record_id")]
        public string SummaryRecordId { get; set; } = string.Empty;

        [Column("prediction_run_id")]
        public string? PredictionRunId { get; set; }

        [Column("scored_at")]
        public DateTime? ScoredAt { get; set; }

        [Column("total_active_claims")]
        public long TotalActiveClaims { get; set; }

        [Column("total_predicted_cost")]
        public double TotalPredictedCost { get; set; }

        [Column("average_cost_per_claim")]
        public double AverageCostPerClaim { get; set; }

        [Column("high_cost_rate")]
        public double HighCostRate { get; set; }

        [Column("budget_deviation_risk")]
        public double BudgetDeviationRisk { get; set; }

        [Column("cost_threshold_tnd")]
        public double CostThresholdTnd { get; set; }

        [Column("projection_month")]
        public long? ProjectionMonth { get; set; }
    }
}
