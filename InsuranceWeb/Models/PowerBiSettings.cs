namespace InsuranceWeb.Models
{
    public class PowerBiSettings
    {
        public string ReportServerBaseUrl { get; set; } = "http://localhost/Reports";
        public string DelayReportPath { get; set; } = string.Empty;
        public string CostReportPath { get; set; } = string.Empty;
        public string FraudReportPath { get; set; } = string.Empty;
        public string ForecastReportPath { get; set; } = string.Empty;

        public string DelayEmbedUrl   => BuildEmbedUrl(DelayReportPath);
        public string CostEmbedUrl    => BuildEmbedUrl(CostReportPath);
        public string FraudEmbedUrl   => BuildEmbedUrl(FraudReportPath);
        public string ForecastEmbedUrl => BuildEmbedUrl(ForecastReportPath);

        private string BuildEmbedUrl(string path) =>
            string.IsNullOrWhiteSpace(path)
                ? string.Empty
                : $"{ReportServerBaseUrl.TrimEnd('/')}{path}?rs:embed=true&rc:Toolbar=false";
    }
}
