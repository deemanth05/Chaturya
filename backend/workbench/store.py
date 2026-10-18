import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "workbench.sqlite3"
        self.audit_lock = threading.Lock()
        root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('admin','inspector','reviewer')), created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
              workflow TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL,
              updated REAL NOT NULL, state TEXT NOT NULL DEFAULT '{}', error TEXT);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT REFERENCES jobs(id),
              actor TEXT, time REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_job_id ON events(job_id,id);
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT UNIQUE NOT NULL,
              synthetic INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks (
              id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
              page INTEGER NOT NULL, section TEXT NOT NULL, text TEXT NOT NULL,
              vector TEXT, embedding_model TEXT);
            CREATE TABLE IF NOT EXISTS reviews (
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES jobs(id),
              actor TEXT NOT NULL, note TEXT NOT NULL, time REAL NOT NULL);
            """)
            # Additive migrations preserve existing accounts, jobs and audit history.
            for table, columns in {
                "users": {"college_role": "TEXT", "active": "INTEGER NOT NULL DEFAULT 1"},
                "documents": {"owner_id": "TEXT", "audience": "TEXT NOT NULL DEFAULT 'private'",
                    "department": "TEXT NOT NULL DEFAULT ''", "course": "TEXT NOT NULL DEFAULT ''",
                    "status": "TEXT NOT NULL DEFAULT 'archived'", "version": "TEXT NOT NULL DEFAULT ''",
                    "language": "TEXT NOT NULL DEFAULT ''", "extraction": "TEXT NOT NULL DEFAULT 'text'", "source_path": "TEXT"},
            }.items():
                present = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for name, definition in columns.items():
                    if name not in present:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            db.execute("CREATE TABLE IF NOT EXISTS memberships (user_id TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL CHECK(kind IN ('department','course')), value TEXT NOT NULL, PRIMARY KEY(user_id,kind,value))")

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def rows(self, sql, args=()):
        with self.db() as db:
            return [dict(row) for row in db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def execute(self, sql, args=()):
        with self.db() as db:
            return db.execute(sql, args).rowcount

    def event(self, kind, payload, job_id=None, actor=None):
        now = time.time()
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        with self.db() as db:
            cursor = db.execute("INSERT INTO events(job_id,actor,time,kind,payload) VALUES(?,?,?,?,?)",
                                (job_id, actor, now, kind, encoded))
            event = dict(id=cursor.lastrowid, job_id=job_id, actor=actor, time=now, kind=kind, payload=payload)
        # SQLite is the authoritative durable audit store. JSONL is a mirror.
        with self.audit_lock:
            try:
                with (self.root / "audit.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError:
                import logging
                logging.getLogger(__name__).exception("Audit mirror write failed; event persisted in SQLite")
        return event

    def events(self, job_id=None, after=0, limit=300):
        where, args = ("job_id=? AND id>?", (job_id, after)) if job_id else ("id>?", (after,))
        result = self.rows(f"SELECT * FROM events WHERE {where} ORDER BY id LIMIT ?", (*args, limit))
        for event in result:
            event["payload"] = json.loads(event["payload"])
        return result

    def snapshot(self, job_id, state, status=None, error=None):
        with self.db() as db:
            db.execute("UPDATE jobs SET state=?, updated=?, status=COALESCE(?,status), error=? WHERE id=?",
                       (json.dumps(state, ensure_ascii=False, allow_nan=False), time.time(), status, error, job_id))

