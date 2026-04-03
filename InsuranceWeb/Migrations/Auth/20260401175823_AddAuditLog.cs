using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace InsuranceWeb.Migrations.Auth
{
    /// <inheritdoc />
    public partial class AddAuditLog : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "audit_logs",
                columns: table => new
                {
                    log_id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    user_id = table.Column<int>(type: "int", nullable: true),
                    login_attempted = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    event_type = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    ip_address = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    previous_ip = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    severity = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    message = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    consecutive_failures = table.Column<int>(type: "int", nullable: false),
                    is_resolved = table.Column<bool>(type: "bit", nullable: false),
                    resolved_by = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    resolved_at = table.Column<DateTime>(type: "datetime2", nullable: true),
                    created_at = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_audit_logs", x => x.log_id);
                    table.ForeignKey(
                        name: "FK_audit_logs_users_user_id",
                        column: x => x.user_id,
                        principalTable: "users",
                        principalColumn: "user_id");
                });

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2798));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2803));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2804));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2805));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2806));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2808));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2809));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2810));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2811));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2813));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2814));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2815));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2816));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2817));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2841));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2843));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2844));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2845));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2846));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2847));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2848));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2849));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2849));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2851));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2852));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2852));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2853));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2854));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 15,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2855));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 16,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2855));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 17,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2856));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 18,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2857));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 19,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2858));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 20,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2859));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2727));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2730));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 4, 1, 17, 58, 23, 375, DateTimeKind.Utc).AddTicks(2731));

            migrationBuilder.CreateIndex(
                name: "IX_audit_logs_user_id",
                table: "audit_logs",
                column: "user_id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "audit_logs");

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(60));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(66));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(68));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(69));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(70));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(72));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(73));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(74));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(75));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(76));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(77));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(78));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(79));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(80));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(105));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(108));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(109));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(110));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(111));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(112));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(113));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(114));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(115));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(116));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(117));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(118));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(119));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(119));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 15,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(120));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 16,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(121));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 17,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(122));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 18,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(123));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 19,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(124));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 20,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 542, DateTimeKind.Utc).AddTicks(125));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 541, DateTimeKind.Utc).AddTicks(9973));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 541, DateTimeKind.Utc).AddTicks(9980));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 31, 14, 9, 52, 541, DateTimeKind.Utc).AddTicks(9981));
        }
    }
}
