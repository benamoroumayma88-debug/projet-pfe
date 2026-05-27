# Insurance Web Platform - RBAC Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                      │
│  User navigates to Insurance BI Platform                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ASP.NET Core 8.0 Web App                   │
│  InsuranceWeb Project                                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Controllers (Authorization Required)                │  │
│  │  ┌────────────────┐  ┌──────────────────────────┐   │  │
│  │  │ AccountCtrl    │  │ Dashboard Controllers    │   │  │
│  │  │ • Login        │  │ • HomeController         │   │  │
│  │  │ • Logout       │  │ • DelayPredictions       │   │  │
│  │  │ • Verify Creds │  │ • CostPredictions        │   │  │
│  │  │ • Hash Check   │  │ • Forecast               │   │  │
│  │  │ • Set Claims   │  │ • FraudPredictions       │   │  │
│  │  └────────────────┘  └──────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Middleware Pipeline                                 │  │
│  │  1. Authentication (Cookie scheme)                   │  │
│  │  2. Authorization (Role/ResourceAuthorize attributes)│  │
│  │  3. Claims validation                                │  │
│  │  4. Access check (Policy enforcement)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Access Layer                                   │  │
│  │  ┌─────────────────────┐  ┌────────────────────┐    │  │
│  │  │ AppDbContext        │  │ AuthDbContext      │    │  │
│  │  │ (InsuranceBI DB)    │  │ (InsurancePlatform)│    │  │
│  │  │ • Predictions       │  │ • Users            │    │  │
│  │  │ • Summaries         │  │ • Roles            │    │  │
│  │  │ • Forecasts         │  │ • Permissions      │    │  │
│  │  │ • Fraud data        │  │ • RolePermissions  │    │  │
│  │  └─────────────────────┘  └────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │              │
         ┌───────────────┘              └────────────────┐
         │                                               │
         ▼                                               ▼
┌───────────────────────────┐               ┌──────────────────────┐
│   SQL Server              │               │   SQL Server         │
│   InsuranceBI Database    │               │   InsurancePlatform  │
│                           │               │   Database           │
│ Tables:                   │               │                      │
│ • claim_delay_*           │               │ Tables:              │
│ • claim_cost_*            │               │ • users              │
│ • claim_fraud_*           │               │ • roles              │
│ • claim_forecast_*        │               │ • permissions        │
│                           │               │ • role_permissions   │
└───────────────────────────┘               └──────────────────────┘
```

## Authentication Flow

```
┌─────────────────┐
│ User navigates  │
│ to /Account/    │
│ Login           │
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │ Login Page │  (GET /Account/Login)
    │ Displayed  │  – No authentication required
    └────────┬───┘
             │
         User enters credentials
             │
             ▼
    ┌─────────────────┐
    │ Submit Form     │  (POST /Account/Login)
    │ login=xxx       │  – Form validation
    │ password=xxx    │
    └────────┬────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ Query Users by Login      │
    │ SELECT * FROM users       │  Include role & permissions
    │ WHERE login = @login      │  via Include(.Role).ThenInclude(...)
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ Verify Password           │
    │ PasswordHasher.Verify()   │  SHA256 compare
    │ password_hash match?      │
    └────────┬──────────────────┘
             │
         ┌───┴───┐
         │       │
    ✓ Match  ✗ No match
         │       │
         ▼       ▼
    Create    Show Error
    Claims    + Redirect
    Principal │ to Login
         │
         ▼
    ┌───────────────────────────┐
    │ Create Claims (7 total)   │
    │ • NameIdentifier: UserId  │
    │ • Name: Username          │
    │ • Email: Email            │
    │ • Role: RoleName          │
    │ • Permissions: CSV list   │
    │ • Login: Login string     │
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ Sign In User (Cookie)     │
    │ HttpContext.SignInAsync( │
    │   ClaimsIdentity,         │
    │   AuthProperties          │ Persistent? Remember Me
    │ )                         │ Expires: 24 hours
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ Set Authentication Cookie │
    │ • Name: .AspNetCore.Auth  │
    │ • Value: Encrypted claims │
    │ • HttpOnly: true          │
    │ • Secure: true (HTTPS)    │
    │ • SameSite: Strict        │
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ Check Return URL          │
    │ if Url.IsLocalUrl()       │
    │   Redirect to ReturnUrl   │
    │ else                      │
    │   Redirect to Home        │
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ User Logged In!           │
    │ Access Dashboard          │
    └───────────────────────────┘
