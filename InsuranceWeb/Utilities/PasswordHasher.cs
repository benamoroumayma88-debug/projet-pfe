using System.Security.Cryptography;
using System.Text;

namespace InsuranceWeb.Utilities
{
    public static class PasswordHasher
    {
        /// <summary>
        /// Hash a password using PBKDF2
        /// </summary>
        public static string HashPassword(string password)
        {
            using (var sha256 = SHA256.Create())
            {
                var hashedBuffer = sha256.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hashedBuffer);
            }
        }

        /// <summary>
        /// Verify a password against its hash
        /// </summary>
        public static bool VerifyPassword(string password, string hash)
        {
            var hashOfInput = HashPassword(password);
            return hashOfInput.Equals(hash);
        }
    }
}
