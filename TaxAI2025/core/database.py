import sqlite3
import os
import datetime
import json

DB_FILE = "taxpilot_user_data.db"

class DatabaseManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema if not exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # User Profile Table (now storing Pydantic JSON directly by session_id)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            session_id TEXT PRIMARY KEY,
            profile_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Chat History Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Document Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT 0
        )
        """)

        conn.commit()
        conn.close()

    def add_message(self, session_id, role, message):
        conn = self._get_connection()
        conn.execute("INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)", 
                     (session_id, role, message))
        conn.commit()
        conn.close()

    def get_history(self, session_id):
        conn = self._get_connection()
        cursor = conn.execute("SELECT role, message FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def log_document(self, filename):
        conn = self._get_connection()
        conn.execute("INSERT INTO documents (filename, processed) VALUES (?, 1)", (filename,))
        conn.commit()
        conn.close()

    def save_user_profile(self, session_id, profile_dict):
        conn = self._get_connection()
        conn.execute("INSERT OR REPLACE INTO user_profile (session_id, profile_json) VALUES (?, ?)",
                     (session_id, json.dumps(profile_dict)))
        conn.commit()
        conn.close()

    def get_user_profile(self, session_id):
        conn = self._get_connection()
        cursor = conn.execute("SELECT profile_json FROM user_profile WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
        from TaxAI2025.core.schema import UserProfile
        return UserProfile().model_dump()
