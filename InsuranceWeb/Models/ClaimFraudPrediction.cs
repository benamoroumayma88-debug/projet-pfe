using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_fraud_predictions", Schema = "ml")]
    public class ClaimFraudPrediction
    {
        [Key]
        [Column("prediction_record_id")]
        public string PredictionRecordId { get; set; } = string.Empty;

        [Column("prediction_run_id")]
        public string? PredictionRunId { get; set; }

        [Column("scored_at")]
        public DateTime? ScoredAt { get; set; }

        [Column("model_name")]
        public string? ModelName { get; set; }

        [Column("decision_threshold")]
        public double? DecisionThreshold { get; set; }

        [Column("currency")]
        public string? Currency { get; set; }

        [Column("claim_id")]
        public string? ClaimId { get; set; }

        [Column("client_id")]
        public string? ClientId { get; set; }

        [Column("contract_id")]
        public string? ContractId { get; set; }

        [Column("vehicle_id")]
        public string? VehicleId { get; set; }

        [Column("date_sinistre_claim")]
        public DateTime? DateSinistreClaim { get; set; }

        [Column("statut_sinistre_claim")]
        public string? StatutSinistreClaim { get; set; }

        [Column("type_sinistre_claim")]
        public string? TypeSinistreClaim { get; set; }

        [Column("claim_severity_bucket")]
        public string? ClaimSeverityBucket { get; set; }

        [Column("fraud_probability")]
        public double FraudProbability { get; set; }

        [Column("risk_level")]
        public string? RiskLevel { get; set; }

        [Column("recommended_action")]
        public string? RecommendedAction { get; set; }

        [Column("predicted_fraud")]
        public long PredictedFraud { get; set; }

        [Column("suspected_fraud_flag")]
        public long SuspectedFraudFlag { get; set; }

        [Column("high_risk_flag")]
        public long HighRiskFlag { get; set; }

        [Column("managerial_intervention_required")]
        public long ManagerialInterventionRequired { get; set; }

        [Column("estimated_investigation_hours")]
        public double? EstimatedInvestigationHours { get; set; }

        [Column("estimated_investigation_cost_tnd")]
        public double? EstimatedInvestigationCostTnd { get; set; }

        [Column("claim_amount_tnd")]
        public double? ClaimAmountTnd { get; set; }

        [Column("expected_fraud_exposure_claim_tnd")]
        public double? ExpectedFraudExposureClaimTnd { get; set; }

        [Column("expected_preventable_loss_claim_tnd")]
        public double? ExpectedPreventableLossClaimTnd { get; set; }
    }
}
