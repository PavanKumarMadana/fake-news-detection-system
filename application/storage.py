import sqlite3
from pathlib import Path


class AppStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    blocked INTEGER DEFAULT 0,
                    email_verified INTEGER DEFAULT 1,
                    profile_picture TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reset_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    news_text TEXT NOT NULL,
                    source_url TEXT DEFAULT '',
                    label TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    fake_probability REAL NOT NULL,
                    real_probability REAL NOT NULL,
                    source_score INTEGER DEFAULT 0,
                    risk_level TEXT DEFAULT '',
                    processing_time_ms REAL DEFAULT 0,
                    model_used TEXT DEFAULT '',
                    explanation TEXT DEFAULT '',
                    saved INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    label TEXT NOT NULL,
                    sample_text TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 0,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._migrate(connection)

    def _migrate(self, connection):
        self._ensure_column(connection, "users", "role", "TEXT DEFAULT 'user'")
        self._ensure_column(connection, "users", "blocked", "INTEGER DEFAULT 0")
        self._ensure_column(connection, "users", "email_verified", "INTEGER DEFAULT 1")
        self._ensure_column(connection, "users", "profile_picture", "TEXT DEFAULT ''")
        self._ensure_column(connection, "predictions", "user_id", "INTEGER DEFAULT 0")
        self._ensure_column(connection, "predictions", "source_url", "TEXT DEFAULT ''")
        self._ensure_column(connection, "predictions", "source_score", "INTEGER DEFAULT 0")
        self._ensure_column(connection, "predictions", "risk_level", "TEXT DEFAULT ''")
        self._ensure_column(connection, "predictions", "processing_time_ms", "REAL DEFAULT 0")
        self._ensure_column(connection, "predictions", "model_used", "TEXT DEFAULT ''")
        self._ensure_column(connection, "predictions", "explanation", "TEXT DEFAULT ''")
        self._ensure_column(connection, "predictions", "saved", "INTEGER DEFAULT 0")

    def _ensure_column(self, connection, table, column, definition):
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_user(self, name, email, password_hash, role="user"):
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO users (name, email, password_hash, role, email_verified)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, email.lower(), password_hash, role, 1),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

    def update_user(self, user_id, name, email, profile_picture=""):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET name = ?, email = ?, profile_picture = COALESCE(NULLIF(?, ''), profile_picture)
                WHERE id = ?
                """,
                (name, email.lower(), profile_picture, user_id),
            )

    def update_password(self, user_id, password_hash):
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )

    def update_role(self, user_id, role):
        with self._connect() as connection:
            connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))

    def set_user_blocked(self, user_id, blocked):
        with self._connect() as connection:
            connection.execute("UPDATE users SET blocked = ? WHERE id = ?", (blocked, user_id))

    def find_user_by_email(self, email):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, name, email, password_hash, role, blocked,
                       email_verified, profile_picture, created_at
                FROM users
                WHERE email = ?
                """,
                (email.lower(),),
            ).fetchone()
            return dict(row) if row else None

    def find_user_by_id(self, user_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, name, email, role, blocked, email_verified,
                       profile_picture, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_users(self):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, name, email, role, blocked, email_verified,
                       profile_picture, created_at
                FROM users
                ORDER BY id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def create_session(self, token, user_id):
        with self._connect() as connection:
            connection.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))

    def delete_session(self, token):
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def user_for_session(self, token):
        if not token:
            return None
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT users.id, users.name, users.email, users.role, users.blocked,
                       users.email_verified, users.profile_picture
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
            return dict(row) if row else None

    def create_reset_token(self, token, user_id):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO reset_tokens (token, user_id) VALUES (?, ?)",
                (token, user_id),
            )

    def consume_reset_token(self, token):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT token, user_id, used FROM reset_tokens WHERE token = ?",
                (token,),
            ).fetchone()
            if not row or row["used"]:
                return None
            connection.execute("UPDATE reset_tokens SET used = 1 WHERE token = ?", (token,))
            return dict(row)

    def add_prediction(self, user_id, news_text, result, source_url=""):
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO predictions (
                    user_id, news_text, source_url, label, confidence,
                    fake_probability, real_probability, source_score, risk_level,
                    processing_time_ms, model_used, explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    news_text,
                    source_url,
                    result["label"],
                    result["confidence"],
                    result["fake_probability"],
                    result["real_probability"],
                    result.get("source_score", 0),
                    result.get("risk_level", ""),
                    result.get("processing_time_ms", 0),
                    result.get("model_used", ""),
                    "\n".join(result.get("signals", [])),
                ),
            )
            return cursor.lastrowid

    def recent_predictions(self, user_id, limit=20, saved_only=False):
        return self.search_predictions(user_id, limit=limit, saved_only=saved_only)

    def search_predictions(self, user_id, limit=10, offset=0, search="", label="", sort="desc", saved_only=False):
        sql = """
            SELECT id, news_text, source_url, label, confidence, fake_probability,
                   real_probability, source_score, risk_level, processing_time_ms,
                   model_used, explanation, saved, created_at
            FROM predictions
            WHERE user_id = ?
        """
        params = [user_id]
        if saved_only:
            sql += " AND saved = 1"
        if label in ("fake", "real"):
            sql += " AND label = ?"
            params.append(label)
        if search:
            sql += " AND (news_text LIKE ? OR source_url LIKE ? OR explanation LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        sql += " ORDER BY created_at " + ("ASC" if sort == "asc" else "DESC") + " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def count_predictions(self, user_id, search="", label="", saved_only=False):
        sql = "SELECT COUNT(*) AS count FROM predictions WHERE user_id = ?"
        params = [user_id]
        if saved_only:
            sql += " AND saved = 1"
        if label in ("fake", "real"):
            sql += " AND label = ?"
            params.append(label)
        if search:
            sql += " AND (news_text LIKE ? OR source_url LIKE ? OR explanation LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        with self._connect() as connection:
            return connection.execute(sql, params).fetchone()[0]

    def prediction_detail(self, user_id, prediction_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT predictions.*, users.name AS user_name, users.email AS user_email
                FROM predictions
                JOIN users ON users.id = predictions.user_id
                WHERE predictions.id = ? AND predictions.user_id = ?
                """,
                (prediction_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def admin_prediction_detail(self, prediction_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT predictions.*, users.name AS user_name, users.email AS user_email
                FROM predictions
                JOIN users ON users.id = predictions.user_id
                WHERE predictions.id = ?
                """,
                (prediction_id,),
            ).fetchone()
            return dict(row) if row else None

    def save_report(self, user_id, prediction_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE predictions SET saved = 1 WHERE id = ? AND user_id = ?",
                (prediction_id, user_id),
            )

    def delete_report(self, prediction_id):
        with self._connect() as connection:
            connection.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))

    def delete_user_report(self, user_id, prediction_id):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM predictions WHERE id = ? AND user_id = ?",
                (prediction_id, user_id),
            )
            return cursor.rowcount > 0

    def add_dataset_sample(self, title, label, sample_text):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO datasets (title, label, sample_text) VALUES (?, ?, ?)",
                (title, label, sample_text),
            )

    def list_dataset_samples(self):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM datasets ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    def analytics(self):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            counts = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM users) AS users,
                    (SELECT COUNT(*) FROM predictions) AS predictions,
                    (SELECT COUNT(*) FROM predictions WHERE label = 'fake') AS fake_count,
                    (SELECT COUNT(*) FROM predictions WHERE label = 'real') AS real_count,
                    (SELECT COUNT(*) FROM datasets) AS datasets
                """
            ).fetchone()
            recent = connection.execute(
                "SELECT label, confidence, source_score, created_at FROM predictions ORDER BY id DESC LIMIT 10"
            ).fetchall()
            return dict(counts), [dict(row) for row in recent]

    def user_dashboard_stats(self, user_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            stats = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN label = 'fake' THEN 1 ELSE 0 END) AS fake_count,
                    SUM(CASE WHEN label = 'real' THEN 1 ELSE 0 END) AS real_count,
                    ROUND(AVG(confidence), 1) AS accuracy,
                    MAX(created_at) AS last_verification
                FROM predictions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            monthly = connection.execute(
                """
                SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS total
                FROM predictions
                WHERE user_id = ?
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
                """,
                (user_id,),
            ).fetchall()
            return dict(stats), [dict(row) for row in monthly]

    def list_all_reports(self, limit=100):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT predictions.id, users.name, users.email, predictions.news_text,
                       predictions.label, predictions.confidence, predictions.created_at
                FROM predictions
                JOIN users ON users.id = predictions.user_id
                ORDER BY predictions.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def log_activity(self, user_id, action, details=""):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id or 0, action, details),
            )

    def list_activity_logs(self, limit=100):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT activity_logs.*, users.name, users.email
                FROM activity_logs
                LEFT JOIN users ON users.id = activity_logs.user_id
                ORDER BY activity_logs.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]


PredictionStore = AppStore
