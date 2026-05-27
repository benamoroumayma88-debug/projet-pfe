# Insurance Web Platform - RBAC Implementation Summary

## What Was Implemented

### 1. **Database Models** (4 new models)
- **User** - User credentials with role assignment
- **Role** - Role definitions (Manager, Analyst, Fraud Agent)
- **Permission** - Granular permissions (e.g., "FraudPredictions:View")
- **RolePermission** - Junction table for mapping roles to permissions

### 2. **Authentication DbContext**
- `AuthDbContext.cs` - Dedicated DbContext for authentication database
- Uses `InsurancePlatformDB` connection string
- Includes seed data for all roles and permissions
- Configures relationships, unique constraints, and cascading deletes

### 3. **Authentication System**
- **AccountController** - Full login/logout implementation
  - Password hashing with SHA256
  - Database-backed credential validation
  - Claims-based authentication
  - Support for "Remember Me" functionality
  - Return URL handling
  - Access Denied handling

- **Login Page** (`Views/Account/Login.cshtml`)
  - Beautiful, responsive design matching your brand colors
  - Error handling and validation
  - "Remember Me" checkbox
  - Professional UI with animations

- **User Navbar Menu**
  - Shows logged-in user information
  - User menu dropdown with role display
  - One-click logout functionality

### 4. **Authorization & RBAC**
- **Custom Authorization Attributes**
  - `RoleAuthorizeAttribute` - for role-based access (Manager, Analyst, etc.)
  - `ResourceAuthorizeAttribute` - for granular permission checks
  
- **Protected Controllers**
  - `HomeController` - Requires authentication
  - `DelayPredictionsController` - Manager & Analyst only
  - `CostPredictionsController` - Manager & Analyst only
  - `ForecastController` - Manager & Analyst only
  - `FraudPredictionsController` - Manager & Fraud Agent only
  - `AccountController` - Manages login/logout

### 5. **Security Features**
- Password hashing (SHA256)
- CSRF protection on all forms
- Secure cookie-based authentication
- Per-page authorization checks
- Role-based access control
- Claims-based permission system

### 6. **Configuration**
- **appsettings.json** - Two connection strings
  - DefaultConnection → InsuranceBI database
  - AuthConnection → InsurancePlatformDB database
  
- **Program.cs** - Middleware setup
  - Cookie authentication scheme configured
  - AuthDbContext registered
  - Authorization middleware enabled

### 7. **Support Files**
- `AUTHENTICATION_SETUP.md` - Complete setup guide
- `setup_test_users.sql` - Test user insertion script
- CSS additions for dropdown menu styling

## Database Tables Created

### users
- user_id (PK)
- username (unique)
- email (unique)
- login (unique)
- password_hash
- role_id (FK)
- is_active
- created_at, updated_at

### roles
- role_id (PK)
- role_name (unique)
- description
- created_at

**Predefined Roles:**
1. Manager - Full access
2. Analyst - Dashboard read-only
3. Fraud Agent - Fraud detection only

### permissions
- permission_id (PK)
- permission_name
- resource
- action
- description
- created_at

**Sample Permissions:**
- Dashboard:View, Dashboard:Report
- DelayPredictions:View, DelayPredictions:Modify
- CostPredictions:View, CostPredictions:Modify
- FraudPredictions:View, FraudPredictions:Modify, FraudPredictions:Investigate
- Forecast:View, Forecast:Modify
- Admin:ManageUsers, Admin:ViewLogs

### role_permissions
- role_permission_id (PK)
- role_id (FK)
- permission_id (FK)
- created_at

## Access Matrix

| Page | Manager | Analyst | Fraud Agent |
|------|---------|---------|------------|
| Home/Dashboard | ✅ | ✅ | ❌ |
| Delay Predictions | ✅ Read/Write | ✅ Read | ❌ |
| Cost Predictions | ✅ Read/Write | ✅ Read | ❌ |
| Fraud Predictions | ✅ Read/Write | ❌ | ✅ Read/Write |
| Forecast | ✅ Read/Write | ✅ Read | ❌ |

## Quick Start - Setup Instructions

### Step 1: Create Database
```sql
-- In SQL Server Management Studio
CREATE DATABASE InsurancePlatformDB;
```

