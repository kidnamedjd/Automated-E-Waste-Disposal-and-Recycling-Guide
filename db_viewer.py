"""
db_viewer.py  —  Streamlit DB Viewer for E-Waste Management System
===================================================================
A lightweight admin page for browsing, filtering, editing, and
exporting your ewaste.db — runs inside your existing Streamlit app.

HOW TO USE:
    streamlit run db_viewer.py           # standalone
    — OR —
    Add a link from main.py sidebar:
        st.page_link("db_viewer.py", label="🗄️ DB Viewer")
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH = Path("static/ewaste.db")

st.set_page_config(
    page_title="E-Waste DB Viewer",
    page_icon="🗄️",
    layout="wide",
)


# ── Connection ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn() -> sqlite3.Connection:
    """Shared, cached connection (invalidated on reset)."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame | str:
    """
    Execute SQL and return a DataFrame (SELECT) or a status string (DML).
    Returns an error string on failure.
    """
    try:
        conn = get_conn()
        if sql.strip().upper().startswith("SELECT"):
            return pd.read_sql_query(sql, conn, params=params)
        else:
            conn.execute(sql, params)
            conn.commit()
            return "ok"
    except Exception as e:
        return str(e)


def list_tables() -> list[str]:
    """Return all table names in the database."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def table_schema(table: str) -> pd.DataFrame:
    """Return PRAGMA table_info as a DataFrame."""
    conn = get_conn()
    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return pd.DataFrame(cols, columns=["cid", "name", "type", "not_null", "default", "pk"])


# ── Page ───────────────────────────────────────────────────────────────────────
st.title("🗄️ Database Viewer")
st.caption(f"Connected to: `{DB_PATH.resolve()}`")

if not DB_PATH.exists():
    st.error("Database not found. Run `streamlit run main.py` once to create it.")
    st.stop()

# File stats strip
stat = DB_PATH.stat()
c1, c2, c3 = st.columns(3)
c1.metric("File size",    f"{stat.st_size / 1024:.1f} KB")
c2.metric("Tables",       len(list_tables()))
c3.metric("Last modified", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"))

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_browse, tab_query, tab_export, tab_schema = st.tabs(
    ["📋 Browse", "⌨️ SQL Query", "📥 Export", "🔍 Schema"]
)


# ── Browse tab ────────────────────────────────────────────────────────────────
with tab_browse:
    tables = list_tables()
    if not tables:
        st.info("No tables found in the database.")
        st.stop()

    col_sel, col_search = st.columns([2, 3])
    with col_sel:
        table = st.selectbox("Table", tables)
    with col_search:
        search = st.text_input("Filter rows (searches all text columns)", placeholder="e.g. Samsung")

    # Load table
    df = run_query(f"SELECT * FROM '{table}'")
    if isinstance(df, str):
        st.error(df)
        st.stop()

    # Apply text filter across all string columns
    if search:
        mask = df.apply(
            lambda col: col.astype(str).str.contains(search, case=False, na=False)
        ).any(axis=1)
        df = df[mask]

    st.caption(f"{len(df)} row(s) shown")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Inline Delete ──────────────────────────────────────────────────────────
    with st.expander("🗑️ Delete a row"):
        if "id" in df.columns:
            del_id = st.number_input("Row ID to delete", min_value=1, step=1)
            if st.button("Delete row", type="primary"):
                result = run_query(f"DELETE FROM '{table}' WHERE id = ?", (int(del_id),))
                if result == "ok":
                    st.success(f"Deleted row id={del_id} from '{table}'.")
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error(result)
        else:
            st.info("Delete requires an 'id' column in this table.")

    # ── Inline Edit ───────────────────────────────────────────────────────────
    with st.expander("✏️ Edit a row (UPDATE by id)"):
        if "id" in df.columns:
            edit_id = st.number_input("Row ID to edit", min_value=1, step=1, key="edit_id")
            row_df  = run_query(f"SELECT * FROM '{table}' WHERE id = ?", (int(edit_id),))

            if not isinstance(row_df, str) and not row_df.empty:
                row    = row_df.iloc[0].to_dict()
                schema = table_schema(table)
                pk_col = schema.loc[schema["pk"] == 1, "name"].values

                updated = {}
                for col, val in row.items():
                    if col in pk_col:
                        st.text_input(col, value=str(val), disabled=True)
                    else:
                        updated[col] = st.text_input(col, value="" if val is None else str(val))

                if st.button("Save changes", type="primary"):
                    set_clause = ", ".join(f'"{c}" = ?' for c in updated)
                    values     = list(updated.values()) + [int(edit_id)]
                    result     = run_query(
                        f"UPDATE '{table}' SET {set_clause} WHERE id = ?", tuple(values)
                    )
                    if result == "ok":
                        st.success("Row updated.")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error(result)
            elif not isinstance(row_df, str):
                st.warning("No row found with that ID.")
        else:
            st.info("Edit requires an 'id' column in this table.")


# ── SQL Query tab ─────────────────────────────────────────────────────────────
with tab_query:
    st.markdown("Run any SQL — SELECT returns a table; INSERT/UPDATE/DELETE commits.")

    # Quick-pick templates
    quick = st.selectbox("Quick templates", [
        "— pick a template —",
        "SELECT * FROM products",
        "SELECT * FROM recycling_centers",
        "SELECT category, COUNT(*) AS total FROM products GROUP BY category",
        "SELECT hazard_level, COUNT(*) AS total FROM products GROUP BY hazard_level",
        "SELECT disposal_recommendation, COUNT(*) AS total FROM products GROUP BY disposal_recommendation",
        "UPDATE products SET hazard_level = 'Low' WHERE id = 1",
        "DELETE FROM products WHERE id = 999",
    ])

    default_sql = "" if quick.startswith("—") else quick
    sql_input   = st.text_area("SQL", value=default_sql, height=100,
                               placeholder="SELECT * FROM products WHERE hazard_level = 'High'")

    if st.button("Run", type="primary"):
        if sql_input.strip():
            result = run_query(sql_input)
            if isinstance(result, pd.DataFrame):
                st.caption(f"{len(result)} row(s)")
                st.dataframe(result, use_container_width=True, hide_index=True)
            elif result == "ok":
                st.success("Query executed successfully.")
                st.cache_resource.clear()
            else:
                st.error(f"SQL error: {result}")
        else:
            st.warning("Enter a SQL statement first.")


# ── Export tab ────────────────────────────────────────────────────────────────
with tab_export:
    tables    = list_tables()
    exp_table = st.selectbox("Table to export", tables, key="exp_table")
    exp_fmt   = st.radio("Format", ["CSV", "JSON"], horizontal=True)

    if st.button("Download", type="primary"):
        df = run_query(f"SELECT * FROM '{exp_table}'")
        if isinstance(df, str):
            st.error(df)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if exp_fmt == "CSV":
                st.download_button(
                    label=f"💾 Save {exp_table}.csv",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name=f"{exp_table}_{ts}.csv",
                    mime="text/csv",
                )
            else:
                st.download_button(
                    label=f"💾 Save {exp_table}.json",
                    data=json.dumps(df.to_dict(orient="records"), indent=2, ensure_ascii=False).encode("utf-8"),
                    file_name=f"{exp_table}_{ts}.json",
                    mime="application/json",
                )


# ── Schema tab ────────────────────────────────────────────────────────────────
with tab_schema:
    for tname in list_tables():
        st.subheader(tname)
        st.dataframe(table_schema(tname), use_container_width=True, hide_index=True)
        row_count = run_query(f"SELECT COUNT(*) AS total FROM '{tname}'")
        if isinstance(row_count, pd.DataFrame):
            st.caption(f"{row_count.iloc[0]['total']} rows in this table")
        st.divider()