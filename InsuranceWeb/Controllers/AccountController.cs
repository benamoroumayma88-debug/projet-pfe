using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using System.Security.Claims;
using InsuranceWeb.Data;
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

        [HttpGet]
        public IActionResult Login(string? returnUrl = null)
        {
            // If user is already authenticated, redirect to home
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
                    _logger.LogWarning($"Login attempt with non-existent user: {login}");
                    ModelState.AddModelError("", "Invalid login credentials.");
                    ViewData["ReturnUrl"] = returnUrl;
                    return View();
                }

                // Verify password
                if (!PasswordHasher.VerifyPassword(password, user.PasswordHash))
                {
                    _logger.LogWarning($"Failed password attempt for user: {login}");
                    ModelState.AddModelError("", "Invalid login credentials.");
                    ViewData["ReturnUrl"] = returnUrl;
                    return View();
                }

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
