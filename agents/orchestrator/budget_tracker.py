from dataclasses import dataclass, field
from agents.llm.config import PROVIDER_CONFIGS

@dataclass
class ProviderBudget:
    rpm_used:  int = 0
    rpd_used:  int = 0
    rpm_limit: int = 30
    rpd_limit: int = 1000

    def can_use(self) -> bool:
        return self.rpm_used < self.rpm_limit and self.rpd_used < self.rpd_limit

    def record_use(self):
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
