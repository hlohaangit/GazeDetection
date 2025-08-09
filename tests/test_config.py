"""
Pytest configuration for the gaze tracking system tests.
"""

import pytest
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Mark tests based on their location
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide the test data directory."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture(scope="session")
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        'system': {
            'fps': 30.0,
            'frame_skip': 1,
            'logging_level': 'INFO'
        },
        'face_detection': {
            'detection_confidence': 0.3,
            'mesh_confidence': 0.3,
            'model_selection': 1
        },
        'face_tracking': {
            'iou_threshold': 0.3,
            'max_frames_missing': 20,
            'min_session_duration': 0.5
        },
        'pose_estimation': {
            'estimator_type': 'mediapipe',
            'yaw_multiplier': 1.5,
            'pitch_multiplier': 2.0
        },
        'zone_mapping': {
            'mapper_type': 'bakery',
            'config_path': None
        },
        'visualization': {
            'display_output': True,
            'save_output': False,
            'output_path': 'test_output.mp4'
        },
        'analytics': {
            'console_output': True,
            'database_output': False,
            'json_output': False,
            'db_path': 'test_analytics.db',
            'json_output_dir': 'test_analytics_output',
            'verbose': True
        }
    } 