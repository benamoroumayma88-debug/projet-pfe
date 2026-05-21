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

        [NotMapped]
        public long EstimatedDelayedClaims { get; set; }

        [Column("total_excess_days")]
        public long EstimatedTotalDelayDays { get; set; }

        [Column("avg_excess_days_per_delayed")]
        public double AvgDelayDaysPerClaim { get; set; }

        [Column("estimated_delay_penalty_tnd")]
        public double EstimatedCostImpactTnd { get; set; }

        [NotMapped]
        public double AvgCostPerDelayedClaim { get; set; }

        [Column("recommended_agents")]
        public long RecommendedStaff { get; set; }

        [Column("staffing_cost_tnd")]
        public double StaffingCostTnd { get; set; }

        [Column("projection_month")]
        public long? ProjectionMonth { get; set; }
    }
}
