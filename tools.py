"""tools.py — Tool dispatch.

Register tools as plain functions, then call them by name.
"""
from __future__ import annotations
import math
import os
import sqlite3
import subprocess
from datetime import datetime
from logger import logger

SANDBOX = "/tmp/sandbox"
os.makedirs(SANDBOX, exist_ok=True)

# ---------- tool definitions ----------
def calc(expression: str) -> str:
    """Evaluate a math expression, e.g. '2 + 3 * 4'."""
    # Only allow safe math chars
    allowed = set("0123456789+-*/()._ sqrt")
    if not all(c in allowed for c in expression.replace(" ", "")):
        return "Error: unsafe expression"
    try:
        result = eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def get_time() -> str:
    """Return current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def web_search(query: str) -> str:
    """Placeholder web search (returns a hint in sandbox)."""
    return f"[sandbox] Web search not available. Query was: {query}"

def write_file(filename: str, content: str) -> str:
    """Write content to a file."""
    with open(filename, "w") as f:
        f.write(content)
    return f"Wrote content to {filename}"

    
def run_python(filename: str) -> str:
    """
    Execute a Python file inside the sandbox directory.

    Args:
        filename: Name of the Python file to run
    """
    path = _safe_path(filename)
    if not os.path.exists(path):
        return f"❌ Error: {path} does not exist. Did you write the file first?"
    try:
        result = subprocess.run(
            ["python3", path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=SANDBOX,
        )
        output = result.stdout or result.stderr or "(no output)"
    except subprocess.TimeoutExpired:
        output = "❌ Timeout: execution exceeded 15 seconds and was terminated."

    if len(output) > 2000:
        output = output[:2000] + "\n... (output truncated)"
    return output


# ── sqlite3 tool  ────────────────────────────────────────

_DB_PATH = "/tmp/sandbox/harness.db"



def run_sql(sql: str) -> str:
    """
    Execute a SQL statement against a local SQLite database and return the result.

    The database file lives at /tmp/sandbox/harness.db and is created automatically.
    Supports SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE, etc.
    Results are returned as a formatted text table.

    Args:
        sql: The SQL statement to execute (e.g. "SELECT * FROM users")
    """
    if not sql or not sql.strip():
        return "❌ Empty SQL statement."

    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)

        # Detect if this was a query (returns rows) or a write statement
        if cursor.description:
            rows = cursor.fetchall()
            if not rows:
                result = "✅ Query executed — no rows returned."
            else:
                headers = [desc[0] for desc in cursor.description]
                # Build a simple aligned table
                col_widths = [len(h) for h in headers]
                for row in rows:
                    for i, val in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(str(val)))
                # Header row
                lines = []
                header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
                sep = "-+-".join("-" * w for w in col_widths)
                lines.append(header_line)
                lines.append(sep)
                for row in rows:
                    vals = [str(v) if v is not None else "NULL" for v in row]
                    lines.append(" | ".join(v.ljust(col_widths[i]) for i, v in enumerate(vals)))
                result = f"✅ Query returned {len(rows)} row(s):\n" + "\n".join(lines)
        else:
            result = f"✅ SQL executed. ({cursor.rowcount} row(s) affected)"

        conn.commit()
        conn.close()
        return result

    except sqlite3.Error as e:
        return f"❌ SQL error: {e}"


# ---------- registry ----------
TOOL_REGISTRY: dict[str, dict] = {
    "calc":        {"fn": calc,        "desc": "Evaluate a math expression", "args": "expression"},
    "get_time":    {"fn": get_time,    "desc": "Get current date & time",     "args": ""},
    "web_search":  {"fn": web_search,  "desc": "Search the web (placeholder)", "args": "query"},
    "write_file":  {"fn": write_file,  "desc": "Write content to a file",     "args": "filename, content"},
    "run_python":  {"fn": run_python,  "desc": "Execute a Python file",        "args": "filename"},
    "run_sql":     {"fn": run_sql,     "desc": "Execute a SQL statement",     "args": "sql"},
}


def list_tool_descriptions() -> str:
    """Produce a readable list of tools for the prompt."""
    lines = []
    for name, info in TOOL_REGISTRY.items():
        args = f" (args: {info['args']})" if info["args"] else ""
        lines.append(f"  - {name}{args}: {info['desc']}")
    return "\n".join(lines)


def dispatch(tool_name: str, args: dict) -> str:
    """Call a registered tool by name. Returns the result string."""
    if tool_name not in TOOL_REGISTRY:
        return f"Error: unknown tool '{tool_name}'"
    fn = TOOL_REGISTRY[tool_name]["fn"]
    try:
        logger.info("Dispatching tool: %s(%s)", tool_name, args)
        result = fn(**args) if args else fn()
        logger.debug("Tool result: %s", result)
        return result
    except Exception as e:
        logger.error("Tool error: %s", e)
        return f"Error: {e}"
