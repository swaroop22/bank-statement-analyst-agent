"""
Unit tests for Bank Statement Spending Analyst Agent.
Validates extraction, hygiene, categorization schema, 100% sum checksum, and redaction guardrails.
"""

import pytest
import os
from core.models import Transaction, TransactionType, SpendingCategory
from core.parsers.csv_excel_parser import CsvExcelParser
from core.hygiene import TransactionHygiene
from core.categorizer import ExpenseCategorizer
from core.analyst import StatementAnalyst
from core.pipeline import SpendingAnalysisPipeline


@pytest.fixture
def sample_dir():
    return os.path.join(os.path.dirname(__file__), "..", "samples")


def test_csv_parser(sample_dir):
    parser = CsvExcelParser()
    checking_file = os.path.join(sample_dir, "chase_checking_oct2024_act4812.csv")
    assert os.path.exists(checking_file), "Sample checking file should exist"

    metadata, txs = parser.parse(checking_file)
    assert len(txs) > 10
    assert metadata.currency == "USD"
    assert "4812" in metadata.account_number_masked

    # Dates should be YYYY-MM-DD
    for t in txs:
        assert len(t.date) == 10
        assert t.date.count("-") == 2
        assert t.amount > 0


def test_hygiene_and_transfers():
    hygiene = TransactionHygiene()

    # Create dummy transactions
    tx_normal = Transaction(
        id="1", date="2024-10-01", raw_description="SAFEWAY #123", clean_payee="Safeway",
        amount=50.0, type=TransactionType.DEBIT, account_source="Checking ...1234"
    )
    tx_payment = Transaction(
        id="2", date="2024-10-05", raw_description="AUTOMATIC PAYMENT - CHASE CARD", clean_payee="Chase Card",
        amount=450.0, type=TransactionType.DEBIT, account_source="Checking ...1234"
    )
    tx_transfer = Transaction(
        id="3", date="2024-10-06", raw_description="ONLINE TRANSFER TO SAVINGS", clean_payee="Transfer",
        amount=200.0, type=TransactionType.DEBIT, account_source="Checking ...1234"
    )

    active, excluded, stats = hygiene.clean_transactions([tx_normal, tx_payment, tx_transfer])
    assert len(active) == 1
    assert len(excluded) == 2
    assert stats["internal_transfers_excluded"] == 2
    assert active[0].id == "1"


def test_categorization_schema():
    categorizer = ExpenseCategorizer()

    samples = [
        ("RENT PAYMENT GREYSTAR", TransactionType.DEBIT, SpendingCategory.HOUSING_UTILITIES.value),
        ("TRADER JOES GROCERY", TransactionType.DEBIT, SpendingCategory.GROCERIES.value),
        ("DOORDASH DELIVERY", TransactionType.DEBIT, SpendingCategory.DINING_DELIVERY.value),
        ("UBER TRIP", TransactionType.DEBIT, SpendingCategory.TRANSPORTATION.value),
        ("CVS PHARMACY PRESCRIPTION", TransactionType.DEBIT, SpendingCategory.HEALTHCARE_MEDICAL.value),
        ("BEST BUY ELECTRONICS", TransactionType.DEBIT, SpendingCategory.SHOPPING_DISCRETIONARY.value),
        ("NETFLIX.COM", TransactionType.DEBIT, SpendingCategory.ENTERTAINMENT_SUBSCRIPTIONS.value),
        ("NELNET STUDENT LOAN", TransactionType.DEBIT, SpendingCategory.DEBT_SERVICE.value),
        ("ATM CASH WITHDRAWAL", TransactionType.DEBIT, SpendingCategory.MISCELLANEOUS_OTHER.value),
        ("ACME CORP PAYROLL", TransactionType.CREDIT, SpendingCategory.INCOME_INFLOWS.value),
    ]

    for desc, tx_type, expected_cat in samples:
        tx = Transaction(
            id="t", date="2024-10-01", raw_description=desc, clean_payee=desc,
            amount=100.0, type=tx_type, account_source="Checking ...1234"
        )
        cat = categorizer.categorize_transaction(tx)
        assert cat == expected_cat, f"Failed for {desc}: expected {expected_cat}, got {cat}"


def test_end_to_end_100_percent_checksum(sample_dir):
    pipeline = SpendingAnalysisPipeline()
    files = [
        os.path.join(sample_dir, "chase_checking_oct2024_act4812.csv"),
        os.path.join(sample_dir, "amex_credit_card_oct2024_act8821.csv")
    ]
    report, txs, md_text = pipeline.process_files(files)

    # Verify 100% sum
    total_pct = sum(b.percentage_of_spend for b in report.category_breakdowns)
    assert abs(total_pct - 100.0) < 0.1, f"Total percentage must sum to 100.0%, got {total_pct}"

    # Verify outflow equals sum of category spent
    sum_spent = sum(b.total_spent for b in report.category_breakdowns)
    assert abs(sum_spent - report.total_outflow) < 0.05

    # Verify redaction
    analyst = StatementAnalyst()
    redacted = analyst.redact_pii("Account 123456789012 and SSN 123-45-6789")
    assert "123456789012" not in redacted
    assert "123-45-6789" not in redacted
    assert "...9012" in redacted


def test_pdf_parser(sample_dir):
    from core.parsers.pdf_parser import PdfStatementParser
    pdf_path = os.path.join(sample_dir, "bank_of_america_checking_oct2024.pdf")
    assert os.path.exists(pdf_path), "Sample PDF statement should exist"

    parser = PdfStatementParser()
    meta, txs = parser.parse(pdf_path)

    assert meta.bank_institution == "Bank of America"
    assert "7724" in meta.account_number_masked
    assert len(txs) >= 10

    # Ensure internal transfer was recognized
    hygiene = TransactionHygiene()
    active, excluded, stats = hygiene.clean_transactions(txs)
    assert stats["internal_transfers_excluded"] >= 1

