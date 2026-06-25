import os
import json
import time
from fastapi import Request
from dotenv import load_dotenv

load_dotenv(override=True)

def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

class RateLimiter:
    def __init__(self):
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        project_root = os.path.dirname(backend_dir)
        self.cache_dir = os.path.join(project_root, "cache")
        self.file_path = os.path.join(self.cache_dir, "rate_limits.json")
        
        self.data = {"ip_limit": {}, "thread_ip": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[Rate Limiter] Error loading file: {e}")
                
        if "ip_limit" not in self.data:
            self.data["ip_limit"] = {}
        if "thread_ip" not in self.data:
            self.data["thread_ip"] = {}

    def _save(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Rate Limiter] Error saving file: {e}")

    def register_thread(self, thread_id: str, ip: str):
        self.data["thread_ip"][thread_id] = ip
        self._save()

    def get_thread_ip(self, thread_id: str) -> str:
        return self.data["thread_ip"].get(thread_id, "")

    def check_rate_limit(self, ip: str) -> bool:
        """
        Returns True if client is allowed to start a new request, False if blocked.
        Clean up timestamps older than 24 hours.
        Skip rate check if DEVELOPER_MODE is enabled.
        """
        dev_mode = os.getenv("DEVELOPER_MODE", "false").lower().strip()
        if dev_mode in ("true", "1", "yes"):
            print(f"[Rate Limiter] Developer mode active — skipping rate limit check for IP: {ip}")
            return True

        now = time.time()
        day_ago = now - 24 * 3600
        
        history = self.data["ip_limit"].get(ip, [])
        history = [ts for ts in history if ts > day_ago]
        self.data["ip_limit"][ip] = history
        self._save()
        
        return len(history) < 2

    def record_success(self, thread_id: str):
        ip = self.get_thread_ip(thread_id)
        if not ip:
            print(f"[Rate Limiter] No IP registered for thread {thread_id}")
            return
        
        now = time.time()
        day_ago = now - 24 * 3600
        
        history = self.data["ip_limit"].get(ip, [])
        history = [ts for ts in history if ts > day_ago]
        history.append(now)
        
        self.data["ip_limit"][ip] = history
        self._save()
        print(f"[Rate Limiter] Successful itinerary recorded for IP: {ip}. Count in last 24h: {len(history)}")
