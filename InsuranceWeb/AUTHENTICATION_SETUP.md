# Insurance Web Platform - Authentication & RBAC Setup Guide

## Overview
This document explains the authentication and role-based access control (RBAC) system implementation for the Insurance Web Platform.

## Database Setup

### 1. Create the InsurancePlatformDB Database
The authentication system uses a separate database called `InsurancePlatformDB` to store user credentials, roles, and permissions.

### 2. Run Entity Framework Migrations

Execute the following commands to create the database tables:

```powershell
# Navigate to the InsuranceWeb project directory
cd "c:\Projet PFE\InsuranceWeb"

# Create migration for AuthDbContext
dotnet ef migrations add InitialAuthDb --context AuthDbContext -o Migrations/Auth

# Apply the migration to InsurancePlatformDB
dotnet ef database update --context AuthDbContext

# Verify the tables were created in InsurancePlatformDB
```

After running migrations, the following tables will be created in `InsurancePlatformDB`:
- **users** - User accounts with credentials
- **roles** - User roles (Manager, Analyst, Fraud Agent)
- **permissions** - System permissions
- **role_permissions** - Mapping between roles and permissions

## Database Schema

### users Table
```sql
CREATE TABLE users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(100) NOT NULL UNIQUE,
    email NVARCHAR(255) NOT NULL UNIQUE,
    login NVARCHAR(100) NOT NULL UNIQUE,
    password_hash NVARCHAR(MAX) NOT NULL,
    role_id INT FOREIGN KEY REFERENCES roles(role_id),
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL,
    updated_at DATETIME2 NOT NULL
);
```

### roles Table
Predefined roles:
- **Manager** - Full access to all features and can modify settings
- **Analyst** - Read-only access to dashboards and reports
- **Fraud Agent** - Access to fraud detection and investigation tools

### permissions Table
Permissions are defined as `Resource:Action` pairs:
- Dashboard:View
- Dashboard:Report
- DelayPredictions:View
- DelayPredictions:Modify
- CostPredictions:View
- CostPredictions:Modify
- FraudPredictions:View
- FraudPredictions:Modify
- FraudPredictions:Investigate
- Forecast:View
- Forecast:Modify
- Admin:ManageUsers
- Admin:ViewLogs

### role_permissions Table
Junction table that maps roles to their available permissions.

## Role Access Matrix

| Feature | Manager | Analyst | Fraud Agent |
|---------|---------|---------|-------------|
| Dashboard | ✓ View & Report | ✓ View & Report | ✗ |
| Delay Predictions | ✓ View & Modify | ✓ View Only | ✗ |
| Cost Predictions | ✓ View & Modify | ✓ View Only | ✗ |
| Fraud Predictions | ✓ View & Modify | ✗ | ✓ View & Modify |
| Forecast | ✓ View & Modify | ✓ View Only | ✗ |
| User Management | ✓ | ✗ | ✗ |

## Seeded Data

The `AuthDbContext.OnModelCreating()` method automatically seeds the following data:

### Default Roles (3 roles)
- Manager (ID: 1)
- Analyst (ID: 2)
- Fraud Agent (ID: 3)

### Default Permissions (13 permissions)
All CRUD permissions for each dashboard component

### Default Role Permissions
Automatic assignment of permissions to roles as per the access matrix above

## Creating Test Users

To create test users, you can use SQL or EF Core. Example SQL:

```sql
-- Manager User
INSERT INTO users (username, email, login, password_hash, role_id, is_active, created_at, updated_at)
VALUES ('John Manager', 'john@insurance.com', 'john_manager', 
        'hashed_password_here', 1, 1, GETUTCDATE(), GETUTCDATE());

-- Analyst User
INSERT INTO users (username, email, login, password_hash, role_id, is_active, created_at, updated_at)
VALUES ('Jane Analyst', 'jane@insurance.com', 'jane_analyst',
        'hashed_password_here', 2, 1, GETUTCDATE(), GETUTCDATE());

-- Fraud Agent User
INSERT INTO users (username, email, login, password_hash, role_id, is_active, created_at, updated_at)
VALUES ('Dave Fraud', 'dave@insurance.com', 'dave_fraud',
        'hashed_password_here', 3, 1, GETUTCDATE(), GETUTCDATE());
```

