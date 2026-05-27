#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def kaggle_bin() -> str:
    candidates = [
        Path(sys.prefix) / "bin" / "kaggle",
        Path(sys.prefix) / "Scripts" / "kaggle.exe",
        Path(sys.executable).resolve().with_name("kaggle"),
        Path(sys.executable).resolve().with_name("kaggle.exe"),
    ]
    return str(next((path for path in candidates if path.exists()), "kaggle"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cache_path(root: Path, competition: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in competition)
    return root / "runs" / f"kaggle_submissions_cache_{safe}.json"


def _parse_rows(text: str) -> list[dict[str, str]]:
    start = text.find("fileName,date,description,status,publicScore,privateScore")
    if start >= 0:
        text = text[start:]
    return list(csv.DictReader(io.StringIO(text)))


def _read_cache(root: Path, competition: str, max_age_seconds: int) -> tuple[list[dict[str, str]], str | None]:
    path = _cache_path(root, competition)
    if not path.exists():
        return [], None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], None
    if payload.get("competition") != competition:
        return [], None
    rows = payload.get("rows")
    fetched_at = payload.get("fetched_at_utc")
    if not isinstance(rows, list) or not isinstance(fetched_at, str):
        return [], None
    try:
        fetched_dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except Exception:
        return [], None
    age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
    if age > max_age_seconds:
        return [], None
    return [row for row in rows if isinstance(row, dict)], fetched_at


def _write_cache(root: Path, competition: str, rows: list[dict[str, str]]) -> None:
    path = _cache_path(root, competition)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "competition": competition,
                "fetched_at_utc": _utc_now(),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def kaggle_submissions(
    root: Path,
    competition: str,
    *,
    page_size: int = 200,
    retries: int = 4,
    initial_sleep_seconds: int = 20,
    cache_max_age_seconds: int = 1800,
    timeout_seconds: int = 75,
) -> tuple[bool, list[dict[str, str]], str | None]:
    command = [
        kaggle_bin(),
        "competitions",
        "submissions",
        "-c",
        competition,
        "-v",
        "--page-size",
        str(page_size),
    ]
    last_output = ""
    for attempt in range(retries + 1):
        try:
            proc = subprocess.run(
                command,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            last_output = (exc.stdout or exc.stderr or "")
            if isinstance(last_output, bytes):
                last_output = last_output.decode("utf-8", errors="replace")
            last_output = f"Kaggle submissions command timed out after {timeout_seconds}s: {last_output[-2000:]}"
            break
        if proc.returncode == 0:
            rows = _parse_rows(proc.stdout)
            _write_cache(root, competition, rows)
            return True, rows, None
        last_output = proc.stdout[-4000:]
        if "429" not in last_output and "Too Many Requests" not in last_output:
            break
        if attempt < retries:
            time.sleep(initial_sleep_seconds * (2**attempt))

    cached_rows, fetched_at = _read_cache(root, competition, cache_max_age_seconds)
    if cached_rows and fetched_at:
        return True, cached_rows, f"using cached Kaggle submissions from {fetched_at}; latest API error: {last_output}"
    return False, [], last_output or "Kaggle submissions command failed"
