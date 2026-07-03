import aiosqlite
import json

DB_NAME = "timetrack.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Settings table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                pomo_duration INTEGER DEFAULT 25,
                break_duration INTEGER DEFAULT 5
            )
        ''')
        # Stats table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                total_timers INTEGER DEFAULT 0,
                total_pomo_sessions INTEGER DEFAULT 0,
                total_focus_time INTEGER DEFAULT 0
            )
        ''')
        # Persistent active timers for premium recovery
        await db.execute('''
            CREATE TABLE IF NOT EXISTS active_timers (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                chat_id INTEGER,
                expiry REAL,
                label TEXT
            )
        ''')
        await db.commit()

async def get_settings(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT timezone, pomo_duration, break_duration FROM settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"timezone": row[0], "pomo_duration": row[1], "break_duration": row[2]}
            await db.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
            await db.commit()
            return {"timezone": "UTC", "pomo_duration": 25, "break_duration": 5}

async def increment_stat(user_id: int, column: str, amount: int = 1):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))
        await db.execute(f"UPDATE stats SET {column} = {column} + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT total_timers, total_pomo_sessions, total_focus_time FROM stats WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row if row else (0, 0, 0)

async def save_active_timer(timer_id: str, user_id: int, chat_id: int, expiry: float, label: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO active_timers VALUES (?, ?, ?, ?, ?)", (timer_id, user_id, chat_id, expiry, label))
        await db.commit()

async def remove_active_timer(timer_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM active_timers WHERE id = ?", (timer_id,))
        await db.commit()

