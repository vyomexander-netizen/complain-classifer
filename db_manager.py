import sqlite3

DB_MAP = {
    "archive": "master_archive.db",
    "complaints": "complaints_archive.db",

    "academics": "academics_data.db",
    "mess": "mess_data.db",
    "hostel": "hostel_data.db",

    "academics_summarized": "academics_summarized.db",
    "mess_summarized": "mess_summarized.db",
    "hostel_summarized": "hostel_summarized.db",

    "display_academics": "academics_summarized.db",
    "display_mess": "mess_summarized.db",
    "display_hostel": "hostel_summarized.db",
}


def store_in_db(category: str, text: str):
    db_file = DB_MAP.get(category.lower())

    if not db_file:
        raise ValueError(f"Category '{category}' does not exist in DB_MAP.")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            processed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("SELECT 1 FROM emails WHERE content = ?", (text,))

    if not cursor.fetchone():
        cursor.execute("INSERT INTO emails (content) VALUES (?)", (text,))
        conn.commit()
        status = "stored"
    else:
        status = "already_exists"

    conn.close()
    return status


def store_summary_in_db(category: str, summary: str, full_content: str):
    db_file = DB_MAP.get(category.lower())

    if not db_file:
        raise ValueError(f"Category '{category}' does not exist in DB_MAP.")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            full_content TEXT,
            processed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(emails)")
    columns = [row[1] for row in cursor.fetchall()]

    if "full_content" not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN full_content TEXT")

    cursor.execute("SELECT 1 FROM emails WHERE content = ?", (summary,))

    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO emails (content, full_content) VALUES (?, ?)",
            (summary, full_content),
        )
        conn.commit()
        status = "stored"
    else:
        status = "already_exists"

    conn.close()
    return status


def convert_record_to_dictionary(category: str):
    db_file = DB_MAP.get(category.lower())

    if not db_file:
        raise ValueError(f"Category '{category}' does not exist in DB_MAP.")

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            full_content TEXT,
            processed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(emails)")
    columns = [row[1] for row in cursor.fetchall()]

    if "full_content" not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN full_content TEXT")

    conn.commit()

    cursor.execute("SELECT * FROM emails ORDER BY id DESC")
    data = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return data
