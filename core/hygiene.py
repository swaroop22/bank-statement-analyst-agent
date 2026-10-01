"""
Transaction Hygiene & De-duplication Module.
Ensures zero double-counting by:
1. Filtering internal transfers & credit card payments.
2. Removing duplicate transaction entries.
3. Offsetting retail refunds against corresponding expense categories.
"""

import re
from typing import List, Tuple, Dict, Any, Set
from core.models import Transaction, TransactionType, SpendingCategory


class TransactionHygiene:
    """Hygiene filter and de-duplication engine."""

    # Patterns indicating internal transfers or balance statements that should be ignored
    INTERNAL_TRANSFER_PATTERNS = [
        r'(?:automatic|online|mobile)?\s*payment\s*[-:]?\s*.*(?:chase|amex|citi|discover|capital|sbi\s*card|cred|card|thank\s*you)',
        r'autopay\b.*',
        r'automatic\s+payment\b.*',
        r'payment\s+(?:to|for)\s+.*(?:chase|amex|citi|discover|capital|sbi|credit|card)',
        r'amex\s+epayment',
        r'credit\s+card\s+(?:payment|autopay|billpay)',
        r'cred\s+(?:club|billpay|payment)',
        r'transfer\s+(?:to|from)\s+(?:sav|chk|checking|savings|account|self|mod|fd|ppf)',
        r'(?:to|by)\s+transfer-inb\s+(?:to|from|a/c)',
        r'sweep\s+trf\s+to\s+mod',
        r'trf\s+from\s+mod',
        r'mod\s+balance',
        r'online\s+transfer\s+(?:to|from)',
        r'internal\s+transfer',
        r'zelle\s+transfer\s+to\s+self',
        r'beginning\s+balance',
        r'ending\s+balance',
        r'previous\s+balance',
        r'statement\s+balance',
        r'balance\s+forward',
        r'opening\s+balance',
        r'closing\s+balance',
        r'interest\s+charge\s+summary',
    ]

    # Retail / service merchants where credits indicate returns / refunds rather than income
    REFUND_MERCHANT_PATTERNS = [
        r'amazon', r'target', r'walmart', r'best\s*buy', r'nordstrom',
        r'macys', r'apple\.com', r'uber(?:\s*refund)?', r'lyft(?:\s*refund)?',
        r'delta\s*air', r'united\s*air', r'southwest', r'airbnb',
        r'swiggy(?:\s*refund)?', r'zomato(?:\s*refund)?', r'flipkart(?:\s*refund)?',
        r'myntra(?:\s*refund)?', r'irctc(?:\s*refund)?', r'zepto(?:\s*refund)?',
        r'blinkit(?:\s*refund)?', r'ola(?:\s*refund)?',
        r'refund', r'return', r'reversal', r'chargeback'
    ]

    def __init__(self):
        self.transfer_regex = re.compile('|'.join(self.INTERNAL_TRANSFER_PATTERNS), re.I)
        self.refund_regex = re.compile('|'.join(self.REFUND_MERCHANT_PATTERNS), re.I)

    def is_internal_transfer(self, tx: Transaction) -> bool:
        """Identify internal transfers, card payments, and balance statements."""
        desc = tx.raw_description.lower()
        if self.transfer_regex.search(desc):
            return True
        # Check payee
        if self.transfer_regex.search(tx.clean_payee.lower()):
            return True
        return False

    def is_retail_refund(self, tx: Transaction) -> bool:
        """Identify if a CREDIT transaction is a merchant refund rather than income."""
        if tx.type != TransactionType.CREDIT:
            return False
        desc = tx.raw_description.lower()
        # Explicit payroll or interest is NOT a refund
        if any(term in desc for term in ['payroll', 'salary', 'direct dep', 'direct deposit', 'interest paid', 'dividend', 'irs treas']):
            return False
        return bool(self.refund_regex.search(desc))

    def clean_transactions(
        self, transactions: List[Transaction]
    ) -> Tuple[List[Transaction], List[Transaction], Dict[str, int]]:
        """
        Process transactions:
        1. De-duplicate identical transactions.
        2. Detect internal transfers and exclude them from spend/income.
        3. Identify refunds vs genuine income.
        
        Returns:
            Tuple[List[Transaction], List[Transaction], Dict[str, int]]:
            - Valid active transactions (debits + genuine income)
            - Excluded / Internal transfer transactions
            - Stats dict
        """
        seen_keys: Set[str] = set()
        active_transactions: List[Transaction] = []
        excluded_transactions: List[Transaction] = []

        stats = {
            "total_raw": len(transactions),
            "duplicates_removed": 0,
            "internal_transfers_excluded": 0,
            "refunds_detected": 0
        }

        for tx in transactions:
            # Generate de-duplication fingerprint
            fingerprint = f"{tx.date}_{tx.amount:.2f}_{tx.clean_payee.lower().strip()}_{tx.type.value}"
            if fingerprint in seen_keys:
                stats["duplicates_removed"] += 1
                continue
            seen_keys.add(fingerprint)

            # Check internal transfers
            if self.is_internal_transfer(tx):
                tx.is_internal_transfer = True
                tx.notes = "Internal account transfer / Card payoff ignored to prevent double counting"
                excluded_transactions.append(tx)
                stats["internal_transfers_excluded"] += 1
                continue

            # Check refund
            if self.is_retail_refund(tx):
                tx.is_refund = True
                tx.notes = "Merchant return / refund to offset against expense category"
                stats["refunds_detected"] += 1

            active_transactions.append(tx)

        return active_transactions, excluded_transactions, stats
