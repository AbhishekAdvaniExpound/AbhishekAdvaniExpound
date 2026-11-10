#!/usr/bin/env python3
"""Fetch and validate public GitHub profile data without third-party services."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "contributions.json"
DEFAULT_USER = "AbhishekAdvaniExpound"
USER_AGENT = "profile-card-renderer/1.0 (+https://github.com/AbhishekAdvaniExpound)"


class CalendarParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cells: dict[str, dict[str, Any]] = {}
        self.tooltip_target: str | None = None
        self.tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "td" and values.get("data-date") and values.get("id"):
            self.cells[values["id"]] = {
                "date": values["data-date"],
                "level": int(values.get("data-level") or 0),
                "count": 0,
            }
        elif tag == "tool-tip" and values.get("for"):
            self.tooltip_target = values["for"]
            self.tooltip_text = []

    def handle_data(self, data: str) -> None:
        if self.tooltip_target:
            self.tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "tool-tip" or not self.tooltip_target:
            return
        text = " ".join(self.tooltip_text).strip()
        match = re.search(r"([\d,]+) contributions? on", text)
        if self.tooltip_target in self.cells:
            self.cells[self.tooltip_target]["count"] = int(match.group(1).replace(",", "")) if match else 0
        self.tooltip_target = None
        self.tooltip_text = []


def request_bytes(url: str, token: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub returned HTTP {response.status} for {url}")
        return response.read()


def request_json(url: str, token: str | None = None) -> Any:
    return json.loads(request_bytes(url, token).decode("utf-8"))


def parse_calendar(payload: bytes) -> list[dict[str, Any]]:
    parser = CalendarParser()
    parser.feed(payload.decode("utf-8"))
    days = list(parser.cells.values())
    if len(days) < 350:
        raise ValueError(f"Contribution calendar contained only {len(days)} dated cells")
    for item in days:
        date.fromisoformat(item["date"])
        if item["count"] < 0 or not 0 <= item["level"] <= 4:
            raise ValueError("Contribution calendar contained an invalid value")
    return days


def streaks(days: list[dict[str, Any]]) -> tuple[int, int]:
    longest = current = run = 0
    for item in days:
        if item["count"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    for item in reversed(days):
        if item["count"] > 0:
            current += 1
        else:
            break
    return longest, current


def safe_repo(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": repo.get("name", ""),
        "url": repo.get("html_url", ""),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stars": int(repo.get("stargazers_count") or 0),
        "fork": bool(repo.get("fork")),
        "archived": bool(repo.get("archived")),
    }


def safe_event(event: dict[str, Any]) -> dict[str, Any]:
    repo_name = (event.get("repo") or {}).get("name", "")
    return {
        "type": event.get("type", "Activity"),
        "repository": repo_name,
        "repository_url": f"https://github.com/{repo_name}" if repo_name else "",
        "created_at": event.get("created_at"),
    }


def build_payload(username: str, today: date, token: str | None) -> dict[str, Any]:
    start = today - timedelta(days=364)
    all_days: dict[str, dict[str, Any]] = {}
    for year in range(start.year, today.year + 1):
        url = f"https://github.com/users/{username}/contributions?from={year}-01-01&to={year}-12-31"
        for item in parse_calendar(request_bytes(url)):
            all_days[item["date"]] = item

    days = []
    cursor = start
    while cursor <= today:
        key = cursor.isoformat()
        if key not in all_days:
            raise ValueError(f"Missing contribution data for {key}")
        days.append(all_days[key])
        cursor += timedelta(days=1)

    api = "https://api.github.com"
    profile = request_json(f"{api}/users/{username}", token)
    repos = request_json(f"{api}/users/{username}/repos?per_page=100&sort=updated", token)
    events = request_json(f"{api}/users/{username}/events/public?per_page=30", token)
    if profile.get("login", "").lower() != username.lower() or not isinstance(repos, list) or not isinstance(events, list):
        raise ValueError("GitHub API returned an unexpected payload")

    months: dict[str, int] = defaultdict(int)
    for item in days:
        months[item["date"][:7]] += item["count"]
    longest, current = streaks(days)
    best = max(days, key=lambda item: item["count"])
    return {
        "schema_version": 1,
        "username": profile["login"],
        "name": profile.get("name") or profile["login"],
        "profile_url": profile.get("html_url"),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "period": {"from": start.isoformat(), "to": today.isoformat()},
        "summary": {
            "total": sum(item["count"] for item in days),
            "active_days": sum(item["count"] > 0 for item in days),
            "longest_streak": longest,
            "current_streak": current,
            "best_day": {"date": best["date"], "count": best["count"]},
            "public_repositories": int(profile.get("public_repos") or 0),
        },
        "months": [{"month": key, "count": months[key]} for key in sorted(months)],
        "days": days,
        "repositories": [safe_repo(repo) for repo in repos if not repo.get("private")],
        # Ignore this profile repository's automated refresh pushes so the
        # workflow does not create a self-sustaining daily data diff.
        "recent_activity": [
            safe_event(event) for event in events
            if (event.get("repo") or {}).get("name", "").lower() != f"{username}/{username}".lower()
        ][:8],
    }


def atomic_json_write(path: Path, payload: dict[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            comparable_existing = {key: value for key, value in existing.items() if key != "generated_at"}
            comparable_new = {key: value for key, value in payload.items() if key != "generated_at"}
            if comparable_existing == comparable_new:
                return False
        except (OSError, json.JSONDecodeError):
            pass
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.environ.get("GITHUB_REPOSITORY_OWNER", DEFAULT_USER))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="Calendar end date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        payload = build_payload(args.username, args.date, os.environ.get("GITHUB_TOKEN"))
        changed = atomic_json_write(args.output, payload)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"fetch_contributions: {exc}", file=os.sys.stderr)
        print("Existing data was left untouched.", file=os.sys.stderr)
        return 1
    action = "Wrote" if changed else "Verified unchanged"
    print(f"{action} {args.output} with {payload['summary']['total']} verified contributions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
