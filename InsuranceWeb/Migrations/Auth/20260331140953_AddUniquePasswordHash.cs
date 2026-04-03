using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace InsuranceWeb.Migrations.Auth
{
    /// <inheritdoc />
    public partial class AddUniquePasswordHash : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<string>(
                name: "password_hash",
                table: "users",
                type: "nvarchar(450)",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "nvarchar(max)");

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

            migrationBuilder.CreateIndex(
                name: "IX_users_password_hash",
                table: "users",
                column: "password_hash",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_users_password_hash",
                table: "users");

            migrationBuilder.AlterColumn<string>(
                name: "password_hash",
                table: "users",
                type: "nvarchar(max)",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "nvarchar(450)");

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

            migrationBuilder.UpdateData(
                table: "permissions",
                keyColumn: "permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5090));

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
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5163));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 13,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5164));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 14,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5165));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 15,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5167));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 16,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5168));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 17,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5170));

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
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5174));

            migrationBuilder.UpdateData(
                table: "role_permissions",
                keyColumn: "role_permission_id",
                keyValue: 20,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(5176));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 1,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4885));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 2,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4891));

            migrationBuilder.UpdateData(
                table: "roles",
                keyColumn: "role_id",
                keyValue: 3,
                column: "created_at",
                value: new DateTime(2026, 3, 30, 14, 11, 9, 912, DateTimeKind.Utc).AddTicks(4893));
        }
    }
}
