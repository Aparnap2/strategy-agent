import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Database file path
DB_PATH = Path("history.db")

def init_db():
    """Initialize the database with required tables."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Create requests table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY,
            user_input TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            result TEXT
        )
        ''')
        
        conn.commit()

def save_request(request_id: str, user_input: str, status: str = 'pending', result: Optional[Dict] = None):
    """Save or update a request in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if request exists
        cursor.execute('SELECT 1 FROM requests WHERE id = ?', (request_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing request
            if result is not None:
                cursor.execute(
                    'UPDATE requests SET status = ?, completed_at = ?, result = ? WHERE id = ?',
                    (status, datetime.utcnow().isoformat(), str(result) if result else None, request_id)
                )
            else:
                cursor.execute(
                    'UPDATE requests SET status = ? WHERE id = ?',
                    (status, request_id)
                )
        else:
            # Insert new request
            cursor.execute(
                'INSERT INTO requests (id, user_input, status, result) VALUES (?, ?, ?, ?)',
                (request_id, user_input, status, str(result) if result else None)
            )
        
        conn.commit()

def get_requests(limit: int = 10) -> List[Dict[str, Any]]:
    """Get a list of recent requests."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_input, status, created_at, completed_at 
            FROM requests 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]

def get_request(request_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific request by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        
        return dict(row) if row else None

# Initialize the database when this module is imported
init_db()
