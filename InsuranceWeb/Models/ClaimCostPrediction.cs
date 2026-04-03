using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_cost_predictions", Schema = "ml")]
    public class ClaimCostPrediction
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

        [Column("predicted_cost")]
        public double PredictedCost { get; set; }

        [Column("cost_risk_level")]
        public string? CostRiskLevel { get; set; }

        [Column("prediction_month")]
        public long? PredictionMonth { get; set; }
    }
}
