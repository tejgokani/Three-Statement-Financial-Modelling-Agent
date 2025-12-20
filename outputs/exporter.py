"""
Output Generation Module.

Exports financial model results to CSV files for audit and review.
"""

import csv
from pathlib import Path
from typing import Dict, List, Any
from validators.validator import ModelResults
from engine.income_statement import IncomeStatement
from engine.balance_sheet import BalanceSheet
from engine.cash_flow import CashFlowStatement


class OutputExporter:
    """Exports model results to structured CSV files."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize the output exporter.
        
        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_all(self, results: ModelResults, scenario_name: str) -> None:
        """
        Export all financial statements to CSV files.
        
        Args:
            results: ModelResults object containing all projections
            scenario_name: Name of scenario (for file naming)
        """
        # Export Income Statement
        self.export_income_statement(
            results.income_statements,
            scenario_name
        )
        
        # Export Balance Sheet
        self.export_balance_sheet(
            results.balance_sheets,
            scenario_name
        )
        
        # Export Cash Flow Statement
        self.export_cash_flow(
            results.cash_flow_statements,
            scenario_name
        )
    
    def export_income_statement(self, statements: List[IncomeStatement], 
                                scenario_name: str) -> None:
        """Export Income Statement to CSV."""
        filename = self.output_dir / f"income_statement_{scenario_name}.csv"
        
        if not statements:
            raise ValueError("No income statements to export")
        
        # Get all column names from first statement
        first_dict = statements[0].to_dict()
        fieldnames = list(first_dict.keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for stmt in statements:
                writer.writerow(stmt.to_dict())
        
        print(f"Exported Income Statement to {filename}")
    
    def export_balance_sheet(self, balance_sheets: List[BalanceSheet],
                            scenario_name: str) -> None:
        """Export Balance Sheet to CSV."""
        filename = self.output_dir / f"balance_sheet_{scenario_name}.csv"
        
        if not balance_sheets:
            raise ValueError("No balance sheets to export")
        
        # Get all column names from first balance sheet
        first_dict = balance_sheets[0].to_dict()
        fieldnames = list(first_dict.keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for bs in balance_sheets:
                writer.writerow(bs.to_dict())
        
        print(f"Exported Balance Sheet to {filename}")
    
    def export_cash_flow(self, cash_flow_statements: List[CashFlowStatement],
                        scenario_name: str) -> None:
        """Export Cash Flow Statement to CSV."""
        filename = self.output_dir / f"cash_flow_{scenario_name}.csv"
        
        if not cash_flow_statements:
            raise ValueError("No cash flow statements to export")
        
        # Get all column names from first statement
        first_dict = cash_flow_statements[0].to_dict()
        fieldnames = list(first_dict.keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for cf in cash_flow_statements:
                writer.writerow(cf.to_dict())
        
        print(f"Exported Cash Flow Statement to {filename}")

