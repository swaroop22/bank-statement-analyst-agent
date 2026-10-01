"""
Recurring Subscriptions & Fixed Costs Detection Engine.
Identifies recurring merchant charges (streaming, fitness, utilities, software, memberships)
and calculates monthly recurring burn rate.
"""

import re
from typing import List, Dict
from collections import defaultdict
from core.models import Transaction, RecurringCost, TransactionType, SpendingCategory


class RecurringCostDetector:
    """Detects recurring subscriptions and fixed living expenses."""

    # Merchants universally known to be fixed/recurring monthly or annual services
    KNOWN_SUBSCRIPTIONS = {
        "netflix": ("Entertainment & Subscriptions", "Monthly"),
        "spotify": ("Entertainment & Subscriptions", "Monthly"),
        "hulu": ("Entertainment & Subscriptions", "Monthly"),
        "disney+": ("Entertainment & Subscriptions", "Monthly"),
        "max.com": ("Entertainment & Subscriptions", "Monthly"),
        "hbo max": ("Entertainment & Subscriptions", "Monthly"),
        "apple.com/bill": ("Entertainment & Subscriptions", "Monthly"),
        "icloud": ("Entertainment & Subscriptions", "Monthly"),
        "youtube premium": ("Entertainment & Subscriptions", "Monthly"),
        "amazon prime": ("Shopping & Discretionary", "Monthly"),
        "gym": ("Entertainment & Subscriptions", "Monthly"),
        "equinox": ("Entertainment & Subscriptions", "Monthly"),
        "planet fitness": ("Entertainment & Subscriptions", "Monthly"),
        "24 hour fitness": ("Entertainment & Subscriptions", "Monthly"),
        "orange theory": ("Entertainment & Subscriptions", "Monthly"),
        "nytimes": ("Entertainment & Subscriptions", "Monthly"),
        "wall street journal": ("Entertainment & Subscriptions", "Monthly"),
        "chatgpt": ("Entertainment & Subscriptions", "Monthly"),
        "openai": ("Entertainment & Subscriptions", "Monthly"),
        "github": ("Entertainment & Subscriptions", "Monthly"),
        "audible": ("Entertainment & Subscriptions", "Monthly"),
        # Fixed Utilities & Telecommunications
        "comcast": ("Housing & Utilities", "Monthly (Utility/Internet)"),
        "xfinity": ("Housing & Utilities", "Monthly (Utility/Internet)"),
        "at&t": ("Housing & Utilities", "Monthly (Telecom)"),
        "verizon": ("Housing & Utilities", "Monthly (Telecom)"),
        "t-mobile": ("Housing & Utilities", "Monthly (Telecom)"),
        "spectrum": ("Housing & Utilities", "Monthly (Utility/Internet)"),
        "pg&e": ("Housing & Utilities", "Monthly (Utility/Electric)"),
        "con edison": ("Housing & Utilities", "Monthly (Utility/Electric)"),
        "duke energy": ("Housing & Utilities", "Monthly (Utility/Electric)"),
        "water dept": ("Housing & Utilities", "Monthly (Utility/Water)"),
        "waste management": ("Housing & Utilities", "Monthly (Trash/Recycle)"),
    }

    def detect_recurring(self, transactions: List[Transaction]) -> List[RecurringCost]:
        """
        Analyze debit transactions to extract recurring subscriptions and fixed utility costs.
        """
        merchant_groups: Dict[str, List[Transaction]] = defaultdict(list)

        for tx in transactions:
            if tx.type != TransactionType.DEBIT or tx.is_internal_transfer or tx.is_refund:
                continue
            norm_merchant = tx.clean_payee.lower().strip()
            merchant_groups[norm_merchant].append(tx)

        recurring_items: List[RecurringCost] = []
        already_identified_merchants = set()

        # Step 1: Detect from Known Subscriptions & Fixed Utilities
        for norm_merchant, tx_list in merchant_groups.items():
            for known_key, (category, cadence) in self.KNOWN_SUBSCRIPTIONS.items():
                if known_key in norm_merchant and norm_merchant not in already_identified_merchants:
                    # Mark transactions as subscription
                    for t in tx_list:
                        t.is_subscription = True

                    avg_amount = sum(t.amount for t in tx_list) / len(tx_list)
                    dates = sorted([t.date for t in tx_list])
                    
                    recurring_items.append(RecurringCost(
                        merchant=tx_list[0].clean_payee,
                        category=category,
                        cadence=cadence,
                        monthly_amount=round(avg_amount, 2),
                        occurrences=len(tx_list),
                        sample_dates=dates
                    ))
                    already_identified_merchants.add(norm_merchant)
                    break

        # Step 2: Cadence / Pattern-based detection for multi-occurrence identical amounts
        for norm_merchant, tx_list in merchant_groups.items():
            if norm_merchant in already_identified_merchants:
                continue

            if len(tx_list) >= 2:
                # Check if amounts are virtually identical (within 2%)
                amounts = [t.amount for t in tx_list]
                avg_amt = sum(amounts) / len(amounts)
                if all(abs(a - avg_amt) <= 0.05 * avg_amt for a in amounts):
                    # Likely a recurring charge
                    for t in tx_list:
                        t.is_subscription = True

                    dates = sorted([t.date for t in tx_list])
                    recurring_items.append(RecurringCost(
                        merchant=tx_list[0].clean_payee,
                        category=tx_list[0].category,
                        cadence="Monthly Recurring",
                        monthly_amount=round(avg_amt, 2),
                        occurrences=len(tx_list),
                        sample_dates=dates
                    ))
                    already_identified_merchants.add(norm_merchant)

        # Sort descending by monthly amount
        recurring_items.sort(key=lambda x: x.monthly_amount, reverse=True)
        return recurring_items
