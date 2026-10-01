"""
Data models for the Bank Statement Spending Analyst Agent.
Enforces strict categorization schema, transaction capture, and reporting structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any


class AccountType(str, Enum):
    CHECKING = "Checking"
    SAVINGS = "Savings"
    CREDIT_CARD = "Credit Card"
    INVESTMENT = "Investment"
    UNKNOWN = "Unknown"


class TransactionType(str, Enum):
    DEBIT = "DEBIT"    # Standardized as Outflow / Spending
    CREDIT = "CREDIT"  # Standardized as Inflow / Refund


class SpendingCategory(str, Enum):
    HOUSING_UTILITIES = "Housing & Utilities"
    GROCERIES = "Groceries"
    DINING_DELIVERY = "Dining Out & Food Delivery"
    TRANSPORTATION = "Transportation"
    HEALTHCARE_MEDICAL = "Healthcare & Medical"
    SHOPPING_DISCRETIONARY = "Shopping & Discretionary"
    ENTERTAINMENT_SUBSCRIPTIONS = "Entertainment & Subscriptions"
    DEBT_SERVICE = "Debt Service"
    MISCELLANEOUS_OTHER = "Miscellaneous / Other"
    INCOME_INFLOWS = "Income / Inflows"
    UNCATEGORIZED = "Uncategorized / Needs Review"


# Primary spending categories expected in breakdown table (excluding Income)
PRIMARY_EXPENSE_CATEGORIES = [
    SpendingCategory.HOUSING_UTILITIES.value,
    SpendingCategory.GROCERIES.value,
    SpendingCategory.DINING_DELIVERY.value,
    SpendingCategory.TRANSPORTATION.value,
    SpendingCategory.HEALTHCARE_MEDICAL.value,
    SpendingCategory.SHOPPING_DISCRETIONARY.value,
    SpendingCategory.ENTERTAINMENT_SUBSCRIPTIONS.value,
    SpendingCategory.DEBT_SERVICE.value,
    SpendingCategory.MISCELLANEOUS_OTHER.value,
    SpendingCategory.UNCATEGORIZED.value,
]


@dataclass
class Transaction:
    id: str
    date: str  # YYYY-MM-DD
    raw_description: str
    clean_payee: str
    amount: float  # Absolute positive amount
    type: TransactionType
    account_source: str  # E.g. "Checking ...1234"
    category: str = SpendingCategory.UNCATEGORIZED.value
    is_internal_transfer: bool = False
    is_refund: bool = False
    is_subscription: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "date": str(self.date),
            "raw_description": str(self.raw_description),
            "clean_payee": str(self.clean_payee),
            "amount": float(round(self.amount, 2)),
            "type": self.type.value if isinstance(self.type, TransactionType) else str(self.type),
            "account_source": str(self.account_source),
            "category": str(self.category),
            "is_internal_transfer": bool(self.is_internal_transfer),
            "is_refund": bool(self.is_refund),
            "is_subscription": bool(self.is_subscription),
            "notes": str(self.notes or "")
        }


@dataclass
class StatementMetadata:
    account_name: str
    account_type: AccountType
    account_number_masked: str  # Only last 4 digits, e.g. "...4321"
    currency: str = "USD"
    currency_symbol: str = "$"
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    raw_file_name: str = ""
    bank_institution: str = "Unknown Bank"


@dataclass
class CategorySummary:
    category: str
    total_spent: float
    percentage_of_spend: float  # Must sum precisely to 100.0% across all categories
    top_merchants: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "total_spent": round(self.total_spent, 2),
            "percentage_of_spend": round(self.percentage_of_spend, 2),
            "top_merchants": [{"merchant": m, "amount": round(a, 2)} for m, a in self.top_merchants]
        }


@dataclass
class RecurringCost:
    merchant: str
    category: str
    cadence: str  # Monthly, Annual, Weekly
    monthly_amount: float
    occurrences: int
    sample_dates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant": self.merchant,
            "category": self.category,
            "cadence": self.cadence,
            "monthly_amount": round(self.monthly_amount, 2),
            "occurrences": self.occurrences,
            "sample_dates": self.sample_dates
        }


@dataclass
class AnalysisReport:
    statement_period: str
    total_inflow: float
    total_outflow: float
    net_cash_flow: float
    savings_rate: float
    category_breakdowns: List[CategorySummary]
    recurring_costs: List[RecurringCost]
    total_recurring_monthly: float
    top_outflow_drivers: List[str]
    anomalies_and_spikes: List[str]
    optimization_opportunities: List[str]
    account_sources: List[str]
    total_transactions_parsed: int
    internal_transfers_excluded: int
    refunds_offset: int
    currency: str = "USD"
    currency_symbol: str = "$"
    redaction_guardrails_applied: bool = True
    checksum_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement_period": str(self.statement_period),
            "currency": str(self.currency),
            "currency_symbol": str(self.currency_symbol),
            "total_inflow": float(round(self.total_inflow, 2)),
            "total_outflow": float(round(self.total_outflow, 2)),
            "net_cash_flow": float(round(self.net_cash_flow, 2)),
            "savings_rate": float(round(self.savings_rate, 2)),
            "category_breakdowns": [c.to_dict() for c in self.category_breakdowns],
            "recurring_costs": [r.to_dict() for r in self.recurring_costs],
            "total_recurring_monthly": float(round(self.total_recurring_monthly, 2)),
            "top_outflow_drivers": [str(d) for d in self.top_outflow_drivers],
            "anomalies_and_spikes": [str(a) for a in self.anomalies_and_spikes],
            "optimization_opportunities": [str(o) for o in self.optimization_opportunities],
            "account_sources": [str(s) for s in self.account_sources],
            "total_transactions_parsed": int(self.total_transactions_parsed),
            "internal_transfers_excluded": int(self.internal_transfers_excluded),
            "refunds_offset": int(self.refunds_offset),
            "redaction_guardrails_applied": bool(self.redaction_guardrails_applied),
            "checksum_valid": bool(self.checksum_valid)
        }
