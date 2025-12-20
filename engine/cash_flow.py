"""
Cash Flow Statement Engine.

Generates indirect cash flow statement from Income Statement and Balance Sheet changes.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from engine.income_statement import IncomeStatement
from engine.working_capital import WorkingCapital


@dataclass
class CashFlowStatement:
    """Cash Flow Statement for a single period."""
    period: str
    # Operating Activities
    net_income: float = 0.0
    depreciation: float = 0.0
    change_in_ar: float = 0.0
    change_in_inventory: float = 0.0
    change_in_ap: float = 0.0
    operating_cash_flow: float = 0.0
    # Investing Activities
    capex: float = 0.0
    investing_cash_flow: float = 0.0
    # Financing Activities
    debt_issuance: float = 0.0
    debt_repayment: float = 0.0
    financing_cash_flow: float = 0.0
    # Net Change
    net_change_in_cash: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for export."""
        return {
            "Period": self.period,
            "Net Income": self.net_income,
            "Depreciation": self.depreciation,
            "Change in AR": self.change_in_ar,
            "Change in Inventory": self.change_in_inventory,
            "Change in AP": self.change_in_ap,
            "Operating Cash Flow": self.operating_cash_flow,
            "CapEx": self.capex,
            "Investing Cash Flow": self.investing_cash_flow,
            "Debt Issuance": self.debt_issuance,
            "Debt Repayment": self.debt_repayment,
            "Financing Cash Flow": self.financing_cash_flow,
            "Net Change in Cash": self.net_change_in_cash
        }


class CashFlowEngine:
    """Generates cash flow statements using indirect method."""
    
    def __init__(self, assumptions: Dict[str, Any]):
        """
        Initialize the Cash Flow engine.
        
        Args:
            assumptions: Dictionary of financial assumptions
        """
        self.assumptions = assumptions
    
    def generate(self, 
                 income_statements: List[IncomeStatement],
                 working_capital_changes: List[Dict[str, float]],
                 prior_period_cash: float = 0.0) -> List[CashFlowStatement]:
        """
        Generate cash flow statements for multiple periods.
        
        Args:
            income_statements: List of IncomeStatement objects
            working_capital_changes: List of working capital change dictionaries
            prior_period_cash: Cash balance from period before first projection
            
        Returns:
            List of CashFlowStatement objects
            
        Raises:
            ValueError: If inputs are invalid
        """
        if len(income_statements) != len(working_capital_changes):
            raise ValueError(
                "Income statements and working capital changes must have same length"
            )
        
        if not income_statements:
            raise ValueError("Income statements list cannot be empty")
        
        cash_flow_statements = []
        current_cash = prior_period_cash
        
        for i, (is_stmt, wc_changes) in enumerate(zip(income_statements, working_capital_changes)):
            cf_stmt = self._generate_single_period(
                is_stmt,
                wc_changes,
                i == 0  # First period flag
            )
            cash_flow_statements.append(cf_stmt)
        
        return cash_flow_statements
    
    def _generate_single_period(self, 
                                income_stmt: IncomeStatement,
                                wc_changes: Dict[str, float],
                                is_first_period: bool) -> CashFlowStatement:
        """
        Generate cash flow statement for a single period.
        
        Logic:
        1. Start from Net Income
        2. Add non-cash items (depreciation)
        3. Adjust for working capital changes
        4. Subtract CapEx
        5. Account for financing activities
        
        Args:
            income_stmt: IncomeStatement for the period
            wc_changes: Working capital changes dictionary
            is_first_period: Whether this is the first projected period
            
        Returns:
            CashFlowStatement object
        """
        cf = CashFlowStatement(period=income_stmt.period)
        
        # Operating Activities
        cf.net_income = income_stmt.net_income
        cf.depreciation = income_stmt.depreciation
        
        # Working capital changes (negative for uses of cash, positive for sources)
        cf.change_in_ar = -wc_changes.get("Change in AR", 0.0)  # Increase in AR uses cash
        cf.change_in_inventory = -wc_changes.get("Change in Inventory", 0.0)  # Increase uses cash
        cf.change_in_ap = wc_changes.get("Change in AP", 0.0)  # Increase in AP is source of cash
        
        cf.operating_cash_flow = (
            cf.net_income +
            cf.depreciation +
            cf.change_in_ar +
            cf.change_in_inventory +
            cf.change_in_ap
        )
        
        # Investing Activities
        # CapEx: based on capex_ratio assumption
        capex_ratio = self.assumptions["capex_ratio"]
        cf.capex = -income_stmt.revenue * capex_ratio  # Negative (use of cash)
        cf.investing_cash_flow = cf.capex
        
        # Financing Activities
        # For now, assume no debt issuance/repayment
        # This will be refined when balance sheet is integrated
        cf.debt_issuance = 0.0
        cf.debt_repayment = 0.0
        cf.financing_cash_flow = cf.debt_issuance + cf.debt_repayment
        
        # Net Change in Cash
        cf.net_change_in_cash = (
            cf.operating_cash_flow +
            cf.investing_cash_flow +
            cf.financing_cash_flow
        )
        
        return cf

