"""
Working Capital Model.

Calculates Accounts Receivable, Inventory, and Accounts Payable
based on operational days (DSO, DIO, DPO).
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class WorkingCapital:
    """Working capital components for a single period."""
    period: str
    accounts_receivable: float = 0.0
    inventory: float = 0.0
    accounts_payable: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for export."""
        return {
            "Period": self.period,
            "Accounts Receivable": self.accounts_receivable,
            "Inventory": self.inventory,
            "Accounts Payable": self.accounts_payable
        }


class WorkingCapitalEngine:
    """Calculates working capital components using operational days."""
    
    def __init__(self, assumptions: Dict[str, Any]):
        """
        Initialize the Working Capital engine.
        
        Args:
            assumptions: Dictionary of financial assumptions
        """
        self.assumptions = assumptions
    
    def calculate(self, periods: List[str], 
                  revenues: List[float], 
                  cogs_list: List[float]) -> List[WorkingCapital]:
        """
        Calculate working capital for multiple periods.
        
        Args:
            periods: List of period identifiers
            revenues: List of revenues for each period
            cogs_list: List of COGS for each period
            
        Returns:
            List of WorkingCapital objects
            
        Raises:
            ValueError: If inputs are invalid or assumptions missing
        """
        if len(periods) != len(revenues) or len(periods) != len(cogs_list):
            raise ValueError(
                "Periods, revenues, and COGS lists must have same length"
            )
        
        if not periods:
            raise ValueError("Periods list cannot be empty")
        
        working_capital_list = []
        
        for i, period in enumerate(periods):
            wc = self._calculate_single_period(
                period, 
                revenues[i], 
                cogs_list[i]
            )
            working_capital_list.append(wc)
        
        return working_capital_list
    
    def _calculate_single_period(self, period: str, revenue: float, 
                                 cogs: float) -> WorkingCapital:
        """
        Calculate working capital for a single period.
        
        Formulas:
        - AR = Revenue * (DSO / 365)
        - Inventory = COGS * (DIO / 365)
        - AP = COGS * (DPO / 365)
        
        Args:
            period: Period identifier
            revenue: Revenue for the period
            cogs: COGS for the period
            
        Returns:
            WorkingCapital object
        """
        wc = WorkingCapital(period=period)
        
        # Accounts Receivable: based on DSO
        dso = self.assumptions["dso"]
        wc.accounts_receivable = revenue * (dso / 365.0)
        
        # Inventory: based on DIO
        dio = self.assumptions["dio"]
        wc.inventory = cogs * (dio / 365.0)
        
        # Accounts Payable: based on DPO
        dpo = self.assumptions["dpo"]
        wc.accounts_payable = cogs * (dpo / 365.0)
        
        return wc
    
    def calculate_changes(self, working_capital_list: List[WorkingCapital]) -> List[Dict[str, float]]:
        """
        Calculate period-over-period changes in working capital.
        
        Args:
            working_capital_list: List of WorkingCapital objects
            
        Returns:
            List of dictionaries with change values
        """
        changes = []
        
        for i, wc in enumerate(working_capital_list):
            change_dict = {"Period": wc.period}
            
            if i == 0:
                # First period: assume no prior period (change is 0 or use historical)
                change_dict["Change in AR"] = 0.0
                change_dict["Change in Inventory"] = 0.0
                change_dict["Change in AP"] = 0.0
            else:
                prev_wc = working_capital_list[i - 1]
                change_dict["Change in AR"] = wc.accounts_receivable - prev_wc.accounts_receivable
                change_dict["Change in Inventory"] = wc.inventory - prev_wc.inventory
                change_dict["Change in AP"] = wc.accounts_payable - prev_wc.accounts_payable
            
            changes.append(change_dict)
        
        return changes

