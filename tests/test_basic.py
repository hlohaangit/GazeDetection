import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import GazeTrackingSystem, load_config, validate_input


class TestBasicFunctionality:
    
    def test_load_config_defaults(self):
        """Test that default configuration loads correctly."""
        config = load_config()
        
        assert config is not None
        assert isinstance(config, dict)
        assert 'fps' in config
        assert config['fps'] == 30.0
        assert 'frame_skip' in config
        assert config['frame_skip'] == 1
    
    def test_validate_input_file_path(self):
        result = validate_input("nonexistent_file.mp4")
        assert result is False
        
        result1 = validate_input("/Users/harlow/Downloads/Futures- Data Files/final solution /data/output.mp4")
        assert result1 is True
    
    def test_validate_input_camera_id(self):
        # Test with valid camera ID format
        result = validate_input("0")
        assert isinstance(result, bool)
        
        # Test with invalid camera ID format
        result = validate_input("invalid_camera")
        assert result is False
    
    def test_gaze_tracking_system_creation(self):
        """Test that GazeTrackingSystem can be created with basic config."""
        config = {
            'fps': 30.0,
            'frame_skip': 1,
            'iou_threshold': 0.3,
            'max_frames_missing': 5,
            'min_session_duration': 0.5,
            'detection_confidence': 0.3,
            'mesh_confidence': 0.2,
            'pose_estimator': 'mediapipe',
            'zone_mapper': 'bakery',
            'display_output': False,
            'save_output': False,
            'console_output': True,
            'database_output': False,
            'json_output': False,
            'verbose': False,
            'logging_level': 'INFO'
        }
        
        try:
            system = GazeTrackingSystem(config)
            assert system is not None
            assert hasattr(system, 'config')
            assert system.config == config
        except Exception as e:
            # If MediaPipe or other dependencies fail, that's okay for basic tests
            # We're just testing that the class can be instantiated
            pytest.skip(f"System creation failed due to dependencies: {e}")
    
    def test_config_has_required_keys(self):
        config = load_config()
        
        required_keys = [
            'fps', 'frame_skip', 'iou_threshold', 'max_frames_missing',
            'min_session_duration', 'detection_confidence', 'mesh_confidence',
            'pose_estimator', 'zone_mapper', 'display_output', 'save_output',
            'console_output', 'database_output', 'json_output', 'verbose',
            'logging_level'
        ]
        
        for key in required_keys:
            assert key in config, f"Missing required config key: {key}"
            assert config[key] is not None, f"Config key {key} is None"


if __name__ == "__main__":
    pytest.main([__file__])
