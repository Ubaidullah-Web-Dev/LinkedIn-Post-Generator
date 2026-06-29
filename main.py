import argparse
import sys
import json
import os

from core.daemon import run_daemon
from core.content_manager import ContentManager

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {}

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Post Automator (Enterprise Edition)")
    parser.add_argument("--daemon", action="store_true", help="Start the background SQLite queue daemon")
    parser.add_argument("--post-now", action="store_true", help="Instantly generate and post (headless)")
    
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.post_now:
        config = load_config()
        manager = ContentManager(config)
        print("Executing headless post generation...")
        manager.post_content(provider="auto", image_model="auto")
    else:
        # No args = Textual GUI
        from core.gui import AutomatorApp
        app = AutomatorApp()
        app.run()

if __name__ == "__main__":
    main()
