using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_forecast_summary", Schema = "ml")]
    public class ClaimForecastSummary
    {
        [Key]
        [Column("summary_record_id")]
        public string SummaryRecordId { get; set; } = string.Empty;

        [Column("forecast_run_id")]
        public string? ForecastRunId { get; set; }

        [Column("generated_at")]
        public DateTime? GeneratedAt { get; set; }

        [Column("model_trained_at")]
        public string? ModelTrainedAt { get; set; }

        [Column("data_source")]
        public string? DataSource { get; set; }

        [Column("training_history_months")]
        public long TrainingHistoryMonths { get; set; }

        [Column("forecast_horizon_months")]
        public long ForecastHorizonMonths { get; set; }

        [Column("currency")]
        public string? Currency { get; set; }

        [Column("total_forecast_period")]
        public string? TotalForecastPeriod { get; set; }

        [Column("total_expected_claims")]
        public double TotalExpectedClaims { get; set; }

        [Column("total_expected_cost_tnd")]
        public double TotalExpectedCostTnd { get; set; }

        [Column("avg_monthly_delay_rate_pct")]
        public double AvgMonthlyDelayRatePct { get; set; }

        [Column("avg_monthly_fraud_rate_pct")]
        public double AvgMonthlyFraudRatePct { get; set; }

        [Column("total_expected_delays")]
        public double TotalExpectedDelays { get; set; }

        [Column("total_fraud_exposure_tnd")]
        public double TotalFraudExposureTnd { get; set; }

        [Column("total_net_savings_potential_tnd")]
        public double TotalNetSavingsPotentialTnd { get; set; }

        [Column("avg_agents_needed_per_month")]
        public double AvgAgentsNeededPerMonth { get; set; }

        [Column("peak_volume_month")]
        public string? PeakVolumeMonth { get; set; }

        [Column("peak_volume_claims")]
        public double PeakVolumeClaims { get; set; }

        [Column("peak_delay_month")]
        public string? PeakDelayMonth { get; set; }

        [Column("peak_delay_rate_pct")]
        public double PeakDelayRatePct { get; set; }

        [Column("peak_cost_month")]
        public string? PeakCostMonth { get; set; }

        [Column("peak_cost_tnd")]
        public double PeakCostTnd { get; set; }

        [Column("high_risk_months")]
        public string? HighRiskMonths { get; set; }

        [Column("surge_expected_months")]
        public string? SurgeExpectedMonths { get; set; }

        [Column("total_alerts")]
        public long TotalAlerts { get; set; }

        [Column("critical_alerts")]
        public long CriticalAlerts { get; set; }

        [Column("high_alerts")]
        public long HighAlerts { get; set; }

        [Column("strategic_insight")]
        public string? StrategicInsight { get; set; }
    }
}
