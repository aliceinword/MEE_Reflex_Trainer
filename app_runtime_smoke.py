# -*- coding: utf-8 -*-
"""Runtime smoke test for the Streamlit app using a disposable database copy."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_DB = ROOT / "mee_trainer.db"


def _prepare_temp_db(tmp_dir: Path) -> Path:
    temp_db = tmp_dir / "mee_trainer_runtime_smoke.db"
    shutil.copy2(SOURCE_DB, temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("DELETE FROM app_users")
        conn.commit()
    finally:
        conn.close()

    return temp_db


def _wait_for_http(port: int, proc: subprocess.Popen, timeout_seconds: int = 25) -> bool:
    deadline = time.time() + timeout_seconds
    url = f"http://127.0.0.1:{port}/"

    while time.time() < deadline:
        if proc.poll() is not None:
            return False

        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)

    return False


def main() -> None:
    if not SOURCE_DB.exists():
        raise SystemExit(f"Source database not found: {SOURCE_DB}")

    port = int(os.environ.get("MEE_RUNTIME_SMOKE_PORT", "8780"))

    with tempfile.TemporaryDirectory(prefix="mee_runtime_smoke_") as tmp:
        tmp_dir = Path(tmp)
        temp_db = _prepare_temp_db(tmp_dir)
        stdout_path = tmp_dir / "streamlit_stdout.log"
        stderr_path = tmp_dir / "streamlit_stderr.log"

        env = os.environ.copy()
        env["MEE_TRAINER_DB"] = str(temp_db)
        env["MEE_DISABLE_AUTH"] = "1"

        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "app.py",
                    "--server.headless=true",
                    f"--server.port={port}",
                    "--browser.gatherUsageStats=false",
                ],
                cwd=ROOT,
                env=env,
                stdout=stdout,
                stderr=stderr,
            )

        try:
            ready = _wait_for_http(port, proc)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")

        if not ready:
            print("--- Streamlit stdout ---")
            print(stdout_text[-3000:])
            print("--- Streamlit stderr ---")
            print(stderr_text[-3000:])
            raise SystemExit("Streamlit runtime smoke failed.")

    print(f"Runtime smoke passed on http://127.0.0.1:{port}/ using a disposable DB copy.")


if __name__ == "__main__":
    main()
