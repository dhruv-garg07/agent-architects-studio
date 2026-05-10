"""
GitMem v2.0 — Job Workers

Background worker pool that polls gitmem_jobs for pending work.
Each job type maps to a handler function.

Runs as a daemon thread alongside the Flask/SocketIO server.
"""

import threading
import time
from typing import Dict, Callable, Any
from gitmem.core.jobs.queue import JobQueue


class WorkerPool:
    """
    Background worker pool.
    
    Usage:
        pool = WorkerPool(job_queue, poll_interval=5)
        pool.register("embed", handle_embed_job)
        pool.register("summarize", handle_summarize_job)
        pool.start(num_workers=2)
        # ... later ...
        pool.stop()
    """

    def __init__(self, queue: JobQueue, poll_interval: int = 5):
        self.queue = queue
        self.poll_interval = poll_interval
        self._handlers: Dict[str, Callable] = {}
        self._workers: list = []
        self._running = False

    def register(self, job_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler

    def start(self, num_workers: int = 1):
        """Start worker threads."""
        if self._running:
            return

        self._running = True
        for i in range(num_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"gitmem-worker-{i}",
                daemon=True
            )
            t.start()
            self._workers.append(t)

        job_types = list(self._handlers.keys())
        print(f"[Workers] Started {num_workers} worker(s) for: {job_types}")

    def stop(self):
        """Signal workers to stop."""
        self._running = False
        for t in self._workers:
            t.join(timeout=10)
        self._workers.clear()
        print("[Workers] Stopped")

    def _worker_loop(self):
        """Main worker loop: poll → claim → execute → report."""
        job_types = list(self._handlers.keys())

        while self._running:
            try:
                job = self.queue.dequeue(job_types=job_types)
                if not job:
                    time.sleep(self.poll_interval)
                    continue

                job_id = job["id"]
                job_type = job["job_type"]
                payload = job.get("payload", {})
                attempts = job.get("attempts", 1)
                max_attempts = job.get("max_attempts", 3)

                handler = self._handlers.get(job_type)
                if not handler:
                    self.queue.fail(job_id, f"No handler for job type: {job_type}",
                                   max_attempts, attempts)
                    continue

                # Execute the handler
                try:
                    result = handler(payload)
                    self.queue.complete(job_id, result=result)
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    print(f"[Workers] Job {job_id} ({job_type}) failed: {error_msg}")
                    self.queue.fail(job_id, error_msg, max_attempts, attempts)

            except Exception as e:
                print(f"[Workers] Worker loop error: {e}")
                time.sleep(self.poll_interval)
