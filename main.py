"""
Main entry point for the Deterministic Three-Statement Financial Modeling Engine.

This module orchestrates the financial modeling workflow:
1. Load historical data
2. Load assumptions
3. Run projections
4. Validate results
5. Generate outputs
"""

import sys
from pathlib import Path
import os
from typing import Tuple

from engine.income_statement import IncomeStatementEngine
from engine.working_capital import WorkingCapitalEngine
from engine.cash_flow import CashFlowEngine
from engine.balance_sheet import BalanceSheetEngine
from data.loader import DataLoader
from assumptions.loader import AssumptionLoader
from validators.validator import ModelValidator
from scenarios.scenario_engine import ScenarioEngine
from outputs.exporter import OutputExporter
from outputs.display import TerminalDisplay


def validate_ticker(ticker_symbol: str) -> Tuple[bool, str]:
    """
    Validate ticker symbol and get company name.
    
    Args:
        ticker_symbol: Ticker symbol to validate
        
    Returns:
        Tuple of (is_valid, company_name)
        is_valid: True if ticker exists and has data
        company_name: Company name if valid, error message if invalid
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        if not info or 'symbol' not in info:
            return False, f"Ticker '{ticker_symbol}' not found"
        
        # Check if company has financial data
        quarterly_financials = ticker.quarterly_financials
        if quarterly_financials is None or quarterly_financials.empty:
            return False, f"Ticker '{ticker_symbol}' found but has no financial data available"
        
        # Get company name
        company_name = info.get('longName') or info.get('shortName') or info.get('symbol', ticker_symbol)
        
        return True, company_name
    except Exception as e:
        return False, f"Error validating ticker: {str(e)}"


def main():
    """
    Main execution function.
    
    Raises:
        FileNotFoundError: If required input files are missing
        ValueError: If assumptions or data are invalid
        RuntimeError: If model validation fails
    """
    print("=" * 70)
    print("Deterministic Three-Statement Financial Modeling Engine")
    print("=" * 70)
    print()
    
    # Check if running interactively (TTY)
    is_interactive = sys.stdin.isatty()
    
    # Interactive ticker input with validation
    if len(sys.argv) < 2:
        if is_interactive:
            # Loop until valid ticker is entered
            while True:
                print("Enter the company ticker symbol to analyze (e.g., AAPL, MSFT, GOOGL):")
                ticker = input("Ticker: ").strip().upper()
                
                if not ticker:
                    print("❌ Error: Ticker symbol cannot be empty. Please try again.\n")
                    continue
                
                # Validate ticker
                print(f"🔍 Validating ticker '{ticker}'...")
                is_valid, company_info = validate_ticker(ticker)
                
                if is_valid:
                    print(f"✅ Found: {company_info}")
                    print()
                    break
                else:
                    print(f"❌ {company_info}")
                    print("   Please enter a valid ticker symbol.\n")
        else:
            print("Error: Ticker symbol is required.")
            print("Usage: python main.py <ticker> [assumptions_file] [scenario] [period]")
            sys.exit(1)
    else:
        ticker = sys.argv[1].strip().upper()
        
        # Validate ticker even in command-line mode
        if is_interactive:
            print(f"🔍 Validating ticker '{ticker}'...")
            is_valid, company_info = validate_ticker(ticker)
            
            if not is_valid:
                print(f"❌ {company_info}")
                print("   Please provide a valid ticker symbol.")
                sys.exit(1)
            
            print(f"✅ Found: {company_info}")
            print()
    
    # Get assumptions file
    if len(sys.argv) >= 3:
        assumptions_file = Path(sys.argv[2])
    else:
        assumptions_file = Path("assumptions/base.json")
        if not assumptions_file.exists() and is_interactive:
            print(f"Using default assumptions file: {assumptions_file}")
            print("(To use a different file, run: python main.py <ticker> <assumptions_file>)")
    
    # Get scenario
    if len(sys.argv) >= 4:
        scenario_name = sys.argv[3].lower()
    else:
        if is_interactive:
            print("\nSelect scenario:")
            print("  1. Base (baseline assumptions)")
            print("  2. Bull (optimistic - higher growth)")
            print("  3. Bear (pessimistic - lower growth)")
            scenario_choice = input("Enter choice (1-3, default: 1): ").strip()
            if scenario_choice == "2":
                scenario_name = "bull"
            elif scenario_choice == "3":
                scenario_name = "bear"
            else:
                scenario_name = "base"
        else:
            scenario_name = "base"  # Default for non-interactive
    
    # Get period
    if len(sys.argv) >= 5:
        period = sys.argv[4].lower()
    else:
        if is_interactive:
            print("\nSelect data period:")
            print("  1. Quarterly (default)")
            print("  2. Annual")
            period_choice = input("Enter choice (1-2, default: 1): ").strip()
            period = "annual" if period_choice == "2" else "quarterly"
        else:
            period = "quarterly"  # Default for non-interactive
    
    print()
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Ticker: {ticker}")
    print(f"  Assumptions: {assumptions_file}")
    print(f"  Scenario: {scenario_name}")
    print(f"  Period: {period}")
    print("=" * 70)
    print()
    
    # Validate assumptions file exists
    if not assumptions_file.exists():
        raise FileNotFoundError(f"Assumptions file not found: {assumptions_file}")
    
    # Load historical data from Yahoo Finance
    # Company name already validated, so proceed with data loading
    print(f"📊 Fetching financial data for {ticker} from Yahoo Finance...")
    print("   Loading historical statements...")
    try:
        data_loader = DataLoader(ticker, period=period)
        historical_data = data_loader.load_all()
        
        # Show what was loaded
        if historical_data.income_statement:
            last_period = historical_data.income_statement.periods[-1]
            last_revenue = historical_data.income_statement.get_value("Revenue", last_period)
            print(f"   ✓ Last historical period: {last_period}")
            if last_revenue >= 1_000_000_000:
                print(f"   ✓ Last historical revenue: ${last_revenue/1_000_000_000:.2f}B")
            elif last_revenue >= 1_000_000:
                print(f"   ✓ Last historical revenue: ${last_revenue/1_000_000:.2f}M")
            else:
                print(f"   ✓ Last historical revenue: ${last_revenue:,.2f}")
            
            # Warn if revenue is zero or very small
            if last_revenue <= 0:
                print()
                print("   ⚠️  WARNING: Last historical revenue is zero or negative.")
                print("   ⚠️  This company may be pre-revenue or have insufficient data.")
                print("   ⚠️  Projections may not be meaningful.")
                print()
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print()
        print("❌ ERROR: Failed to fetch financial data")
        print(f"   {str(e)}")
        print()
        print("💡 Suggestions:")
        print("   - Verify the ticker symbol is correct (e.g., AAPL, MSFT, GOOGL)")
        print("   - Some tickers may not have complete financial data available")
        print("   - Try a different ticker or check Yahoo Finance for data availability")
        print()
        
        # If interactive, ask if user wants to try again
        if is_interactive:
            retry = input("Would you like to try a different ticker? (y/n): ").strip().lower()
            if retry == 'y':
                # Restart the program
                main()
                return
        sys.exit(1)
    
    # Load assumptions
    print("⚙️  Loading assumptions...")
    assumption_loader = AssumptionLoader(assumptions_file)
    assumptions = assumption_loader.load()
    print("   ✓ Assumptions loaded successfully")
    print(f"   - Revenue Growth: {assumptions['revenue_growth']*100:.1f}%")
    print(f"   - Gross Margin: {assumptions['gross_margin']*100:.1f}%")
    print(f"   - Tax Rate: {assumptions['tax_rate']*100:.1f}%")
    print()
    
    # Run scenario
    print(f"🔮 Running {scenario_name.upper()} scenario...")
    print("   Calculating projections...")
    print("   - Income Statement projections...")
    try:
        scenario_engine = ScenarioEngine(
            historical_data=historical_data,
            assumptions=assumptions,
            scenario_name=scenario_name
        )
        
        results = scenario_engine.run()
        print("   - Balance Sheet projections...")
        print("   - Cash Flow projections...")
        print(f"   ✓ Projected {len(results.periods)} periods: {', '.join(results.periods)}")
        print()
    except ValueError as e:
        if "zero or negative revenue" in str(e).lower():
            print()
            print("❌ ERROR: Cannot project from zero or negative revenue")
            print(f"   {str(e)}")
            print()
            print("💡 This company may be:")
            print("   - Pre-revenue (startup without sales yet)")
            print("   - Have incomplete financial data")
            print("   - In a restructuring phase")
            print()
            print("💡 Suggestions:")
            print("   - Try a different ticker with positive historical revenue")
            print("   - Use a company that has been operating for at least a few quarters")
            print()
            if is_interactive:
                retry = input("Would you like to try a different ticker? (y/n): ").strip().lower()
                if retry == 'y':
                    main()
                    return
            sys.exit(1)
        else:
            raise
    
    # Validate results
    print("✅ Validating model results...")
    validator = ModelValidator()
    diagnostics = validator.validate_all(results)
    
    if diagnostics.has_errors():
        print("❌ ERROR: Model validation failed!")
        print(diagnostics.get_report())
        raise RuntimeError("Model validation failed. See diagnostics above.")
    
    if diagnostics.has_warnings():
        print("⚠️  WARNING: Model validation produced warnings:")
        print(diagnostics.get_report())
        print()
    else:
        print("   ✓ All validations passed")
        print()
    
    # Display results in terminal
    print("📊 Displaying financial statements...")
    TerminalDisplay.display_all(results, scenario_name)
    
    # Export outputs
    print("\n📁 Exporting results to CSV files...")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    exporter = OutputExporter(output_dir)
    exporter.export_all(results, scenario_name)
    
    print()
    print("=" * 100)
    print("✅ MODEL EXECUTION COMPLETE")
    print("=" * 100)
    print(f"Company: {ticker}")
    print(f"Scenario: {scenario_name.upper()}")
    print(f"Periods projected: {len(results.periods)}")
    print()
    print(f"Results exported to: {output_dir}/")
    print(f"  - income_statement_{scenario_name}.csv")
    print(f"  - balance_sheet_{scenario_name}.csv")
    print(f"  - cash_flow_{scenario_name}.csv")
    print("=" * 100)


if __name__ == "__main__":
    main()

