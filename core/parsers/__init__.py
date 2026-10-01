"""
Parser dispatcher for bank and credit card statements.
"""

import os
from typing import List, Tuple, Optional
from core.models import StatementMetadata, Transaction
from core.parsers.base_parser import BaseStatementParser
from core.parsers.csv_excel_parser import CsvExcelParser
from core.parsers.pdf_parser import PdfStatementParser

PARSERS: List[BaseStatementParser] = [
    CsvExcelParser(),
    PdfStatementParser(),
]


def parse_statement_file(file_path: str, password: Optional[str] = None) -> Tuple[StatementMetadata, List[Transaction]]:
    """Automatically select the right parser and extract metadata + transactions."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    for parser in PARSERS:
        if parser.can_parse(file_path):
            return parser.parse(file_path, password=password)

    raise ValueError(f"Unsupported file format for statement: {os.path.basename(file_path)}. Supported: PDF, CSV, XLSX, XLS.")
