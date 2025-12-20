"""
Model Integrity Validator.

Detects logical and financial inconsistencies in projected financial statements.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from engine.income_statement import IncomeStatement
from engine.balance_sheet import BalanceSheet
from engine.cash_flow import CashFlowStatement


@dataclass
class Diagnostic:
    """Single diagnostic message."""
    level: str  # "error", "warning", "info"
    category: str
    period: str
    message: str


@dataclass
class DiagnosticsReport:
    """Collection of diagnostic messages."""
    diagnostics: List[Diagnostic] = field(default_factory=list)
    
    def add(self, level: str, category: str, period: str, message: str) -> None:
        """Add a diagnostic message."""
        self.diagnostics.append(
            Diagnostic(level=level, category=category, period=period, message=message)
        )
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(d.level == "error" for d in self.diagnostics)
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(d.level == "warning" for d in self.diagnostics)
    
    def get_report(self) -> str:
        """Get formatted report string."""
        if not self.diagnostics:
            return "No diagnostics to report."
        
        lines = []
        errors = [d for d in self.diagnostics if d.level == "error"]
        warnings = [d for d in self.diagnostics if d.level == "warning"]
        infos = [d for d in self.diagnostics if d.level == "info"]
        
        if errors:
            lines.append("ERRORS:")
            for err in errors:
                lines.append(f"  [{err.period}] {err.category}: {err.message}")
        
        if warnings:
            lines.append("\nWARNINGS:")
            for warn in warnings:
                lines.append(f"  [{warn.period}] {warn.category}: {warn.message}")
        
        if infos:
            lines.append("\nINFO:")
            for info in infos:
                lines.append(f"  [{info.period}] {info.category}: {info.message}")
        
        return "\n".join(lines)


@dataclass
class ModelResults:
    """Container for all projected financial statements."""
    periods: List[str]
    income_statements: List[IncomeStatement]
    balance_sheets: List[BalanceSheet]
    cash_flow_statements: List[CashFlowStatement]


class ModelValidator:
    """Validates financial model integrity."""
    
    # Thresholds for validation
    NEGATIVE_CASH_THRESHOLD = -10_000_000_000.0  # Allow negative cash up to -$10B (some large companies can have this)
    UNREALISTIC_MARGIN_THRESHOLD = -0.5  # Gross margin below -50% is unrealistic
    BALANCE_TOLERANCE = 0.01  # Allowed difference for balance check
    
    def validate_all(self, results: ModelResults) -> DiagnosticsReport:
        """
        Run all validation checks.
        
        Args:
            results: ModelResults object containing all projections
            
        Returns:
            DiagnosticsReport with all findings
        """
        report = DiagnosticsReport()
        
        # Validate balance sheets balance
        self._validate_balance_sheets(results, report)
        
        # Check for negative cash
        self._validate_cash_balances(results, report)
        
        # Check for unrealistic margins
        self._validate_margins(results, report)
        
        # Check for logical inconsistencies
        self._validate_logical_consistency(results, report)
        
        return report
    
    def _validate_balance_sheets(self, results: ModelResults, 
                                 report: DiagnosticsReport) -> None:
        """Validate that all balance sheets balance."""
        for bs in results.balance_sheets:
            if not bs.check_balance(self.BALANCE_TOLERANCE):
                imbalance = bs.total_assets - bs.total_liabilities_and_equity
                report.add(
                    "error",
                    "Balance Sheet",
                    bs.period,
                    f"Balance sheet does not balance. Imbalance: {imbalance:.2f}"
                )
    
    def _validate_cash_balances(self, results: ModelResults,
                                report: DiagnosticsReport) -> None:
        """Check for negative cash balances."""
        for i, bs in enumerate(results.balance_sheets):
            # Check if starting cash was already negative (from historical data)
            starting_cash_negative = False
            if i == 0 and abs(bs.cash) > 1_000_000:
                # First period - check if this is from historical data
                # If cash is very negative, it might be legitimate (e.g., company in distress)
                starting_cash_negative = bs.cash < -1_000_000
            
            if bs.cash < self.NEGATIVE_CASH_THRESHOLD:
                # Check if this is due to starting with zero revenue
                if results.income_statements and results.income_statements[0].revenue <= 0:
                    report.add(
                        "error",
                        "Cash Balance",
                        bs.period,
                        f"Cash balance is critically negative: {bs.cash:.2f}. "
                        f"This may be due to starting with zero revenue. "
                        f"Please use a company with positive historical revenue."
                    )
                elif starting_cash_negative and i == 0:
                    # Starting cash was negative - this is a warning, not an error
                    report.add(
                        "warning",
                        "Cash Balance",
                        bs.period,
                        f"Starting cash balance is negative: {bs.cash:.2f}. "
                        f"This may indicate financial distress in historical data."
                    )
                else:
                    report.add(
                        "error",
                        "Cash Balance",
                        bs.period,
                        f"Cash balance is critically negative: {bs.cash:.2f}"
                    )
            elif bs.cash < 0:
                report.add(
                    "warning",
                    "Cash Balance",
                    bs.period,
                    f"Cash balance is negative: {bs.cash:.2f}"
                )
    
    def _validate_margins(self, results: ModelResults,
                          report: DiagnosticsReport) -> None:
        """Check for unrealistic profit margins."""
        for is_stmt in results.income_statements:
            if is_stmt.revenue == 0:
                continue
            
            gross_margin_pct = (is_stmt.gross_profit / is_stmt.revenue) * 100
            if gross_margin_pct < self.UNREALISTIC_MARGIN_THRESHOLD * 100:
                report.add(
                    "warning",
                    "Margin",
                    is_stmt.period,
                    f"Gross margin is very negative: {gross_margin_pct:.1f}%"
                )
            
            net_margin_pct = (is_stmt.net_income / is_stmt.revenue) * 100
            if net_margin_pct < -100:
                report.add(
                    "error",
                    "Margin",
                    is_stmt.period,
                    f"Net margin is extremely negative: {net_margin_pct:.1f}%"
                )
    
    def _validate_logical_consistency(self, results: ModelResults,
                                     report: DiagnosticsReport) -> None:
        """Check for logical inconsistencies across statements."""
        for i, period in enumerate(results.periods):
            is_stmt = results.income_statements[i]
            bs = results.balance_sheets[i]
            cf = results.cash_flow_statements[i]
            
            # Check that Net Income matches across statements
            if abs(is_stmt.net_income - cf.net_income) > 0.01:
                report.add(
                    "error",
                    "Consistency",
                    period,
                    f"Net Income mismatch: IS={is_stmt.net_income:.2f}, "
                    f"CF={cf.net_income:.2f}"
                )
            
            # Check that Depreciation matches
            if abs(is_stmt.depreciation - cf.depreciation) > 0.01:
                report.add(
                    "error",
                    "Consistency",
                    period,
                    f"Depreciation mismatch: IS={is_stmt.depreciation:.2f}, "
                    f"CF={cf.depreciation:.2f}"
                )
            
            # Check that working capital components match
            if i < len(results.balance_sheets):
                # AR should match
                # (This assumes working capital is properly linked)
                pass  # Can add more checks as needed

