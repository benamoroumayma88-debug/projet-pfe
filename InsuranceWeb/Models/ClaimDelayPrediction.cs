using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_delay_predictions", Schema = "ml")]
    public class ClaimDelayPrediction
    {
        [Key]
        [Column("prediction_record_id")]
        public string PredictionRecordId { get; set; } = string.Empty;

        [Column("prediction_run_id")]
        public string? PredictionRunId { get; set; }

        [Column("scored_at")]
        public DateTime? ScoredAt { get; set; }

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

        [Column("montant_estime_dommage_claim")]
        public double? MontantEstimeDommageClaim { get; set; }

        [Column("montant_indemnisation_claim")]
        public double? MontantIndemnisationClaim { get; set; }

        [Column("sla_jours")]
        public double? SlaJours { get; set; }

        [Column("delay_probability")]
        public double DelayProbability { get; set; }

        [Column("risk_level")]
        public string? RiskLevel { get; set; }

        [Column("predicted_delayed")]
        public long PredictedDelayedInt { get; set; }

        [NotMapped]
        public bool PredictedDelayed 
        { 
            get => PredictedDelayedInt != 0; 
            set => PredictedDelayedInt = value ? 1 : 0; 
        }

        [Column("predicted_delay_days")]
        public double? PredictedDelayDays { get; set; }

        [Column("estimated_cost_impact_claim")]
        public double? EstimatedCostImpactClaim { get; set; }

        [Column("decision_threshold")]
        public double? DecisionThreshold { get; set; }

        [Column("model_mode")]
        public string? ModelMode { get; set; }

        [Column("prediction_month")]
        public long? PredictionMonth { get; set; }
    }
}
