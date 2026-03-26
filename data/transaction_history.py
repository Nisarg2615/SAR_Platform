"""
TransactionHistoryStore — in-memory past-transaction context for risk assessment.
Provides velocity checks, rolling-window totals, and historical pattern detection.
"""
from datetime import datetime, timedelta
from data.transactions_dataset import TRANSACTIONS


class TransactionHistoryStore:
    def __init__(self, transactions: list[dict]):
        self._by_account: dict[str, list[dict]] = {}
        for txn in transactions:
            acct = txn.get("account_id", "")
            self._by_account.setdefault(acct, []).append(txn)
        # Sort each account's list chronologically once at startup.
        for acct in self._by_account:
            self._by_account[acct].sort(key=lambda t: t["timestamp"])

    def get_history(self, account_id: str, before_timestamp: str) -> list[dict]:
        """Return all past transactions for account strictly before given ISO timestamp."""
        return [
            t for t in self._by_account.get(account_id, [])
            if t["timestamp"] < before_timestamp
        ]

    def get_velocity(self, account_id: str, before_timestamp: str, hours: int = 24) -> int:
        """Count transactions in the last N hours before before_timestamp."""
        cutoff_dt = datetime.fromisoformat(before_timestamp) - timedelta(hours=hours)
        cutoff = cutoff_dt.isoformat()
        return sum(
            1 for t in self._by_account.get(account_id, [])
            if cutoff <= t["timestamp"] < before_timestamp
        )

    def get_total_amount_last_n_days(
        self, account_id: str, before_timestamp: str, days: int = 30
    ) -> float:
        """Sum of all transaction amounts in the last N days before before_timestamp."""
        cutoff_dt = datetime.fromisoformat(before_timestamp) - timedelta(days=days)
        cutoff = cutoff_dt.isoformat()
        return sum(
            float(t.get("amount_usd", 0))
            for t in self._by_account.get(account_id, [])
            if cutoff <= t["timestamp"] < before_timestamp
        )

    def has_structuring_pattern(self, account_id: str, before_timestamp: str) -> bool:
        """True if any past transaction was a cash deposit within $500 below $10,000."""
        return any(
            9000 <= float(t.get("amount_usd", 0)) < 10000
            and t.get("transaction_type") == "cash_deposit"
            for t in self.get_history(account_id, before_timestamp)
        )


# Module-level singleton — import this from other modules.
history_store = TransactionHistoryStore(TRANSACTIONS)
