import json
import sqlite3
from pathlib import Path

TABLES = {"projects", "teams", "providers", "agents", "sessions", "tasks", "messages", "events", "artifacts", "decisions"}


class Database:
    """Single-process PoC store. Named collections keep schema migration small."""
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        for table in TABLES:
            self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, data TEXT NOT NULL)")
            self.connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_project ON {table}(project_id)")
        self.connection.commit()

    def _table(self, table):
        if table not in TABLES:
            raise ValueError("unknown collection")
        return table

    def put(self, table, value):
        table = self._table(table)
        data = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
        self.connection.execute(f"INSERT INTO {table} VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id, data=excluded.data", (data["id"], data.get("project_id", ""), json.dumps(data)))
        self.connection.commit()

    def get(self, table, key):
        row = self.connection.execute(f"SELECT data FROM {self._table(table)} WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, table, project_id=None):
        query = f"SELECT data FROM {self._table(table)}"
        args = ()
        if project_id is not None:
            query += " WHERE project_id=?"
            args = (project_id,)
        return [json.loads(row[0]) for row in self.connection.execute(query + " ORDER BY rowid", args)]

    def delete(self, table, key):
        self.connection.execute(f"DELETE FROM {self._table(table)} WHERE id=?", (key,))
        self.connection.commit()

    def close(self):
        self.connection.close()
