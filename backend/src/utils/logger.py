import asyncio
from typing import Dict, Optional, Any

class SessionQueueManager:
    """
    Manages async log queues for active sessions.
    Allows capturing prints/logs from different agent nodes and routing them
    to the correct SSE client streaming connection based on thread_id.
    """
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def register(self, thread_id: str) -> asyncio.Queue:
        """Registers a new queue for a thread_id and captures the running event loop."""
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        queue = asyncio.Queue()
        self.queues[thread_id] = queue
        return queue

    def unregister(self, thread_id: str):
        """Unregisters/deletes the queue for a thread_id."""
        if thread_id in self.queues:
            del self.queues[thread_id]

    def get_queue(self, thread_id: str) -> Optional[asyncio.Queue]:
        """Gets the queue associated with the thread_id."""
        return self.queues.get(thread_id)

    def log(self, thread_id: str, message: str):
        """Prints the message to the console and pushes it to the thread's queue."""
        print(message, flush=True)
        queue = self.get_queue(thread_id)
        if queue:
            # Thread-safely push log message to main event loop queue if it is running
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(queue.put_nowait, message)

    def log_event(self, thread_id: str, event_data: Dict[str, Any]):
        """Pushes a structured event to the thread's queue (bypassing raw console prints)."""
        queue = self.get_queue(thread_id)
        if queue:
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(queue.put_nowait, event_data)

# Global logger instance
session_logger = SessionQueueManager()

def log_agent(config: Optional[Any], message: str):
    """
    Helper function to be called from inside LangGraph nodes.
    Extracts the thread_id from the LangGraph config object and logs the message.
    """
    thread_id = "default"
    if isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id", "default")
    elif hasattr(config, "configurable"):
        thread_id = config.configurable.get("thread_id", "default")
    session_logger.log(thread_id, message)

def log_dev(config: Optional[Any], message: str):
    """
    Helper function to log technical/developer details (e.g. latency metrics, debug loops)
    to the server console only. Bypasses the client-facing SSE queue.
    """
    thread_id = "default"
    if isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id", "default")
    elif hasattr(config, "configurable"):
        thread_id = config.configurable.get("thread_id", "default")
    print(f"[Dev Log] [{thread_id}] {message}", flush=True)

def emit_event(config: Optional[Any], event_data: Dict[str, Any]):
    """
    Emits a structured event to the client-facing SSE queue.
    """
    thread_id = "default"
    if isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id", "default")
    elif hasattr(config, "configurable"):
        thread_id = config.configurable.get("thread_id", "default")
    session_logger.log_event(thread_id, event_data)
