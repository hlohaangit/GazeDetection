# Test Suite for Modular Gaze Tracking System

This directory contains comprehensive unit and integration tests for the modular gaze tracking system.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_config_manager.py
│   ├── test_event_bus.py
│   ├── test_visualizer.py
│   └── test_frame_processor.py
├── integration/             # Integration tests for component interactions
│   └── test_pipeline_integration.py
├── fixtures/                # Test data and mock objects
│   └── test_data.py
├── run_tests.py            # Test runner script
├── test_config.py          # Pytest configuration
└── README.md               # This file
```

## Running Tests

### Using the Test Runner

```bash
# Run all tests
python tests/run_tests.py

# Run specific test file
python tests/run_tests.py tests.unit.test_config_manager

# Run specific test case
python tests/run_tests.py tests.unit.test_config_manager.TestConfigManager.test_init
```

### Using Pytest

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests with verbose output
pytest -v tests/

# Run tests with coverage
pytest --cov=src tests/
```

### Using unittest directly

```bash
# Run all tests
python -m unittest discover tests/

# Run specific test file
python -m unittest tests.unit.test_config_manager

# Run specific test case
python -m unittest tests.unit.test_config_manager.TestConfigManager.test_init
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **`test_config_manager.py`**: Tests for configuration management
- **`test_event_bus.py`**: Tests for event-driven communication
- **`test_visualizer.py`**: Tests for visualization components
- **`test_frame_processor.py`**: Tests for frame processing logic

### Integration Tests

Integration tests verify that components work together correctly:

- **`test_pipeline_integration.py`**: Tests for the complete pipeline

### Test Fixtures

The `fixtures/` directory contains reusable test data and mock objects:

- **`test_data.py`**: Mock objects and test data generators

## Test Coverage

The test suite covers:

### Core Components
- ✅ Configuration management
- ✅ Event bus communication
- ✅ Interface implementations

### Processing Components
- ✅ Frame processing coordination
- ✅ Video processing integration
- ✅ Face detection integration

### Visualization Components
- ✅ Drawing operations
- ✅ Zone boundary rendering
- ✅ Status information display

### Pipeline Integration
- ✅ Component initialization
- ✅ Dependency injection
- ✅ Configuration management
- ✅ Error handling

## Writing New Tests

### Unit Test Template

```python
"""
Unit tests for [Component Name].
"""

import unittest
from unittest.mock import Mock, patch
from src.[module].[component] import [ComponentClass]
from tests.fixtures.test_data import create_test_config


class Test[ComponentClass](unittest.TestCase):
    """Test cases for the [ComponentClass] class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = create_test_config()
        self.component = [ComponentClass](self.config)
    
    def test_init(self):
        """Test component initialization."""
        self.assertIsNotNone(self.component)
        # Add specific assertions
    
    def test_method_name(self):
        """Test specific method functionality."""
        # Test implementation
        pass
    
    def test_error_handling(self):
        """Test error handling scenarios."""
        # Test error cases
        pass


if __name__ == '__main__':
    unittest.main()
```

### Integration Test Template

```python
"""
Integration tests for [Component Name].
"""

import unittest
from unittest.mock import Mock, patch
from src.[module].[component] import [ComponentClass]
from tests.fixtures.test_data import create_test_config


class Test[ComponentClass]Integration(unittest.TestCase):
    """Integration tests for the [ComponentClass] class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = create_test_config()
    
    def test_component_integration(self):
        """Test component integration with other components."""
        # Test integration scenarios
        pass
    
    def test_end_to_end_workflow(self):
        """Test complete workflow."""
        # Test complete workflows
        pass


if __name__ == '__main__':
    unittest.main()
```

## Test Best Practices

### 1. **Use Descriptive Test Names**
```python
def test_config_manager_loads_json_file_successfully(self):
    """Test that config manager can load JSON configuration files."""
```

### 2. **Test One Thing at a Time**
```python
def test_get_config_returns_dict(self):
    """Test that get_config returns a dictionary."""
    
def test_get_config_returns_empty_dict_for_nonexistent_section(self):
    """Test that get_config returns empty dict for missing sections."""
```

### 3. **Use Appropriate Assertions**
```python
# Use specific assertions
self.assertEqual(actual, expected)
self.assertIsInstance(obj, expected_type)
self.assertIn(item, container)
self.assertTrue(condition)
self.assertFalse(condition)
```

### 4. **Mock External Dependencies**
```python
@patch('src.component.external_library')
def test_method_with_external_dependency(self, mock_external):
    """Test method that uses external dependency."""
    mock_external.some_method.return_value = expected_value
    # Test implementation
```

### 5. **Test Error Conditions**
```python
def test_invalid_input_raises_exception(self):
    """Test that invalid input raises appropriate exception."""
    with self.assertRaises(ValueError):
        self.component.process_invalid_input()
```

### 6. **Use Test Fixtures**
```python
def setUp(self):
    """Set up test fixtures."""
    self.config = create_test_config()
    self.component = ComponentClass(self.config)
```

## Test Data Management

### Creating Test Data

Use the fixtures in `tests/fixtures/test_data.py`:

```python
from tests.fixtures.test_data import (
    create_test_config,
    create_test_frame,
    MockFaceDetection,
    MockTrackedFace
)

def test_with_mock_data(self):
    """Test using mock data."""
    config = create_test_config()
    frame = create_test_frame(640, 480)
    face = MockFaceDetection()
```

### Temporary Files

Use `tempfile` for tests that need files:

```python
import tempfile
import json

def test_save_config(self):
    """Test saving configuration to file."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        self.component.save_config(config_path)
        # Verify file contents
    finally:
        os.unlink(config_path)
```

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python tests/run_tests.py
```

## Performance Testing

For performance-critical components, add performance tests:

```python
import time

def test_performance_benchmark(self):
    """Test component performance."""
    start_time = time.time()
    
    # Run performance test
    for _ in range(1000):
        self.component.process_data(test_data)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Assert performance requirements
    self.assertLess(duration, 1.0)  # Should complete in under 1 second
```

## Coverage Reporting

Generate coverage reports:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run -m pytest tests/

# Generate report
coverage report

# Generate HTML report
coverage html
```

## Debugging Tests

### Running Tests in Debug Mode

```python
import pdb

def test_debug_example(self):
    """Test with debugging."""
    result = self.component.process_data(test_data)
    pdb.set_trace()  # Debugger will stop here
    self.assertEqual(result, expected)
```

### Using Print Statements

```python
def test_with_debug_output(self):
    """Test with debug output."""
    result = self.component.process_data(test_data)
    print(f"Debug: result = {result}")  # Will show in test output
    self.assertEqual(result, expected)
```

This comprehensive test suite ensures the reliability and maintainability of the modular gaze tracking system. 