```

## Authorization Flow (Per Request)

```
┌──────────────────────────┐
│ User Requests Page       │
│ GET /DelayPredictions/   │
│ Index                    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Extract Auth Cookies     │
│ Parse ClaimsIdentity     │
│ Build ClaimsPrincipal    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Check [Authorize] Attribute          │
│ DelayPredictionsController.cs:       │
│ [Authorize(Roles =                   │
│   "Manager,Analyst")]                │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Extract User.Claims:     │
│ • Find Role claim        │
│ • Check Roles list       │
└────────┬─────────────────┘
         │
      ┌──┴──┐
        │   │
    Found  Not Found
        │   │
        ▼   ▼
    ✓ Allow ✗ Deny
        │   │
        │   └──→ Redirect to
        │        /Account/
        │        AccessDenied
        │
        ▼
    Load Page
    (Home Dashboard)
```

## Role-Permission Architecture

```
User
  │
  └─→ Role (assigned via role_id FK)
       │
       ├─→ Manager
       │   │
       │   └─→ 13 Permissions
       │       • Dashboard: View ✓
       │       • Dashboard: Report ✓
       │       • DelayPredictions: View ✓
       │       • DelayPredictions: Modify ✓
       │       • CostPredictions: View ✓
       │       • CostPredictions: Modify ✓
       │       • FraudPredictions: View ✓
       │       • FraudPredictions: Modify ✓
       │       • FraudPredictions: Investigate ✓
       │       • Forecast: View ✓
       │       • Forecast: Modify ✓
       │       • Admin: ManageUsers ✓
       │       • Admin: ViewLogs ✓
       │
       ├─→ Analyst
       │   │
       │   └─→ 5 Permissions
       │       • Dashboard: View ✓
       │       • Dashboard: Report ✓
       │       • DelayPredictions: View ✓
       │       • CostPredictions: View ✓
       │       • Forecast: View ✓
       │
       └─→ Fraud Agent
           │
           └─→ 3 Permissions
               • FraudPredictions: View ✓
               • FraudPredictions: Modify ✓
               • FraudPredictions: Investigate ✓
```

## Data Model Relationships

```
users (1) ──FK──┐
                │
             (N) roles
                │
                ├──FK──┐
                │      │
        (N) role_permissions (N)
                │
                └──FK──→ permissions
