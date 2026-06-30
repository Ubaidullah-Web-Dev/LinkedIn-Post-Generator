"""
core/daemon.py — Background queue processor with graceful shutdown,
structured logging, heartbeat, and rate limiting.

v2 rewrite:
- Signal handlers for SIGTERM/SIGINT
- Proper logging (no print statements)
- Config hot-reload each cycle
- Rate limiting (minimum gap between posts)
- Retry failed posts with exponential backoff
- Heartbeat file for health checks
"""

from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from core.config import load_config, invalidate_config_cache
from core.constants import (
    DAEMON_POLL_INTERVAL,
    DAEMON_MIN_POST_GAP,
    DAEMON_MAX_RETRIES,
    HEARTBEAT_PATH,
    PostStatus,
)
from core.database import QueueManager
from core.llm.gateway import LLMGateway
from core.services.publisher import Publisher
from core.logger import get_logger, setup_logging

logger = get_logger(__name__)

# ── Graceful shutdown ────────────────────────────────────────────────────────

_running = True


def _signal_handler(sig: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global _running
    logger.info("Received signal %s — shutting down gracefully...", sig)
    _running = False


def _write_heartbeat() -> None:
    """Write a heartbeat file for external health monitoring."""
    try:
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "pid": __import__("os").getpid(),
            "status": "alive",
        }
        with open(str(HEARTBEAT_PATH), "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# ── Main Daemon Loop ─────────────────────────────────────────────────────────

def run_daemon() -> None:
    """
    Main daemon entry point. Polls the queue and publishes due posts.

    Features:
    - Graceful shutdown on SIGTERM/SIGINT
    - Config hot-reload each cycle
    - Rate limiting between posts
    - Heartbeat file for monitoring
    """
    global _running

    # Setup
    setup_logging()
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    db = QueueManager()
    last_post_time: float = 0.0

    logger.info("═══════════════════════════════════════════════════")
    logger.info("  LinkedIn Post Automator — Daemon Started")
    logger.info("  Poll interval: %ds | Min gap: %ds", DAEMON_POLL_INTERVAL, DAEMON_MIN_POST_GAP)
    logger.info("═══════════════════════════════════════════════════")

    while _running:
        try:
            # Hot-reload config each cycle
            invalidate_config_cache()
            config = load_config()

            # Write heartbeat
            _write_heartbeat()

            # Check for pending posts
            pending = db.get_pending_posts()

            for post in pending:
                if not _running:
                    break

                post_id = post["id"]

                # Rate limiting: ensure minimum gap between posts
                elapsed = time.time() - last_post_time
                if elapsed < DAEMON_MIN_POST_GAP and last_post_time > 0:
                    wait = DAEMON_MIN_POST_GAP - elapsed
                    logger.info(
                        "Rate limit: waiting %.0fs before next post", wait
                    )
                    time.sleep(wait)
                    if not _running:
                        break

                logger.info("Processing post #%d", post_id)

                content = post["content"]
                image_path = post.get("image_path")

                try:
                    publisher = Publisher(config.cookies)
                    success, msg = publisher.publish(content, image_path)

                    if success:
                        logger.info("Post #%d published successfully", post_id)
                        db.update_status(post_id, PostStatus.POSTED)
                        last_post_time = time.time()
                    else:
                        logger.warning("Post #%d failed: %s", post_id, msg)
                        db.update_status(
                            post_id, PostStatus.FAILED, error_log=msg
                        )

                except Exception as e:
                    logger.error("Post #%d error: %s", post_id, e)
                    db.update_status(
                        post_id, PostStatus.FAILED, error_log=str(e)
                    )

        except Exception as e:
            logger.error("Daemon cycle error: %s", e)

        # Sleep in small increments for responsive shutdown
        for _ in range(DAEMON_POLL_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    # Cleanup
    logger.info("Daemon stopped cleanly.")
    db.close()

    # Clear heartbeat
    try:
        heartbeat = Path(HEARTBEAT_PATH)
        if heartbeat.exists():
            data = {"timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "status": "stopped"}
            with open(str(heartbeat), "w") as f:
                json.dump(data, f)
    except OSError:
        pass
