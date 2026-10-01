"""
PDF Bank & Credit Card Statement Parser.
Extracts statement period, account metadata, masks sensitive identifiers,
and extracts tabular transactions using structured text analysis.
"""

import os
import re
from typing import List, Tuple, Optional
from datetime import datetime
from pypdf import PdfReader

from core.parsers.base_parser import BaseStatementParser
from core.models import (
    StatementMetadata,
    Transaction,
    AccountType,
    TransactionType,
    SpendingCategory
)


class PdfStatementParser(BaseStatementParser):
    """Parser for PDF bank and credit card statements."""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith('.pdf')

    def parse(self, file_path: str, password: Optional[str] = None) -> Tuple[StatementMetadata, List[Transaction]]:
        reader = PdfReader(file_path)

        # Handle password-protected / encrypted PDFs
        if reader.is_encrypted:
            decrypted = False
            if password:
                for cand in [password, password.strip(), password.upper(), password.lower()]:
                    try:
                        res = reader.decrypt(cand)
                        if res != 0:
                            # Verify decryption by reading pages
                            _ = len(reader.pages)
                            decrypted = True
                            break
                    except Exception:
                        pass

            if not decrypted:
                raise ValueError(
                    f"File '{os.path.basename(file_path)}' is password-protected (encrypted).\n"
                    "For State Bank of India (SBI) statements, please enter your password:\n"
                    "• 11-digit SBI Account Number\n"
                    "• Date of Birth in DDMMYYYY format (e.g. 15081995)\n"
                    "• Last 5 digits of registered mobile + DOB in DDMM format (e.g. 123451508)\n"
                    "• PAN Card Number in UPPERCASE\n"
                    "Please enter your statement password in the password field to decrypt."
                )

        full_text = ""
        page_texts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            page_texts.append(t)
            full_text += t + "\n"

        metadata = self._extract_metadata(file_path, full_text)
        transactions = self._extract_transactions(full_text, metadata, page_texts=page_texts)

        # Update period start and end from actual transactions if found
        if transactions:
            tx_dates = [t.date for t in transactions if t.date]
            if tx_dates:
                if not metadata.period_start:
                    metadata.period_start = min(tx_dates)
                if not metadata.period_end:
                    metadata.period_end = max(tx_dates)

        return metadata, transactions


    def _extract_metadata(self, file_path: str, text: str) -> StatementMetadata:
        filename = os.path.basename(file_path).lower()
        
        # Bank institution detection
        bank_name = "Financial Institution"
        if re.search(r'state\s+bank\s+of\s+india|\bsbi\b|sbin\d{7}', text, re.I) or "sbi" in filename or filename.startswith("721371"):
            bank_name = "State Bank of India"
        elif re.search(r'chase|jpmorgan', text, re.I) or "chase" in filename:
            bank_name = "Chase"
        elif re.search(r'bank\s+of\s+america|bofa', text, re.I) or "bofa" in filename:
            bank_name = "Bank of America"
        elif re.search(r'wells\s+fargo', text, re.I) or "wells" in filename:
            bank_name = "Wells Fargo"
        elif re.search(r'american\s+express|amex', text, re.I) or "amex" in filename:
            bank_name = "American Express"
        elif re.search(r'citibank|citi', text, re.I) or "citi" in filename:
            bank_name = "Citibank"
        elif re.search(r'capital\s+one', text, re.I) or "capital" in filename:
            bank_name = "Capital One"

        # Account Type detection
        account_type = AccountType.UNKNOWN
        if re.search(r'savings?\s+(?:bank\s+)?accounts?|\bsaving\s+account\b|\bsb\s+a/c\b', text, re.I) or "saving" in filename:
            account_type = AccountType.SAVINGS
        elif re.search(r'credit\s+card|cardmember|rewards|sapphire|sbi\s*card', text, re.I) or "credit" in filename or "card" in filename:
            account_type = AccountType.CREDIT_CARD
        elif re.search(r'current\s+account', text, re.I):
            account_type = AccountType.CHECKING
        elif re.search(r'checking\s+account|total\s+checking', text, re.I) or "checking" in filename:
            account_type = AccountType.CHECKING
        else:
            account_type = AccountType.SAVINGS if bank_name == "State Bank of India" else AccountType.CHECKING

        # Masked Account Number
        acct_match = re.search(r'(?:account\s*(?:number|no)?|ending\s+in|a/c\s*(?:no)?|act#?)[\s:]*(?:x+|[*]+|[0-9]{4,15})*(\d{4})', text, re.I)
        last4 = acct_match.group(1) if acct_match else "XXXX"
        if last4 == "XXXX" and re.search(r'\b\d{11}\b', text):
            # 11-digit SBI account number
            acct_11 = re.search(r'\b\d{7}(\d{4})\b', text)
            if acct_11:
                last4 = acct_11.group(1)

        source_label = f"{bank_name} {account_type.value} ...{last4}"

        # Currency
        currency = "USD"
        currency_symbol = "$"
        if "₹" in text or "inr" in text.lower() or "rs." in text.lower() or bank_name == "State Bank of India":
            currency = "INR"
            currency_symbol = "₹"
        elif "£" in text or "GBP" in text:
            currency = "GBP"
            currency_symbol = "£"
        elif "€" in text or "EUR" in text:
            currency = "EUR"
            currency_symbol = "€"
        elif "CAD" in text or "C$" in text:
            currency = "CAD"
            currency_symbol = "C$"

        # Statement Period
        period_start = None
        period_end = None

        # Check for SBI "As on DD-MM-YY" and "Opening Balance on DD-MM-YY"
        m_as_on = re.search(r"As on (\d{2}-\d{2}-\d{2})", text)
        if m_as_on:
            d, m, y = m_as_on.group(1).split("-")
            period_end = f"20{y}-{m}-{d}"
        m_open = re.search(r"Opening Balance on (\d{2}-\d{2}-\d{2})", text)
        if m_open:
            d, m, y = m_open.group(1).split("-")
            period_start = f"20{y}-{m}-{d}"

        period_match = re.search(r'(?:statement\s+period|billing\s+cycle|period|date\s*:)[\s:]*([A-Za-z0-9\s,/-]+?)\s*(?:through|to|-)\s*([A-Za-z0-9\s,/-]+)', text, re.I)
        if period_match and not period_start:
            period_start = self._standardize_date_str(period_match.group(1), currency)
            period_end = self._standardize_date_str(period_match.group(2), currency)

        return StatementMetadata(
            account_name=f"{bank_name} {account_type.value}",
            account_type=account_type,
            account_number_masked=last4,
            currency=currency,
            currency_symbol=currency_symbol,
            period_start=period_start,
            period_end=period_end,
            raw_file_name=os.path.basename(file_path),
            bank_institution=bank_name
        )

    def _extract_transactions(self, text: str, metadata: StatementMetadata, page_texts: Optional[List[str]] = None) -> List[Transaction]:
        # Branch 1: State Bank of India multi-column table layout
        sbi_date_start = re.compile(r"^(\d{2}-\d{2}-\d{2})\s+(.*)$")
        sbi_amt_end = re.compile(r"^(.*?)\s+(?:([0-9,]+\.\d{2})|-)\s+(?:([0-9,]+\.\d{2})|-)\s+([0-9,]+\.\d{2})$")
        
        pages_to_check = page_texts if page_texts else [text]
        sbi_transactions: List[Transaction] = []

        for p_txt in pages_to_check:
            acct_last4 = metadata.account_number_masked
            m_acct = re.search(r"SAVING ACCOUNT\s+XXXXXXX(\d{4})", p_txt)
            if m_acct:
                acct_last4 = m_acct.group(1)
            acct_source = f"{metadata.bank_institution} {metadata.account_type.value} ...{acct_last4}"

            p_lines = [l.strip() for l in p_txt.splitlines() if l.strip()]
            i = 0
            while i < len(p_lines):
                l = p_lines[i]
                m_dt = sbi_date_start.match(l)
                if m_dt:
                    dt_str, rest = m_dt.groups()
                    d, m, y = dt_str.split("-")
                    iso_date = f"20{y}-{m}-{d}"
                    m_amt = sbi_amt_end.match(rest)
                    raw_desc, cr, dr, bal = None, None, None, None
                    if m_amt:
                        raw_desc, cr, dr, bal = m_amt.groups()
                    elif i + 1 < len(p_lines):
                        m_next = sbi_amt_end.match(p_lines[i+1])
                        if m_next:
                            raw_desc = (rest + " " + m_next.groups()[0])
                            cr, dr, bal = m_next.groups()[1:]
                            i += 1
                    if raw_desc and (cr or dr):
                        raw_desc = raw_desc.rstrip("- ").strip()
                        if cr:
                            val = float(cr.replace(",", ""))
                            tx_type = TransactionType.CREDIT
                        else:
                            val = float(dr.replace(",", ""))
                            tx_type = TransactionType.DEBIT

                        clean_merchant = self._clean_merchant_name(raw_desc)
                        sbi_transactions.append(Transaction(
                            id=f"tx_{iso_date}_{len(sbi_transactions)}_{val}",
                            date=iso_date,
                            raw_description=raw_desc,
                            clean_payee=clean_merchant,
                            amount=round(val, 2),
                            type=tx_type,
                            account_source=acct_source,
                            category=SpendingCategory.UNCATEGORIZED.value
                        ))
                i += 1

        if sbi_transactions:
            return sbi_transactions

        # Branch 2: Standard US / International Single & Multi-Line Statements
        transactions = []
        lines = text.splitlines()

        year = "2024"
        if metadata.period_start:
            year = metadata.period_start[:4]
        else:
            year_match = re.search(r'\b(202[0-9])\b', text)
            if year_match:
                year = year_match.group(1)

        is_indian = (metadata.currency == "INR" or metadata.bank_institution == "State Bank of India")

        date_pattern_str = r'(\d{1,2}(?:[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{2,4}|[/-]\d{1,2}(?:[/-]\d{2,4})?))'
        
        tx_pattern_a = re.compile(
            rf'^\s*{date_pattern_str}(?:\s+{date_pattern_str})?\s+(.*?)\s+([-+]?[₹$Rs\.]*[0-9,]+\.\d{{2}})(?:\s+([-+]?[₹$Rs\.]*[0-9,]+\.\d{{2}}))?(?:\s+([-+]?[₹$Rs\.]*[0-9,]+\.\d{{2}}))?\s*$',
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if any(skip in line_str.lower() for skip in ['page ', 'balance summary', 'interest charge', 'total fees', 'account summary', 'statement period', 'opening balance', 'closing balance']):
                continue

            match = tx_pattern_a.match(line_str)
            if match:
                groups = match.groups()
                raw_date = groups[0]
                raw_desc = groups[2]
                amt1 = groups[3]
                amt2 = groups[4]
                amt3 = groups[5]

                if any(k in raw_desc.lower() for k in ['previous balance', 'ending balance', 'new balance', 'total credit', 'minimum payment', 'carried forward']):
                    continue

                raw_amt = amt1
                tx_type_override = None

                if amt3:
                    if amt1 and amt1 != '0.00':
                        raw_amt = amt1
                        tx_type_override = TransactionType.DEBIT
                    elif amt2 and amt2 != '0.00':
                        raw_amt = amt2
                        tx_type_override = TransactionType.CREDIT
                elif amt2:
                    raw_amt = amt1
                
                tx = self._build_tx(raw_date, raw_desc, raw_amt, year, metadata, tx_type_override=tx_type_override)
                if tx:
                    transactions.append(tx)

        # Fallback multi-line staggered layout
        if not transactions:
            date_re = re.compile(rf'^{date_pattern_str}$', re.IGNORECASE)
            amt_re = re.compile(r'^[-+]?[₹$Rs\.]*[0-9,]+\.\d{2}$')

            i = 0
            while i < len(lines):
                line_i = lines[i].strip()
                if date_re.match(line_i):
                    raw_date = line_i
                    if i + 1 < len(lines):
                        raw_desc = lines[i + 1].strip()
                        if i + 2 < len(lines):
                            amt_match = amt_re.match(lines[i + 2].strip())
                            if amt_match:
                                raw_amt = lines[i + 2].strip()
                                tx = self._build_tx(raw_date, raw_desc, raw_amt, year, metadata)
                                if tx:
                                    transactions.append(tx)
                                i += 3
                                continue
                i += 1

        return transactions


    def _build_tx(self, raw_date: str, raw_desc: str, raw_amt: str, year: str, metadata: StatementMetadata, tx_type_override: Optional[TransactionType] = None) -> Optional[Transaction]:
        clean_date = self._parse_pdf_date(raw_date, year, is_indian=(metadata.currency == "INR"))
        if not clean_date:
            return None

        amt_str = raw_amt.replace('$', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').replace(',', '').strip()
        try:
            val = float(amt_str)
        except ValueError:
            return None

        amount = abs(val)

        if tx_type_override:
            tx_type = tx_type_override
        else:
            # Check description indicators
            desc_lower = raw_desc.lower()
            is_credit_signal = any(
                sig in desc_lower for sig in [
                    'upi/cr', '/cr/', 'by transfer', 'credit', 'refund', 'deposit', 
                    'salary', 'interest paid', 'cashback', 'reversal', 'ach credit', 'zelle from'
                ]
            ) or '(cr)' in desc_lower or desc_lower.endswith(' cr')

            is_debit_signal = any(
                sig in desc_lower for sig in [
                    'upi/dr', '/dr/', 'to transfer', 'debit', 'atm wdl', 'pos', 'purchase',
                    'withdrawal', 'payment to', 'fee', 'charge'
                ]
            ) or '(dr)' in desc_lower or desc_lower.endswith(' dr')

            if metadata.account_type == AccountType.CREDIT_CARD:
                if is_credit_signal or val < 0:
                    tx_type = TransactionType.CREDIT
                else:
                    tx_type = TransactionType.DEBIT
            else:
                if is_credit_signal:
                    tx_type = TransactionType.CREDIT
                elif is_debit_signal or val < 0:
                    tx_type = TransactionType.DEBIT
                else:
                    tx_type = TransactionType.DEBIT

        clean_payee = self._clean_merchant_name(raw_desc)
        account_source = f"{metadata.bank_institution} {metadata.account_type.value} ...{metadata.account_number_masked}"

        return Transaction(
            id=f"tx_{clean_date}_{abs(hash(raw_desc + str(amount))) % 1000000}",
            date=clean_date,
            raw_description=raw_desc,
            clean_payee=clean_payee,
            amount=round(amount, 2),
            type=tx_type,
            account_source=account_source,
            category=SpendingCategory.UNCATEGORIZED.value
        )


    def _parse_pdf_date(self, date_str: str, year: str, is_indian: bool = False) -> Optional[str]:
        date_str = date_str.strip()
        
        # Check DD Mon YYYY / DD-Mon-YYYY format (e.g. 15 Oct 2023, 15-Oct-2023)
        mon_match = re.match(r'^(\d{1,2})[-\s]([A-Za-z]{3})[-\s]?(\d{2,4})?$', date_str)
        if mon_match:
            d, mon, y = mon_match.groups()
            y = y or year
            if len(y) == 2:
                y = f"20{y}"
            try:
                dt = datetime.strptime(f"{d} {mon} {y}", "%d %b %Y")
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        parts = re.split(r'[/-]', date_str)
        if len(parts) == 2:
            p1, p2 = int(parts[0]), int(parts[1])
            if is_indian or p1 > 12:
                # DD/MM
                return f"{year}-{p2:02d}-{p1:02d}"
            else:
                # MM/DD
                return f"{year}-{p1:02d}-{p2:02d}"
        elif len(parts) == 3:
            p1, p2, y = parts
            if len(y) == 2:
                y = f"20{y}"
            val1, val2 = int(p1), int(p2)
            if is_indian or val1 > 12:
                # DD/MM/YYYY (Indian standard)
                return f"{y}-{val2:02d}-{val1:02d}"
            else:
                # MM/DD/YYYY
                return f"{y}-{val1:02d}-{val2:02d}"
        return None

    def _standardize_date_str(self, date_str: str, currency: str = "USD") -> Optional[str]:
        date_str = date_str.strip().replace(',', '')
        is_indian = (currency == "INR")
        
        formats = [
            "%d/%m/%Y" if is_indian else "%m/%d/%Y",
            "%d-%m-%Y" if is_indian else "%m-%d-%Y",
            "%d %b %Y", "%d %B %Y",
            "%B %d %Y", "%b %d %Y",
            "%Y-%m-%d"
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
        return None

    @staticmethod
    def _clean_merchant_name(description: str) -> str:
        text = description.strip()

        # Clean Indian UPI transactions:
        # Format 1: UPI/DR/428491829102/ZOMATO/ICIC/zomato@icici
        # Format 2: UPI/329482938492/SWIGGY/HDFC/...
        # Format 3: UPI/SWIGGY/428941/...
        upi_match = re.search(r'UPI/(?:DR|CR)/\d+/([^/]+)', text, re.I)
        if upi_match:
            return upi_match.group(1).replace('-', ' ').strip().title()

        upi_match2 = re.search(r'UPI/\d+/([^/]+)', text, re.I)
        if upi_match2:
            return upi_match2.group(1).replace('-', ' ').strip().title()

        upi_match3 = re.search(r'UPI/([A-Za-z0-9_-]+)/', text, re.I)
        if upi_match3:
            return upi_match3.group(1).replace('-', ' ').strip().title()

        # Clean Indian Cheque & NEFT patterns
        chq_match = re.search(r'Chq No\.?\s*\d+\s+[A-Z0-9]+\s+([A-Za-z\s]+?)(?:\s+\d+|$)', text, re.I)
        if chq_match and chq_match.group(1).strip():
            return chq_match.group(1).strip().title()

        if re.search(r'(?:NEFT\s+UTR\s+)?NO:\s*SBIN', text, re.I):
            return "NEFT Transfer"

        if re.search(r'TRANSFER\s+TO\b', text, re.I):
            return "Bank Account Transfer"

        if re.search(r'Transfer through GCC', text, re.I):
            return "GCC Bank Transfer"

        if re.search(r'IMPS.*HDFC', text, re.I):
            return "HDFC Bank Transfer (IMPS)"

        # Clean NEFT, IMPS, RTGS, Transfer-INB
        text = re.sub(r'^(?:NEFT|IMPS|RTGS)[-\s:]*(?:[A-Z0-9]+)?\s*', '', text, flags=re.I)
        text = re.sub(r'^(?:TO|BY)\s+TRANSFER-(?:INB|UPI|NEFT|RTGS)\s*', '', text, flags=re.I)
        text = re.sub(r'^(?:TO|BY)\s+TRANSFER\s+', '', text, flags=re.I)
        text = re.sub(r'^TRANSFER\s+FROM\s+', '', text, flags=re.I)
        # Clean Indian SBI POS transactions:
        pos_match = re.search(r'(?:OTHPOS|SBIPOS)\d+(.*?)(?:HYDERABAD|AHMED|MUMBAI|RANGA|\s{2,}|$)', text, re.I)
        if pos_match and pos_match.group(1).strip():
            return pos_match.group(1).strip().title()

        if re.search(r'^ATM CASH', text, re.I):
            return "ATM Cash Withdrawal"

        if re.search(r'^CASH WITHDRAWAL BY CHQ', text, re.I):
            return "Cash Withdrawal (Cheque)"

        if re.search(r'^CHEQUE TRANSFER TO', text, re.I):
            return "Cheque Transfer"

        if re.search(r'^LOCKER RENT', text, re.I):
            return "SBI Safe Deposit Locker Rent"

        if re.search(r'^INTEREST CREDIT', text, re.I):
            return "SBI Savings Interest Credit"

        if re.search(r'for loan against gold', text, re.I):
            return "SBI Gold Loan Service"

        if re.search(r'TDS 194N ON CASH WDL', text, re.I):
            return "TDS on Cash Withdrawal"

        # US/International prefixes
        text = re.sub(r'^(POS DEBIT|CHECKCARD|PURCHASE|DEBIT CARD PURCHASE|CHECK #\d+|ACH)\s*', '', text, flags=re.I)
        text = re.sub(r'\s+#\d+.*$', '', text)
        text = re.sub(r'\s+[A-Z]{2}\s+\d{5,6}.*$', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if text else description

