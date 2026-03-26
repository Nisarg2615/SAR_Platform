import time
from collections import deque

class ProviderHealth:
    def __init__(self, window: int = 5, failure_threshold: int = 2, cooldown_s: int = 60):
        self._results: deque = deque(maxlen=window)
        self._fail_threshold = failure_threshold
        self._cooldown_s = cooldown_s
        self._unhealthy_until: float = 0.0

    def record(self, success: bool):
        self._results.append(success)
        recent_failures = sum(1 for r in list(self._results)[-self._fail_threshold:] if not r)
        if recent_failures >= self._fail_threshold:
            self._unhealthy_until = time.time() + self._cooldown_s

    def is_healthy(self) -> bool:
        return time.time() >= self._unhealthy_until

class HealthCache:
    def __init__(self):
        self._providers: dict[str, ProviderHealth] = {}

    def _get(self, provider: str) -> ProviderHealth:
        if provider not in self._providers:
            self._providers[provider] = ProviderHealth()
        return self._providers[provider]

    def record_success(self, provider: str):
        self._get(provider).record(True)

    def record_failure(self, provider: str):
        self._get(provider).record(False)

    def is_healthy(self, provider: str) -> bool:
        return self._get(provider).is_healthy()

health_cache = HealthCache()
