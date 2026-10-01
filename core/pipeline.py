"""
End-to-End Statement Processing Pipeline.
Orchestrates Drive download, statement parsing, hygiene, categorization,
recurring detection, financial analysis, and report generation.
"""

import os
from typing import List, Tuple, Optional, Dict, Any

from core.models import AnalysisReport, Transaction, StatementMetadata
from core.drive_downloader import GoogleDriveDownloader
from core.parsers import parse_statement_file
from core.hygiene import TransactionHygiene
from core.categorizer import ExpenseCategorizer
from core.analyst import StatementAnalyst


class SpendingAnalysisPipeline:
    """Master pipeline for the Bank Statement Spending Analyst Agent."""

    def __init__(self, download_dir: str = "downloads"):
        self.downloader = GoogleDriveDownloader(download_dir=download_dir)
        self.hygiene = TransactionHygiene()
        self.categorizer = ExpenseCategorizer()
        self.analyst = StatementAnalyst()

    def process_files(self, file_paths: List[str], password: Optional[str] = None) -> Tuple[AnalysisReport, List[Transaction], str]:
        """
        Process a list of local statement files (PDF, CSV, XLSX).
        Returns:
            Tuple[AnalysisReport, List[Transaction], str]:
            (AnalysisReport, All Cleaned Transactions, Markdown Report Text)
        """
        all_transactions: List[Transaction] = []
        all_metadata: List[StatementMetadata] = []

        for fpath in file_paths:
            if not os.path.exists(fpath):
                continue
            meta, tx_list = parse_statement_file(fpath, password=password)
            all_metadata.append(meta)
            all_transactions.extend(tx_list)

        if not all_transactions:
            raise ValueError("No valid transactions could be extracted from the provided files.")

        # 1. Hygiene & De-duplication
        active_txs, excluded_txs, stats = self.hygiene.clean_transactions(all_transactions)

        # 2. Categorization
        categorized_txs = self.categorizer.categorize_all(active_txs)

        # 3. Financial Analysis & Report Generation
        report = self.analyst.analyze(categorized_txs, all_metadata, hygiene_stats=stats)

        # 4. Generate Markdown
        markdown_text = self.analyst.format_markdown_report(report)

        return report, categorized_txs, markdown_text

    def process_google_drive(self, drive_url: str, password: Optional[str] = None) -> Tuple[Optional[AnalysisReport], List[Transaction], Optional[str], Optional[str]]:
        """
        Download from Google Drive link and execute pipeline.
        Returns:
            Tuple[Optional[AnalysisReport], List[Transaction], Optional[str], Optional[str]]:
            (Report, Transactions, MarkdownText, Error/Permission Message)
        """
        files, err = self.downloader.fetch_from_url(drive_url)
        if err or not files:
            return None, [], None, err

        try:
            report, txs, md_text = self.process_files(files, password=password)
            return report, txs, md_text, None
        except Exception as e:
            return None, [], None, str(e)

