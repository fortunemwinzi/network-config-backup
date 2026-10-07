#!/usr/bin/env python3
"""Network Config Backup and Change Detector v0.1
Pulls each device's configuration (from a file or over SSH), saves a
timestamped copy only when it changed, logs the diff, and sends a
Telegram alert that never includes the config contents."""

import difflib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

DEVICES_FILE = Path("devices.json")
BACKUP_DIR = Path("backups")
CHANGE_LOG = BACKUP_DIR / "changes.log"

# Lines that differ on every pull and would cause false change alerts
VOLATILE = [
    re.compile(r"^Building configuration"),
    re.compile(r"^Current configuration"),
    re.compile(r"^! Last configuration change"),
    re.compile(r"^! NVRAM config last updated"),
    re.compile(r"^ntp clock-period"),
]


def clean(config: str) -> str:
    """Strip trailing spaces and volatile lines so only real changes show."""
    lines = [line.rstrip() for line in config.splitlines()]
    kept = [l for l in lines if not any(p.match(l) for p in VOLATILE)]
    return "\n".join(kept).strip() + "\n"


def fetch_config(device: dict) -> str:
    """Get the running config from a file (lab mode) or over SSH."""
    if "source_file" in device:
        return Path(device["source_file"]).read_text()
    from netmiko import ConnectHandler  # only needed for real devices

    conn = ConnectHandler(
        device_type=device.get("device_type", "cisco_ios"),
        host=device["host"],
        port=device.get("port", 22),
        username=os.environ["DEVICE_USERNAME"],
        password=os.environ["DEVICE_PASSWORD"],
        timeout=20,
    )
    try:
        return conn.send_command("show running-config")
    finally:
        conn.disconnect()


def latest_backup(name: str):
    folder = BACKUP_DIR / name
    files = sorted(folder.glob("*.cfg")) if folder.exists() else []
    return files[-1] if files else None


def save_backup(name: str, config: str) -> Path:
    folder = BACKUP_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.cfg"
    path.write_text(config)
    return path


def make_diff(old_path: Path, old: str, new: str, name: str):
    diff = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=old_path.name, tofile=f"{name} (current)", lineterm="", n=0))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    return diff, added, removed


def log_change(name: str, diff: list) -> None:
    BACKUP_DIR.mkdir(exist_ok=True)
    with CHANGE_LOG.open("a") as f:
        f.write(f"\n=== {name} changed at {datetime.now().isoformat(timespec='seconds')} ===\n")
        f.write("\n".join(diff) + "\n")


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured; skipping alert.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as resp:
            return resp.status == 200
    except OSError as exc:
        print(f"Telegram alert failed: {exc}")
        return False


def main() -> int:
    devices = json.loads(DEVICES_FILE.read_text())
    alerts, errors = [], 0
    print(f"{'DEVICE':<20}{'RESULT':<12}DETAIL")

    for device in devices:
        name = device["name"]
        try:
            new = clean(fetch_config(device))
        except Exception as exc:  # one bad device must not stop the run
            errors += 1
            print(f"{name:<20}{'ERROR':<12}{exc}")
            alerts.append(f"{name}: backup FAILED")
            continue

        previous = latest_backup(name)
        if previous is None:
            path = save_backup(name, new)
            print(f"{name:<20}{'NEW':<12}first backup saved ({path.name})")
            continue

        old = previous.read_text()
        if old == new:
            print(f"{name:<20}{'UNCHANGED':<12}-")
            continue

        diff, added, removed = make_diff(previous, old, new, name)
        save_backup(name, new)
        log_change(name, diff)
        print(f"{name:<20}{'CHANGED':<12}+{added} / -{removed} lines")
        alerts.append(f"{name}: config changed (+{added} / -{removed} lines)")

    if alerts:
        send_telegram("Config Change Alert\n" + "\n".join(alerts))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())