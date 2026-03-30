using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using InsuranceWeb.Data;
using InsuranceWeb.Models;
using InsuranceWeb.Utilities;

namespace InsuranceWeb.Controllers
{
    [Authorize(Roles = "Admin")]
    public class AdminController : Controller
    {
        private readonly AuthDbContext _authDb;
        private readonly ILogger<AdminController> _logger;

        public AdminController(AuthDbContext authDb, ILogger<AdminController> logger)
        {
            _authDb = authDb;
            _logger = logger;
        }

        // GET: Admin Dashboard
        public async Task<IActionResult> Index()
        {
            var users = await _authDb.Users
                .Include(u => u.Role)
                .OrderByDescending(u => u.CreatedAt)
                .AsNoTracking()
                .ToListAsync();

            var roles = await _authDb.Roles
                .Include(r => r.Permissions)
                .ThenInclude(rp => rp.Permission)
                .AsNoTracking()
                .ToListAsync();

            ViewBag.Roles = roles;
            ViewBag.TotalUsers = users.Count;
            ViewBag.ActiveUsers = users.Count(u => u.IsActive);
            ViewBag.InactiveUsers = users.Count(u => !u.IsActive);

            return View(users);
        }

        // GET: Create User form
        [HttpGet]
        public async Task<IActionResult> CreateUser()
        {
            ViewBag.Roles = await _authDb.Roles.OrderBy(r => r.RoleName).ToListAsync();
            return View();
        }

        // POST: Create User
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> CreateUser(string username, string email, string login, string password, int roleId)
        {
            ViewBag.Roles = await _authDb.Roles.OrderBy(r => r.RoleName).ToListAsync();

            if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(email) ||
                string.IsNullOrWhiteSpace(login) || string.IsNullOrWhiteSpace(password))
            {
                ViewBag.Error = "All fields are required.";
                return View();
            }

            // Check for duplicates
            var exists = await _authDb.Users.AnyAsync(u => u.Login == login || u.Email == email || u.Username == username);
            if (exists)
            {
                ViewBag.Error = "A user with this username, email, or login already exists.";
                return View();
            }

            var user = new User
            {
                Username = username,
                Email = email,
                Login = login,
                PasswordHash = PasswordHasher.HashPassword(password),
                RoleId = roleId,
                IsActive = true,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };

            _authDb.Users.Add(user);
            await _authDb.SaveChangesAsync();

            _logger.LogInformation("Admin {Admin} created user {User}",
                User.FindFirst("Login")?.Value, login);

            TempData["Success"] = $"User '{username}' created successfully.";
            return RedirectToAction("Index");
        }

        // GET: Edit User
        [HttpGet]
        public async Task<IActionResult> EditUser(int id)
        {
            var user = await _authDb.Users.Include(u => u.Role).FirstOrDefaultAsync(u => u.UserId == id);
            if (user == null) return NotFound();

            ViewBag.Roles = await _authDb.Roles.OrderBy(r => r.RoleName).ToListAsync();
            return View(user);
        }

        // POST: Edit User
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> EditUser(int id, string username, string email, string login, string? password, int roleId, bool isActive)
        {
            var user = await _authDb.Users.FirstOrDefaultAsync(u => u.UserId == id);
            if (user == null) return NotFound();

            ViewBag.Roles = await _authDb.Roles.OrderBy(r => r.RoleName).ToListAsync();

            if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(login))
            {
                ViewBag.Error = "Username, email, and login are required.";
                return View(user);
            }

            // Check duplicates (excluding current user)
            var duplicate = await _authDb.Users
                .AnyAsync(u => u.UserId != id && (u.Login == login || u.Email == email || u.Username == username));
            if (duplicate)
            {
                ViewBag.Error = "Another user already has this username, email, or login.";
                return View(user);
            }

            user.Username = username;
            user.Email = email;
            user.Login = login;
            user.RoleId = roleId;
            user.IsActive = isActive;
            user.UpdatedAt = DateTime.UtcNow;

            if (!string.IsNullOrWhiteSpace(password))
            {
                user.PasswordHash = PasswordHasher.HashPassword(password);
            }

            await _authDb.SaveChangesAsync();

            _logger.LogInformation("Admin {Admin} updated user {User}",
                User.FindFirst("Login")?.Value, login);

            TempData["Success"] = $"User '{username}' updated successfully.";
            return RedirectToAction("Index");
        }

        // POST: Toggle active status
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> ToggleActive(int id)
        {
            var user = await _authDb.Users.FirstOrDefaultAsync(u => u.UserId == id);
            if (user == null) return NotFound();

            user.IsActive = !user.IsActive;
            user.UpdatedAt = DateTime.UtcNow;
            await _authDb.SaveChangesAsync();

            _logger.LogInformation("Admin {Admin} {Action} user {User}",
                User.FindFirst("Login")?.Value,
                user.IsActive ? "activated" : "deactivated",
                user.Login);

            TempData["Success"] = $"User '{user.Username}' has been {(user.IsActive ? "activated" : "deactivated")}.";
            return RedirectToAction("Index");
        }

        // POST: Reset password
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> ResetPassword(int id, string newPassword)
        {
            var user = await _authDb.Users.FirstOrDefaultAsync(u => u.UserId == id);
            if (user == null) return NotFound();

            if (string.IsNullOrWhiteSpace(newPassword) || newPassword.Length < 6)
            {
                TempData["Error"] = "Password must be at least 6 characters.";
                return RedirectToAction("EditUser", new { id });
            }

            user.PasswordHash = PasswordHasher.HashPassword(newPassword);
            user.UpdatedAt = DateTime.UtcNow;
            await _authDb.SaveChangesAsync();

            _logger.LogInformation("Admin {Admin} reset password for user {User}",
                User.FindFirst("Login")?.Value, user.Login);

            TempData["Success"] = $"Password reset for '{user.Username}'.";
            return RedirectToAction("Index");
        }
    }
}
