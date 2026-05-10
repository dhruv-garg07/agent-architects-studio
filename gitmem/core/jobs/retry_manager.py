"""
GitMem v2.0 — Retry Manager

Handles retry logic and dead-letter queue for failed jobs.
Scans for stuck/failed jobs and re-enqueues or marks as dead.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List


class RetryManager:
    """
    Manages retry policies for the job queue.
    
    - Resets 'failed' jobs back to 'pending' (if under max_attempts)
    - Moves jobs exceeding max_attempts to 'dead'
    - Detects stuck 'running' jobs (heartbeat timeout) and reclaims them
    """

    def __init__(self, supabase_client, stuck_timeout_minutes: int = 15):
        self.client = supabase_client
        self._table = "gitmem_jobs"
        self.stuck_timeout = timedelta(minutes=stuck_timeout_minutes)

    def sweep(self) -> Dict[str, int]:
        """
        Run a single sweep:
        1. Reclaim stuck running jobs
        2. Move exhausted failed jobs to dead

        Returns counts of reclaimed and killed jobs.
        """
        if not self.client:
            return {"reclaimed": 0, "killed": 0}

        reclaimed = self._reclaim_stuck_jobs()
        killed = self._kill_exhausted_jobs()

        return {"reclaimed": reclaimed, "killed": killed}

    def _reclaim_stuck_jobs(self) -> int:
        """Find jobs stuck in 'running' state past timeout, reset to pending."""
        if not self.client:
            return 0

        try:
            cutoff = (datetime.now() - self.stuck_timeout).isoformat()

            # Find stuck jobs
            res = self.client.table(self._table).select("id, attempts, max_attempts") \
                .eq("status", "running") \
                .lt("started_at", cutoff) \
                .limit(50) \
                .execute()

            if not res.data:
                return 0

            count = 0
            for job in res.data:
                if job["attempts"] >= job["max_attempts"]:
                    # Exhausted — kill
                    self.client.table(self._table).update({
                        "status": "dead",
                        "error": "Stuck in running state — max attempts exhausted",
                        "completed_at": datetime.now().isoformat()
                    }).eq("id", job["id"]).execute()
                else:
                    # Reset to pending
                    self.client.table(self._table).update({
                        "status": "pending",
                        "started_at": None,
                        "error": "Reclaimed from stuck running state"
                    }).eq("id", job["id"]).execute()
                    count += 1

            return count

        except Exception as e:
            print(f"[RetryManager] Reclaim error: {e}")
            return 0

    def _kill_exhausted_jobs(self) -> int:
        """Move jobs that have exceeded max_attempts from failed to dead."""
        if not self.client:
            return 0

        try:
            # This is tricky with Supabase — we can't do attempts >= max_attempts
            # directly. Fetch failed jobs and check in Python.
            res = self.client.table(self._table).select("id, attempts, max_attempts") \
                .eq("status", "failed") \
                .limit(100) \
                .execute()

            if not res.data:
                return 0

            count = 0
            for job in res.data:
                if job["attempts"] >= job["max_attempts"]:
                    self.client.table(self._table).update({
                        "status": "dead",
                        "completed_at": datetime.now().isoformat()
                    }).eq("id", job["id"]).execute()
                    count += 1

            return count

        except Exception as e:
            print(f"[RetryManager] Kill exhausted error: {e}")
            return 0

    def get_dead_jobs(self, workspace_id: str = None, limit: int = 50) -> List[Dict]:
        """Get dead-letter queue contents."""
        if not self.client:
            return []

        try:
            query = self.client.table(self._table).select("*") \
                .eq("status", "dead") \
                .order("completed_at", desc=True) \
                .limit(limit)

            if workspace_id:
                query = query.eq("workspace_id", workspace_id)

            res = query.execute()
            return res.data or []

        except Exception as e:
            print(f"[RetryManager] Dead jobs query failed: {e}")
            return []
