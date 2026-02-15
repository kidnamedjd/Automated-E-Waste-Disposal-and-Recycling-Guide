"""
db_manager.py  —  CLI Database Tool for E-Waste Management System
==================================================================
Drop this file into your ewaste_streamlit/ root folder.
Run from terminal to view, edit, export, and reset ewaste.db.

COMMANDS:
    python db_manager.py info                         # File stats + row counts
    python db_manager.py tables                       # Schema for all tables
    python db_manager.py show <table>                 # Print all rows
    python db_manager.py query "<SQL>"                # Run any SQL statement
    python db_manager.py export <table> <csv|json>    # Export to file
    python db_manager.py delete <table> <id>          # Delete row by id
    python db_manager.py backup                       # Timestamped DB copy
    python db_manager.py reset                        # Wipe + re-seed DB

EXAMPLES:
    python db_manager.py show products
    python db_manager.py show recycling_centers
    python db_manager.py query "SELECT * FROM products WHERE hazard_level='High'"
    python db_manager.py query "UPDATE products SET hazard_level='Low' WHERE id=2"
    python db_manager.py export products csv
    python db_manager.py export recycling_centers json
    python db_manager.py delete products 5
    python db_manager.py backup
"""

import sqlite3
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH    = Path("static/ewaste.db")
BACKUP_DIR = Path("static/backups")


# ── Connection ────────────────────────────────────────────────────────────────
def connect() -> sqlite3.Connection:
    """Return a dict-style DB connection; exit clearly if file is missing."""
    if not DB_PATH.exists():
        sys.exit(
            f"\n  [ERROR] Database not found at '{DB_PATH}'.\n"
            "          Run  streamlit run main.py  once to create it.\n"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # enables row["column"] access
    return conn


# ── Rendering ─────────────────────────────────────────────────────────────────
def print_table(rows: list, headers: list) -> None:
    """Print rows as a fixed-width ASCII table."""
    if not rows:
        print("  (no rows)\n")
        return

    # Column widths = max of header length vs. longest cell value
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len("NULL" if val is None else str(val)))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"

    print(sep)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        cells = ["NULL" if v is None else str(v) for v in row]
        print(fmt.format(*cells))
    print(sep)
    print(f"  {len(rows)} row(s)\n")


# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_info() -> None:
    """Show file path, size, last-modified date, and row count per table."""
    stat = DB_PATH.stat()
    print(f"\n  Path     : {DB_PATH.resolve()}")
    print(f"  Size     : {stat.st_size / 1024:.1f} KB")
    print(f"  Modified : {datetime.fromtimestamp(stat.st_mtime):%Y-%m-%d %H:%M:%S}\n")

    conn   = connect()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM '{t['name']}'").fetchone()[0]
        print(f"  {t['name']:<25} {count} row(s)")

    print()
    conn.close()


def cmd_tables() -> None:
    """Print the column schema for every table."""
    conn   = connect()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    for t in tables:
        name = t["name"]
        print(f"\n  ── {name} ──")
        cols = conn.execute(f"PRAGMA table_info('{name}')").fetchall()
        print_table(
            [tuple(c) for c in cols],
            ["cid", "name", "type", "not_null", "default", "pk"],
        )
    conn.close()


def cmd_show(table: str) -> None:
    """Print every row from the given table."""
    conn = connect()
    try:
        cur     = conn.execute(f"SELECT * FROM '{table}'")
        rows    = cur.fetchall()
        headers = [d[0] for d in cur.description]
        print(f"\n  ── {table} ({len(rows)} rows) ──")
        print_table([tuple(r) for r in rows], headers)
    except sqlite3.OperationalError as e:
        print(f"\n  [ERROR] {e}\n")
    conn.close()


def cmd_query(sql: str) -> None:
    """
    Run any SQL.
      SELECT  → results printed as a table.
      INSERT / UPDATE / DELETE → committed; reports affected row count.
    """
    conn = connect()
    try:
        cur = conn.execute(sql)
        if cur.description:                        # read query
            rows    = cur.fetchall()
            headers = [d[0] for d in cur.description]
            print()
            print_table([tuple(r) for r in rows], headers)
        else:                                       # write query
            conn.commit()
            print(f"\n  Done. Rows affected: {cur.rowcount}\n")
    except sqlite3.Error as e:
        print(f"\n  [ERROR] {e}\n")
    conn.close()


def cmd_export(table: str, fmt: str) -> None:
    """Export a table to CSV or JSON (saved in the current directory)."""
    conn = connect()
    try:
        cur     = conn.execute(f"SELECT * FROM '{table}'")
        rows    = cur.fetchall()
        headers = [d[0] for d in cur.description]
    except sqlite3.OperationalError as e:
        print(f"\n  [ERROR] {e}\n")
        conn.close()
        return

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table}_{ts}.{fmt}"

    if fmt == "csv":
        with open(filename, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([headers] + [tuple(r) for r in rows])

    elif fmt == "json":
        data = [dict(zip(headers, tuple(r))) for r in rows]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    else:
        print(f"\n  [ERROR] Unknown format '{fmt}'. Use 'csv' or 'json'.\n")
        conn.close()
        return

    print(f"\n  Exported {len(rows)} rows  →  {filename}\n")
    conn.close()


def cmd_delete(table: str, row_id: str) -> None:
    """Delete a row by its integer 'id' primary key."""
    conn = connect()
    try:
        cur = conn.execute(f"DELETE FROM '{table}' WHERE id = ?", (int(row_id),))
        conn.commit()
        msg = f"Deleted row id={row_id} from '{table}'." if cur.rowcount \
              else f"No row with id={row_id} found in '{table}'."
        print(f"\n  {msg}\n")
    except (sqlite3.Error, ValueError) as e:
        print(f"\n  [ERROR] {e}\n")
    conn.close()


def cmd_backup() -> None:
    """Copy ewaste.db to static/backups/ with a timestamp suffix."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"ewaste_backup_{ts}.db"
    shutil.copy2(DB_PATH, dest)
    print(f"\n  Backup saved  →  {dest}\n")


def cmd_reset() -> None:
    """Wipe the database and re-run initialize_database() from functions.py."""
    confirm = input("  This will DELETE all data and re-seed. Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("  Aborted.\n")
        return
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from functions import initialize_database          # your project's init
        DB_PATH.unlink(missing_ok=True)
        initialize_database()
        print(f"\n  Database reset and re-seeded at '{DB_PATH}'.\n")
    except ImportError:
        print(
            "\n  [ERROR] Could not import 'initialize_database' from functions.py.\n"
            "          Make sure db_manager.py is in the same folder.\n"
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    cmd = args[0].lower()

    match cmd:
        case "info":
            cmd_info()
        case "tables":
            cmd_tables()
        case "show"   if len(args) == 2:
            cmd_show(args[1])
        case "query"  if len(args) == 2:
            cmd_query(args[1])
        case "export" if len(args) == 3:
            cmd_export(args[1], args[2].lower())
        case "delete" if len(args) == 3:
            cmd_delete(args[1], args[2])
        case "backup":
            cmd_backup()
        case "reset":
            cmd_reset()
        case _:
            print(f"\n  [ERROR] Unrecognised command: {' '.join(args)}")
            print("  Run without arguments to see usage.\n")


if __name__ == "__main__":
    main()