"""Run backend from project root: python scripts/run_backend.py"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    env = {"PYTHONPATH": str(ROOT), **dict(__import__("os").environ)}
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    subprocess.run(cmd, cwd=ROOT / "backend", env=env, check=False)


if __name__ == "__main__":
    main()
