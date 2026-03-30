using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_fraud_priority_cases", Schema = "ml")]
    public class ClaimFraudPriorityCase
    {
        [Key]
        [Column("priority_case_record_id")]
        public string PriorityCaseRecordId { get; set; } = string.Empty;

        [Column("prediction_run_id")]
        public string? PredictionRunId { get; set; }

        [Column("scored_at")]
        public DateTime? ScoredAt { get; set; }

        [Column("model_name")]
        public string? ModelName { get; set; }

        [Column("decision_threshold")]
        public double? DecisionThreshold { get; set; }

        [Column("priority_list_type")]
        public string? PriorityListType { get; set; }

        [Column("priority_rank")]
        public long PriorityRank { get; set; }

        [Column("claim_id")]
        public string? ClaimId { get; set; }

        [Column("client_id")]
        public string? ClientId { get; set; }

        [Column("contract_id")]
        public string? ContractId { get; set; }

        [Column("fraud_probability")]
        public double FraudProbability { get; set; }

        [Column("risk_level")]
        public string? RiskLevel { get; set; }

        [Column("recommended_action")]
        public string? RecommendedAction { get; set; }

        [Column("predicted_fraud")]
        public long PredictedFraud { get; set; }

        [Column("estimated_investigation_hours")]
        public double? EstimatedInvestigationHours { get; set; }

        [Column("estimated_investigation_cost_tnd")]
        public double? EstimatedInvestigationCostTnd { get; set; }
    }
}
