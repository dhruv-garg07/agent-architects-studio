"""
GitMem v2.0 — Job Queue

Supabase-backed job queue. No Redis/Celery needed for v2.0.
Workers poll gitmem_jobs table for pending work.

Async operations:
- embed: Generate vector embeddings
- summarize: AI summarization of old memories
- compact: Snapshot compaction (packfiles)
- gc: Garbage collection of orphaned objects
- reindex: Full vector rebuild for a repo
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from gitmem.core.models import Job, JobStatus
import uuid


class JobQueue:
    """
    Supabase-backed job queue.
    
    Usage:
        queue = JobQueue(supabase_client)
        job_id = queue.enqueue("embed", workspace_id, {"memory_id": "abc", "content": "..."})
        job = queue.dequeue()  # Workers call this
        queue.complete(job_id, result={...})
    """

    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table = "gitmem_jobs"

    def enqueue(self, job_type: str, workspace_id: str,
                payload: Dict[str, Any] = None,
                priority: int = 0,
                max_attempts: int = 3) -> str:
        """Add a job to the queue. Returns job ID."""
        job = Job(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            job_type=job_type,
            payload=payload or {},
            priority=priority,
            max_attempts=max_attempts
        )

        if not self.client:
            print(f"[JobQueue] No DB client — job {job.job_type} dropped")
            return job.id

        try:
            self.client.table(self._table).insert(
                job.model_dump(mode='json')
            ).execute()
        except Exception as e:
            print(f"[JobQueue] Failed to enqueue job: {e}")

        return job.id

    def dequeue(self, job_types: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Claim the next pending job. Returns None if queue is empty.
        Uses UPDATE ... RETURNING to prevent race conditions.
        """
        if not self.client:
            return None

        try:
            # Fetch oldest pending job with highest priority
            query = self.client.table(self._table).select("*") \
                .eq("status", "pending") \
                .order("priority", desc=True) \
                .order("created_at", desc=False) \
                .limit(1)

            if job_types:
                query = query.in_("job_type", job_types)

            res = query.execute()
            if not res.data:
                return None

            job_data = res.data[0]
            job_id = job_data["id"]

            # Claim it (optimistic lock via status check)
            update_res = self.client.table(self._table) \
                .update({
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "attempts": job_data.get("attempts", 0) + 1
                }) \
                .eq("id", job_id) \
                .eq("status", "pending") \
                .execute()

            if update_res.data:
                return update_res.data[0]
            return None  # Someone else claimed it

        except Exception as e:
            print(f"[JobQueue] Dequeue failed: {e}")
            return None

    def complete(self, job_id: str, result: Dict[str, Any] = None) -> None:
        """Mark a job as completed."""
        if not self.client:
            return
        try:
            self.client.table(self._table).update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "result": result or {}
            }).eq("id", job_id).execute()
        except Exception as e:
            print(f"[JobQueue] Complete failed: {e}")

    def fail(self, job_id: str, error: str, max_attempts: int = 3,
             current_attempts: int = 0) -> None:
        """Mark a job as failed. Move to 'dead' if max attempts reached."""
        if not self.client:
            return
        try:
            new_status = "dead" if current_attempts >= max_attempts else "failed"
            # If failed (not dead), reset to pending for retry
            if new_status == "failed":
                new_status = "pending"

            self.client.table(self._table).update({
                "status": new_status,
                "error": error,
                "completed_at": datetime.now().isoformat() if new_status == "dead" else None
            }).eq("id", job_id).execute()
        except Exception as e:
            print(f"[JobQueue] Fail update failed: {e}")

    def get_stats(self, workspace_id: str = None) -> Dict[str, int]:
        """Get job queue statistics."""
        if not self.client:
            return {"pending": 0, "running": 0, "completed": 0, "failed": 0, "dead": 0}

        stats = {}
        try:
            for status in ["pending", "running", "completed", "failed", "dead"]:
                query = self.client.table(self._table) \
                    .select("*", count="exact") \
                    .eq("status", status)
                if workspace_id:
                    query = query.eq("workspace_id", workspace_id)
                res = query.limit(1).execute()
                stats[status] = res.count or 0
        except Exception as e:
            print(f"[JobQueue] Stats query failed: {e}")
            stats = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "dead": 0}

        return stats
