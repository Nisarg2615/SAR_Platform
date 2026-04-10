from dataclasses import dataclass, field
from datetime import datetime, timedelta
from agents.llm.config import PROVIDER_CONFIGS

@dataclass
class ProviderBudget:
    rpm_used:  int = 0
    rpd_used:  int = 0
    rpm_limit: int = 30
    rpd_limit: int = 1000
    rpm_window_start: datetime = field(default_factory=datetime.utcnow)
    rpd_window_start: datetime = field(default_factory=datetime.utcnow)

    def _maybe_reset(self):
        now = datetime.utcnow()
        # Reset per-minute budget every 60s.
        if now - self.rpm_window_start >= timedelta(minutes=1):
            self.rpm_used = 0
            self.rpm_window_start = now
        # Reset per-day budget every 24h.
        if now - self.rpd_window_start >= timedelta(days=1):
            self.rpd_used = 0
            self.rpd_window_start = now

    def can_use(self) -> bool:
        self._maybe_reset()
        return self.rpm_used < self.rpm_limit and self.rpd_used < self.rpd_limit

    def record_use(self):
        self._maybe_reset()
        self.rpm_used += 1
        self.rpd_used += 1

class BudgetTracker:
    def __init__(self):
        self._budgets: dict[str, ProviderBudget] = {
            name: ProviderBudget(
                rpm_limit=cfg["rpm_limit"],
                rpd_limit=cfg["rpd_limit"]
            )
            for name, cfg in PROVIDER_CONFIGS.items()
        }

    def can_use(self, provider: str) -> bool:
        return self._budgets.get(provider, ProviderBudget()).can_use()

    def record_use(self, provider: str):
        if provider in self._budgets:
            self._budgets[provider].record_use()

    def get_status(self) -> dict:
        return {
            name: {"rpm_used": b.rpm_used, "rpd_used": b.rpd_used,
                   "can_use": b.can_use()}
            for name, b in self._budgets.items()
        }

budget_tracker = BudgetTracker()
