import os
import sys

import mysql.connector
from rich.console import Console

console = Console()


def dbconfig():
    """Create a MySQL/MariaDB connection.

    Connection parameters are read from environment variables so that no
    credentials are ever hardcoded in the source tree:

        DB_HOST      (default: localhost)
        DB_PORT      (default: 3306)
        DB_USER      (default: root)
        DB_NAME      (optional; queries use the fully-qualified `pm.*` names)
        DB_PASSWORD  (REQUIRED - there is no default password)

    See `.env.example` for documentation of these variables. If DB_PASSWORD is
    not set we fail loudly rather than falling back to an insecure default.
    """
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ.get("DB_USER", "root")
    database = os.environ.get("DB_NAME")  # optional; may be None
    password = os.environ.get("DB_PASSWORD")

    # Never assume a default password. If it is missing, tell the user exactly
    # what to do instead of connecting with an empty/guessed secret.
    if password is None:
        console.print(
            "[red][!] DB_PASSWORD environment variable is not set.[/red]\n"
            "    Set your database credentials before running, e.g.:\n"
            "        export DB_PASSWORD='your-db-password'\n"
            "    See .env.example for all supported variables."
        )
        sys.exit(1)

    connect_kwargs = {
        "host": host,
        "port": port,
        "user": user,
        "passwd": password,
    }
    # Only pass a database if one was explicitly provided; the app otherwise
    # relies on the fully-qualified `pm.secret` / `pm.entries` table names.
    if database:
        connect_kwargs["database"] = database

    try:
        db = mysql.connector.connect(**connect_kwargs)
    except Exception:
        console.print_exception(show_locals=True)
        sys.exit(1)

    return db
