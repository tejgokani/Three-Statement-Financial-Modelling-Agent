"""
Balance Sheet Projection Engine.

Rolls forward Balance Sheet ensuring Assets = Liabilities + Equity at every timestep.
Cash acts as the balancing plug.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from engine.income_statement import IncomeStatement
from engine.working_capital import WorkingCapital
from engine.cash_flow import CashFlowStatement


@dataclass
class BalanceSheet:
    """Balance Sheet for a single period."""
    period: str
    # Assets
    cash: float = 0.0
    accounts_receivable: float = 0.0
    inventory: float = 0.0
    ppe: float = 0.0
    total_assets: float = 0.0
    # Liabilities
    accounts_payable: float = 0.0
    debt: float = 0.0
    total_liabilities: float = 0.0
    # Equity
    equity: float = 0.0
    retained_earnings: float = 0.0
    total_equity: float = 0.0
    total_liabilities_and_equity: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for export."""
        return {
            "Period": self.period,
            "Cash": self.cash,
            "Accounts Receivable": self.accounts_receivable,
            "Inventory": self.inventory,
            "PP&E": self.ppe,
            "Total Assets": self.total_assets,
            "Accounts Payable": self.accounts_payable,
            "Debt": self.debt,
            "Total Liabilities": self.total_liabilities,
            "Equity": self.equity,
            "Retained Earnings": self.retained_earnings,
            "Total Equity": self.total_equity,
            "Total Liabilities and Equity": self.total_liabilities_and_equity
        }
    
    def check_balance(self, tolerance: float = 0.01) -> bool:
        """
        Check if balance sheet balances.
        
        Args:
            tolerance: Allowed difference between assets and liabilities+equity
            
        Returns:
            True if balanced, False otherwise
        """
        difference = abs(self.total_assets - self.total_liabilities_and_equity)
        return difference <= tolerance