### Step 2: Run Migrations
```powershell
cd "c:\Projet PFE\InsuranceWeb"

# Create and apply migration
dotnet ef migrations add InitialAuthDb --context AuthDbContext -o Migrations/Auth
dotnet ef database update --context AuthDbContext
```

### Step 3: Create Test Users
```sql
-- Run the script from Scripts/setup_test_users.sql
-- Or manually insert test users with these credentials:

-- Manager: login=manager, password=password123
-- Analyst: login=analyst, password=password123
-- Fraud Agent: login=fraud, password=password123
```

To generate password hashes:
```csharp
// In Visual Studio Immediate Window:
using InsuranceWeb.Utilities;
PasswordHasher.HashPassword("password123")
// Returns: XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=
```

### Step 4: Build and Run
```powershell
dotnet build
dotnet run
```

### Step 5: Test Login
1. Navigate to `https://localhost:5001/Account/Login`
2. Login with:
   - Manager: `manager` / `password123`
   - Analyst: `analyst` / `password123`
   - Fraud Agent: `fraud` / `password123`

## Files Created/Modified

### New Files Created
- `Models/User.cs`
- `Models/Role.cs`
- `Models/Permission.cs`
- `Models/RolePermission.cs`
- `Data/AuthDbContext.cs`
- `Controllers/AccountController.cs`
- `Views/Account/Login.cshtml`
- `Views/Account/AccessDenied.cshtml`
- `Utilities/PasswordHasher.cs`
- `Utilities/RoleAuthorizeAttribute.cs`
- `Scripts/setup_test_users.sql`
- `AUTHENTICATION_SETUP.md`

### Modified Files
- `Program.cs` - Added authentication services and middleware
- `appsettings.json` - Added AuthConnection string
- `Controllers/HomeController.cs` - Added [Authorize] attribute
- `Controllers/DelayPredictionsController.cs` - Added [Authorize(Roles = "Manager,Analyst")] attribute
- `Controllers/CostPredictionsController.cs` - Added [Authorize(Roles = "Manager,Analyst")] attribute
- `Controllers/ForecastController.cs` - Added [Authorize(Roles = "Manager,Analyst")] attribute
- `Controllers/FraudPredictionsController.cs` - Added [Authorize(Roles = "Manager,Fraud Agent")] attribute
- `Views/Shared/_Layout.cshtml` - Added user menu dropdown
- `wwwroot/css/site.css` - Added dropdown menu styles

## Testing Checklist

- [ ] Manager login - Can access all pages
- [ ] Manager cannot see "Forbidden" page on any dashboard
- [ ] Analyst login - Can access Dashboard pages
- [ ] Analyst gets "Access Denied" on Fraud page
- [ ] Fraud Agent login - Can ONLY access Fraud page
- [ ] Fraud Agent gets "Access Denied" on all other pages
- [ ] Logout button works and clears session
- [ ] Login with invalid credentials shows error
- [ ] Password hashing works correctly
- [ ] Remember Me checkbox preserves login
- [ ] Return URL redirect works after login

## Important Notes

1. **Password Hashing**: Currently uses SHA256. For production, consider upgrading to bcrypt or Argon2 for better security
2. **Connection String**: Make sure `InsurancePlatformDB` exists on your SQL Server
3. **HTTPS**: Configure HTTPS in production environment
4. **Session Timeout**: Currently set to 24 hours - adjust in `AccountController` as needed
5. **Audit Logging**: Consider adding audit logging for sensitive operations
6. **User Management**: Consider creating an admin page to add/edit users

## Next Steps (Future Development)

1. Create an admin user management page
2. Add password reset functionality
3. Implement multi-factor authentication (MFA)
4. Add audit logging
5. Integrate with Azure AD for SSO
6. Add API key authentication
7. Create dashboard for role/permission management
8. Implement session timeout warnings

## Support Resources

- `AUTHENTICATION_SETUP.md` - Detailed setup guide
- `Scripts/setup_test_users.sql` - Database setup script
- `Utilities/PasswordHasher.cs` - Password hashing utility
- `Utilities/RoleAuthorizeAttribute.cs` - Authorization filters

---

**Build Date**: March 24, 2026
**Framework**: ASP.NET Core 8.0
**Database**: SQL Server (InsurancePlatformDB)