### Getting Password Hashes

Use the `PasswordHasher` utility to generate hashes:

```csharp
// In Visual Studio Immediate Window or a test method:
using InsuranceWeb.Utilities;
var hash = PasswordHasher.HashPassword("your_password_here");
// Copy the hash to your SQL insert statement
```

## Authentication Flow

1. User navigates to `/Account/Login`
2. Enters login credentials (username/password)
3. System verifies password against stored hash
4. System loads user's role and permissions
5. Creates authentication cookie with claims:
   - UserId
   - Username
   - Email
   - Role
   - Permissions (comma-separated list)
6. User is redirected to the requested page or home dashboard
7. Session expires after 24 hours (configurable in `AccountController`)

## Authorization in Controllers

### By Role
```csharp
[Authorize(Roles = "Manager,Analyst")]
public class DashboardController : Controller { }
```

### By Resource Permission
```csharp
[ResourceAuthorize("FraudPredictions", "Modify")]
public IActionResult ModifySettings() { }
```

### General Authentication Required
```csharp
[Authorize]
public class HomeController : Controller { }
```

## Access Denied Handling

When a user tries to access a resource they don't have permission for:
1. System returns HTTP 403 Forbidden
2. User is redirected to `/Account/AccessDenied`
3. AccessDenied view displays with instructions

## Logout

Users can logout via:
- View: Click logout button in navigation (if implemented)
- Direct URL: POST to `/Account/Logout`
- Automatic: Session expires after 24 hours

## Connection Strings

Two separate connection strings are configured:

**appsettings.json:**
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=InsuranceBI;Trusted_Connection=True;TrustServerCertificate=True;",
    "AuthConnection": "Server=localhost;Database=InsurancePlatformDB;Trusted_Connection=True;TrustServerCertificate=True;"
  }
}
```

- **DefaultConnection**: Connects to `InsuranceBI` (predictions and dashboards)
- **AuthConnection**: Connects to `InsurancePlatformDB` (users, roles, permissions)

## Security Considerations

1. **Password Hashing**: Uses SHA256 hashing (consider upgrading to bcrypt or Argon2 for production)
2. **HTTPS Required**: Configure HTTPS in production
3. **Cookie Security**: Set `SameSite=Strict` and `Secure=true` in production
4. **CSRF Protection**: `[ValidateAntiForgeryToken]` on all POST actions
5. **SQL Injection**: Protected via Entity Framework Core parameterized queries
6. **XSS Protection**: Razor views HTML-encode by default

## Future Enhancements

1. ✓ Multi-factor authentication (MFA)
2. ✓ OAuth/OIDC integration with Azure AD
3. ✓ Password reset via email
4. ✓ Audit logging for admin/sensitive actions
5. ✓ Session management and force logout
6. ✓ API key authentication for programmatic access
7. ✓ Dynamic permission assignment
8. ✓ User registration workflow

## Troubleshooting

### Login Page Shows "Invalid login credentials"
- Verify user exists in database with `IsActive = 1`
- Check password hash matches what's in database
- Verify connection string in appsettings.json

### Access Denied on all pages after login
- Verify user has a role assigned (`RoleId` not null)
- Verify role has required permissions
- Check browser developer tools for cookie presence

### AuthDbContext not found
- Ensure `AuthDbContext.cs` is in `Data` folder
- Verify `Program.cs` registers both DbContexts
- Check project compiles without errors

### Migrations not applying
```powershell
# List pending migrations
dotnet ef migrations list --context AuthDbContext

# Check database for _EFMigrationsHistory table
SELECT * FROM __EFMigrationsHistory;
```

## Testing the Implementation

1. **Test Manager Access**: 
   - Login with manager account
   - Should see all pages
   
2. **Test Analyst Access**:
   - Login with analyst account
   - Should see Dashboard, Delay, Cost, Forecast
   - Should NOT see Fraud page
   
3. **Test Fraud Agent Access**:
   - Login with fraud agent account
   - Should only see Fraud page
   - Should get Access Denied on other pages

4. **Test Logout**:
   - Click logout
   - Should redirect to login page
   - Browser cookie should be cleared