class BalanceSheetEngine:
    """Projects Balance Sheets with cash as balancing plug."""
    
    def __init__(self, assumptions: Dict[str, Any], historical_data: Any = None):
        """
        Initialize the Balance Sheet engine.
        
        Args:
            assumptions: Dictionary of financial assumptions
            historical_data: HistoricalData object (optional, for starting balances)
        """
        self.assumptions = assumptions
        self.historical_data = historical_data
    
    def project(self,
                periods: List[str],
                income_statements: List[IncomeStatement],
                working_capital_list: List[WorkingCapital],
                cash_flow_statements: List[CashFlowStatement],
                prior_period_bs: Optional[BalanceSheet] = None) -> List[BalanceSheet]:
        """
        Project Balance Sheets for multiple periods.
        
        Logic:
        1. Roll forward working capital from working capital engine
        2. Update PP&E based on CapEx and depreciation
        3. Update Retained Earnings from Net Income
        4. Calculate cash from cash flow statement
        5. Use cash as plug to ensure balance
        
        Args:
            periods: List of period identifiers
            income_statements: List of IncomeStatement objects
            working_capital_list: List of WorkingCapital objects
            cash_flow_statements: List of CashFlowStatement objects
            prior_period_bs: Balance Sheet from period before first projection
            
        Returns:
            List of projected BalanceSheet objects
            
        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If balance sheet cannot be balanced
        """
        if not all(len(lst) == len(periods) for lst in 
                  [income_statements, working_capital_list, cash_flow_statements]):
            raise ValueError(
                "All input lists must have same length as periods"
            )
        
        if not periods:
            raise ValueError("Periods list cannot be empty")
        
        # Get starting balance sheet
        if prior_period_bs is None:
            prior_period_bs = self.get_starting_balance_sheet()
        
        balance_sheets = []
        current_bs = prior_period_bs
        
        for i, period in enumerate(periods):
            new_bs = self._project_single_period(
                period,
                income_statements[i],
                working_capital_list[i],
                cash_flow_statements[i],
                current_bs
            )
            
            # Validate balance
            if not new_bs.check_balance():
                imbalance = new_bs.total_assets - new_bs.total_liabilities_and_equity
                raise RuntimeError(
                    f"Balance sheet does not balance for period {period}. "
                    f"Imbalance: {imbalance:.2f}. "
                    f"Assets: {new_bs.total_assets:.2f}, "
                    f"Liabilities + Equity: {new_bs.total_liabilities_and_equity:.2f}"
                )
            
            balance_sheets.append(new_bs)
            current_bs = new_bs
        
        return balance_sheets
    
    def get_starting_balance_sheet(self) -> BalanceSheet:
        """
        Get starting balance sheet from historical data.
        
        Returns:
            BalanceSheet from last historical period
            
        Raises:
            ValueError: If historical data is missing
        """
        if not self.historical_data or not self.historical_data.balance_sheet:
            raise ValueError(
                "Cannot determine starting balance sheet: no historical data "
                "and prior_period_bs not provided"
            )
        
        hist_bs = self.historical_data.balance_sheet
        if not hist_bs.periods:
            raise ValueError("Historical balance sheet has no periods")
        
        last_period = hist_bs.periods[-1]
        bs = BalanceSheet(period=last_period)
        
        # Load all values from historical data
        bs.cash = hist_bs.get_value("Cash", last_period)
        bs.accounts_receivable = hist_bs.get_value("Accounts Receivable", last_period)
        bs.inventory = hist_bs.get_value("Inventory", last_period)
        bs.ppe = hist_bs.get_value("PP&E", last_period)
        bs.accounts_payable = hist_bs.get_value("Accounts Payable", last_period)
        bs.debt = hist_bs.get_value("Debt", last_period)
        bs.equity = hist_bs.get_value("Equity", last_period)
        bs.retained_earnings = hist_bs.get_value("Retained Earnings", last_period)
        
        # Calculate totals
        bs.total_assets = bs.cash + bs.accounts_receivable + bs.inventory + bs.ppe
        bs.total_liabilities = bs.accounts_payable + bs.debt
        bs.total_equity = bs.equity + bs.retained_earnings
        bs.total_liabilities_and_equity = bs.total_liabilities + bs.total_equity
        
        return bs
    
    def _project_single_period(self,
                               period: str,
                               income_stmt: IncomeStatement,
                               working_capital: WorkingCapital,
                               cash_flow: CashFlowStatement,
                               prior_bs: BalanceSheet) -> BalanceSheet:
        """
        Project Balance Sheet for a single period.
        
        Args:
            period: Period identifier
            income_stmt: IncomeStatement for the period
            working_capital: WorkingCapital for the period
            cash_flow: CashFlowStatement for the period
            prior_bs: Balance Sheet from prior period
            
        Returns:
            Projected BalanceSheet
        """
        bs = BalanceSheet(period=period)
        
        # Assets
        # Cash: roll forward from prior period + net change from cash flow
        bs.cash = prior_bs.cash + cash_flow.net_change_in_cash
        
        # Working capital components from working capital engine
        bs.accounts_receivable = working_capital.accounts_receivable
        bs.inventory = working_capital.inventory
        
        # PP&E: roll forward + CapEx - Depreciation
        # CapEx is negative in cash flow, so we add it (it's an investment)
        capex = abs(cash_flow.capex)  # Make positive
        depreciation = income_stmt.depreciation
        bs.ppe = prior_bs.ppe + capex - depreciation
        
        # Total Assets
        bs.total_assets = bs.cash + bs.accounts_receivable + bs.inventory + bs.ppe
        
        # Liabilities
        bs.accounts_payable = working_capital.accounts_payable
        
        # Debt: roll forward (assume no new issuance/repayment for now)
        # This can be refined based on cash needs
        bs.debt = prior_bs.debt + cash_flow.debt_issuance - cash_flow.debt_repayment
        
        bs.total_liabilities = bs.accounts_payable + bs.debt
        
        # Equity
        bs.equity = prior_bs.equity  # Assume no new equity issuance
        
        # Retained Earnings: roll forward + Net Income
        bs.retained_earnings = prior_bs.retained_earnings + income_stmt.net_income
        
        bs.total_equity = bs.equity + bs.retained_earnings
        
        # Calculate what liabilities + equity should be
        bs.total_liabilities_and_equity = bs.total_liabilities + bs.total_equity
        
        # Use cash as plug to balance
        # If assets > liabilities+equity, reduce cash
        # If assets < liabilities+equity, increase cash
        imbalance = bs.total_assets - bs.total_liabilities_and_equity
        bs.cash = bs.cash - imbalance
        
        # Recalculate total assets with adjusted cash
        bs.total_assets = bs.cash + bs.accounts_receivable + bs.inventory + bs.ppe
        
        return bs

