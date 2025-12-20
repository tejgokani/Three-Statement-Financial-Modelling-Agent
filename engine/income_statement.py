"""
Income Statement Projection Engine.

Projects Income Statement deterministically based on assumptions and historical data.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class IncomeStatement:
    """Projected Income Statement for a single period."""
    period: str
    revenue: float = 0.0
    cogs: float = 0.0
    gross_profit: float = 0.0
    operating_expenses: float = 0.0
    ebitda: float = 0.0
    depreciation: float = 0.0
    ebit: float = 0.0
    interest_expense: float = 0.0
    ebt: float = 0.0
    tax_expense: float = 0.0
    net_income: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for export."""
        return {
            "Period": self.period,
            "Revenue": self.revenue,
            "COGS": self.cogs,
            "Gross Profit": self.gross_profit,
            "Operating Expenses": self.operating_expenses,
            "EBITDA": self.ebitda,
            "Depreciation": self.depreciation,
            "EBIT": self.ebit,
            "Interest Expense": self.interest_expense,
            "EBT": self.ebt,
            "Tax Expense": self.tax_expense,
            "Net Income": self.net_income
        }


class IncomeStatementEngine:
    """Projects Income Statements deterministically."""
    
    def __init__(self, assumptions: Dict[str, Any], historical_data: Any):
        """
        Initialize the Income Statement engine.
        
        Args:
            assumptions: Dictionary of financial assumptions
            historical_data: HistoricalData object with historical statements
        """
        self.assumptions = assumptions
        self.historical_data = historical_data
    
    def project(self, periods: List[str], prior_period_revenue: float = None) -> List[IncomeStatement]:
        """
        Project Income Statements for multiple periods.
        
        Args:
            periods: List of period identifiers (e.g., ["2024-Q1", "2024-Q2"])
            prior_period_revenue: Revenue from the period immediately before periods[0]
                                  If None, uses last historical period
            
        Returns:
            List of projected IncomeStatement objects
            
        Raises:
            ValueError: If required assumptions or data are missing
        """
        if not periods:
            raise ValueError("Periods list cannot be empty")
        
        # Get starting revenue
        if prior_period_revenue is None:
            if not self.historical_data.income_statement:
                raise ValueError(
                    "Cannot determine starting revenue: no historical data and "
                    "prior_period_revenue not provided"
                )
            hist_is = self.historical_data.income_statement
            if not hist_is.periods:
                raise ValueError("Historical income statement has no periods")
            last_period = hist_is.periods[-1]
            prior_period_revenue = hist_is.get_value("Revenue", last_period)
        
        # Validate starting revenue
        if prior_period_revenue <= 0:
            raise ValueError(
                f"Cannot project from zero or negative revenue. "
                f"Last historical revenue: ${prior_period_revenue:,.2f}. "
                f"Company may be pre-revenue or have insufficient historical data. "
                f"Please use a company with positive historical revenue."
            )
        
        projected_statements = []
        current_revenue = prior_period_revenue
        
        for period in periods:
            statement = self._project_single_period(period, current_revenue)
            projected_statements.append(statement)
            current_revenue = statement.revenue  # For next period growth
        
        return projected_statements
    
    def _project_single_period(self, period: str, prior_revenue: float) -> IncomeStatement:
        """
        Project Income Statement for a single period.
        
        Args:
            period: Period identifier
            prior_revenue: Revenue from prior period
            
        Returns:
            Projected IncomeStatement
        """
        statement = IncomeStatement(period=period)
        
        # Revenue: grow from prior period
        revenue_growth = self.assumptions["revenue_growth"]
        statement.revenue = prior_revenue * (1 + revenue_growth)
        
        # COGS: based on gross margin
        gross_margin = self.assumptions["gross_margin"]
        statement.cogs = statement.revenue * (1 - gross_margin)
        statement.gross_profit = statement.revenue - statement.cogs
        
        # Operating Expenses: based on opex ratio
        opex_ratio = self.assumptions["opex_ratio"]
        statement.operating_expenses = statement.revenue * opex_ratio
        
        # EBITDA
        statement.ebitda = statement.gross_profit - statement.operating_expenses
        
        # Depreciation: based on depreciation rate
        # For simplicity, assume depreciation is a percentage of revenue
        # In practice, this would be based on PP&E, but we use revenue as proxy
        depreciation_rate = self.assumptions["depreciation_rate"]
        statement.depreciation = statement.revenue * depreciation_rate
        
        # EBIT
        statement.ebit = statement.ebitda - statement.depreciation
        
        # Interest Expense: based on interest rate
        # This will be refined when we link to balance sheet debt
        # For now, use a simple assumption based on revenue
        interest_rate = self.assumptions["interest_rate"]
        # Assume interest is calculated on prior period debt
        # If no debt info available, use revenue as proxy
        statement.interest_expense = statement.revenue * interest_rate * 0.1  # 10% debt-to-revenue assumption
        
        # EBT (Earnings Before Tax)
        statement.ebt = statement.ebit - statement.interest_expense
        
        # Tax Expense
        tax_rate = self.assumptions["tax_rate"]
        statement.tax_expense = statement.ebt * tax_rate
        
        # Net Income
        statement.net_income = statement.ebt - statement.tax_expense
        
        return statement

