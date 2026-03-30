using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_fraud_summary", Schema = "ml")]
    public class ClaimFraudSummary
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

        [Column("currency")]
        public string? Currency { get; set; }

        [Column("threshold_used")]
        public double ThresholdUsed { get; set; }

        [Column("total_scored_claims")]
        public long TotalScoredClaims { get; set; }

        [Column("flagged_for_investigation")]
        public long FlaggedForInvestigation { get; set; }

        [Column("investigation_load_rate")]
        public double InvestigationLoadRate { get; set; }

        [Column("total_investigation_hours")]
        public double TotalInvestigationHours { get; set; }

        [Column("expected_fraud_cases_total")]
        public double ExpectedFraudCasesTotal { get; set; }

        [Column("expected_true_fraud_in_queue")]
        public double ExpectedTrueFraudInQueue { get; set; }

        [Column("expected_fraud_exposure_total_tnd")]
        public double ExpectedFraudExposureTotalTnd { get; set; }

        [Column("expected_preventable_loss_tnd")]
        public double ExpectedPreventableLossTnd { get; set; }

        [Column("expected_review_cost_tnd")]
        public double ExpectedReviewCostTnd { get; set; }

        [Column("expected_net_savings_tnd")]
        public double ExpectedNetSavingsTnd { get; set; }

        [Column("expected_roi")]
        public double ExpectedRoi { get; set; }

        [Column("precision_at_top_5pct")]
        public double PrecisionAtTop5Pct { get; set; }

        [Column("precision_at_top_10pct")]
        public double PrecisionAtTop10Pct { get; set; }

        [Column("capture_rate_top_10pct")]
        public double CaptureRateTop10Pct { get; set; }

        [Column("avg_ticket_size_in_queue_tnd")]
        public double AvgTicketSizeInQueueTnd { get; set; }

        [Column("high_risk_claim_rate")]
        public double HighRiskClaimRate { get; set; }

        [Column("average_predictive_risk_score")]
        public double AveragePredictiveRiskScore { get; set; }

        [Column("managerial_intervention_rate")]
        public double ManagerialInterventionRate { get; set; }

        [Column("suspected_fraud_claim_rate")]
        public double SuspectedFraudClaimRate { get; set; }

        [Column("low_risk_count")]
        public long LowRiskCount { get; set; }

        [Column("medium_risk_count")]
        public long MediumRiskCount { get; set; }

        [Column("high_risk_count")]
        public long HighRiskCount { get; set; }

        [Column("critical_risk_count")]
        public long CriticalRiskCount { get; set; }
    }
}
