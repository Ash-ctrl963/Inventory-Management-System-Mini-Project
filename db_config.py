# db_config.py
import mysql.connector
from mysql.connector import Error

# ─── EDIT THESE ──────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "Kb96goingfor@6",          # ← your MySQL password
    "database": "inventory_db",
    "port":     3306,
}
# ─────────────────────────────────────────────────────────────


def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise ConnectionError(f"MySQL connection failed: {e}")


def execute_query(query, params=None, fetch=False):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        if fetch == "all":
            return cur.fetchall()
        elif fetch == "one":
            return cur.fetchone()
        else:
            conn.commit()
            return cur.lastrowid
    except Error as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def test_connection():
    try:
        get_connection().close()
        return True
    except:
        return False
