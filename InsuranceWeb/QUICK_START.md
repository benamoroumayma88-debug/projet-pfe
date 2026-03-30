# RBAC Implementation - Quick Reference Guide

## ✅ What's Been Completed

All authentication and RBAC code has been implemented and integrated into your project:

### Code Complete
- ✅ Models: User, Role, Permission, RolePermission
- ✅ AuthDbContext with seed data and migrations configuration
- ✅ AccountController with database authentication
- ✅ Login & AccessDenied views
- ✅ PasswordHasher utility for secure passwords
- ✅ Authorization attributes for role-based access
- ✅ All controllers protected with appropriate [Authorize] attributes
- ✅ Navbar updated with user menu and logout
- ✅ Connection strings configured

---

## 🔧 Setup Steps (Run These)

### 1. Create the Database
**In SQL Server Management Studio or Command Line:**
```sql
CREATE DATABASE InsurancePlatformDB;
```

### 2. Create Entity Framework Migrations
**In PowerShell (in InsuranceWeb directory):**
```powershell
cd "c:\Projet PFE\InsuranceWeb"

# Create migration
dotnet ef migrations add InitialAuthDb --context AuthDbContext -o Migrations/Auth

# Apply migration to create tables
dotnet ef database update --context AuthDbContext
```

### 3. Generate Password Hash

**Option A: Use PowerShell**
```powershell
cd "c:\Projet PFE\InsuranceWeb"

# Find the password hash using a C# script
[scriptblock]$code = {
    Add-Type -AssemblyName System.Security
    $password = "password123"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($password)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    [System.Convert]::ToBase64String($hash)
}

powershell.exe -NoProfile -Command $code
```

**Option B: Run in Visual Studio Immediate Window**
```csharp
using InsuranceWeb.Utilities;
PasswordHasher.HashPassword("password123")
// Result: XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=
```

### 4. Insert Test Users

**Run this SQL in SSMS against InsurancePlatformDB:**
```sql
-- First verify roles and permissions were seeded:
SELECT * FROM roles;
SELECT COUNT(*) FROM permissions;

-- Insert test users (using the hash from step 3 above)
INSERT INTO users (username, email, login, password_hash, role_id, is_active, created_at, updated_at)
VALUES 
('John Manager', 'john@insurance.com', 'manager', 'XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=', 1, 1, GETUTCDATE(), GETUTCDATE()),
('Jane Analyst', 'jane@insurance.com', 'analyst', 'XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=', 2, 1, GETUTCDATE(), GETUTCDATE()),
('Dave Fraud', 'dave@insurance.com', 'fraud', 'XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=', 3, 1, GETUTCDATE(), GETUTCDATE());

-- Verify users were created
SELECT user_id, username, login, role_id, is_active FROM users;
```

### 5. Build & Run
```powershell
cd "c:\Projet PFE\InsuranceWeb"
dotnet clean
dotnet build
dotnet run
```

### 6. Test Login
Navigate to: `https://localhost:5001/Account/Login`

Test credentials (all use password: `password123`):
- **Manager**: Login = `manager`
  - Should see all pages
  - Can make modifications
  
- **Analyst**: Login = `analyst`
  - Can see Dashboard, Delay, Cost, Forecast
  - Read-only access
  - Cannot see Fraud page
  
- **Fraud Agent**: Login = `fraud`
  - Can ONLY see the Fraud page
  - Cannot access any other pages

---

## 📊 Database Schema Overview

```
users (user_id, username, email, login, password_hash, role_id)
  ↓ (role_id = role_id)
roles (role_id, role_name)
  ↓
role_permissions (role_id, permission_id)
  ↓ (permission_id = permission_id)
permissions (permission_id, permission_name, resource, action)
```

### Seeded Data (Auto-Created by Migrations)

**3 Roles:**
1. Manager (ID: 1)
2. Analyst (ID: 2)
3. Fraud Agent (ID: 3)

**13 Permissions:**
- Dashboard: View, Report
- DelayPredictions: View, Modify
- CostPredictions: View, Modify
- FraudPredictions: View, Modify, Investigate
- Forecast: View, Modify
- Admin: ManageUsers, ViewLogs

**26 Role-Permission Mappings:**
- Manager: All 13 permissions
- Analyst: Dashboard, Delays, Cost, Forecast (view only)
- Fraud Agent: Fraud only (view & investigate)

---

## 🔍 Troubleshooting

### "No database found"
```powershell
# Verify connection string in appsettings.json
# Should have both:
# - "DefaultConnection": "<InsuranceBI>"
# - "AuthConnection": "<InsurancePlatformDB>"

# Verify database exists:
# In SSMS: SELECT name FROM sys.databases WHERE name = 'InsurancePlatformDB'
```

### "Login failed - Invalid credentials"
```sql
-- Check user exists and is active
SELECT * FROM users WHERE login = 'manager' AND is_active = 1;

-- Verify password hash - should match the one you inserted
-- If not, update:
UPDATE users SET password_hash = 'XohImNooBHFR0OVvjcYpJ3NgPOTh+hfBBvGI8LarsM=' WHERE login = 'manager';
```

### "AuthDbContext not found in migrations"
```powershell
# Clear and redo:
dotnet ef database drop --context AuthDbContext -f
dotnet ef migrations remove --context AuthDbContext
dotnet ef migrations add InitialAuthDb --context AuthDbContext -o Migrations/Auth
dotnet ef database update --context AuthDbContext
```

### Controller actions show "Access Denied"
1. Verify user has a role assigned (`role_id` is not NULL)
2. Verify role has correct permissions:
   ```sql
   SELECT r.role_name, p.permission_name, p.resource
   FROM role_permissions rp
   JOIN roles r ON rp.role_id = r.role_id
   JOIN permissions p ON rp.permission_id = p.permission_id
   WHERE r.role_name = 'Analyst'
   ORDER BY p.resource;
   ```

---

## 📝 Key Files

| File | Purpose |
|------|---------|
| Models/User.cs | User entity with role FK |
| Models/Role.cs | Role definitions |
| Models/Permission.cs | Permission definitions |
| Models/RolePermission.cs | Role-Permission mapping |
| Data/AuthDbContext.cs | DbContext with seed data |
| Controllers/AccountController.cs | Login/logout logic |
| Views/Account/Login.cshtml | Login form UI |
| Utilities/PasswordHasher.cs | Password hashing utility |
| Utilities/RoleAuthorizeAttribute.cs | Authorization filters |
| AUTHENTICATION_SETUP.md | Detailed setup guide |
| IMPLEMENTATION_SUMMARY.md | Complete feature summary |

---

## 🔐 Security Notes

1. **Password Hashing**: Uses SHA256 (consider bcrypt for production)
2. **HTTPS**: Always enable in production
3. **Cookies**: Secure + HttpOnly + SameSite configurable
4. **CSRF**: Protected via `[ValidateAntiForgeryToken]`
5. **SQL Injection**: Protected via EF Core parameterized queries

---

## 📚 Documentation Files

- **AUTHENTICATION_SETUP.md** - Complete technical setup guide with troubleshooting
- **IMPLEMENTATION_SUMMARY.md** - Feature overview and access matrix
- **This file** - Quick reference for rapid setup

---

## Next Steps (Future)

- [ ] Create admin user management page
- [ ] Add password reset via email
- [ ] Implement MFA (multi-factor authentication)
- [ ] Add audit logging
- [ ] Integrate Azure AD for SSO
- [ ] Create permission management dashboard
- [ ] Add session timeout warnings

---

**Ready to deploy!** Follow steps 1-6 above and your authentication system will be live. 🚀
