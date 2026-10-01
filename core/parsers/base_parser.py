"""
Base parser interface for bank and credit card statements.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from core.models import StatementMetadata, Transaction


class BaseStatementParser(ABC):
    """Abstract base class for all file parsers."""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Return True if this parser supports the given file format."""
        pass

    @abstractmethod
    def parse(self, file_path: str, password: Optional[str] = None) -> Tuple[StatementMetadata, List[Transaction]]:
        """Parse the statement and return statement metadata and normalized transactions."""
        pass
