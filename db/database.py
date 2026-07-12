import sqlite3
import os

from paths import app_root

DB_PATH = os.path.join(app_root(), "database.db")

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
