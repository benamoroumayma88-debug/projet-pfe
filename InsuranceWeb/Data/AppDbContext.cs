using InsuranceWeb.Models;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        // Delay
        public DbSet<ClaimDelayPrediction> ClaimDelayPredictions { get; set; }
        public DbSet<ClaimDelayRunSummary> ClaimDelayRunSummaries { get; set; }

        // Cost
        public DbSet<ClaimCostPrediction> ClaimCostPredictions { get; set; }
        public DbSet<ClaimCostRunSummary> ClaimCostRunSummaries { get; set; }

        // Fraud
        public DbSet<ClaimFraudPrediction> ClaimFraudPredictions { get; set; }
        public DbSet<ClaimFraudSummary> ClaimFraudSummaries { get; set; }
        public DbSet<ClaimFraudPriorityCase> ClaimFraudPriorityCases { get; set; }

        // Forecast
        public DbSet<ClaimForecastMonthly> ClaimForecastMonthlies { get; set; }
        public DbSet<ClaimForecastSummary> ClaimForecastSummaries { get; set; }
        public DbSet<ClaimForecastAlert> ClaimForecastAlerts { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<ClaimDelayPrediction>().ToTable("claim_delay_predictions", "ml");
            modelBuilder.Entity<ClaimDelayRunSummary>().ToTable("claim_delay_run_summary", "ml");
            modelBuilder.Entity<ClaimCostPrediction>().ToTable("claim_cost_predictions", "ml");
            modelBuilder.Entity<ClaimCostRunSummary>().ToTable("claim_cost_run_summary", "ml");
            modelBuilder.Entity<ClaimFraudPrediction>().ToTable("claim_fraud_predictions", "ml");
            modelBuilder.Entity<ClaimFraudSummary>().ToTable("claim_fraud_summary", "ml");
            modelBuilder.Entity<ClaimFraudPriorityCase>().ToTable("claim_fraud_priority_cases", "ml");
            modelBuilder.Entity<ClaimForecastMonthly>().ToTable("claim_forecast_monthly", "ml");
            modelBuilder.Entity<ClaimForecastSummary>().ToTable("claim_forecast_summary", "ml");
            modelBuilder.Entity<ClaimForecastAlert>().ToTable("claim_forecast_alerts", "ml");
        }
    }
}
