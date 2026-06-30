#!/usr/bin/env python3
"""
main.py — Entry point for the LinkedIn Post Automator v2.

Usage:
    python main.py              Launch the Textual TUI
    python main.py --daemon     Run the background queue processor
    python main.py --status     Check daemon health
    python main.py --install    Install systemd service
    python main.py --uninstall  Uninstall systemd service
    python main.py --reset-db   Reset the database (with confirmation)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.constants import HEARTBEAT_PATH, DB_PATH
from core.logger import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LinkedIn Post Automator v2 — AI-powered LinkedIn content creation",
    )
    parser.add_argument("--daemon", action="store_true", help="Run background queue processor")
    parser.add_argument("--status", action="store_true", help="Check daemon health status")
    parser.add_argument("--install", action="store_true", help="Install systemd user service")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall systemd user service")
    parser.add_argument("--reset-db", action="store_true", help="Reset database (destructive)")

    args = parser.parse_args()

    if args.daemon:
        setup_logging()
        from core.daemon import run_daemon
        run_daemon()

    elif args.status:
        _check_status()

    elif args.install:
        from core.service_manager import ServiceManager
        svc = ServiceManager()
        svc.install()
        print("✅ Service installed and started.")

    elif args.uninstall:
        from core.service_manager import ServiceManager
        svc = ServiceManager()
        svc.uninstall()
        print("✅ Service uninstalled.")

    elif args.reset_db:
        _reset_db()

    else:
        # Launch TUI
        from core.gui import AutomatorApp
        app = AutomatorApp()
        app.run()


def _check_status() -> None:
    """Check daemon heartbeat status."""
    heartbeat = Path(HEARTBEAT_PATH)
    if not heartbeat.exists():
        print("❌ No heartbeat file found. Daemon may not be running.")
        return

    try:
        with open(str(heartbeat)) as f:
            data = json.load(f)
        status = data.get("status", "unknown")
        ts = data.get("timestamp", "unknown")
        pid = data.get("pid", "unknown")

        if status == "alive":
            print(f"✅ Daemon is running (PID: {pid}, last heartbeat: {ts})")
        elif status == "stopped":
            print(f"⏹  Daemon stopped at {ts}")
        else:
            print(f"⚠  Unknown status: {status} (last: {ts})")

    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ Error reading heartbeat: {e}")


def _reset_db() -> None:
    """Reset the database with confirmation."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("No database found. Nothing to reset.")
        return

    confirm = input(f"⚠  This will DELETE all data in {db_path}. Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Cancelled.")
        return

    # Backup first
    from core.database import QueueManager
    db = QueueManager()
    backup_path = db.backup(suffix="pre-reset")
    if backup_path:
        print(f"📦 Backup created: {backup_path}")

    db.close()
    db_path.unlink()
    print("✅ Database reset. A fresh one will be created on next launch.")


if __name__ == "__main__":
    main()
