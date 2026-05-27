using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace InsuranceWeb.Migrations.Auth
{
    /// <inheritdoc />
    public partial class InitialAuthDb : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "permissions",
                columns: table => new
                {
                    permission_id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    permission_name = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    description = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    resource = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    action = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    created_at = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_permissions", x => x.permission_id);
                });

            migrationBuilder.CreateTable(
                name: "roles",
                columns: table => new
                {
                    role_id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    role_name = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    description = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    created_at = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_roles", x => x.role_id);
                });

            migrationBuilder.CreateTable(
                name: "role_permissions",
                columns: table => new
                {
                    role_permission_id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    role_id = table.Column<int>(type: "int", nullable: false),
                    permission_id = table.Column<int>(type: "int", nullable: false),
                    created_at = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_role_permissions", x => x.role_permission_id);
                    table.ForeignKey(
                        name: "FK_role_permissions_permissions_permission_id",
                        column: x => x.permission_id,
                        principalTable: "permissions",
                        principalColumn: "permission_id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_role_permissions_roles_role_id",
                        column: x => x.role_id,
                        principalTable: "roles",
                        principalColumn: "role_id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    user_id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    username = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    email = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    password_hash = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    login = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    role_id = table.Column<int>(type: "int", nullable: true),
                    is_active = table.Column<bool>(type: "bit", nullable: false),
                    created_at = table.Column<DateTime>(type: "datetime2", nullable: false),
                    updated_at = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.user_id);
                    table.ForeignKey(
                        name: "FK_users_roles_role_id",
                        column: x => x.role_id,
                        principalTable: "roles",
                        principalColumn: "role_id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.InsertData(
                table: "permissions",
                columns: new[] { "permission_id", "action", "created_at", "description", "permission_name", "resource" },
                values: new object[,]
                {
                    { 1, "View", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5725), null, "View Dashboard", "Dashboard" },
                    { 2, "Report", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5734), null, "Generate Reports", "Dashboard" },
                    { 3, "View", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5738), null, "View Delay Predictions", "DelayPredictions" },
                    { 4, "Modify", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5741), null, "Modify Delay Settings", "DelayPredictions" },
                    { 5, "View", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5744), null, "View Cost Predictions", "CostPredictions" },
                    { 6, "Modify", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5752), null, "Modify Cost Settings", "CostPredictions" },
                    { 7, "View", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5814), null, "View Fraud Predictions", "FraudPredictions" },
                    { 8, "Modify", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5818), null, "Modify Fraud Settings", "FraudPredictions" },
                    { 9, "Investigate", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5821), null, "Investigate Fraud", "FraudPredictions" },
                    { 10, "View", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5826), null, "View Forecast", "Forecast" },
                    { 11, "Modify", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5829), null, "Modify Forecast", "Forecast" },
                    { 12, "ManageUsers", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5832), null, "Manage Users", "Admin" },
                    { 13, "ViewLogs", new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5835), null, "View Audit Logs", "Admin" }
                });

            migrationBuilder.InsertData(
                table: "roles",
                columns: new[] { "role_id", "created_at", "description", "role_name" },
                values: new object[,]
                {
                    { 1, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5509), "Full access to all features and reporting", "Manager" },
                    { 2, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5517), "Read-only access to dashboards and reports", "Analyst" },
                    { 3, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5521), "Access to fraud detection and investigation tools", "Fraud Agent" }
                });

            migrationBuilder.InsertData(
                table: "role_permissions",
                columns: new[] { "role_permission_id", "created_at", "permission_id", "role_id" },
                values: new object[,]
                {
                    { 1, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5923), 1, 1 },
                    { 2, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5929), 2, 1 },
                    { 3, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5932), 3, 1 },
                    { 4, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5935), 4, 1 },
                    { 5, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5937), 5, 1 },
                    { 6, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5942), 6, 1 },
                    { 7, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5944), 7, 1 },
                    { 8, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5947), 8, 1 },
                    { 9, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5949), 9, 1 },
                    { 10, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5954), 10, 1 },
                    { 11, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5956), 11, 1 },
                    { 12, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5959), 12, 1 },
                    { 13, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5962), 13, 1 },
                    { 14, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5964), 1, 2 },
                    { 15, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5967), 2, 2 },
                    { 16, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5969), 3, 2 },
                    { 17, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5971), 5, 2 },
                    { 18, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5977), 10, 2 },
                    { 19, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5979), 7, 3 },
                    { 20, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5982), 8, 3 },
                    { 21, new DateTime(2026, 3, 27, 21, 30, 18, 564, DateTimeKind.Utc).AddTicks(5984), 9, 3 }
                });

            migrationBuilder.CreateIndex(
                name: "IX_permissions_permission_name",
                table: "permissions",
                column: "permission_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_role_permissions_permission_id",
                table: "role_permissions",
                column: "permission_id");

            migrationBuilder.CreateIndex(
                name: "IX_role_permissions_role_id_permission_id",
                table: "role_permissions",
                columns: new[] { "role_id", "permission_id" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_roles_role_name",
                table: "roles",
                column: "role_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_users_email",
                table: "users",
                column: "email",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_users_login",
                table: "users",
                column: "login",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_users_role_id",
                table: "users",
                column: "role_id");

            migrationBuilder.CreateIndex(
                name: "IX_users_username",
                table: "users",
                column: "username",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "role_permissions");

            migrationBuilder.DropTable(
                name: "users");

            migrationBuilder.DropTable(
                name: "permissions");

            migrationBuilder.DropTable(
                name: "roles");
        }
    }
}
