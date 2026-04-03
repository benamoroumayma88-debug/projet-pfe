using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using System.Security.Claims;
using InsuranceWeb.Data;
using InsuranceWeb.Models;
using InsuranceWeb.Utilities;
using Microsoft.EntityFrameworkCore;

namespace InsuranceWeb.Controllers
{
    public class AccountController : Controller
    {
        private readonly AuthDbContext _authContext;
        private readonly ILogger<AccountController> _logger;

        public AccountController(AuthDbContext authContext, ILogger<AccountController> logger)
        {
            _authContext = authContext;
            _logger = logger;
        }

        private string GetClientIp()
        {
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
            // Normalize IPv6 loopback
            if (ip == "::1") ip = "127.0.0.1";
            return ip;
        }

        [HttpGet]
        public IActionResult Login(string? returnUrl = null)
        {
            if (User.Identity?.IsAuthenticated == true)
            {
                return RedirectToAction("Index", "Home");
            }

            ViewData["ReturnUrl"] = returnUrl;
            return View();
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Login(string login, string password, bool rememberMe = false, string? returnUrl = null)
        {
            if (!ModelState.IsValid)
            {
                ModelState.AddModelError("", "Please enter your credentials.");
                ViewData["ReturnUrl"] = returnUrl;
                return View();
            }

            var clientIp = GetClientIp();

            try
            {
                // Find user by login
                var user = await _authContext.Users
                    .Include(u => u.Role)
                    .ThenInclude(r => r!.Permissions)
                    .ThenInclude(rp => rp.Permission)
                    .FirstOrDefaultAsync(u => u.Login == login && u.IsActive);

                if (user == null)
                {
                    _logger.LogWarning("Login attempt with non-existent user: {Login}", login);

                    // Log failed attempt for unknown user
                    _authContext.AuditLogs.Add(new AuditLog
                    {
                        LoginAttempted = login,
                        EventType = "LOGIN_FAILED",
                        IpAddress = clientIp,
                        Severity = "WARNING",
                        Message = $"Login attempt with unknown user '{login}'",
                        ConsecutiveFailures = 1,
                        CreatedAt = DateTime.UtcNow
                    });
                    await _authContext.SaveChangesAsync();

                    ModelState.AddModelError("", "Invalid login credentials.");
                    ViewData["ReturnUrl"] = returnUrl;
                    return View();
                }

                // Verify password
                if (!PasswordHasher.VerifyPassword(password, user.PasswordHash))
                {
                    _logger.LogWarning("Failed password attempt for user: {Login}", login);

                    // Count recent consecutive failures for this user
                    var recentFailures = await _authContext.AuditLogs
                        .Where(a => a.UserId == user.UserId && a.EventType == "LOGIN_FAILED")
                        .OrderByDescending(a => a.CreatedAt)
                        .Take(10)
                        .ToListAsync();

                    // Count consecutive failures (until last success)
                    var lastSuccess = await _authContext.AuditLogs
                        .Where(a => a.UserId == user.UserId && a.EventType == "LOGIN_SUCCESS")
                        .OrderByDescending(a => a.CreatedAt)
                        .FirstOrDefaultAsync();

                    var consecutiveCount = lastSuccess != null
                        ? recentFailures.Count(f => f.CreatedAt > lastSuccess.CreatedAt) + 1
                        : recentFailures.Count + 1;

                    var severity = consecutiveCount >= 3 ? "ERROR" : "WARNING";
                    var message = consecutiveCount >= 3
                        ? $"User '{login}' failed login {consecutiveCount} times in a row — possible brute force"
                        : $"Failed password attempt for user '{login}'";

                    var auditEntry = new AuditLog
                    {
                        UserId = user.UserId,
                        LoginAttempted = login,
                        EventType = "LOGIN_FAILED",
                        IpAddress = clientIp,
                        Severity = severity,
                        Message = message,
                        ConsecutiveFailures = consecutiveCount,
                        CreatedAt = DateTime.UtcNow
                    };
                    _authContext.AuditLogs.Add(auditEntry);

                    // If 3+ failures, also create an ACCOUNT_LOCKED alert
                    if (consecutiveCount == 3)
                    {
                        _authContext.AuditLogs.Add(new AuditLog
                        {
                            UserId = user.UserId,
                            LoginAttempted = login,
                            EventType = "ACCOUNT_LOCKED",
                            IpAddress = clientIp,
                            Severity = "ERROR",
                            Message = $"Account '{login}' flagged: {consecutiveCount} consecutive failed login attempts. Password reset recommended.",
                            ConsecutiveFailures = consecutiveCount,
                            CreatedAt = DateTime.UtcNow
                        });
                    }

                    await _authContext.SaveChangesAsync();

                    ModelState.AddModelError("", "Invalid login credentials.");
                    ViewData["ReturnUrl"] = returnUrl;
                    return View();
                }

                // --- Login successful ---

                // Check for IP change
                var lastSuccessLogin = await _authContext.AuditLogs
                    .Where(a => a.UserId == user.UserId && a.EventType == "LOGIN_SUCCESS")
                    .OrderByDescending(a => a.CreatedAt)
                    .FirstOrDefaultAsync();

                if (lastSuccessLogin != null && lastSuccessLogin.IpAddress != clientIp)
                {
                    _authContext.AuditLogs.Add(new AuditLog
                    {
                        UserId = user.UserId,
                        LoginAttempted = login,
                        EventType = "IP_CHANGE",
                        IpAddress = clientIp,
                        PreviousIp = lastSuccessLogin.IpAddress,
                        Severity = "WARNING",
                        Message = $"User '{login}' logged in from new IP {clientIp} (previous: {lastSuccessLogin.IpAddress})",
                        CreatedAt = DateTime.UtcNow
                    });
                }

                // Log successful login
                _authContext.AuditLogs.Add(new AuditLog
                {
                    UserId = user.UserId,
                    LoginAttempted = login,
                    EventType = "LOGIN_SUCCESS",
                    IpAddress = clientIp,
                    Severity = "INFO",
                    Message = $"User '{login}' logged in successfully",
                    CreatedAt = DateTime.UtcNow
                });
                await _authContext.SaveChangesAsync();

                // Create claims for the authenticated user
                var claims = new List<Claim>
                {
                    new Claim(ClaimTypes.NameIdentifier, user.UserId.ToString()),
                    new Claim("UserId", user.UserId.ToString()),
                    new Claim(ClaimTypes.Name, user.Username),
                    new Claim(ClaimTypes.Email, user.Email),
                    new Claim("Login", user.Login)
                };

                // Add role claim if user has a role
                if (user.Role != null)
                {
                    claims.Add(new Claim(ClaimTypes.Role, user.Role.RoleName));
                    claims.Add(new Claim("Role", user.Role.RoleName));

                    // Add permission claims
                    if (user.Role.Permissions?.Count > 0)
                    {
                        var permissions = string.Join(",", user.Role.Permissions
                            .Where(rp => rp.Permission != null)
                            .Select(rp => $"{rp.Permission!.Resource}:{rp.Permission.Action}"));
                        
                        claims.Add(new Claim("Permissions", permissions));
                    }
                }

                // Create principal and sign in
                var claimsIdentity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
                var authProperties = new AuthenticationProperties
                {
                    IsPersistent = rememberMe,
                    ExpiresUtc = DateTimeOffset.UtcNow.AddHours(24)
                };

                await HttpContext.SignInAsync(
                    CookieAuthenticationDefaults.AuthenticationScheme,
                    new ClaimsPrincipal(claimsIdentity),
                    authProperties);

                _logger.LogInformation($"User logged in successfully: {login}");

                // Redirect to return URL or role-appropriate page
                if (!string.IsNullOrEmpty(returnUrl) && Url.IsLocalUrl(returnUrl))
                {
                    return Redirect(returnUrl);
                }

                // Admin goes to Admin dashboard, others go to Home
                if (user.Role?.RoleName == "Admin")
                {
                    return RedirectToAction("Index", "Admin");
                }

                return RedirectToAction("Index", "Home");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during login");
                ModelState.AddModelError("", "An error occurred during login. Please try again.");
                ViewData["ReturnUrl"] = returnUrl;
                return View();
            }
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Logout()
        {
            var login = User.FindFirst("Login")?.Value ?? "Unknown";
            _logger.LogInformation($"User logged out: {login}");
            
            await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            return RedirectToAction("Login", "Account");
        }

        public IActionResult AccessDenied()
        {
            return View();
        }
    }
}
