import time
import os
import json
from datetime import datetime
from core.database import QueueManager
from core.content_manager import ContentManager

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {}

def run_daemon():
    db = QueueManager()
    config = load_config()
    manager = ContentManager(config)
    
    print(f"[{datetime.now()}] Background Daemon Started. Polling QueueManager...")
    
    while True:
        try:
            pending = db.get_pending_posts()
            for post in pending:
                print(f"[{datetime.now()}] Found pending post ID: {post['id']}")
                
                content = post['content']
                image_path = post.get('image_path')
                
                success, msg = manager.publish_post(content, image_path)
                if success:
                    print(f"[{datetime.now()}] Post {post['id']} successful: {msg}")
                    db.update_status(post['id'], 'POSTED')
                else:
                    print(f"[{datetime.now()}] Post {post['id']} failed: {msg}")
                    db.update_status(post['id'], 'FAILED')
                    
        except Exception as e:
            print(f"[{datetime.now()}] Daemon error: {e}")
            
        time.sleep(60)
