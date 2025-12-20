"""
Assumption Management Layer.

Loads and validates financial modeling assumptions from JSON or YAML files.
All assumptions are required - no default values are provided.
"""

import json
from pathlib import Path
from typing import Dict, Any

try:
    import yaml
except ImportError:
    yaml = None


class AssumptionLoader:
    """Loads and validates financial modeling assumptions."""
    
    REQUIRED_ASSUMPTIONS = [
        "revenue_growth",
        "gross_margin",
        "opex_ratio",
        "dso",  # Days Sales Outstanding
        "dio",  # Days Inventory Outstanding
        "dpo",  # Days Payable Outstanding
        "capex_ratio",
        "depreciation_rate",
        "tax_rate",
        "interest_rate"
    ]
    
    def __init__(self, assumptions_file: Path):
        """
        Initialize the assumption loader.
        
        Args:
            assumptions_file: Path to JSON or YAML assumptions file
            
        Raises:
            FileNotFoundError: If assumptions file does not exist
        """
        self.assumptions_file = Path(assumptions_file)
        if not self.assumptions_file.exists():
            raise FileNotFoundError(
                f"Assumptions file not found: {assumptions_file}"
            )
    
    def load(self) -> Dict[str, Any]:
        """
        Load assumptions from file.
        
        Returns:
            Dictionary of assumptions
            
        Raises:
            ValueError: If required assumptions are missing or invalid
            RuntimeError: If file format is unsupported
        """
        file_ext = self.assumptions_file.suffix.lower()
        
        if file_ext == ".json":
            assumptions = self._load_json()
        elif file_ext in [".yaml", ".yml"]:
            assumptions = self._load_yaml()
        else:
            raise RuntimeError(
                f"Unsupported file format: {file_ext}. "
                "Supported formats: .json, .yaml, .yml"
            )
        
        self._validate(assumptions)
        return assumptions
    
    def _load_json(self) -> Dict[str, Any]:
        """Load assumptions from JSON file."""
        with open(self.assumptions_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in assumptions file: {e}"
                ) from e
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load assumptions from YAML file."""
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required for YAML support. "
                "Install with: pip install pyyaml"
            )
        
        with open(self.assumptions_file, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(
                    f"Invalid YAML in assumptions file: {e}"
                ) from e
    
    def _validate(self, assumptions: Dict[str, Any]) -> None:
        """
        Validate that all required assumptions are present.
        
        Args:
            assumptions: Dictionary of assumptions to validate
            
        Raises:
            ValueError: If required assumptions are missing or invalid
        """
        if not isinstance(assumptions, dict):
            raise ValueError("Assumptions must be a dictionary")
        
        # Check for missing assumptions
        missing = [req for req in self.REQUIRED_ASSUMPTIONS 
                  if req not in assumptions]
        if missing:
            raise ValueError(
                f"Missing required assumptions: {missing}. "
                f"All of the following must be provided: {self.REQUIRED_ASSUMPTIONS}"
            )
        
        # Validate numeric assumptions are numeric
        for key in self.REQUIRED_ASSUMPTIONS:
            value = assumptions[key]
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Assumption '{key}' must be numeric, got {type(value).__name__}"
                )
            
            # Validate ranges for certain assumptions
            if key in ["revenue_growth", "gross_margin", "opex_ratio", 
                      "tax_rate"] and not (-1.0 <= value <= 1.0):
                # Allow growth to be negative (decline) but warn if extreme
                if key == "revenue_growth" and value < -0.5:
                    raise ValueError(
                        f"Assumption '{key}' has extreme negative value: {value}. "
                        "Revenue decline exceeds 50%."
                    )
            
            if key in ["dso", "dio", "dpo"] and value < 0:
                raise ValueError(
                    f"Assumption '{key}' must be non-negative, got {value}"
                )
            
            if key == "depreciation_rate" and not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"Assumption 'depreciation_rate' must be between 0 and 1, got {value}"
                )

