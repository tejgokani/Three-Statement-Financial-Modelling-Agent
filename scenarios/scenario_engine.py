"""
Scenario and Stress Testing Engine.

Runs Base, Bull, and Bear scenarios with different assumption sets.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from engine.income_statement import IncomeStatementEngine
from engine.working_capital import WorkingCapitalEngine
from engine.cash_flow import CashFlowEngine
from engine.balance_sheet import BalanceSheetEngine
from validators.validator import ModelResults


class ScenarioEngine:
    """Runs financial model scenarios with different assumption sets."""
    
    def __init__(self, historical_data: Any, assumptions: Dict[str, Any], 
                 scenario_name: str = "base"):
        """
        Initialize the scenario engine.
        
        Args:
            historical_data: HistoricalData object
            assumptions: Base assumptions dictionary
            scenario_name: Name of scenario to run ("base", "bull", "bear")
        """
        self.historical_data = historical_data
        self.base_assumptions = assumptions
        self.scenario_name = scenario_name.lower()
    
    def run(self, periods: Optional[List[str]] = None) -> ModelResults:
        """
        Run the specified scenario.
        
        Args:
            periods: List of periods to project. If None, generates 4 quarters.
            
        Returns:
            ModelResults object with all projected statements
        """
        # Generate periods if not provided
        if periods is None:
            # Assume starting from next period after last historical
            if self.historical_data.income_statement:
                last_period = self.historical_data.income_statement.periods[-1]
                # Parse last period and generate next 4 quarters
                # Format: "YYYY-QN"
                if "-Q" in last_period:
                    parts = last_period.split("-Q")
                    year = int(parts[0])
                    quarter = int(parts[1])
                    # Calculate next quarter
                    next_quarter = quarter + 1
                    next_year = year
                    if next_quarter > 4:
                        next_quarter = 1
                        next_year += 1
                    
                    # Generate 4 periods starting from next quarter
                    periods = []
                    current_year = next_year
                    current_quarter = next_quarter
                    for i in range(4):
                        periods.append(f"{current_year}-Q{current_quarter}")
                        current_quarter += 1
                        if current_quarter > 4:
                            current_quarter = 1
                            current_year += 1
                else:
                    # Fallback: assume format is just year, add quarters
                    periods = [f"{last_period}-Q1", f"{last_period}-Q2", 
                              f"{last_period}-Q3", f"{last_period}-Q4"]
            else:
                raise ValueError("Cannot generate periods: no historical data")
        
        # Get scenario-specific assumptions
        scenario_assumptions = self._get_scenario_assumptions()
        
        # Initialize engines
        is_engine = IncomeStatementEngine(scenario_assumptions, self.historical_data)
        wc_engine = WorkingCapitalEngine(scenario_assumptions)
        cf_engine = CashFlowEngine(scenario_assumptions)
        bs_engine = BalanceSheetEngine(scenario_assumptions, self.historical_data)
        
        # Project Income Statements
        income_statements = is_engine.project(periods)
        
        # Extract revenues and COGS for working capital
        revenues = [is_stmt.revenue for is_stmt in income_statements]
        cogs_list = [is_stmt.cogs for is_stmt in income_statements]
        
        # Calculate Working Capital
        working_capital_list = wc_engine.calculate(periods, revenues, cogs_list)
        working_capital_changes = wc_engine.calculate_changes(working_capital_list)
        
        # Generate Cash Flow Statements
        prior_cash = 0.0
        if self.historical_data.balance_sheet and self.historical_data.balance_sheet.periods:
            last_period = self.historical_data.balance_sheet.periods[-1]
            prior_cash = self.historical_data.balance_sheet.get_value("Cash", last_period)
        
        cash_flow_statements = cf_engine.generate(
            income_statements,
            working_capital_changes,
            prior_cash
        )
        
        # Project Balance Sheets
        prior_bs = None
        if self.historical_data.balance_sheet:
            prior_bs = bs_engine.get_starting_balance_sheet()
        
        balance_sheets = bs_engine.project(
            periods,
            income_statements,
            working_capital_list,
            cash_flow_statements,
            prior_bs
        )
        
        return ModelResults(
            periods=periods,
            income_statements=income_statements,
            balance_sheets=balance_sheets,
            cash_flow_statements=cash_flow_statements
        )
    
    def _get_scenario_assumptions(self) -> Dict[str, Any]:
        """
        Get scenario-specific assumptions.
        
        Returns:
            Dictionary of assumptions adjusted for scenario
        """
        assumptions = self.base_assumptions.copy()
        
        if self.scenario_name == "bull":
            # Bull scenario: higher growth, stable costs
            assumptions["revenue_growth"] = assumptions["revenue_growth"] * 1.5
            # Keep margins stable or slightly better
            assumptions["gross_margin"] = min(assumptions["gross_margin"] * 1.1, 0.9)
            assumptions["opex_ratio"] = assumptions["opex_ratio"] * 0.95
        
        elif self.scenario_name == "bear":
            # Bear scenario: revenue shock, margin compression
            assumptions["revenue_growth"] = assumptions["revenue_growth"] * 0.5
            if assumptions["revenue_growth"] > 0:
                assumptions["revenue_growth"] = -0.1  # Force decline
            # Margin compression
            assumptions["gross_margin"] = assumptions["gross_margin"] * 0.8
            assumptions["opex_ratio"] = assumptions["opex_ratio"] * 1.1
            # Longer payment terms (worse working capital)
            assumptions["dso"] = assumptions["dso"] * 1.2
            assumptions["dpo"] = assumptions["dpo"] * 0.9
        
        # Base scenario uses assumptions as-is
        return assumptions

