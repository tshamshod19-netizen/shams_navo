import sqlite3
import random
from datetime import datetime

class Database:
    def __init__(self, db_path="music_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER UNIQUE,
                    full_name TEXT,
                    joined_at TEXT
                )
            """)
            
            # Music table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS music (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_id TEXT,
                    downloads INTEGER DEFAULT 0,
                    added_at TEXT
                )
            """)
            
            conn.commit()
    
    # ==================== USERS ====================
    
    def add_user(self, user_id: int, full_name: str):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, full_name, joined_at)
                VALUES (?, ?, ?)
            """, (user_id, full_name, datetime.now().isoformat()))
            conn.commit()
    
    def get_users_count(self) -> int:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
    
    # ==================== MUSIC ====================
    
    def add_music(self, title: str, artist: str, file_path: str, file_id: str = None) -> int:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO music (title, artist, file_path, file_id, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (title, artist, file_path, file_id, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_music(self) -> list:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, artist, file_path, file_id, downloads
                FROM music ORDER BY added_at DESC
            """)
            rows = cursor.fetchall()
            return [
                {"id": r[0], "title": r[1], "artist": r[2],
                 "file_path": r[3], "file_id": r[4], "downloads": r[5]}
                for r in rows
            ]
    
    def search_music(self, query: str) -> list:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            like = f"%{query}%"
            cursor.execute("""
                SELECT id, title, artist, file_path, file_id, downloads
                FROM music
                WHERE title LIKE ? OR artist LIKE ?
                ORDER BY downloads DESC
            """, (like, like))
            rows = cursor.fetchall()
            return [
                {"id": r[0], "title": r[1], "artist": r[2],
                 "file_path": r[3], "file_id": r[4], "downloads": r[5]}
                for r in rows
            ]
    
    def get_music_by_id(self, song_id: int) -> dict:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, artist, file_path, file_id, downloads
                FROM music WHERE id = ?
            """, (song_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "title": row[1], "artist": row[2],
                        "file_path": row[3], "file_id": row[4], "downloads": row[5]}
            return None
    
    def get_random_music(self) -> dict:
        songs = self.get_all_music()
        if not songs:
            return None
        return random.choice(songs)
    
    def increment_downloads(self, song_id: int):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE music SET downloads = downloads + 1 WHERE id = ?
            """, (song_id,))
            conn.commit()
    
    def delete_music(self, song_id: int) -> bool:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM music WHERE id = ?", (song_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ==================== STATS ====================
    
    def get_stats(self) -> dict:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM music")
            songs = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(downloads) FROM music")
            result = cursor.fetchone()[0]
            downloads = result if result else 0
            
            return {"users": users, "songs": songs, "downloads": downloads}
