"""
Database module for PostgreSQL support.
Handles both SQLite (local dev) and PostgreSQL (production) connections.
"""

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

# PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection wrapper that supports both SQLite and PostgreSQL."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.db_path = os.getenv("DB_PATH", "food_diary.db")
        self.use_postgres = bool(self.db_url and POSTGRES_AVAILABLE)
        
        # In AWS Lambda, get database credentials from the environment
        if os.getenv("AWS_LAMBDA_RUNTIME") and self.use_postgres:
            self._setup_aws_database_connection()

    def _setup_aws_database_connection(self):
        """Set up database connection using AWS Secrets Manager."""
        try:
            import boto3
            import json
            
            # Get the secret name from RDS - it should be auto-generated
            secret_name = os.getenv("DB_SECRET_NAME")
            if not secret_name:
                logger.warning("DB_SECRET_NAME not found in environment")
                return
                
            # Get secret from AWS Secrets Manager
            session = boto3.Session()
            client = session.client('secretsmanager')
            
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response['SecretString'])
            
            # Build database URL with actual credentials
            host = secret['host']
            port = secret['port']
            username = secret['username']
            password = secret['password']
            dbname = secret['dbname']
            
            self.db_url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
            logger.info(f"Successfully configured database connection to {host}")
            
        except Exception as e:
            logger.error(f"Failed to setup AWS database connection: {e}")
            self.use_postgres = False

    def get_connection(self):
        """Get database connection based on environment."""
        if self.use_postgres:
            return psycopg2.connect(self.db_url)
        else:
            return sqlite3.connect(self.db_path)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts."""
        conn = self.get_connection()
        try:
            if self.use_postgres:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows or lastrowid."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if hasattr(cursor, "lastrowid") else cursor.rowcount
        finally:
            conn.close()


# Global database instance
db = DatabaseConnection()


def init_database():
    """Initialize the database with the users and entries tables."""
    conn = db.get_connection()
    try:
        cursor = conn.cursor()

        if db.use_postgres:
            # PostgreSQL table creation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    github_id INTEGER UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    timestamp TEXT NOT NULL,
                    event_datetime TEXT,
                    text TEXT,
                    photo TEXT,
                    synced BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite table creation (original)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    github_id INTEGER UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    avatar_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_datetime TEXT,
                    text TEXT,
                    photo TEXT,
                    synced BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Migration for existing SQLite databases
            cursor.execute("PRAGMA table_info(entries)")
            columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN user_id INTEGER")
                cursor.execute("UPDATE entries SET user_id = 1 WHERE user_id IS NULL")

            if "event_datetime" not in columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN event_datetime TEXT")
                cursor.execute(
                    "UPDATE entries SET event_datetime = timestamp WHERE event_datetime IS NULL"
                )

        conn.commit()
        logger.info(
            f"Database initialized successfully ({'PostgreSQL' if db.use_postgres else 'SQLite'})"
        )

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        conn.close()


def get_current_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    if not user_id:
        return None

    query = (
        """
        SELECT id, github_id, username, name, email, avatar_url 
        FROM users WHERE id = %s
    """
        if db.use_postgres
        else """
        SELECT id, github_id, username, name, email, avatar_url 
        FROM users WHERE id = ?
    """
    )

    results = db.execute_query(query, (user_id,))
    return results[0] if results else None


def create_or_update_user(github_user_data: Dict[str, Any]) -> int:
    """Create or update a user based on GitHub user data."""
    github_id = github_user_data["id"]

    # Check if user exists
    check_query = (
        "SELECT id FROM users WHERE github_id = %s"
        if db.use_postgres
        else "SELECT id FROM users WHERE github_id = ?"
    )
    existing_users = db.execute_query(check_query, (github_id,))

    if existing_users:
        # Update existing user
        user_id = existing_users[0]["id"]
        update_query = (
            """
            UPDATE users SET 
                username = %s, name = %s, email = %s, avatar_url = %s
            WHERE github_id = %s
        """
            if db.use_postgres
            else """
            UPDATE users SET 
                username = ?, name = ?, email = ?, avatar_url = ?
            WHERE github_id = ?
        """
        )
        db.execute_update(
            update_query,
            (
                github_user_data["login"],
                github_user_data.get("name"),
                github_user_data.get("email"),
                github_user_data.get("avatar_url"),
                github_id,
            ),
        )
    else:
        # Create new user
        insert_query = (
            """
            INSERT INTO users (github_id, username, name, email, avatar_url)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
            if db.use_postgres
            else """
            INSERT INTO users (github_id, username, name, email, avatar_url)
            VALUES (?, ?, ?, ?, ?)
        """
        )
        user_id = db.execute_update(
            insert_query,
            (
                github_id,
                github_user_data["login"],
                github_user_data.get("name"),
                github_user_data.get("email"),
                github_user_data.get("avatar_url"),
            ),
        )

    return user_id
