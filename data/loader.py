"""
Historical Financial Data Loader.

Loads and validates Income Statement, Balance Sheet, and Cash Flow data from CSV files
or from Yahoo Finance using yfinance.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class HistoricalStatement:
    """Container for historical financial statement data."""
    periods: List[str] = field(default_factory=list)
    data: Dict[str, List[float]] = field(default_factory=dict)
    
    def get_value(self, line_item: str, period: str) -> float:
        """Get a specific value from the statement."""
        if period not in self.periods:
            raise ValueError(f"Period '{period}' not found in statement")
        if line_item not in self.data:
            raise ValueError(f"Line item '{line_item}' not found in statement")
        period_idx = self.periods.index(period)
        return self.data[line_item][period_idx]


@dataclass
class HistoricalData:
    """Container for all historical financial statements."""
    income_statement: Optional[HistoricalStatement] = None
    balance_sheet: Optional[HistoricalStatement] = None
    cash_flow: Optional[HistoricalStatement] = None


class DataLoader:
    """
    Loads and validates historical financial data from CSV files or Yahoo Finance.
    
    Supports two modes:
    1. CSV mode: Provide a directory path containing CSV files
    2. yfinance mode: Provide a ticker symbol (e.g., "AAPL") to fetch from Yahoo Finance
    """
    
    # Required columns for each statement type
    REQUIRED_INCOME_STATEMENT_COLS = [
        "Revenue", "COGS", "Operating Expenses", "Depreciation", 
        "Interest Expense", "Tax Expense", "Net Income"
    ]
    
    REQUIRED_BALANCE_SHEET_COLS = [
        "Cash", "Accounts Receivable", "Inventory", "PP&E", "Accounts Payable",
        "Debt", "Equity", "Retained Earnings"
    ]
    
    REQUIRED_CASH_FLOW_COLS = [
        "Net Income", "Depreciation", "Change in AR", "Change in Inventory",
        "Change in AP", "CapEx", "Operating Cash Flow"
    ]
    
    def __init__(self, data_source: Union[Path, str], period: str = "quarterly"):
        """
        Initialize the data loader.
        
        Args:
            data_source: Either:
                - Path to directory containing CSV files, OR
                - Ticker symbol (e.g., "AAPL") to fetch from Yahoo Finance
            period: For yfinance mode, "quarterly" or "annual" (default: "quarterly")
            
        Raises:
            FileNotFoundError: If CSV directory does not exist
            ImportError: If yfinance is required but not installed
        """
        self.data_source = data_source
        self.period = period
        self.use_yfinance = False
        
        # Detect if data_source is a ticker symbol or a path
        if isinstance(data_source, str):
            # Check if it looks like a ticker (short uppercase string, no path separators)
            path_obj = Path(data_source)
            if not path_obj.exists() and len(data_source) <= 10 and data_source.isupper():
                # Likely a ticker symbol
                self.use_yfinance = True
                self.ticker_symbol = data_source
            else:
                # Treat as path
                data_source = path_obj
        
        if isinstance(data_source, Path):
            if not data_source.exists():
                raise FileNotFoundError(f"Data directory not found: {data_source}")
            self.data_dir = Path(data_source)
        elif self.use_yfinance:
            # Will be handled in load_all
            pass
        else:
            raise ValueError(
                f"Invalid data_source: {data_source}. "
                "Must be a Path object, directory path, or ticker symbol."
            )
    
    def load_all(self) -> HistoricalData:
        """
        Load all historical financial statements.
        
        Returns:
            HistoricalData object containing all statements
            
        Raises:
            FileNotFoundError: If required CSV files are missing
            ValueError: If CSV files have invalid schema or missing columns
            RuntimeError: If yfinance data cannot be fetched
        """
        if self.use_yfinance:
            return self._load_from_yfinance()
        else:
            return self._load_from_csv()
    
    def _load_from_yfinance(self, quiet: bool = False) -> HistoricalData:
        """Load data from Yahoo Finance using yfinance."""
        from data.yfinance_loader import YFinanceLoader
        
        yf_loader = YFinanceLoader(self.ticker_symbol, self.period)
        return yf_loader.load_all(quiet=quiet)
    
    def _load_from_csv(self) -> HistoricalData:
        """Load data from CSV files."""
        historical_data = HistoricalData()
        
        # Load Income Statement
        income_file = self.data_dir / "income_statement.csv"
        if income_file.exists():
            historical_data.income_statement = self._load_statement(
                income_file, 
                self.REQUIRED_INCOME_STATEMENT_COLS,
                "Income Statement"
            )
        else:
            raise FileNotFoundError(
                f"Income Statement file not found: {income_file}"
            )
        
        # Load Balance Sheet
        balance_file = self.data_dir / "balance_sheet.csv"
        if balance_file.exists():
            historical_data.balance_sheet = self._load_statement(
                balance_file,
                self.REQUIRED_BALANCE_SHEET_COLS,
                "Balance Sheet"
            )
        else:
            raise FileNotFoundError(
                f"Balance Sheet file not found: {balance_file}"
            )
        
        # Load Cash Flow (optional for historical, but validate if present)
        cash_flow_file = self.data_dir / "cash_flow.csv"
        if cash_flow_file.exists():
            historical_data.cash_flow = self._load_statement(
                cash_flow_file,
                self.REQUIRED_CASH_FLOW_COLS,
                "Cash Flow"
            )
        
        return historical_data
    
    def _load_statement(self, file_path: Path, required_cols: List[str], 
                       statement_name: str) -> HistoricalStatement:
        """
        Load a single financial statement from CSV.
        
        Args:
            file_path: Path to CSV file
            required_cols: List of required column names
            statement_name: Name of statement for error messages
            
        Returns:
            HistoricalStatement object
            
        Raises:
            ValueError: If schema is invalid or columns are missing
        """
        statement = HistoricalStatement()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Get all column names
            all_cols = reader.fieldnames
            if not all_cols:
                raise ValueError(f"{statement_name}: CSV file has no columns")
            
            # First column should be period identifier
            period_col = all_cols[0]
            
            # Validate required columns exist
            missing_cols = [col for col in required_cols if col not in all_cols]
            if missing_cols:
                raise ValueError(
                    f"{statement_name}: Missing required columns: {missing_cols}"
                )
            
            # Initialize data structure
            for col in required_cols:
                statement.data[col] = []
            
            # Read rows
            for row in reader:
                period = row[period_col].strip()
                if not period:
                    raise ValueError(f"{statement_name}: Empty period identifier found")
                
                statement.periods.append(period)
                
                # Parse numeric values
                for col in required_cols:
                    value_str = row.get(col, "").strip()
                    if not value_str:
                        raise ValueError(
                            f"{statement_name}: Missing value for {col} in period {period}"
                        )
                    try:
                        value = float(value_str.replace(",", "").replace("$", ""))
                        statement.data[col].append(value)
                    except ValueError as e:
                        raise ValueError(
                            f"{statement_name}: Invalid numeric value for {col} "
                            f"in period {period}: {value_str}"
                        ) from e
        
        if not statement.periods:
            raise ValueError(f"{statement_name}: No data rows found in CSV")
        
        return statement

