"""
Terminal Display Module.

Formats and displays financial statements in the terminal.
"""

from typing import List
from engine.income_statement import IncomeStatement
from engine.balance_sheet import BalanceSheet
from engine.cash_flow import CashFlowStatement
from validators.validator import ModelResults


class TerminalDisplay:
    """Displays financial statements in formatted tables."""
    
    @staticmethod
    def format_currency(value: float, width: int = 15) -> str:
        """Format a number as currency string."""
        if abs(value) >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B".rjust(width)
        elif abs(value) >= 1_000_000:
            return f"${value/1_000_000:.2f}M".rjust(width)
        elif abs(value) >= 1_000:
            return f"${value/1_000:.2f}K".rjust(width)
        else:
            return f"${value:.2f}".rjust(width)
    
    @staticmethod
    def display_income_statement(statements: List[IncomeStatement], title: str = "INCOME STATEMENT"):
        """Display Income Statement in formatted table."""
        print("\n" + "=" * 100)
        print(f"  {title}")
        print("=" * 100)
        
        # Header
        periods = [stmt.period for stmt in statements]
        header = f"{'Line Item':<30}"
        for period in periods:
            header += f"{period:>15}"
        print(header)
        print("-" * 100)
        
        # Line items
        line_items = [
            ("Revenue", lambda s: s.revenue),
            ("COGS", lambda s: s.cogs),
            ("Gross Profit", lambda s: s.gross_profit),
            ("Operating Expenses", lambda s: s.operating_expenses),
            ("EBITDA", lambda s: s.ebitda),
            ("Depreciation", lambda s: s.depreciation),
            ("EBIT", lambda s: s.ebit),
            ("Interest Expense", lambda s: s.interest_expense),
            ("EBT", lambda s: s.ebt),
            ("Tax Expense", lambda s: s.tax_expense),
            ("Net Income", lambda s: s.net_income),
        ]
        
        for item_name, getter in line_items:
            row = f"{item_name:<30}"
            for stmt in statements:
                value = getter(stmt)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print("=" * 100)
    
    @staticmethod
    def display_balance_sheet(sheets: List[BalanceSheet], title: str = "BALANCE SHEET"):
        """Display Balance Sheet in formatted table."""
        print("\n" + "=" * 100)
        print(f"  {title}")
        print("=" * 100)
        
        # Header
        periods = [bs.period for bs in sheets]
        header = f"{'Line Item':<30}"
        for period in periods:
            header += f"{period:>15}"
        print(header)
        print("-" * 100)
        
        # Assets
        print("ASSETS:")
        asset_items = [
            ("Cash", lambda bs: bs.cash),
            ("Accounts Receivable", lambda bs: bs.accounts_receivable),
            ("Inventory", lambda bs: bs.inventory),
            ("PP&E", lambda bs: bs.ppe),
            ("Total Assets", lambda bs: bs.total_assets),
        ]
        
        for item_name, getter in asset_items:
            row = f"  {item_name:<28}"
            for bs in sheets:
                value = getter(bs)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print()
        print("LIABILITIES & EQUITY:")
        liability_items = [
            ("Accounts Payable", lambda bs: bs.accounts_payable),
            ("Debt", lambda bs: bs.debt),
            ("Total Liabilities", lambda bs: bs.total_liabilities),
            ("Equity", lambda bs: bs.equity),
            ("Retained Earnings", lambda bs: bs.retained_earnings),
            ("Total Equity", lambda bs: bs.total_equity),
            ("Total Liab. + Equity", lambda bs: bs.total_liabilities_and_equity),
        ]
        
        for item_name, getter in liability_items:
            row = f"  {item_name:<28}"
            for bs in sheets:
                value = getter(bs)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print("=" * 100)
    
    @staticmethod
    def display_cash_flow(statements: List[CashFlowStatement], title: str = "CASH FLOW STATEMENT"):
        """Display Cash Flow Statement in formatted table."""
        print("\n" + "=" * 100)
        print(f"  {title}")
        print("=" * 100)
        
        # Header
        periods = [cf.period for cf in statements]
        header = f"{'Line Item':<30}"
        for period in periods:
            header += f"{period:>15}"
        print(header)
        print("-" * 100)
        
        # Operating Activities
        print("OPERATING ACTIVITIES:")
        operating_items = [
            ("Net Income", lambda cf: cf.net_income),
            ("Depreciation", lambda cf: cf.depreciation),
            ("Change in AR", lambda cf: cf.change_in_ar),
            ("Change in Inventory", lambda cf: cf.change_in_inventory),
            ("Change in AP", lambda cf: cf.change_in_ap),
            ("Operating Cash Flow", lambda cf: cf.operating_cash_flow),
        ]
        
        for item_name, getter in operating_items:
            row = f"  {item_name:<28}"
            for cf in statements:
                value = getter(cf)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print()
        print("INVESTING ACTIVITIES:")
        investing_items = [
            ("CapEx", lambda cf: cf.capex),
            ("Investing Cash Flow", lambda cf: cf.investing_cash_flow),
        ]
        
        for item_name, getter in investing_items:
            row = f"  {item_name:<28}"
            for cf in statements:
                value = getter(cf)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print()
        print("FINANCING ACTIVITIES:")
        financing_items = [
            ("Debt Issuance", lambda cf: cf.debt_issuance),
            ("Debt Repayment", lambda cf: cf.debt_repayment),
            ("Financing Cash Flow", lambda cf: cf.financing_cash_flow),
        ]
        
        for item_name, getter in financing_items:
            row = f"  {item_name:<28}"
            for cf in statements:
                value = getter(cf)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print()
        print("NET CHANGE:")
        net_change_items = [
            ("Net Change in Cash", lambda cf: cf.net_change_in_cash),
        ]
        
        for item_name, getter in net_change_items:
            row = f"  {item_name:<28}"
            for cf in statements:
                value = getter(cf)
                row += TerminalDisplay.format_currency(value)
            print(row)
        
        print("=" * 100)
    
    @staticmethod
    def display_summary(results: ModelResults, scenario_name: str):
        """Display summary statistics."""
        print("\n" + "=" * 100)
        print("  FINANCIAL SUMMARY")
        print("=" * 100)
        
        if not results.income_statements:
            return
        
        first_is = results.income_statements[0]
        last_is = results.income_statements[-1]
        first_bs = results.balance_sheets[0]
        last_bs = results.balance_sheets[-1]
        
        # Revenue growth
        revenue_growth = ((last_is.revenue - first_is.revenue) / first_is.revenue) * 100
        
        # Margins
        gross_margin = (last_is.gross_profit / last_is.revenue) * 100 if last_is.revenue > 0 else 0
        net_margin = (last_is.net_income / last_is.revenue) * 100 if last_is.revenue > 0 else 0
        
        # Cash position
        cash_change = last_bs.cash - first_bs.cash
        
        print(f"\nScenario: {scenario_name.upper()}")
        print(f"Projection Periods: {len(results.periods)}")
        print()
        print("Key Metrics (Last Period):")
        print(f"  Revenue:           {TerminalDisplay.format_currency(last_is.revenue)}")
        print(f"  Net Income:        {TerminalDisplay.format_currency(last_is.net_income)}")
        print(f"  Gross Margin:      {gross_margin:.2f}%")
        print(f"  Net Margin:        {net_margin:.2f}%")
        print(f"  Total Assets:      {TerminalDisplay.format_currency(last_bs.total_assets)}")
        print(f"  Cash Balance:     {TerminalDisplay.format_currency(last_bs.cash)}")
        print()
        print("Growth Metrics:")
        print(f"  Revenue Growth:   {revenue_growth:.2f}%")
        print(f"  Cash Change:       {TerminalDisplay.format_currency(cash_change)}")
        print("=" * 100)
    
    @staticmethod
    def display_all(results: ModelResults, scenario_name: str):
        """Display all financial statements."""
        print("\n" + "=" * 100)
        print("  PROJECTED FINANCIAL STATEMENTS")
        print("=" * 100)
        
        TerminalDisplay.display_income_statement(results.income_statements, 
                                                  f"PROJECTED INCOME STATEMENT - {scenario_name.upper()}")
        TerminalDisplay.display_balance_sheet(results.balance_sheets,
                                             f"PROJECTED BALANCE SHEET - {scenario_name.upper()}")
        TerminalDisplay.display_cash_flow(results.cash_flow_statements,
                                          f"PROJECTED CASH FLOW STATEMENT - {scenario_name.upper()}")
        TerminalDisplay.display_summary(results, scenario_name)

