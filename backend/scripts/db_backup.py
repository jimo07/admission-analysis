#!/usr/bin/env python3
"""Cross-platform S0-10 MySQL backup/restore helper; standard library only."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

BACKEND = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND / ".env"


def config():
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    raw = values.get("DATABASE_URL", "")
    if not raw.startswith("mysql+pymysql://"):
        raise RuntimeError("DATABASE_URL must use mysql+pymysql")
    url = urlsplit(raw.replace("mysql+pymysql://", "mysql://", 1))
    db = unquote(url.path.lstrip("/"))
    if not url.hostname or not url.username or not re.fullmatch(r"[A-Za-z0-9_]+", db):
        raise RuntimeError("DATABASE_URL is incomplete or has an invalid schema name")
    return {"host": url.hostname, "port": str(url.port or 3306),
            "user": unquote(url.username), "password": unquote(url.password or ""),
            "database": db, "charset": parse_qs(url.query).get("charset", ["utf8mb4"])[0]}


def binary(name):
    exe = name + (".exe" if os.name == "nt" else "")
    found = shutil.which(exe)
    if found:
        return found
    if os.name == "nt":
        root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MySQL"
        choices = sorted(root.glob(f"MySQL Server */bin/{exe}"), reverse=True)
    else:
        choices = [Path("/usr/local/mysql/bin") / exe,
                   Path("/opt/homebrew/bin") / exe,
                   Path("/opt/homebrew/opt/mysql-client/bin") / exe]
    for path in choices:
        if path.is_file():
            return str(path)
    raise RuntimeError(f"{exe} not found; add MySQL client tools to PATH")


def option(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


class Options:
    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="sfb-mysql-", suffix=".cnf", delete=False)
        if os.name != "nt":
            os.chmod(self.file.name, 0o600)
        for key, val in (("host", CFG["host"]), ("port", CFG["port"]), ("user", CFG["user"]),
                         ("password", CFG["password"]), ("default-character-set", CFG["charset"])):
            if key == "host":
                self.file.write("[client]\n")
            self.file.write(f"{key}={option(val)}\n")
        self.file.close()
        return self.file.name

    def __exit__(self, *_):
        Path(self.file.name).unlink(missing_ok=True)


def main():
    global CFG
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--database", default="")
    b.add_argument("--out-dir", type=Path, default=BACKEND / "scripts" / "backups")
    r = sub.add_parser("restore")
    r.add_argument("dump_file", type=Path)
    r.add_argument("--target-database", required=True)
    a = p.parse_args()
    try:
        CFG = config()
        if a.action == "backup":
            db = a.database or CFG["database"]
            if not re.fullmatch(r"[A-Za-z0-9_]+", db):
                raise RuntimeError("Invalid schema name")
            a.out_dir.mkdir(parents=True, exist_ok=True)
            output = a.out_dir / f"{db}_{datetime.now():%Y%m%d_%H%M%S}.sql"
            with Options() as opts, output.open("wb") as stream:
                command = [binary("mysqldump"), f"--defaults-extra-file={opts}",
                           "--single-transaction", "--routines", "--triggers", "--events",
                           "--no-tablespaces", "--set-gtid-purged=OFF", db]
                result = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE)
            if result.returncode:
                output.unlink(missing_ok=True)
                raise RuntimeError(f"mysqldump failed (exit {result.returncode})")
            print(f"Backup completed: {output} ({output.stat().st_size} bytes)")
        else:
            db = a.target_database
            if not re.fullmatch(r"[A-Za-z0-9_]+", db) or not a.dump_file.is_file():
                raise RuntimeError("Invalid target schema or backup file not found")
            if input(f"Restore into {db}. Type the schema name to continue: ").strip() != db:
                raise RuntimeError("Restore cancelled")
            with Options() as opts, a.dump_file.open("rb") as stream:
                command = [binary("mysql"), f"--defaults-extra-file={opts}", f"--database={db}"]
                result = subprocess.run(command, stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError(f"mysql restore failed (exit {result.returncode})")
            print(f"Restore completed into {db}")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
