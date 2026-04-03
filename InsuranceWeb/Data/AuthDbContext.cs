using InsuranceWeb.Models;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Data
{
    public class AuthDbContext : DbContext
    {
        public AuthDbContext(DbContextOptions<AuthDbContext> options) : base(options) { }

        public DbSet<User> Users { get; set; }
        public DbSet<Role> Roles { get; set; }
        public DbSet<Permission> Permissions { get; set; }
        public DbSet<RolePermission> RolePermissions { get; set; }
        public DbSet<AuditLog> AuditLogs { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Configure User
            modelBuilder.Entity<User>()
                .HasOne(u => u.Role)
                .WithMany(r => r.Users)
                .HasForeignKey(u => u.RoleId)
                .OnDelete(DeleteBehavior.SetNull);

            modelBuilder.Entity<User>()
                .HasIndex(u => u.Username)
                .IsUnique();

            modelBuilder.Entity<User>()
                .HasIndex(u => u.Email)
                .IsUnique();

            modelBuilder.Entity<User>()
                .HasIndex(u => u.Login)
                .IsUnique();

            modelBuilder.Entity<User>()
                .HasIndex(u => u.PasswordHash)
                .IsUnique();

            // Configure Role
            modelBuilder.Entity<Role>()
                .HasKey(r => r.RoleId);

            modelBuilder.Entity<Role>()
                .HasIndex(r => r.RoleName)
                .IsUnique();

            // Configure Permission
            modelBuilder.Entity<Permission>()
                .HasKey(p => p.PermissionId);

            modelBuilder.Entity<Permission>()
                .HasIndex(p => p.PermissionName)
                .IsUnique();

            // Configure RolePermission (junction table)
            modelBuilder.Entity<RolePermission>()
                .HasKey(rp => rp.RolePermissionId);

            modelBuilder.Entity<RolePermission>()
                .HasOne(rp => rp.Role)
                .WithMany(r => r.Permissions)
                .HasForeignKey(rp => rp.RoleId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<RolePermission>()
                .HasOne(rp => rp.Permission)
                .WithMany(p => p.RolePermissions)
                .HasForeignKey(rp => rp.PermissionId)
                .OnDelete(DeleteBehavior.Cascade);

            // Create unique constraint on role_id and permission_id
            modelBuilder.Entity<RolePermission>()
                .HasIndex(rp => new { rp.RoleId, rp.PermissionId })
                .IsUnique();

            // Seed default roles
            modelBuilder.Entity<Role>().HasData(
                new Role { RoleId = 1, RoleName = "Manager", Description = "Full access to all features, data upload, and reporting" },
                new Role { RoleId = 2, RoleName = "Business Analyst", Description = "Read-only access to dashboards and reports" },
                new Role { RoleId = 3, RoleName = "Admin", Description = "User and account management, platform administration" }
            );

            // Seed permissions
            var permissions = new List<Permission>
            {
                // Dashboard Permissions
                new Permission { PermissionId = 1, PermissionName = "View Dashboard", Resource = "Dashboard", Action = "View" },
                new Permission { PermissionId = 2, PermissionName = "Generate Reports", Resource = "Dashboard", Action = "Report" },
                
                // Delay Prediction Permissions
                new Permission { PermissionId = 3, PermissionName = "View Delay Predictions", Resource = "DelayPredictions", Action = "View" },
                new Permission { PermissionId = 4, PermissionName = "Modify Delay Settings", Resource = "DelayPredictions", Action = "Modify" },
                
                // Cost Prediction Permissions
                new Permission { PermissionId = 5, PermissionName = "View Cost Predictions", Resource = "CostPredictions", Action = "View" },
                new Permission { PermissionId = 6, PermissionName = "Modify Cost Settings", Resource = "CostPredictions", Action = "Modify" },
                
                // Fraud Detection Permissions
                new Permission { PermissionId = 7, PermissionName = "View Fraud Predictions", Resource = "FraudPredictions", Action = "View" },
                new Permission { PermissionId = 8, PermissionName = "Modify Fraud Settings", Resource = "FraudPredictions", Action = "Modify" },
                new Permission { PermissionId = 9, PermissionName = "Investigate Fraud", Resource = "FraudPredictions", Action = "Investigate" },
                
                // Forecast Permissions
                new Permission { PermissionId = 10, PermissionName = "View Forecast", Resource = "Forecast", Action = "View" },
                new Permission { PermissionId = 11, PermissionName = "Modify Forecast", Resource = "Forecast", Action = "Modify" },
                
                // Admin Permissions
                new Permission { PermissionId = 12, PermissionName = "Manage Users", Resource = "Admin", Action = "ManageUsers" },
                new Permission { PermissionId = 13, PermissionName = "View Audit Logs", Resource = "Admin", Action = "ViewLogs" },
                
                // Data Upload Permission
                new Permission { PermissionId = 14, PermissionName = "Upload Data", Resource = "DataUpload", Action = "Upload" }
            };
            modelBuilder.Entity<Permission>().HasData(permissions);

            // Seed role permissions
            var rolePermissions = new List<RolePermission>
            {
                // Manager - Full dashboard + data access (all views, modify, upload)
                new RolePermission { RolePermissionId = 1, RoleId = 1, PermissionId = 1 },
                new RolePermission { RolePermissionId = 2, RoleId = 1, PermissionId = 2 },
                new RolePermission { RolePermissionId = 3, RoleId = 1, PermissionId = 3 },
                new RolePermission { RolePermissionId = 4, RoleId = 1, PermissionId = 4 },
                new RolePermission { RolePermissionId = 5, RoleId = 1, PermissionId = 5 },
                new RolePermission { RolePermissionId = 6, RoleId = 1, PermissionId = 6 },
                new RolePermission { RolePermissionId = 7, RoleId = 1, PermissionId = 7 },
                new RolePermission { RolePermissionId = 8, RoleId = 1, PermissionId = 8 },
                new RolePermission { RolePermissionId = 9, RoleId = 1, PermissionId = 9 },
                new RolePermission { RolePermissionId = 10, RoleId = 1, PermissionId = 10 },
                new RolePermission { RolePermissionId = 11, RoleId = 1, PermissionId = 11 },
                new RolePermission { RolePermissionId = 12, RoleId = 1, PermissionId = 14 },  // Upload Data
                
                // Business Analyst - Read-only dashboard access
                new RolePermission { RolePermissionId = 13, RoleId = 2, PermissionId = 1 },
                new RolePermission { RolePermissionId = 14, RoleId = 2, PermissionId = 2 },
                new RolePermission { RolePermissionId = 15, RoleId = 2, PermissionId = 3 },
                new RolePermission { RolePermissionId = 16, RoleId = 2, PermissionId = 5 },
                new RolePermission { RolePermissionId = 17, RoleId = 2, PermissionId = 7 },
                new RolePermission { RolePermissionId = 18, RoleId = 2, PermissionId = 10 },
                
                // Admin - User management only
                new RolePermission { RolePermissionId = 19, RoleId = 3, PermissionId = 12 },
                new RolePermission { RolePermissionId = 20, RoleId = 3, PermissionId = 13 }
            };
            modelBuilder.Entity<RolePermission>().HasData(rolePermissions);
        }
    }
}
