using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_delay_run_summary", Schema = "ml")]
    public class ClaimDelayRunSummary
    {
        [Key]
        [Column("summary_record_id")]
        public string SummaryRecordId { get; set; } = string.Empty;

        [Column("prediction_run_id")]
        public string? PredictionRunId { get; set; }

        [Column("scored_at")]
        public DateTime? ScoredAt { get; set; }

        [Column("model_name")]
        public string? ModelName { get; set; }

        [Column("decision_threshold")]
        public double DecisionThreshold { get; set; }

        [Column("total_active_claims")]
        public long TotalActiveClaims { get; set; }

        [Column("predicted_delayed_count")]
        public long PredictedDelayedCount { get; set; }

        [Column("high_risk_count")]
        public long HighRiskCount { get; set; }

        [Column("medium_risk_count")]
        public long MediumRiskCount { get; set; }

        [Column("low_risk_count")]
        public long LowRiskCount { get; set; }

        [Column("estimated_delayed_claims")]
        public double EstimatedDelayedClaims { get; set; }

        [Column("estimated_total_delay_days")]
        public long EstimatedTotalDelayDays { get; set; }

        [Column("avg_delay_days_per_claim")]
        public double AvgDelayDaysPerClaim { get; set; }

        [Column("estimated_cost_impact_tnd")]
        public double EstimatedCostImpactTnd { get; set; }

        [Column("avg_cost_per_delayed_claim")]
        public double AvgCostPerDelayedClaim { get; set; }

        [Column("recommended_staff")]
        public long RecommendedStaff { get; set; }

        [Column("projection_month")]
        public long? ProjectionMonth { get; set; }
    }
}
