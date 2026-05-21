# config/db_config.py

SERVER = "(localdb)\MSSQLLocalDB"
DATABASE = "InsuranceBI"
DRIVER = "ODBC Driver 17 for SQL Server"

#Windows Auth usage:
TRUSTED_CONNECTION = True

#SQL Login instead, set TRUSTED_CONNECTION=False and fill these:
USERNAME = ""
PASSWORD = ""
