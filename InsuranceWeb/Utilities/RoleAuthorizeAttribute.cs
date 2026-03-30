using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using InsuranceWeb.Data;

namespace InsuranceWeb.Utilities
{
    /// <summary>
    /// Custom authorization attribute for role-based access control
    /// </summary>
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class RoleAuthorizeAttribute : Attribute, IAsyncAuthorizationFilter
    {
        private readonly string[] _requiredRoles;

        public RoleAuthorizeAttribute(params string[] roles)
        {
            _requiredRoles = roles;
        }

        public async Task OnAuthorizationAsync(AuthorizationFilterContext context)
        {
            // Check if user is authenticated
            var userIdClaim = context.HttpContext.User.FindFirst("UserId");
            if (userIdClaim == null)
            {
                context.Result = new RedirectToActionResult("Login", "Account", new { returnUrl = context.HttpContext.Request.Path });
                return;
            }

            // If no specific roles required, user just needs to be authenticated
            if (_requiredRoles.Length == 0)
            {
                return;
            }

            // Check if user has required role
            var userRole = context.HttpContext.User.FindFirst("Role")?.Value;
            if (string.IsNullOrEmpty(userRole) || !_requiredRoles.Contains(userRole))
            {
                context.Result = new ForbidResult();
            }
        }
    }

    /// <summary>
    /// Custom authorization attribute for resource-based access control
    /// </summary>
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class ResourceAuthorizeAttribute : Attribute, IAsyncAuthorizationFilter
    {
        private readonly string _resource;
        private readonly string? _action;

        public ResourceAuthorizeAttribute(string resource, string? action = null)
        {
            _resource = resource;
            _action = action;
        }

        public async Task OnAuthorizationAsync(AuthorizationFilterContext context)
        {
            // Check if user is authenticated
            var userIdClaim = context.HttpContext.User.FindFirst("UserId");
            if (userIdClaim == null)
            {
                context.Result = new RedirectToActionResult("Login", "Account", new { returnUrl = context.HttpContext.Request.Path });
                return;
            }

            // Get user's permissions from claims
            var permissionsClaim = context.HttpContext.User.FindFirst("Permissions")?.Value;
            if (string.IsNullOrEmpty(permissionsClaim))
            {
                context.Result = new ForbidResult();
                return;
            }

            // Check if user has required permission
            var permissions = permissionsClaim.Split(',');
            var hasPermission = _action == null
                ? permissions.Any(p => p.StartsWith(_resource))
                : permissions.Any(p => p == $"{_resource}:{_action}");

            if (!hasPermission)
            {
                context.Result = new ForbidResult();
            }
        }
    }
}
