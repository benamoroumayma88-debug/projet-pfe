using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace InsuranceWeb.Migrations.Auth
{
    /// <inheritdoc />
    public partial class UpdateRolesAndPermissions : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 21);

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5013));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5018));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5021));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5023));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5025));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5029));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5031));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5032));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5034));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5037));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5039));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5041));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5042));

            migrationBuilder.InsertData(
                table: "permissions",
                columns: new[] { "permission_id", "action", "created_at", "description", "permission_name", "resource" },
                values: new object[] { 14, "Upload", new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5090), null, "Upload Data", "DataUpload" });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5141));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5145));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5147));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5149));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5150));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5153));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5155));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5156));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5158));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5160));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5161));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 12,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5163), 14 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 13,
                columns: new[] { "created_at", "permission_id", "role_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5164), 1, 2 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 14,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5165), 2 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 15,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5167), 3 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 16,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5168), 5 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 17,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5170), 7 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 18,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5173));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 19,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5174), 12 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 20,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5176), 13 });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 1,
                columns: new[] { "created_at", "description" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4885), "Full access to all features, data upload, and reporting" });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 2,
                columns: new[] { "created_at", "role_name" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4891), "Business Analyst" });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 3,
                columns: new[] { "created_at", "description", "role_name" },
                values: new object[] { new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4893), "User and account management, platform administration", "Admin" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 14);

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5725));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5734));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5738));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5741));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5744));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5752));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5814));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5818));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5821));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5826));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5829));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 12,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5832));

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5835));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5923));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5929));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5932));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 4,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5935));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 5,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5937));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 6,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5942));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 7,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5944));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 8,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5947));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 9,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5949));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 10,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5954));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 11,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5956));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 12,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5959), 12 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 13,
                columns: new[] { "created_at", "permission_id", "role_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5962), 13, 1 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 14,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5964), 1 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 15,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5967), 2 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 16,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5969), 3 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 17,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5971), 5 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 18,
                column: "created_at",
                value: new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5977));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 19,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5979), 7 });

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 20,
                columns: new[] { "created_at", "permission_id" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5982), 8 });

            migrationBuilder.InsertData(
                table: "role_permissions",
                columns: new[] { "role_permission_id", "created_at", "permission_id", "role_id" },
                values: new object[] { 21, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5984), 9, 3 });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 1,
                columns: new[] { "created_at", "description" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5509), "Full access to all features and reporting" });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 2,
                columns: new[] { "created_at", "role_name" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5517), "Analyst" });

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 3,
                columns: new[] { "created_at", "description", "role_name" },
                values: new object[] { new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5521), "Access to fraud detection and investigation tools", "Fraud Agent" });
        }
    }
}
