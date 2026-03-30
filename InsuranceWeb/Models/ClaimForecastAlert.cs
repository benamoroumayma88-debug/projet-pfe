using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_forecast_alerts", Schema = "ml")]
    public class ClaimForecastAlert
    {
        [Key]
        [Column("alert_record_id")]
        public string AlertRecordId { get; set; } = string.Empty;

        [Column("forecast_run_id")]
        public string? ForecastRunId { get; set; }

        [Column("generated_at")]
        public DateTime? GeneratedAt { get; set; }

        [Column("period")]
        public string? Period { get; set; }

        [Column("month")]
        public string? Month { get; set; }

        [Column("risk_level")]
        public string? RiskLevel { get; set; }

        [Column("alert_level")]
        public string? AlertLevel { get; set; }

        [Column("alert_type")]
        public string? AlertType { get; set; }

        [Column("alert_message")]
        public string? AlertMessage { get; set; }

        [Column("is_surge_month")]
        public bool IsSurgeMonth { get; set; }
    }
}
