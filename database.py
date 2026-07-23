import sqlite3
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

# Try importing psycopg2-binary for Postgres support
IS_POSTGRES = False
if DATABASE_URL:
    try:
        import psycopg2
        import psycopg2.extras
        IS_POSTGRES = True
    except ImportError:
        pass

DB_PATH = os.path.join(os.path.dirname(__file__), "blue_heaven.db")

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        self.conn.commit()

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        # Convert SQLite ? placeholders to Postgres %s
        query = query.replace('?', '%s')
        
        # Adapt table creation statement if running postgres
        if "CREATE TABLE IF NOT EXISTS bookings" in query:
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        
        # Handle lastrowid emulation using RETURNING id
        if query.strip().upper().startswith("INSERT INTO"):
            query += " RETURNING id"
            self.cursor.execute(query, params or ())
            self.lastrowid = self.cursor.fetchone()[0]
        else:
            self.cursor.execute(query, params or ())
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def rowcount(self):
        return self.cursor.rowcount

def get_db():
    if IS_POSTGRES:
        # Convert postgres:// to postgresql:// if needed (Vercel uses postgres://)
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return PostgresConnectionWrapper(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                guests INTEGER NOT NULL,
                package TEXT NOT NULL,
                special_requests TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        if not IS_POSTGRES:
            conn.commit()

def check_date_conflict(check_in: str, check_out: str, exclude_id: int = None) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT COUNT(*) FROM bookings 
            WHERE status = 'confirmed' 
              AND check_in < ? 
              AND check_out > ?
        """
        params = [check_out, check_in]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
            
        cursor.execute(query, params)
        res = cursor.fetchone()
        # Handle dict vs tuple fetch return formats
        count = res[0] if isinstance(res, tuple) else (res.get('count') or list(res.values())[0])
        return count > 0

def create_booking(data: dict) -> dict:
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (
                first_name, last_name, email, phone, check_in, check_out, 
                guests, package, special_requests, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            data['first_name'],
            data['last_name'],
            data['email'],
            data['phone'],
            data['check_in'],
            data['check_out'],
            data['guests'],
            data['package'],
            data.get('special_requests', ''),
            created_at
        ))
        if not IS_POSTGRES:
            conn.commit()
        booking_id = cursor.lastrowid
        return get_booking_by_id(booking_id)

def get_booking_by_id(booking_id: int) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_bookings() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_confirmed_date_ranges() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, check_in, check_out FROM bookings WHERE status = 'confirmed'")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def update_booking_status(booking_id: int, new_status: str) -> dict:
    if new_status not in ('pending', 'confirmed', 'cancelled'):
        raise ValueError(f"Invalid status: {new_status}")
    
    if new_status == 'confirmed':
        booking = get_booking_by_id(booking_id)
        if booking and check_date_conflict(booking['check_in'], booking['check_out'], exclude_id=booking_id):
            raise ValueError("Cannot confirm: dates overlap with an already confirmed booking!")
            
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
        if not IS_POSTGRES:
            conn.commit()
        return get_booking_by_id(booking_id)

def delete_booking(booking_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        if not IS_POSTGRES:
            conn.commit()
        return cursor.rowcount > 0
