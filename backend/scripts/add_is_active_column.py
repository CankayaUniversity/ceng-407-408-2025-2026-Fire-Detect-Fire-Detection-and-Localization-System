"""
One-off: add is_active column to users table if missing.
Run from backend dir: python -m scripts.add_is_active_column
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

settings = get_settings()
url = settings.database_url
if "sqlite" in url:
    # sqlite+aiosqlite:///./file.db -> ./file.db
    path = url.split("///")[-1].split("?")[0]
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    import sqlite3
    conn = sqlite3.connect(path)
    cur = conn.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]
    if "is_active" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
        conn.commit()
        print("Added is_active to users table.")
    else:
        print("is_active already exists.")
    conn.close()
else:
    print("Non-SQLite DB: add is_active column manually if needed (e.g. ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE);")
