using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("claim_forecast_monthly", Schema = "ml")]
    public class ClaimForecastMonthly
    {
        [Key]
        [Column("forecast_record_id")]
        public string ForecastRecordId { get; set; } = string.Empty;

        [Column("forecast_run_id")]
        public string? ForecastRunId { get; set; }

        [Column("generated_at")]
        public DateTime? GeneratedAt { get; set; }

        [Column("period")]
        public string? Period { get; set; }

        [Column("month")]
        public string? Month { get; set; }

        [Column("year")]
        public long? Year { get; set; }

        [Column("month_number")]
        public long? MonthNumber { get; set; }

        [Column("seasonal_context")]
        public string? SeasonalContext { get; set; }

        [Column("risk_level")]
        public string? RiskLevel { get; set; }

        [Column("is_surge_month")]
        public bool IsSurgeMonth { get; set; }

        [Column("volume_surge_pct")]
        public double? VolumeSurgePct { get; set; }

        [Column("alert_count")]
        public long AlertCount { get; set; }

        [Column("alert_messages")]
        public string? AlertMessages { get; set; }

        [Column("recommendations")]
        public string? Recommendations { get; set; }

        [Column("forecast_claim_volume")]
        public double ForecastClaimVolume { get; set; }

        [Column("forecast_total_indemnisation_tnd")]
        public double ForecastTotalIndemnisationTnd { get; set; }

        [Column("forecast_delay_rate_pct")]
        public double ForecastDelayRatePct { get; set; }

        [Column("forecast_fraud_rate_pct")]
        public double ForecastFraudRatePct { get; set; }

        [Column("forecast_avg_claim_amount_tnd")]
        public double ForecastAvgClaimAmountTnd { get; set; }

        [Column("kpi_expected_delayed_claims")]
        public double KpiExpectedDelayedClaims { get; set; }

        [Column("kpi_expected_fraud_cases")]
        public double KpiExpectedFraudCases { get; set; }

        [Column("kpi_expected_fraud_exposure_tnd")]
        public double KpiExpectedFraudExposureTnd { get; set; }

        [Column("kpi_recommended_agents")]
        public long KpiRecommendedAgents { get; set; }

        [Column("kpi_staffing_cost_tnd")]
        public double KpiStaffingCostTnd { get; set; }

        [Column("kpi_total_delay_cost_tnd")]
        public double KpiTotalDelayCostTnd { get; set; }

        [Column("kpi_preventable_delay_cost_tnd")]
        public double KpiPreventableDelayCostTnd { get; set; }

        [Column("kpi_net_fraud_savings_tnd")]
        public double KpiNetFraudSavingsTnd { get; set; }

        [Column("kpi_net_savings_potential_tnd")]
        public double KpiNetSavingsPotentialTnd { get; set; }

        [Column("kpi_intervention_roi_pct")]
        public double KpiInterventionRoiPct { get; set; }

        [Column("kpi_budget_variance_pct")]
        public double KpiBudgetVariancePct { get; set; }

        [Column("kpi_workload_index")]
        public double KpiWorkloadIndex { get; set; }
    }
}
