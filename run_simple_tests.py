#!/usr/bin/env python3
"""
Simple test runner for the modular gaze tracking system.
"""

import unittest
import sys
from pathlib import Path

# Add src to Python path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))


def run_simple_tests():
    """Run simple tests that don't require external dependencies."""
    print("=" * 60)
    print("Running Simple Tests for Modular Gaze Tracking System")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add simple tests
    suite.addTests(loader.loadTestsFromName('tests.unit.test_config_manager_simple'))
    suite.addTests(loader.loadTestsFromName('tests.unit.test_event_bus_simple'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Simple Tests: {'PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 60)
    
    return result.wasSuccessful()


def main():
    """Main test runner function."""
    success = run_simple_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 