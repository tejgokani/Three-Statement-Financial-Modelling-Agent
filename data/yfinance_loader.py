"""
Yahoo Finance Data Loader.

Fetches historical financial statements from Yahoo Finance using yfinance.
Maps yfinance column names to our expected format.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import yfinance as yf
except ImportError:
    yf = None

from data.loader import HistoricalStatement, HistoricalData


class YFinanceLoader:
    """Loads financial data from Yahoo Finance using yfinance."""
    
    # Mapping from yfinance line item names to our expected names
    INCOME_STATEMENT_MAPPING = {
        # Revenue - multiple variations
        "Total Revenue": "Revenue",
        "Revenue": "Revenue",
        "Operating Revenue": "Revenue",
        "Total Operating Revenue": "Revenue",
        "Net Sales": "Revenue",
        "Sales Revenue": "Revenue",
        # COGS - multiple variations
        "Cost Of Goods Sold": "COGS",
        "Cost Of Revenue": "COGS",
        "Reconciled Cost Of Revenue": "COGS",
        "Cost Of Sales": "COGS",
        "Cost Of Goods And Services Sold": "COGS",
        # Operating Expenses - multiple variations
        "Operating Expense": "Operating Expenses",
        "Operating Expenses": "Operating Expenses",
        "Total Operating Expenses": "Operating Expenses",
        "Total Expenses": "Operating Expenses",
        "Operating Costs": "Operating Expenses",
        "Selling General And Administration": "Operating Expenses",
        "Research And Development": "Operating Expenses",
        # Depreciation - multiple variations
        "Depreciation And Amortization": "Depreciation",
        "Depreciation": "Depreciation",
        "Reconciled Depreciation": "Depreciation",
        "Depreciation Amortization Depletion": "Depreciation",
        "Depreciation Amortization Depletion Income Statement": "Depreciation",
        # Interest - multiple variations
        "Interest Expense": "Interest Expense",
        "Interest Income": "Interest Expense",  # Will be negative if it's income
        "Other Income Expense": "Interest Expense",  # May include interest
        "Other Non Operating Income Expenses": "Interest Expense",
        "Net Interest Income": "Interest Expense",
        # Tax - multiple variations
        "Tax Provision": "Tax Expense",
        "Tax Expense": "Tax Expense",
        "Income Tax Expense": "Tax Expense",
        "Provision For Income Taxes": "Tax Expense",
        # Net Income - multiple variations
        "Net Income": "Net Income",
        "Net Income Common Stockholders": "Net Income",
        "Net Income From Continuing Operation Net Minority Interest": "Net Income",
        "Net Income From Continuing And Discontinued Operation": "Net Income",
        "Net Income Continuous Operations": "Net Income",
    }
    
    BALANCE_SHEET_MAPPING = {
        # Cash - multiple variations
        "Cash And Cash Equivalents": "Cash",
        "Cash": "Cash",
        "Cash Cash Equivalents And Short Term Investments": "Cash",
        "Cash And Short Term Investments": "Cash",
        "Cash Equivalents": "Cash",
        "Cash And Due From Banks": "Cash",  # Banks
        "Cash Cash Equivalents And Marketable Securities": "Cash",
        # Accounts Receivable - multiple variations
        "Accounts Receivable": "Accounts Receivable",
        "Net Receivables": "Accounts Receivable",
        "Accounts Receivable Net": "Accounts Receivable",
        "Trade And Other Receivables": "Accounts Receivable",
        "Accounts Receivable Gross": "Accounts Receivable",
        "Receivables": "Accounts Receivable",
        # Inventory - may not exist for service companies
        "Inventory": "Inventory",
        "Inventories": "Inventory",
        "Inventory Net": "Inventory",
        "Total Inventories": "Inventory",
        # PP&E - multiple variations
        "Property Plant Equipment": "PP&E",
        "Net PPE": "PP&E",
        "Property Plant And Equipment Net": "PP&E",
        "PPE Net": "PP&E",
        "Property Plant And Equipment": "PP&E",
        "Net Property Plant And Equipment": "PP&E",
        "Property Plant Equipment Gross": "PP&E",
        # Accounts Payable - multiple variations (may not exist for banks)
        "Accounts Payable": "Accounts Payable",
        "Trade And Other Payables": "Accounts Payable",
        "Accounts Payable And Accrued Expenses": "Accounts Payable",
        "Accounts Payable Trade": "Accounts Payable",
        "Payables": "Accounts Payable",
        "Trade Payables": "Accounts Payable",
        "Payables And Accrued Expenses": "Accounts Payable",  # Common in banks
        "Other Payable": "Accounts Payable",
        # Debt - multiple variations
        "Total Debt": "Debt",
        "Long Term Debt": "Debt",
        "Long Term Debt And Capital Lease Obligation": "Debt",
        "Total Debt Including Capital Lease Obligation": "Debt",
        "Short Term Debt": "Debt",
        "Total Debt Including Current": "Debt",
        "Long Term Debt And Capital Lease Obligation Excluding Current": "Debt",
        # Equity - multiple variations
        "Total Stockholders Equity": "Equity",
        "Stockholders Equity": "Equity",
        "Total Equity": "Equity",
        "Shareholders Equity": "Equity",
        "Common Stock Equity": "Equity",
        "Total Equity Gross Minority Interest": "Equity",
        "Stockholders Equity Including Minority Interest": "Equity",
        "Total Shareholders Equity": "Equity",
        # Retained Earnings - multiple variations
        "Retained Earnings": "Retained Earnings",
        "Retained Earnings Cumulative": "Retained Earnings",
        "Accumulated Retained Earnings Deficit": "Retained Earnings",
        "Gains Losses Not Affecting Retained Earnings": "Retained Earnings",  # Sometimes used as proxy
        "Retained Earnings Total": "Retained Earnings",
        "Accumulated Other Comprehensive Income": "Retained Earnings",  # Fallback if RE not available
    }
    
    CASH_FLOW_MAPPING = {
        "Net Income": "Net Income",
        "Net Income From Continuing Operations": "Net Income",
        "Depreciation And Amortization": "Depreciation",
        "Depreciation Amortization Depletion": "Depreciation",
        "Depreciation": "Depreciation",
        "Change In Receivables": "Change in AR",
        "Changes In Account Receivables": "Change in AR",
        "Change In Receivables": "Change in AR",
        "Change In Inventory": "Change in Inventory",
        "Change In Payables": "Change in AP",
        "Change In Payable": "Change in AP",
        "Change In Account Payable": "Change in AP",
        "Change In Payables And Accrued Expense": "Change in AP",
        "Capital Expenditure": "CapEx",
        "Capital Expenditures": "CapEx",
        "Purchase Of PPE": "CapEx",
        "Operating Cash Flow": "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities": "Operating Cash Flow",
        "Total Cash From Operating Activities": "Operating Cash Flow"
    }
    
    def __init__(self, ticker_symbol: str, period: str = "quarterly"):
        """
        Initialize the yfinance loader.
        
        Args:
            ticker_symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
            period: "quarterly" or "annual" - defaults to quarterly
            
        Raises:
            ImportError: If yfinance is not installed
        """
        if yf is None:
            raise ImportError(
                "yfinance is required for fetching data from Yahoo Finance. "
                "Install with: pip install yfinance"
            )
        
        if pd is None:
            raise ImportError(
                "pandas is required for yfinance integration. "
                "Install with: pip install pandas"
            )
        
        self.ticker_symbol = ticker_symbol.upper()
        self.ticker = yf.Ticker(ticker_symbol)
        self.period = period.lower()
        self._cached_info = None  # Cache for ticker info to avoid redundant calls
        
        if self.period not in ["quarterly", "annual"]:
            raise ValueError(f"Period must be 'quarterly' or 'annual', got '{period}'")
    
    def load_all(self, quiet: bool = False) -> HistoricalData:
        """
        Load all historical financial statements from Yahoo Finance.
        
        Args:
            quiet: If True, suppress print statements (useful for batch testing)
        
        Returns:
            HistoricalData object containing all statements
            
        Raises:
            RuntimeError: If data cannot be fetched or is incomplete
            ValueError: If required data is missing
        """
        # Validate ticker first - cache info to avoid redundant calls
        self._cached_info = None
        try:
            self._cached_info = self.ticker.info
            if not self._cached_info:
                raise RuntimeError(
                    f"Ticker {self.ticker_symbol} not found. "
                    f"Please verify the ticker symbol is correct."
                )
            if not quiet:
                company_name = self._cached_info.get('longName', self._cached_info.get('shortName', self.ticker_symbol))
                print(f"   Company: {company_name}")
        except Exception as e:
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                raise RuntimeError(
                    f"Ticker {self.ticker_symbol} not found or invalid. "
                    f"Please verify the ticker symbol is correct."
                ) from e
            # If info fetch fails, continue but it might be a data issue
        
        historical_data = HistoricalData()
        
        # Load Income Statement
        try:
            historical_data.income_statement = self._load_income_statement()
            if not quiet:
                print(f"   ✓ Income Statement: {len(historical_data.income_statement.periods)} periods loaded")
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(
                f"Failed to load Income Statement for {self.ticker_symbol}: {e}. "
                f"The company may not have sufficient financial data available."
            ) from e
        
        # Load Balance Sheet
        try:
            historical_data.balance_sheet = self._load_balance_sheet()
            if not quiet:
                print(f"   ✓ Balance Sheet: {len(historical_data.balance_sheet.periods)} periods loaded")
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(
                f"Failed to load Balance Sheet for {self.ticker_symbol}: {e}. "
                f"The company may not have sufficient financial data available."
            ) from e
        
        # Load Cash Flow (optional, but try to load if available)
        try:
            historical_data.cash_flow = self._load_cash_flow()
            if not quiet:
                print(f"   ✓ Cash Flow: {len(historical_data.cash_flow.periods)} periods loaded")
        except (ValueError, RuntimeError) as e:
            # Cash flow is optional for historical data
            if not quiet:
                print(f"   ⚠️  Warning: Could not load cash flow data: {e}")
        
        return historical_data
    
    def _load_income_statement(self) -> HistoricalStatement:
        """Load Income Statement from yfinance."""
        if self.period == "quarterly":
            df = self.ticker.quarterly_financials
        else:
            df = self.ticker.financials
        
        if df is None or df.empty:
            raise RuntimeError(
                f"Could not fetch income statement data for {self.ticker_symbol}. "
                f"The ticker may not exist or may not have financial data available."
            )
        
        # Check if ticker info is available
        try:
            info = self.ticker.info
            if not info or 'symbol' not in info:
                raise RuntimeError(
                    f"Ticker {self.ticker_symbol} not found or invalid. "
                    f"Please verify the ticker symbol is correct."
                )
        except Exception:
            # If info fetch fails, continue but warn
            pass
        
        # Required columns - COGS is optional for banks/financial companies
        required_cols = [
            "Revenue", "Operating Expenses", "Depreciation",
            "Interest Expense", "Tax Expense", "Net Income"
        ]
        optional_cols = ["COGS"]  # Can be calculated or defaulted to 0
        
        return self._convert_dataframe_to_statement(
            df,
            self.INCOME_STATEMENT_MAPPING,
            required_cols,
            optional_cols,
            "Income Statement"
        )
    
    def _load_balance_sheet(self) -> HistoricalStatement:
        """Load Balance Sheet from yfinance."""
        if self.period == "quarterly":
            df = self.ticker.quarterly_balance_sheet
        else:
            df = self.ticker.balance_sheet
        
        if df is None or df.empty:
            raise RuntimeError(
                f"Could not fetch balance sheet data for {self.ticker_symbol}"
            )
        
        # Required columns - Many fields are optional for different company types
        # Banks may not have AR, service companies may not have Inventory or PP&E
        # Some companies have zero debt (Debt can be 0)
        # Retained Earnings can sometimes be calculated or inferred
        required_cols = [
            "Cash", "Equity"
        ]
        optional_cols = ["Inventory", "Accounts Payable", "Accounts Receivable", "PP&E", "Retained Earnings", "Debt"]  # Can be defaulted to 0
        
        return self._convert_dataframe_to_statement(
            df,
            self.BALANCE_SHEET_MAPPING,
            required_cols,
            optional_cols,
            "Balance Sheet"
        )
    
    def _load_cash_flow(self) -> HistoricalStatement:
        """Load Cash Flow Statement from yfinance."""
        if self.period == "quarterly":
            df = self.ticker.quarterly_cashflow
        else:
            df = self.ticker.cashflow
        
        if df is None or df.empty:
            raise RuntimeError(
                f"Could not fetch cash flow data for {self.ticker_symbol}"
            )
        
        # Cash flow columns - some changes can be 0
        required_cols = [
            "Net Income", "Depreciation", "Operating Cash Flow"
        ]
        optional_cols = [
            "Change in AR", "Change in Inventory", "Change in AP", "CapEx"
        ]
        
        return self._convert_dataframe_to_statement(
            df,
            self.CASH_FLOW_MAPPING,
            required_cols,
            optional_cols,
            "Cash Flow"
        )
    
    def _convert_dataframe_to_statement(
        self,
        df: pd.DataFrame,
        mapping: Dict[str, str],
        required_cols: List[str],
        optional_cols: List[str] = None,
        statement_name: str = "Statement"
    ) -> HistoricalStatement:
        """
        Convert yfinance DataFrame to HistoricalStatement.
        
        Args:
            df: DataFrame from yfinance (line items as rows, dates as columns)
            mapping: Dictionary mapping yfinance names to our names
            required_cols: List of required column names in our format
            optional_cols: List of optional column names (will default to 0 if missing)
            statement_name: Name of statement for error messages
            
        Returns:
            HistoricalStatement object
            
        Raises:
            ValueError: If required data is missing
        """
        if optional_cols is None:
            optional_cols = []
        
        statement = HistoricalStatement()
        
        # Transpose: dates become rows, line items become columns
        df_transposed = df.T
        
        # Get period identifiers (dates)
        # yfinance provides dates as pandas Timestamps in the index
        # Filter out periods with too much missing data
        statement.periods = []
        valid_period_indices = []
        
        for period_idx, period_date in enumerate(df_transposed.index):
            # Check if this period has sufficient data
            non_null_count = df_transposed.iloc[period_idx].notna().sum()
            total_count = len(df_transposed.columns)
            data_completeness = non_null_count / total_count if total_count > 0 else 0
            
            # Only include periods with at least 30% data completeness
            if data_completeness >= 0.3:
                # Directly extract year and quarter from Timestamp
                if pd is not None and hasattr(period_date, 'year') and hasattr(period_date, 'month'):
                    year = period_date.year
                    quarter = (period_date.month - 1) // 3 + 1
                    period_str = f"{year}-Q{quarter}"
                else:
                    # Fallback to formatting function
                    period_str = self._format_period(period_date)
                statement.periods.append(period_str)
                valid_period_indices.append(period_idx)
        
        if not statement.periods:
            raise ValueError(
                f"{statement_name}: No periods with sufficient data found for {self.ticker_symbol}. "
                f"All periods have less than 30% data completeness."
            )
        
        # Filter dataframe to only valid periods
        df_transposed = df_transposed.iloc[valid_period_indices]
        
        # Initialize data structure for all columns (required + optional)
        all_cols = required_cols + optional_cols
        for col in all_cols:
            statement.data[col] = []
        
        # Map yfinance line items to our format
        yfinance_to_ours = {}
        for yf_name, our_name in mapping.items():
            if yf_name in df.index:
                yfinance_to_ours[yf_name] = our_name
        
        # Check for missing required columns (excluding optional ones)
        found_cols = set()
        for yf_name, our_name in yfinance_to_ours.items():
            if our_name in required_cols:
                found_cols.add(our_name)
        
        missing_cols = set(required_cols) - found_cols
        
        # Special handling for COGS - calculate from Revenue - Gross Profit if missing
        if "COGS" in missing_cols:
            # Try to calculate COGS from Revenue - Gross Profit
            has_revenue = any("Revenue" in col or "Sales" in col for col in df.index)
            has_gross_profit = any("Gross Profit" in col for col in df.index)
            if has_revenue and has_gross_profit:
                found_cols.add("COGS")
                missing_cols.remove("COGS")
                yfinance_to_ours["_CALCULATED_COGS"] = "COGS"
        
        # Special handling for Interest Expense - calculate from EBIT and Pretax Income
        if "Interest Expense" in missing_cols:
            # Interest Expense = EBIT - Pretax Income (EBT)
            # This is because: EBIT - Interest Expense = Pretax Income
            if "EBIT" in df.index and "Pretax Income" in df.index:
                found_cols.add("Interest Expense")
                missing_cols.remove("Interest Expense")
                # Add a special marker for calculated interest
                yfinance_to_ours["_CALCULATED_INTEREST"] = "Interest Expense"
            elif "Other Income Expense" in df.index:
                # Use Other Income Expense as proxy (often contains interest)
                yfinance_to_ours["Other Income Expense"] = "Interest Expense"
                found_cols.add("Interest Expense")
                missing_cols.remove("Interest Expense")
        
        if missing_cols:
            available_cols = list(df.index)
            # Find similar column names that might help
            suggestions = {}
            for missing_col in missing_cols:
                similar = [
                    col for col in available_cols 
                    if missing_col.lower().replace(' ', '') in col.lower().replace(' ', '')
                ][:3]
                if similar:
                    suggestions[missing_col] = similar
            
            error_msg = (
                f"{statement_name}: Could not find required columns in yfinance data: {missing_cols}.\n"
                f"   This ticker ({self.ticker_symbol}) may not have standard financial statements.\n"
                f"   Available columns: {len(available_cols)} total"
            )
            
            # Add suggestions for missing columns
            if suggestions:
                error_msg += "\n   Similar columns found:"
                for missing_col, suggested in suggestions.items():
                    error_msg += f"\n     - {missing_col}: {', '.join(suggested[:2])}"
            
            error_msg += (
                f"\n   Please try a different ticker with complete financial statements "
                f"(e.g., AAPL, MSFT, GOOGL, JPM, JNJ)."
            )
            
            raise ValueError(error_msg)
        
        # Extract data for each period (using filtered periods)
        for period_idx, period in enumerate(statement.periods):
            for col in all_cols:  # Process both required and optional columns
                # Find the yfinance line item that maps to this column
                value = None
                
                # Special handling for calculated COGS
                if col == "COGS" and "_CALCULATED_COGS" in yfinance_to_ours:
                    # Calculate COGS from Revenue - Gross Profit
                    revenue_val = None
                    gross_profit_val = None
                    for yf_name in df.index:
                        if "Total Revenue" in yf_name or yf_name == "Revenue" or "Operating Revenue" in yf_name:
                            val = df_transposed.iloc[period_idx][yf_name]
                            if pd.notna(val):
                                revenue_val = float(val)
                                break
                        if "Gross Profit" in yf_name:
                            val = df_transposed.iloc[period_idx][yf_name]
                            if pd.notna(val):
                                gross_profit_val = float(val)
                                break
                    if pd.notna(revenue_val) and pd.notna(gross_profit_val):
                        value = float(revenue_val - gross_profit_val)
                    elif value is None:
                        value = 0.0  # Default to 0 if can't calculate
                
                # Special handling for calculated Interest Expense
                elif col == "Interest Expense" and "_CALCULATED_INTEREST" in yfinance_to_ours:
                    # Calculate Interest Expense from EBIT - Pretax Income
                    # Formula: EBIT - Interest Expense = Pretax Income
                    # Therefore: Interest Expense = EBIT - Pretax Income
                    if "EBIT" in df.index and "Pretax Income" in df.index:
                        ebit = df_transposed.iloc[period_idx]["EBIT"]
                        pretax_income = df_transposed.iloc[period_idx]["Pretax Income"]
                        if pd.notna(ebit) and pd.notna(pretax_income):
                            # Interest Expense = EBIT - Pretax Income
                            value = float(ebit - pretax_income)
                    # If calculation fails, use 0 as fallback
                    if value is None:
                        value = 0.0
                else:
                    # Normal lookup with multiple attempts
                    for yf_name, our_name in yfinance_to_ours.items():
                        if our_name == col and yf_name != "_CALCULATED_INTEREST":
                            if yf_name in df.index:
                                val = df_transposed.iloc[period_idx][yf_name]
                                if pd.notna(val):
                                    value = float(val)
                                    break
                    
                    # If still None, try to use value from previous period (for missing data)
                    if value is None and period_idx > 0:
                        # Try previous period's value as fallback
                        prev_period_idx = period_idx - 1
                        for yf_name, our_name in yfinance_to_ours.items():
                            if our_name == col and yf_name != "_CALCULATED_INTEREST":
                                if yf_name in df.index:
                                    prev_val = df_transposed.iloc[prev_period_idx][yf_name]
                                    if pd.notna(prev_val):
                                        value = float(prev_val)
                                        break
                    
                    # If still None, try to calculate from other fields
                    if value is None:
                        if col == "COGS" and "Revenue" in [our_name for _, our_name in yfinance_to_ours.items()]:
                            # Try to calculate COGS from Revenue - Gross Profit
                            if "Gross Profit" in df.index or "Total Revenue" in df.index:
                                revenue_val = None
                                gross_profit_val = None
                                for yf_name in df.index:
                                    if "Total Revenue" in yf_name or "Revenue" == yf_name:
                                        revenue_val = df_transposed.iloc[period_idx][yf_name]
                                    if "Gross Profit" in yf_name:
                                        gross_profit_val = df_transposed.iloc[period_idx][yf_name]
                                if pd.notna(revenue_val) and pd.notna(gross_profit_val):
                                    value = float(revenue_val - gross_profit_val)
                    
                    # Last resort: use 0 for optional fields or calculate
                    if value is None:
                        # Some fields can be 0 (like Inventory for service companies, COGS for banks, PP&E for some)
                        if col in optional_cols:  # All optional columns can default to 0
                            value = 0.0
                        elif col == "Retained Earnings":
                            # Retained Earnings can be calculated from Equity - Common Stock - Additional Paid In Capital
                            # Or default to 0 if not available
                            equity_val = None
                            for yf_name in df.index:
                                if any(term in yf_name for term in ["Total Stockholders Equity", "Stockholders Equity", "Total Equity"]):
                                    val = df_transposed.iloc[period_idx][yf_name]
                                    if pd.notna(val):
                                        equity_val = float(val)
                                        break
                            # Default to 0 or use equity as proxy
                            value = equity_val if equity_val is not None else 0.0
                        elif col == "COGS":
                            # Try one more time to calculate COGS
                            revenue_val = None
                            gross_profit_val = None
                            for yf_name in df.index:
                                if any(term in yf_name for term in ["Total Revenue", "Revenue", "Operating Revenue"]):
                                    val = df_transposed.iloc[period_idx][yf_name]
                                    if pd.notna(val):
                                        revenue_val = float(val)
                                if "Gross Profit" in yf_name:
                                    val = df_transposed.iloc[period_idx][yf_name]
                                    if pd.notna(val):
                                        gross_profit_val = float(val)
                            if pd.notna(revenue_val) and pd.notna(gross_profit_val):
                                value = float(revenue_val - gross_profit_val)
                            else:
                                value = 0.0  # Default for companies without COGS (e.g., banks)
                
                if value is None:
                    # If it's an optional column, use default value
                    if col in optional_cols:
                        value = 0.0
                    else:
                        # Try to find alternative periods with data
                        available_periods = []
                        for alt_idx in range(len(statement.periods)):
                            for yf_name, our_name in yfinance_to_ours.items():
                                if our_name == col and yf_name in df.index:
                                    alt_val = df_transposed.iloc[alt_idx][yf_name]
                                    if pd.notna(alt_val):
                                        available_periods.append(statement.periods[alt_idx])
                                        break
                        
                        raise ValueError(
                            f"{statement_name}: Missing value for '{col}' in period {period}. "
                            f"This period may have incomplete data. "
                            f"Available periods with data: {available_periods[:3] if available_periods else 'None'}. "
                            f"Please try a different ticker or check if {self.ticker_symbol} has complete financial statements."
                        )
                
                statement.data[col].append(value)
        
        return statement
    
    def _format_period(self, date_input) -> str:
        """
        Format date to period identifier.
        
        Args:
            date_input: Date from yfinance (can be pd.Timestamp, str, or other)
            
        Returns:
            Formatted period string (e.g., "2024-Q1")
        """
        try:
            # Handle pandas Timestamp directly
            if pd is not None and isinstance(date_input, pd.Timestamp):
                dt = date_input
            elif pd is not None:
                # Try to parse as datetime
                dt = pd.to_datetime(date_input)
            else:
                # Fallback to string parsing
                from datetime import datetime
                if isinstance(date_input, str):
                    dt = datetime.strptime(date_input.split()[0], "%Y-%m-%d")
                else:
                    dt = datetime.strptime(str(date_input).split()[0], "%Y-%m-%d")
            
            year = dt.year
            quarter = (dt.month - 1) // 3 + 1
            return f"{year}-Q{quarter}"
        except (ValueError, AttributeError, TypeError) as e:
            # Fallback: use as-is, removing any time component
            period_str = str(date_input).split()[0] if ' ' in str(date_input) else str(date_input)
            # Remove any existing Q formatting to avoid double formatting
            if '-Q' in period_str and period_str.count('-Q') > 1:
                # Already formatted, return as-is but clean up
                parts = period_str.split('-Q')
                if len(parts) >= 2:
                    return f"{parts[0]}-Q{parts[-1]}"
            return period_str

