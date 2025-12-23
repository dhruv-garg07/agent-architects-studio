"""In-memory rate limiter (no external dependencies).

Note: This is process-local and not suitable for multi-worker distributed
deployments. It implements per-minute buckets for RPM/TPM and a simple
concurrency counter.
"""
import threading
import time
from collections import defaultdict


class LocalRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        # maps (key_id, minute) -> count
        self._rpm = defaultdict(int)
        self._tpm = defaultdict(int)
        # maps key_id -> concurrency count
        self._concurrency = defaultdict(int)

    def _minute_key(self):
        return int(time.time()) // 60

    def allow_request(self, key_id: str, limits: dict, estimated_tokens: int = 1) -> bool:
        minute = self._minute_key()
        rpm_key = (key_id, minute)
        tpm_key = (key_id, minute)

        rpm_limit = int(limits.get("rpm", 60))
        tpm_limit = int(limits.get("tpm", 100000))
        concurrency_limit = int(limits.get("concurrency", 5))

        with self._lock:
            cur_rpm = self._rpm.get(rpm_key, 0)
            cur_tpm = self._tpm.get(tpm_key, 0)
            cur_con = self._concurrency.get(key_id, 0)

            if cur_rpm + 1 > rpm_limit:
                return False
            if cur_tpm + estimated_tokens > tpm_limit:
                return False
            if cur_con + 1 > concurrency_limit:
                return False

            # increment
            self._rpm[rpm_key] = cur_rpm + 1
            self._tpm[tpm_key] = cur_tpm + estimated_tokens
            self._concurrency[key_id] = cur_con + 1

            # best-effort cleanup of old keys
            self._cleanup_old(minute)

            return True

    def end_request(self, key_id: str):
        with self._lock:
            if self._concurrency.get(key_id, 0) > 0:
                self._concurrency[key_id] -= 1

    def _cleanup_old(self, current_minute: int):
        # Remove RPM/TPM keys older than 2 minutes
        cutoff = current_minute - 2
        for k in list(self._rpm.keys()):
            if k[1] < cutoff:
                del self._rpm[k]
        for k in list(self._tpm.keys()):
            if k[1] < cutoff:
                del self._tpm[k]


# Module-level singleton
rate_limiter = LocalRateLimiter()
