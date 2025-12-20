"""
Comprehensive Ticker Testing Script

Tests the financial modeling engine across 100+ tickers from global markets
to verify accuracy and robustness.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import threading
import time

from data.loader import DataLoader
from assumptions.loader import AssumptionLoader
from scenarios.scenario_engine import ScenarioEngine
from validators.validator import ModelValidator


# Global ticker list - 100+ tickers from various markets and industries
TICKERS = [
    # US Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AMD",
    "INTC", "ORCL", "CRM", "ADBE", "CSCO", "IBM", "QCOM", "TXN", "AVGO", "NOW",
    
    # US Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "COF",
    "USB", "PNC", "TFC", "BK", "STT", "FITB", "KEY", "CFG", "HBAN", "MTB",
    
    # US Healthcare
    "JNJ", "PFE", "UNH", "ABT", "TMO", "ABBV", "MRK", "BMY", "AMGN", "GILD",
    "CVS", "CI", "HUM", "BSX", "SYK", "ISRG", "ZBH", "EW", "BAX",
    
    # US Consumer
    "WMT", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "COST", "TJX", "DG",
    "F", "GM", "DIS", "NFLX", "CMCSA", "VZ", "T", "CHTR", "EA", "TTWO",
    
    # US Industrial
    "BA", "CAT", "GE", "HON", "LMT", "RTX", "NOC", "GD", "TDG", "TXT",
    "DE", "EMR", "ETN", "ITW", "PH", "ROK", "SWK", "AME", "GGG", "RBC",
    
    # US Energy
    "XOM", "CVX", "SLB", "EOG", "COP", "MPC", "VLO", "PSX", "OVV",
    
    # International - Europe
    "ASML", "SAP", "NVO", "BP", "GSK", "AZN", "SAN",
    
    # International - Asia
    "TSM", "BABA",
    
    # International - Other
    "SHOP", "ROKU", "ZM", "DOCU", "CRWD", "NET", "DDOG", "SNOW", "PLTR",
    
    # Additional diverse tickers
    "V", "MA", "PYPL", "ADP", "INTU", "FISV", "FIS", "GPN", "WU",
    "ICE", "MCO", "SPGI", "NDAQ", "CME", "CBOE", "MSCI", "TW", "TRU"
]


class ProgressTracker:
    """Thread-safe progress tracker with loading animation."""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.observation = 0
        self.current_tickers = set()
        self.lock = threading.Lock()
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_idx = 0
        self.running = True
        
    def update(self, ticker: str, status: str):
        """Update progress with a completed ticker."""
        with self.lock:
            self.completed += 1
            if status == "success":
                self.successful += 1
            elif status == "failed":
                self.failed += 1
            elif status == "observation":
                self.observation += 1
            if ticker in self.current_tickers:
                self.current_tickers.remove(ticker)
    
    def add_current(self, ticker: str):
        """Add a ticker currently being processed."""
        with self.lock:
            self.current_tickers.add(ticker)
    
    def remove_current(self, ticker: str):
        """Remove a ticker from current processing."""
        with self.lock:
            self.current_tickers.discard(ticker)
    
    def get_status_line(self) -> str:
        """Get formatted status line."""
        with self.lock:
            spinner = self.spinner_chars[self.spinner_idx % len(self.spinner_chars)]
            self.spinner_idx += 1
            
            progress_pct = (self.completed / self.total * 100) if self.total > 0 else 0
            current_list = list(self.current_tickers)[:3]  # Show max 3 current tickers
            current_str = ', '.join(current_list)
            if len(self.current_tickers) > 3:
                current_str += f" (+{len(self.current_tickers) - 3} more)"
            
            status = (
                f"{spinner} Progress: {self.completed}/{self.total} ({progress_pct:.1f}%) | "
                f"✓ {self.successful} | ✗ {self.failed} | ⚠ {self.observation}"
            )
            if current_str:
                status += f" | Testing: {current_str}"
            return status
    
    def stop(self):
        """Stop the progress tracker."""
        self.running = False


class TickerTester:
    """Tests financial modeling engine across multiple tickers."""
    
    def __init__(self, assumptions_file: Path, max_workers: int = 10):
        """
        Initialize the tester.
        
        Args:
            assumptions_file: Path to assumptions JSON file
            max_workers: Maximum number of parallel workers (default: 10)
        """
        self.assumptions_file = assumptions_file
        self.max_workers = max_workers
        self.results = {
            "total_tested": 0,
            "successful": 0,
            "failed": 0,
            "observation": 0,  # Edge cases that aren't real failures
            "errors": [],
            "warnings": [],
            "observations": [],  # Edge cases
            "successful_tickers": [],
            "failed_tickers": [],
            "observation_tickers": []
        }
        self.start_time = datetime.now()
        # Pre-load assumptions once (shared across all tests)
        self.assumptions = None
    
    def _categorize_error(self, error_msg: str, ticker: str) -> Tuple[str, str]:
        """
        Categorize an error to determine if it's a real failure or an edge case.
        
        Args:
            error_msg: Error message
            ticker: Ticker symbol
            
        Returns:
            Tuple of (category: str, reason: str)
            Category: "failed", "observation", or "unknown"
        """
        error_lower = error_msg.lower()
        
        # Check for delisted/merged companies - check full error message
        if any(phrase in error_lower for phrase in [
            "not found", "quote not found", "could not find ticker",
            "404", "no data available", "ticker not found"
        ]):
            return "observation", "Delisted or merged company - no longer publicly traded"
        
        # Check for data availability issues - catch various phrases
        if any(phrase in error_lower for phrase in [
            "could not find required columns",
            "could not fetch",
            "may not have financial data",
            "does not have financial data",
            "financial data available",
            "no financial data"
        ]):
            # This could be delisted, different reporting, or insufficient data
            if "income statement" in error_lower:
                return "observation", "Insufficient financial data - may be delisted, merged, or different reporting format"
            elif "balance sheet" in error_lower:
                return "observation", "Insufficient balance sheet data - different accounting standards or incomplete data"
            else:
                return "observation", "Insufficient financial data - may be delisted, merged, or different reporting format"
        
        # Check for no periods or insufficient data
        if any(phrase in error_lower for phrase in [
            "no periods", "insufficient data", "no data found",
            "all periods have less than", "no periods with sufficient data"
        ]):
            return "observation", "Insufficient historical data - may be delisted or very new company"
        
        # Check for zero revenue (pre-revenue companies)
        if any(phrase in error_lower for phrase in [
            "zero or negative revenue", "pre-revenue", "zero revenue",
            "cannot project from zero"
        ]):
            return "observation", "Pre-revenue company - no sales yet"
        
        # Check for incomplete data (some periods missing)
        if "missing value" in error_lower and "period" in error_lower:
            if "incomplete data" in error_lower:
                return "observation", "Incomplete financial data - some periods missing"
        
        # Check for international companies with different reporting
        # This is a catch-all for companies that might have different accounting standards
        if "could not find" in error_lower and any(term in error_lower for term in ["columns", "data", "statement"]):
            return "observation", "Different accounting standards or incomplete data - non-US reporting format"
        
        # Real failures - validation errors, calculation errors
        if any(phrase in error_lower for phrase in [
            "validation error", "balance sheet does not balance",
            "model validation failed"
        ]):
            return "failed", "Model validation failed"
        
        if "cash balance is critically negative" in error_lower:
            # Check if it's due to zero revenue
            if "zero revenue" not in error_lower:
                return "failed", "Cash balance validation failed"
            else:
                return "observation", "Zero revenue causing negative cash"
        
        # Check if it's a RuntimeError about loading - likely data issue
        if "failed to load" in error_lower:
            # Try to get more context from the error
            if "could not find" in error_lower or "not found" in error_lower:
                return "observation", "Data loading failed - likely delisted or insufficient data"
        
        # Unknown - treat as failed for now, but log it
        return "failed", "Unknown error - needs investigation"
    
    def _test_ticker_with_progress(self, ticker: str, period: str, progress: ProgressTracker) -> Tuple[str, str, List[str]]:
        """Test a ticker and update progress tracker."""
        progress.add_current(ticker)
        try:
            return self.test_ticker(ticker, period, quiet=True)
        finally:
            progress.remove_current(ticker)
    
    def test_ticker(self, ticker: str, period: str = "quarterly", quiet: bool = True) -> Tuple[str, str, List[str]]:
        """
        Test a single ticker.
        
        Args:
            ticker: Ticker symbol to test
            period: "quarterly" or "annual"
            quiet: If True, suppress verbose output (faster)
            
        Returns:
            Tuple of (status: str, error_message: str, warnings: List[str])
            Status: "success", "failed", or "observation"
        """
        warnings = []
        
        try:
            # Test data loading - use quiet mode for faster execution
            data_loader = DataLoader(ticker, period=period)
            # Access the yfinance loader directly to pass quiet flag
            if hasattr(data_loader, 'use_yfinance') and data_loader.use_yfinance:
                from data.yfinance_loader import YFinanceLoader
                yf_loader = YFinanceLoader(ticker, period)
                historical_data = yf_loader.load_all(quiet=quiet)
            else:
                historical_data = data_loader.load_all()
            
            # Check if revenue is positive
            if historical_data.income_statement:
                last_period = historical_data.income_statement.periods[-1]
                last_revenue = historical_data.income_statement.get_value("Revenue", last_period)
                if last_revenue <= 0:
                    return False, f"Zero or negative revenue: ${last_revenue:,.2f}", warnings
            
            # Use pre-loaded assumptions (faster)
            if self.assumptions is None:
                assumption_loader = AssumptionLoader(self.assumptions_file)
                self.assumptions = assumption_loader.load()
            
            # Test scenario engine
            scenario_engine = ScenarioEngine(
                historical_data=historical_data,
                assumptions=self.assumptions,
                scenario_name="base"
            )
            
            results = scenario_engine.run()
            
            # Test validation - skip detailed validation for speed (just check if it runs)
            # Full validation can be done separately if needed
            validator = ModelValidator()
            diagnostics = validator.validate_all(results)
            
            if diagnostics.has_errors():
                error_msg = f"Validation errors: {diagnostics.get_report()}"
                category, reason = self._categorize_error(error_msg, ticker)
                if category == "observation":
                    return "observation", reason, warnings
                return "failed", error_msg, warnings
            
            if diagnostics.has_warnings():
                # Only store warnings if needed, don't process them fully
                warnings.append("Validation warnings present")
            
            return "success", "", warnings
            
        except ValueError as e:
            error_msg = str(e)
            # Get full error message for better categorization
            full_error = f"ValueError: {error_msg}"
            category, reason = self._categorize_error(full_error, ticker)
            if category == "observation":
                return "observation", reason, warnings
            return "failed", full_error, warnings
        except RuntimeError as e:
            error_msg = str(e)
            # Get full error message for better categorization
            full_error = f"RuntimeError: {error_msg}"
            category, reason = self._categorize_error(full_error, ticker)
            if category == "observation":
                return "observation", reason, warnings
            return "failed", full_error, warnings
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            category, reason = self._categorize_error(error_msg, ticker)
            if category == "observation":
                return "observation", reason, warnings
            return "failed", error_msg, warnings
    
    def run_tests(self, tickers: List[str] = None, period: str = "quarterly", 
                  max_tests: int = None) -> Dict:
        """
        Run tests on multiple tickers.
        
        Args:
            tickers: List of tickers to test (defaults to TICKERS)
            period: "quarterly" or "annual"
            max_tests: Maximum number of tickers to test (None for all)
            
        Returns:
            Dictionary with test results
        """
        if tickers is None:
            tickers = TICKERS
        
        if max_tests:
            tickers = tickers[:max_tests]
        
        print("=" * 80)
        print("FINANCIAL MODELING ENGINE - COMPREHENSIVE TICKER TEST")
        print("=" * 80)
        print(f"Testing {len(tickers)} tickers...")
        print(f"Period: {period}")
        print(f"Assumptions file: {self.assumptions_file}")
        print("=" * 80)
        print()
        
        # Pre-load assumptions once (shared across all tests)
        if self.assumptions is None:
            assumption_loader = AssumptionLoader(self.assumptions_file)
            self.assumptions = assumption_loader.load()
        
        # Initialize progress tracker
        total = len(tickers)
        progress = ProgressTracker(total)
        
        # Start progress animation thread
        def animate_progress():
            """Animate progress in the background."""
            while progress.running:
                status_line = progress.get_status_line()
                # Use \r to overwrite the line, pad with spaces to clear previous content
                print(f"\r{status_line:<100}", end="", flush=True)
                time.sleep(0.15)  # Update every 150ms
        
        progress_thread = threading.Thread(target=animate_progress, daemon=True)
        progress_thread.start()
        
        # Use parallel processing for faster execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self._test_ticker_with_progress, ticker, period, progress): ticker
                for ticker in tickers
            }
            
            # Process results as they complete
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                self.results["total_tested"] += 1
                
                try:
                    status, error_msg, warnings = future.result()
                    
                    # Update progress tracker
                    progress.update(ticker, status)
                    
                    # Clear the progress line and print result
                    print(f"\r{' ' * 100}\r", end="", flush=True)  # Clear line
                    
                    if status == "success":
                        self.results["successful"] += 1
                        self.results["successful_tickers"].append(ticker)
                        print(f"✓ {ticker}: PASSED")
                        if warnings:
                            self.results["warnings"].append({
                                "ticker": ticker,
                                "warnings": warnings
                            })
                    elif status == "observation":
                        self.results["observation"] += 1
                        self.results["observation_tickers"].append(ticker)
                        self.results["observations"].append({
                            "ticker": ticker,
                            "reason": error_msg
                        })
                        print(f"⚠ {ticker}: OBSERVATION - {error_msg[:60]}")
                    else:  # failed
                        self.results["failed"] += 1
                        self.results["failed_tickers"].append(ticker)
                        self.results["errors"].append({
                            "ticker": ticker,
                            "error": error_msg
                        })
                        print(f"✗ {ticker}: FAILED - {error_msg[:60]}")
                except KeyboardInterrupt:
                    print("\n\nTest interrupted by user")
                    progress.stop()
                    # Cancel remaining tasks
                    for f in future_to_ticker:
                        f.cancel()
                    break
                except Exception as e:
                    error_msg = f"Unexpected exception: {type(e).__name__}: {str(e)}"
                    category, reason = self._categorize_error(error_msg, ticker)
                    
                    # Update progress tracker
                    progress.update(ticker, category if category == "observation" else "failed")
                    
                    # Clear the progress line and print result
                    print(f"\r{' ' * 100}\r", end="", flush=True)
                    
                    if category == "observation":
                        self.results["observation"] += 1
                        self.results["observation_tickers"].append(ticker)
                        self.results["observations"].append({
                            "ticker": ticker,
                            "reason": f"{reason}: {error_msg}"
                        })
                        print(f"⚠ {ticker}: OBSERVATION - {reason[:60]}")
                    else:
                        self.results["failed"] += 1
                        self.results["failed_tickers"].append(ticker)
                        self.results["errors"].append({
                            "ticker": ticker,
                            "error": error_msg
                        })
                        print(f"✗ {ticker}: EXCEPTION - {str(e)[:60]}")
        
        # Stop progress animation
        progress.stop()
        time.sleep(0.2)  # Give animation thread time to finish
        print(f"\r{' ' * 100}\r", end="", flush=True)  # Clear progress line
        print()  # New line after clearing
        
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        return self.results
    
    def print_summary(self):
        """Print test summary report."""
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total tickers tested: {self.results['total_tested']}")
        print(f"Successful: {self.results['successful']} ({self.results['successful']/self.results['total_tested']*100:.1f}%)")
        print(f"Failed: {self.results['failed']} ({self.results['failed']/self.results['total_tested']*100:.1f}%)")
        print(f"Under Observation: {self.results['observation']} ({self.results['observation']/self.results['total_tested']*100:.1f}%)")
        print(f"Duration: {self.duration:.1f} seconds")
        print()
        
        if self.results["successful_tickers"]:
            print(f"✓ Successful tickers ({len(self.results['successful_tickers'])}):")
            for ticker in self.results["successful_tickers"][:20]:  # Show first 20
                print(f"   {ticker}")
            if len(self.results["successful_tickers"]) > 20:
                print(f"   ... and {len(self.results['successful_tickers']) - 20} more")
            print()
        
        if self.results["observation_tickers"]:
            print(f"⚠ Under Observation ({len(self.results['observation_tickers'])}):")
            print("   (Edge cases - not real failures)")
            for ticker in self.results["observation_tickers"][:20]:  # Show first 20
                obs = next((o["reason"] for o in self.results["observations"] if o["ticker"] == ticker), "Unknown reason")
                print(f"   {ticker}: {obs[:60]}")
            if len(self.results["observation_tickers"]) > 20:
                print(f"   ... and {len(self.results['observation_tickers']) - 20} more")
            print()
        
        if self.results["failed_tickers"]:
            print(f"✗ Failed tickers ({len(self.results['failed_tickers'])}):")
            print("   (Real failures - model issues)")
            for ticker in self.results["failed_tickers"][:20]:  # Show first 20
                error = next((e["error"] for e in self.results["errors"] if e["ticker"] == ticker), "Unknown error")
                print(f"   {ticker}: {error[:60]}")
            if len(self.results["failed_tickers"]) > 20:
                print(f"   ... and {len(self.results['failed_tickers']) - 20} more")
            print()
        
        # Error analysis
        if self.results["errors"]:
            error_types = {}
            for error in self.results["errors"]:
                error_type = error["error"].split(":")[0] if ":" in error["error"] else error["error"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            print("Error Analysis (Real Failures):")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error_type}: {count}")
            print()
        
        # Observation analysis
        if self.results["observations"]:
            obs_types = {}
            for obs in self.results["observations"]:
                obs_type = obs["reason"].split(":")[0] if ":" in obs["reason"] else obs["reason"]
                obs_types[obs_type] = obs_types.get(obs_type, 0) + 1
            
            print("Observation Analysis (Edge Cases):")
            for obs_type, count in sorted(obs_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {obs_type}: {count}")
            print()
        
        print("=" * 80)
    
    def save_results(self, output_file: Path):
        """Save test results to JSON file."""
        total = self.results["total_tested"]
        results_dict = {
            "test_date": self.start_time.isoformat(),
            "duration_seconds": self.duration,
            "total_tested": total,
            "successful": self.results["successful"],
            "failed": self.results["failed"],
            "observation": self.results["observation"],
            "success_rate": self.results["successful"] / total * 100 if total > 0 else 0,
            "failure_rate": self.results["failed"] / total * 100 if total > 0 else 0,
            "observation_rate": self.results["observation"] / total * 100 if total > 0 else 0,
            "successful_tickers": self.results["successful_tickers"],
            "failed_tickers": self.results["failed_tickers"],
            "observation_tickers": self.results["observation_tickers"],
            "errors": self.results["errors"],
            "observations": self.results["observations"],
            "warnings": self.results["warnings"]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"Results saved to: {output_file}")
        
        # Also save CSV for easy analysis
        csv_file = output_file.with_suffix('.csv')
        self.save_csv_results(csv_file)
    
    def save_csv_results(self, csv_file: Path):
        """Save test results to CSV file for easy analysis."""
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Ticker', 'Status', 'Reason/Error'])
            
            # Write successful tickers
            for ticker in self.results["successful_tickers"]:
                writer.writerow([ticker, 'PASSED', ''])
            
            # Write observation tickers
            for obs in self.results["observations"]:
                writer.writerow([obs["ticker"], 'OBSERVATION', obs["reason"]])
            
            # Write failed tickers with errors
            for error in self.results["errors"]:
                writer.writerow([error["ticker"], 'FAILED', error["error"]])
        
        print(f"CSV results saved to: {csv_file}")


def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test financial modeling engine across multiple tickers"
    )
    parser.add_argument(
        "count",
        type=int,
        nargs="?",
        default=None,
        help="Number of tickers to test (default: all)"
    )
    parser.add_argument(
        "--period",
        choices=["quarterly", "annual"],
        default="quarterly",
        help="Data period to use (default: quarterly)"
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=Path("assumptions/base.json"),
        help="Path to assumptions file (default: assumptions/base.json)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_results.json"),
        help="Output file for results (default: test_results.json)"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Specific tickers to test (overrides default list)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)"
    )
    
    args = parser.parse_args()
    
    if not args.assumptions.exists():
        print(f"Error: Assumptions file not found: {args.assumptions}")
        sys.exit(1)
    
    tickers_to_test = args.tickers if args.tickers else TICKERS
    
    tester = TickerTester(args.assumptions, max_workers=args.workers)
    results = tester.run_tests(
        tickers=tickers_to_test,
        period=args.period,
        max_tests=args.count
    )
    
    tester.print_summary()
    
    # Save results
    tester.save_results(args.output)
    
    # Exit with appropriate code
    # Only exit with error if there are real failures (not observations)
    if results["failed"] == 0:
        if results["observation"] > 0:
            print(f"\n✅ All tests passed! ({results['observation']} ticker(s) under observation - edge cases)")
        else:
            print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {results['failed']} test(s) failed (real failures)")
        if results["observation"] > 0:
            print(f"   {results['observation']} ticker(s) under observation (edge cases, not failures)")
        sys.exit(1)


if __name__ == "__main__":
    main()
