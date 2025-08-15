#!/usr/bin/env python3
"""
Test runner script for the Meetings Service.

This script runs all tests with proper configuration and provides
a summary of test results.
"""

import sys
import os
import subprocess
from pathlib import Path


def main() -> int:
    """Run the test suite."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests"
    
    # Change to the tests directory
    os.chdir(tests_dir)
    
    print("🧪 Running Meetings Service Tests")
    print("=" * 50)
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
        "--color=yes",  # Colored output
        "test_*.py"  # Test all test files
    ]
    
    try:
        # Run the tests
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        # Return the exit code
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
