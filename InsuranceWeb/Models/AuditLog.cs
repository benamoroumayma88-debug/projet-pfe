using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace InsuranceWeb.Models
{
    [Table("audit_logs")]
    public class AuditLog
    {
        [Key]
        [Column("log_id")]
        public int LogId { get; set; }

        [Column("user_id")]
        public int? UserId { get; set; }

        [Required]
        [Column("login_attempted")]
        [StringLength(100)]
        public string LoginAttempted { get; set; } = string.Empty;

        [Required]
        [Column("event_type")]
        [StringLength(50)]
        public string EventType { get; set; } = string.Empty;
        // "LOGIN_SUCCESS", "LOGIN_FAILED", "ACCOUNT_LOCKED", "IP_CHANGE"

        [Column("ip_address")]
        [StringLength(50)]
        public string? IpAddress { get; set; }

        [Column("previous_ip")]
        [StringLength(50)]
        public string? PreviousIp { get; set; }

        [Column("severity")]
        [StringLength(20)]
        public string Severity { get; set; } = "INFO";
        // "INFO", "WARNING", "ERROR"

        [Column("message")]
        public string? Message { get; set; }

        [Column("consecutive_failures")]
        public int ConsecutiveFailures { get; set; }

        [Column("is_resolved")]
        public bool IsResolved { get; set; }

        [Column("resolved_by")]
        [StringLength(100)]
        public string? ResolvedBy { get; set; }

        [Column("resolved_at")]
        public DateTime? ResolvedAt { get; set; }

        [Column("created_at")]
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        // Navigation
        [ForeignKey("UserId")]
        public virtual User? User { get; set; }
    }
}
