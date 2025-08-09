#!/usr/bin/env python3
"""
Test runner for the modular gaze tracking system.
"""

import unittest
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

# Also add the current directory for relative imports
sys.path.insert(0, str(current_dir))


def run_unit_tests():
    """Run all unit tests."""
    print("Running unit tests...")
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / 'unit'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run all integration tests."""
    print("Running integration tests...")
    
    # Discover and run integration tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / 'integration'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Modular Gaze Tracking System Tests")
    print("=" * 60)
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    print("\n" + "-" * 60)
    
    # Run integration tests
    integration_success = run_integration_tests()
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Unit Tests: {'PASSED' if unit_success else 'FAILED'}")
    print(f"Integration Tests: {'PASSED' if integration_success else 'FAILED'}")
    print(f"Overall: {'PASSED' if (unit_success and integration_success) else 'FAILED'}")
    print("=" * 60)
    
    return unit_success and integration_success


def run_specific_test(test_path):
    """Run a specific test file or test case."""
    print(f"Running specific test: {test_path}")
    
    # Convert path to module path
    if test_path.endswith('.py'):
        test_path = test_path[:-3]
    
    # Replace slashes with dots
    test_path = test_path.replace('/', '.').replace('\\', '.')
    
    # Load and run the specific test
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_path)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main test runner function."""
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        success = run_specific_test(test_path)
    else:
        # Run all tests
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 