```

### users Table
```
user_id (PK) ──────────┐
username (UNIQUE)      │
email (UNIQUE)         │  Links to roles
login (UNIQUE)         │  via role_id
password_hash          │
role_id (FK) ──────────┘
is_active
created_at, updated_at
```

### roles Table
```
role_id (PK)
role_name (UNIQUE) → {Manager, Analyst, Fraud Agent}
description
created_at
```

### permissions Table
```
permission_id (PK)
permission_name
resource → {Dashboard, DelayPredictions, CostPredictions, etc.}
action → {View, Modify, Investigate, Report, etc.}
description
created_at
```

### role_permissions Table (Junction)
```
role_permission_id (PK)
role_id (FK) ─────────→ roles
permission_id (FK) ───→ permissions
created_at
UNIQUE(role_id, permission_id)
```

## Security Layers

```
┌──────────────────────────────────────────────────┐
│ Layer 1: Client-Side Validation                 │
│ - HTML5 required fields                          │
│ - Client-side validation prompts                 │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 2: HTTPS Transport                         │
│ - Encrypted in transit                           │
│ - TLS 1.2+ required                              │
│ - Certificate validation                         │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 3: Server-Side Validation                  │
│ - ModelState validation                          │
│ - Login string length checks                     │
│ - Password format validation                     │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 4: CSRF Protection                         │
│ - [ValidateAntiForgeryToken] attribute           │
│ - Token verification on form submission          │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 5: Authentication                          │
│ - Database lookup by login                       │
│ - Password hash verification (SHA256)            │
│ - Claims creation with verified user data        │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 6: Cookie Security                         │
│ - HttpOnly: JavaScript cannot access             │
│ - Secure: HTTPS only transmission                │
│ - SameSite: Prevent CSRF attacks                 │
│ - Expires: Auto-logout after 24 hours            │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 7: Authorization                           │
│ - Role claims validation                         │
│ - [Authorize] attribute enforcement              │
│ - Controller-level access checks                 │
│ - Per-request verification                       │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│ Layer 8: Data Access                             │
│ - EF Core parameterized queries (anti-SQLi)      │
│ - Role-based data filtering                      │
│ - Audit logging (future)                         │
└──────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────┐
│      Production Environment         │
│                                    │
│ ┌──────────────────────────────┐  │
│ │   IIS / Azure App Service    │  │
│ │   ASP.NET Core 8.0 App       │  │
│ │   - HTTPS enforced           │  │
│ │   - Handler: Kestrel         │  │
│ │   - AutoStart: true          │  │
│ └──────────────────────────────┘  │
│            │          │            │
│    ┌───────┘          └───────┐   │
│    ▼                          ▼   │
│ ┌────────────────┐  ┌──────────────┐
│ │SQL Server 2019+│  │SQL Server    │
│ │InsuranceBI DB  │  │InsurancePForm│
│ │ • Predictions  │  │ • Users      │
│ │ • Forecasts    │  │ • Roles      │
│ │ • Analytics    │  │ • Permissions│
│ └────────────────┘  └──────────────┘
└────────────────────────────────────┘
         │                  │
         └──────┬───────────┘
                │
         ┌──────▼──────┐
         │  Backups    │
         │  & Logs     │
         └─────────────┘
```

## Key Implementation Details

### Authentication Cookies
- **Name**: `.AspNetCore.Authentication.Cookies`
- **Encryption**: DPAPI (Data Protection API)
- **Session Storage**: Server-side (can be customized)
- **Expiration**: 24 hours (configurable)
- **Flags**: HttpOnly, Secure, SameSite=Strict

### Claims in Cookie
The authentication cookie contains encrypted claims:
```csharp
new Claim(ClaimTypes.NameIdentifier, userId)
new Claim(ClaimTypes.Name, username)
new Claim(ClaimTypes.Email, email)
new Claim(ClaimTypes.Role, roleName)
new Claim("Permissions", "Dashboard:View,Dashboard:Report,...")
new Claim("Login", login)
new Claim("UserId", userId)
```

### Password Hashing
```csharp
// Hash: SHA256(UTF8(password))
byte[] bytes = Encoding.UTF8.GetBytes(password);
byte[] hash = SHA256.Create().ComputeHash(bytes);
string hashString = Convert.ToBase64String(hash);
// Result: 44-character Base64 string
```

### Role-Based Controller Protection
```csharp
[Authorize(Roles = "Manager,Analyst")]
public class DelayPredictionsController : Controller { }
```

This enforces that:
1. User must be authenticated
2. User's Role claim must match one of the specified roles
3. Otherwise, redirects to AccessDenied page

---

## Summary

The RBAC system provides **7 layers of security** with clear separation of concerns:
- **Authentication** layer handles login/password verification
- **Authorization** layer enforces role/permission rules  
- **Data Access** layer ensures secure database queries
- **Infrastructure** layer (HTTPS, cookies) protects in transit
- **Middleware** layer coordinates everything seamlessly

This creates a robust, enterprise-grade authentication and authorization system for your Insurance BI platform.
