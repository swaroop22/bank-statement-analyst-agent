"""
CSV and Excel statement parser.
Robustly parses bank and credit card statement exports from major financial institutions
(Chase, Amex, Bank of America, Wells Fargo, Citi, Capital One, and generic formats).
"""

import os
import re
import uuid
from typing import List, Tuple, Optional
import pandas as pd
from datetime import datetime

from core.parsers.base_parser import BaseStatementParser
from core.models import (
    StatementMetadata,
    Transaction,
    AccountType,
    TransactionType,
    SpendingCategory
)


class CsvExcelParser(BaseStatementParser):
    """Parser for CSV, TSV, XLS, and XLSX bank statements."""

    SUPPORTED_EXTENSIONS = {'.csv', '.tsv', '.xlsx', '.xls'}

    def can_parse(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _normalize_date(self, date_val) -> Optional[str]:
        """Convert various date representations to YYYY-MM-DD."""
        if pd.isna(date_val):
            return None
        date_str = str(date_val).strip()
        
        # Try standard parsing formats
        formats = [
            "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y",
            "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%m/%d/%y", "%d-%b-%y"
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Pandas parser fallback
        try:
            dt = pd.to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

    def _infer_account_type_and_mask(self, file_path: str, df: pd.DataFrame) -> Tuple[AccountType, str, str]:
        """Infer account type (Checking, Savings, Credit Card), masked account number, and bank name."""
        filename = os.path.basename(file_path).lower()
        
        bank_name = "Financial Institution"
        account_type = AccountType.UNKNOWN
        if "sbi" in filename or "state bank" in filename or filename.startswith("721371"):
            bank_name = "State Bank of India"
            account_type = AccountType.SAVINGS
        elif "icici" in filename:
            bank_name = "ICICI Bank"
            account_type = AccountType.CHECKING
        elif "hdfc" in filename:
            bank_name = "HDFC Bank"
            account_type = AccountType.CHECKING
        elif "axis" in filename:
            bank_name = "Axis Bank"
            account_type = AccountType.CHECKING
        elif "kotak" in filename:
            bank_name = "Kotak Mahindra Bank"
            account_type = AccountType.CHECKING
        elif "pnb" in filename:
            bank_name = "Punjab National Bank"
            account_type = AccountType.CHECKING
        elif "chase" in filename:
            bank_name = "Chase"
        elif "amex" in filename or "american express" in filename:
            bank_name = "American Express"
        elif "bofa" in filename or "bank of america" in filename:
            bank_name = "Bank of America"
        elif "wells" in filename or "wf" in filename:
            bank_name = "Wells Fargo"
        elif "citi" in filename:
            bank_name = "Citi"
        elif "capital" in filename:
            bank_name = "Capital One"

        # Check account type from filename if not yet determined
        if account_type == AccountType.UNKNOWN:
            if "credit" in filename or "card" in filename or "amex" in filename:
                account_type = AccountType.CREDIT_CARD
            elif "check" in filename or "current" in filename:
                account_type = AccountType.CHECKING
            elif "saving" in filename:
                account_type = AccountType.SAVINGS

        # Extract last 4 digits if present in filename or columns
        last4_match = re.search(r'(?:x+|[*]+|ending[_\s]*in|act[_\s]*|account[_\s]*)(\d{4})', filename, re.I)
        last4 = last4_match.group(1) if last4_match else "XXXX"
        if last4 == "XXXX" and re.search(r'\b\d{11}\b', filename):
            acct_11 = re.search(r'\b\d{7}(\d{4})\b', filename)
            if acct_11:
                last4 = acct_11.group(1)

        # If still unknown, check columns or first few rows for hints
        for col in df.columns:
            col_str = str(col).lower()
            if "card" in col_str or "credit" in col_str:
                if account_type == AccountType.UNKNOWN:
                    account_type = AccountType.CREDIT_CARD

        if account_type == AccountType.UNKNOWN:
            account_type = AccountType.SAVINGS if bank_name == "State Bank of India" else AccountType.CHECKING

        source_label = f"{bank_name} {account_type.value} ...{last4}"
        return account_type, source_label, bank_name

    def parse(self, file_path: str, password: Optional[str] = None) -> Tuple[StatementMetadata, List[Transaction]]:
        ext = os.path.splitext(file_path)[1].lower()
        
        # Load data frame
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            # Handle potential preamble lines before actual header
            try:
                df = pd.read_csv(file_path)
            except Exception:
                df = pd.read_csv(file_path, sep=None, engine='python')

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Identify key columns
        date_col = None
        desc_col = None
        amount_col = None
        debit_col = None
        credit_col = None

        for col in df.columns:
            c_low = col.lower()
            if not date_col and any(k in c_low for k in ['date', 'posting date', 'trans date', 'transaction date']):
                date_col = col
            elif not desc_col and any(k in c_low for k in ['description', 'payee', 'merchant', 'narrative', 'details', 'name', 'memo']):
                desc_col = col
            elif not debit_col and any(k in c_low for k in ['debit', 'withdrawal', 'outflow', 'charge', 'spend']):
                debit_col = col
            elif not credit_col and any(k in c_low for k in ['credit', 'deposit', 'inflow', 'payment']):
                credit_col = col
            elif not amount_col and any(k in c_low for k in ['amount', 'trans amount', 'net amount']):
                amount_col = col

        if not date_col or (not desc_col and len(df.columns) < 2):
            raise ValueError(f"Unable to detect required Date and Description columns in {os.path.basename(file_path)}")

        account_type, account_source, bank_name = self._infer_account_type_and_mask(file_path, df)

        transactions: List[Transaction] = []
        valid_dates = []

        # Determine signed amount convention if only amount_col exists
        # E.g. in checking accounts, negative is debit (spend) and positive is credit (deposit).
        # In some credit card statements (like Amex or Chase CC exports), positive is charge (spend) and negative is payment.
        cc_inverted_amounts = False
        if amount_col and not debit_col and not credit_col:
            if account_type == AccountType.CREDIT_CARD:
                # Check sample descriptions for "payment" or "autopay"
                payments = df[df[desc_col].astype(str).str.contains(r'payment|thank you|autopay', case=False, na=False)]
                if not payments.empty:
                    # If payments have negative amounts, then positive = spend
                    avg_pay = pd.to_numeric(payments[amount_col].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').mean()
                    if avg_pay < 0:
                        cc_inverted_amounts = True

        for idx, row in df.iterrows():
            raw_date = row.get(date_col)
            clean_date = self._normalize_date(raw_date)
            if not clean_date:
                continue

            raw_desc = str(row.get(desc_col, "")).strip()
            if not raw_desc or raw_desc.lower() in ['nan', 'none', '']:
                raw_desc = "Unidentified Merchant / Item"

            amount = 0.0
            tx_type = TransactionType.DEBIT

            # Determine Amount and TransactionType
            if debit_col or credit_col:
                raw_debit = row.get(debit_col, 0) if debit_col else 0
                raw_credit = row.get(credit_col, 0) if credit_col else 0

                val_debit = pd.to_numeric(str(raw_debit).replace('$', '').replace(',', '').strip(), errors='coerce')
                val_credit = pd.to_numeric(str(raw_credit).replace('$', '').replace(',', '').strip(), errors='coerce')

                if pd.notna(val_debit) and abs(val_debit) > 0.001:
                    amount = abs(val_debit)
                    tx_type = TransactionType.DEBIT
                elif pd.notna(val_credit) and abs(val_credit) > 0.001:
                    amount = abs(val_credit)
                    tx_type = TransactionType.CREDIT
                else:
                    continue
            elif amount_col:
                raw_amt = str(row.get(amount_col, 0)).replace('$', '').replace(',', '').strip()
                val_amt = pd.to_numeric(raw_amt, errors='coerce')
                if pd.isna(val_amt) or abs(val_amt) < 0.001:
                    continue

                if cc_inverted_amounts:
                    # In this CC format: positive = charge (spend/DEBIT), negative = payment/refund (CREDIT)
                    if val_amt > 0:
                        amount = val_amt
                        tx_type = TransactionType.DEBIT
                    else:
                        amount = abs(val_amt)
                        tx_type = TransactionType.CREDIT
                else:
                    # Standard checking format: negative = debit (spend), positive = credit (income/deposit)
                    if val_amt < 0:
                        amount = abs(val_amt)
                        tx_type = TransactionType.DEBIT
                    else:
                        amount = val_amt
                        tx_type = TransactionType.CREDIT

            clean_payee = self._clean_merchant_name(raw_desc)
            valid_dates.append(clean_date)

            tx = Transaction(
                id=f"tx_{clean_date}_{abs(hash(raw_desc + str(amount))) % 1000000}",
                date=clean_date,
                raw_description=raw_desc,
                clean_payee=clean_payee,
                amount=round(amount, 2),
                type=tx_type,
                account_source=account_source,
                category=SpendingCategory.UNCATEGORIZED.value
            )
            transactions.append(tx)

        period_start = min(valid_dates) if valid_dates else None
        period_end = max(valid_dates) if valid_dates else None

        is_indian_bank = any(b in bank_name for b in ["State Bank of India", "ICICI Bank", "HDFC Bank", "Axis Bank", "Kotak", "Punjab National Bank"]) or "inr" in os.path.basename(file_path).lower()
        currency = "INR" if is_indian_bank else "USD"
        currency_symbol = "₹" if currency == "INR" else "$"

        metadata = StatementMetadata(
            account_name=f"{bank_name} {account_type.value}",
            account_type=account_type,
            account_number_masked=account_source.split("...")[-1] if "..." in account_source else "XXXX",
            currency=currency,
            currency_symbol=currency_symbol,
            period_start=period_start,
            period_end=period_end,
            raw_file_name=os.path.basename(file_path),
            bank_institution=bank_name
        )

        return metadata, transactions

    @staticmethod
    def _clean_merchant_name(description: str) -> str:
        """Strip location codes, card terminals, store numbers, and transaction IDs."""
        text = description.strip()

        # UPI Merchant Extraction
        upi_match = re.search(r'UPI/(?:DR|CR)/\d+/([^/]+)', text, re.I)
        if upi_match:
            return upi_match.group(1).replace('-', ' ').strip().title()

        upi_match2 = re.search(r'UPI/\d+/([^/]+)', text, re.I)
        if upi_match2:
            return upi_match2.group(1).replace('-', ' ').strip().title()

        upi_match3 = re.search(r'UPI/([A-Za-z0-9_-]+)/', text, re.I)
        if upi_match3:
            return upi_match3.group(1).replace('-', ' ').strip().title()

        # Clean NEFT, IMPS, RTGS, Transfer-INB
        text = re.sub(r'^(?:NEFT|IMPS|RTGS)[-\s:]*(?:[A-Z0-9]+)?\s*', '', text, flags=re.I)
        text = re.sub(r'^(?:TO|BY)\s+TRANSFER-(?:INB|UPI|NEFT|RTGS)\s*', '', text, flags=re.I)
        text = re.sub(r'^(?:TO|BY)\s+TRANSFER\s+', '', text, flags=re.I)
        text = re.sub(r'^TRANSFER\s+FROM\s+', '', text, flags=re.I)
        if re.search(r'^ATM\s+WDL', text, re.I):
            return "ATM Cash Withdrawal"

        # Remove common prefixes
        text = re.sub(r'^(POS DEBIT|CHECKCARD|PURCHASE AUTHORIZED ON \d\d/\d\d|PURCHASE|DEBIT CARD PURCHASE|RECURRING PAYMENT|CHECK #\d+|WITHDRAWAL|DIRECT DEP)\s*', '', text, flags=re.I)
        # Remove trailing terminal / location / store codes
        text = re.sub(r'\s+#\d+.*$', '', text)
        text = re.sub(r'\s+\d{3,}-\d{3,}.*$', '', text)
        text = re.sub(r'\s+[A-Z]{2}\s+\d{5,6}.*$', '', text)
        text = re.sub(r'\s+(STORE|SHOP|LOC|TERMINAL)\s*\d+.*$', '', text, flags=re.I)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if text else description
