#!/usr/bin/env python3
"""Deterministically rebuild Feed Me, Seymore from Trello.

The script intentionally does no discovery or enrichment. Trello's open
Learn · Enriched and Learn · Recommended lists are the authoritative feed set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TRELLO_API = "https://api.trello.com/1"
JERUSALEM = ZoneInfo("Asia/Jerusalem")

DEFAULT_IDS = {
    "canonical_card": "6a9be0e6a1dc845ae3514be0",
    "enriched_list": "6a9c2408edbcb452bce35076",
    "recommended_list": "6a9c240d84e3397a15a6f202",
    "inbox_list": "6944a5c20c973d5587213ddd",
    "log_card": "6a9d16eed880cf84a8c1d9eb",
    "log_policy_card": "6a9d16e611540e3110483950",
}

FIELDS = "id,name,desc,url,shortUrl,closed,idList"


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def ids() -> dict[str, str]:
    return {
        "canonical_card": env("TRELLO_CANONICAL_CARD_ID", DEFAULT_IDS["canonical_card"]),
        "enriched_list": env("TRELLO_ENRICHED_LIST_ID", DEFAULT_IDS["enriched_list"]),
        "recommended_list": env("TRELLO_RECOMMENDED_LIST_ID", DEFAULT_IDS["recommended_list"]),
        "inbox_list": env("TRELLO_INBOX_LIST_ID", DEFAULT_IDS["inbox_list"]),
        "log_card": env("TRELLO_LOG_CARD_ID", DEFAULT_IDS["log_card"]),
        "log_policy_card": env("TRELLO_LOG_POLICY_CARD_ID", DEFAULT_IDS["log_policy_card"]),
    }


def trello_request(method: str, path: str, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> Any:
    key = env("TRELLO_API_KEY", required=True)
    token = env("TRELLO_TOKEN", required=True)
    query = {"key": key, "token": token}
    if params:
        query.update({k: v for k, v in params.items() if v is not None})
    url = f"{TRELLO_API}{path}?{urllib.parse.urlencode(query)}"
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Trello {method} {path} failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Trello {method} {path} failed: {exc}") from exc
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def get_card(card_id: str) -> dict[str, Any]:
    return trello_request("GET", f"/cards/{card_id}", {"fields": FIELDS})


def get_open_cards(list_id: str) -> list[dict[str, Any]]:
    cards = trello_request(
        "GET",
        f"/lists/{list_id}/cards",
        {"filter": "open", "fields": FIELDS, "limit": 1000},
    )
    if not isinstance(cards, list):
        raise RuntimeError(f"Unexpected Trello response for list {list_id}")
    if len(cards) >= 1000:
        raise RuntimeError(f"List {list_id} reached the 1000-card safety ceiling; refusing a possibly truncated refresh")
    return [c for c in cards if not c.get("closed")]


def stable_shortlink(url: str | None) -> str | None:
    match = re.search(r"trello\.com/c/([^/]+)", url or "", re.IGNORECASE)
    return match.group(1) if match else None


def line_field(desc: str | None, label: str) -> str | None:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", desc or "", re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def section_field(desc: str | None, label: str) -> str | None:
    pattern = rf"(?:^|\n){re.escape(label)}:\s*([\s\S]*?)(?=\n[A-Z][A-Z0-9 ·/_()'’.-]{{2,}}:|$)"
    match = re.search(pattern, desc or "", re.IGNORECASE)
    return match.group(1).strip() if match else None


def build_hook(card: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous and previous.get("hook"):
        return str(previous["hook"]).strip()
    text = (
        section_field(card.get("desc"), "SUMMARY")
        or line_field(card.get("desc"), "DESCRIPTION NOTES")
        or line_field(card.get("desc"), "DESCRIPTION")
        or line_field(card.get("desc"), "WORTH CONSUMING")
        or card.get("name")
        or "No summary available."
    )
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[-•]\s*", "", text)
    if len(text) > 280:
        text = text[:277].rsplit(" ", 1)[0] + "…"
    return text


def infer_type(platform: str, source: str, previous: dict[str, Any] | None) -> str:
    if previous and previous.get("type") in {"WATCH", "READ", "TRY"}:
        return previous["type"]
    probe = f"{platform} {source}".lower()
    if "youtube" in probe or "youtu.be" in probe:
        return "WATCH"
    if "github" in probe:
        return "TRY"
    return "READ"


def item_from_card(card: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any] | None:
    trello = card.get("url") or card.get("shortUrl")
    title = line_field(card.get("desc"), "TITLE") or card.get("name") or (previous or {}).get("title")
    source = line_field(card.get("desc"), "SOURCE") or (previous or {}).get("source")
    if not title or not source or not trello:
        return None

    platform = line_field(card.get("desc"), "PLATFORM") or (previous or {}).get("platform") or "unknown"
    channel = line_field(card.get("desc"), "CHANNEL") or (previous or {}).get("channel")
    duration = line_field(card.get("desc"), "TIME TO CONSUME") or (previous or {}).get("duration") or "unknown"
    item: dict[str, Any] = {
        "title": title,
        "source": source,
        "trello": trello,
        "platform": platform,
    }
    if channel:
        item["channel"] = channel
    item["duration"] = duration
    item["type"] = infer_type(platform, source, previous)
    item["hook"] = build_hook(card, previous)
    return item


def write_github_output(name: str, value: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_feed(feed: dict[str, Any], eligible_cards: list[dict[str, Any]], inbox_cards: list[dict[str, Any]]) -> dict[str, Any]:
    items = feed.get("items")
    unresolved = feed.get("unresolved")
    if not isinstance(items, list) or not isinstance(unresolved, list):
        raise RuntimeError("feed.json must contain list fields: items and unresolved")

    eligible_keys = [stable_shortlink(c.get("url") or c.get("shortUrl")) for c in eligible_cards]
    eligible_keys = [k for k in eligible_keys if k]
    feed_keys = [stable_shortlink(i.get("trello")) for i in items]
    feed_keys = [k for k in feed_keys if k]

    counts: dict[str, int] = {}
    for key in feed_keys:
        counts[key] = counts.get(key, 0) + 1

    missing = sorted(k for k in eligible_keys if counts.get(k, 0) == 0)
    duplicates = sorted(k for k, count in counts.items() if count != 1)
    eligible_set = set(eligible_keys)
    extras = sorted(k for k in feed_keys if k not in eligible_set)

    required_missing = 0
    for item in items:
        for field in ("title", "source", "trello", "platform", "duration", "type", "hook"):
            if field not in item or item[field] in (None, ""):
                required_missing += 1
                break

    inbox_keys = sorted(
        k for k in (stable_shortlink(c.get("url") or c.get("shortUrl")) for c in inbox_cards) if k
    )
    unresolved_keys = sorted(
        k for k in (stable_shortlink(i.get("trello")) for i in unresolved) if k
    )
    unresolved_ok = inbox_keys == unresolved_keys

    ok = (
        not missing
        and not duplicates
        and not extras
        and required_missing == 0
        and unresolved_ok
        and len(items) == len(eligible_cards)
    )
    result = {
        "ok": ok,
        "eligible": len(eligible_cards),
        "published": len(items),
        "inbox": len(inbox_cards),
        "unresolved": len(unresolved),
        "missing": missing,
        "duplicates": duplicates,
        "extras": extras,
        "required_missing": required_missing,
        "unresolved_ok": unresolved_ok,
    }
    if not ok:
        raise RuntimeError(f"Feed verification failed: {json.dumps(result, ensure_ascii=False)}")
    return result


def refresh(feed_path: Path, summary_path: Path) -> int:
    cfg = ids()
    canonical = get_card(cfg["canonical_card"])
    status_line = next((line.strip() for line in (canonical.get("desc") or "").splitlines() if line.strip()), "")
    active = status_line.casefold() == "status: active" and not canonical.get("closed", False)
    write_github_output("active", "true" if active else "false")
    if not active:
        summary = {"active": False, "status": status_line or "unknown"}
        save_json(summary_path, summary)
        print(f"Canonical automation is not active ({status_line or 'missing status'}); no changes made.")
        return 0

    enriched = get_open_cards(cfg["enriched_list"])
    recommended = get_open_cards(cfg["recommended_list"])
    inbox = get_open_cards(cfg["inbox_list"])
    eligible = recommended + enriched

    old = load_json(feed_path)
    old_items = old.get("items", [])
    if not isinstance(old_items, list):
        raise RuntimeError("Existing feed.json items field is not a list")

    old_by_key = {
        key: item
        for item in old_items
        if isinstance(item, dict)
        for key in [stable_shortlink(item.get("trello"))]
        if key
    }

    additions = 0
    metadata_updates = 0
    unusable: list[str] = []
    new_items: list[dict[str, Any]] = []

    for card in eligible:
        key = stable_shortlink(card.get("url") or card.get("shortUrl"))
        previous = old_by_key.get(key) if key else None
        item = item_from_card(card, previous)
        if item is None:
            unusable.append(card.get("name") or card.get("id") or "unknown")
            continue
        if previous is None:
            additions += 1
        elif item != previous:
            metadata_updates += 1
        new_items.append(item)

    if unusable:
        raise RuntimeError(
            "Eligible cards missing minimum metadata (title/source/Trello URL); refusing partial feed: "
            + ", ".join(unusable)
        )

    eligible_keys = {
        key
        for card in eligible
        for key in [stable_shortlink(card.get("url") or card.get("shortUrl"))]
        if key
    }
    removals = sum(
        1
        for item in old_items
        if isinstance(item, dict)
        and (key := stable_shortlink(item.get("trello")))
        and key not in eligible_keys
    )

    rebuilt = {
        "updated": datetime.now(JERUSALEM).isoformat(timespec="seconds"),
        "unresolved": [
            {"title": card.get("name") or "Untitled", "trello": card.get("url") or card.get("shortUrl")}
            for card in inbox
        ],
        "items": new_items,
    }

    verification = validate_feed(rebuilt, eligible, inbox)
    save_json(feed_path, rebuilt)

    summary = {
        "active": True,
        "timestamp": rebuilt["updated"],
        "enriched": len(enriched),
        "recommended": len(recommended),
        "eligible": len(eligible),
        "published": len(new_items),
        "inbox": len(inbox),
        "unresolved": len(rebuilt["unresolved"]),
        "additions": additions,
        "removals": removals,
        "metadata_updates": metadata_updates,
        "verification": verification,
    }
    save_json(summary_path, summary)

    for name in ("enriched", "recommended", "eligible", "published", "inbox", "additions", "removals", "metadata_updates"):
        write_github_output(name, str(summary[name]))
    write_github_output("updated", summary["timestamp"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def verify_remote(feed_path: Path, summary_path: Path) -> int:
    feed = load_json(feed_path)
    summary = load_json(summary_path)
    expected_timestamp = summary.get("timestamp")
    if feed.get("updated") != expected_timestamp:
        raise RuntimeError(
            f"Remote feed timestamp mismatch: expected {expected_timestamp!r}, got {feed.get('updated')!r}"
        )
    if len(feed.get("items", [])) != summary.get("published"):
        raise RuntimeError("Remote feed item count does not match refresh summary")
    if len(feed.get("unresolved", [])) != summary.get("unresolved"):
        raise RuntimeError("Remote unresolved count does not match refresh summary")
    print(
        f"Remote verification passed: {summary.get('published')} feed items, "
        f"{summary.get('unresolved')} unresolved, timestamp {expected_timestamp}"
    )
    return 0


def make_log_line(summary: dict[str, Any] | None, error: bool) -> str:
    now = datetime.now(JERUSALEM).strftime("%m-%d %H:%M")
    if error:
        if summary and summary.get("active"):
            return (
                f"{now} | E{summary.get('enriched','?')} R{summary.get('recommended','?')} "
                f"feedFAIL err1"
            )
        return f"{now} | refresh failed; err1"
    assert summary is not None
    return (
        f"{now} | E{summary['enriched']} R{summary['recommended']} "
        f"feed{summary['published']} I{summary['inbox']} "
        f"+{summary['additions']}/-{summary['removals']} err0"
    )


def update_log(summary_path: Path, *, error: bool) -> int:
    cfg = ids()
    get_card(cfg["log_policy_card"])
    log_card = get_card(cfg["log_card"])

    summary: dict[str, Any] | None = None
    if summary_path.exists():
        summary = load_json(summary_path)
        if summary.get("active") is False:
            return 0

    line = make_log_line(summary, error)
    if len(line) > 55:
        line = line[:55]

    desc = log_card.get("desc") or ""
    match = re.search(r"(^|\n)LOG\n", desc)
    if not match:
        raise RuntimeError("Dedicated log card has no LOG section")

    log_start = match.end()
    header = desc[:log_start]
    existing = [row for row in desc[log_start:].splitlines() if row.strip()]
    lines = [line, *existing][:30]

    while lines and len(header + "\n".join(lines)) >= 2000:
        lines.pop()

    new_desc = header + "\n".join(lines)
    trello_request("PUT", f"/cards/{cfg['log_card']}", data={"desc": new_desc})
    print(f"Trello run log updated: {line}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    refresh_cmd = sub.add_parser("refresh")
    refresh_cmd.add_argument("--feed", type=Path, default=Path("feed.json"))
    refresh_cmd.add_argument("--summary-file", type=Path, default=Path("/tmp/feed_refresh_summary.json"))

    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--feed", type=Path, required=True)
    verify_cmd.add_argument("--summary-file", type=Path, required=True)

    log_cmd = sub.add_parser("log")
    log_cmd.add_argument("--summary-file", type=Path, default=Path("/tmp/feed_refresh_summary.json"))
    log_cmd.add_argument("--error", action="store_true")

    args = parser.parse_args()
    if args.command == "refresh":
        return refresh(args.feed, args.summary_file)
    if args.command == "verify":
        return verify_remote(args.feed, args.summary_file)
    if args.command == "log":
        return update_log(args.summary_file, error=args.error)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
