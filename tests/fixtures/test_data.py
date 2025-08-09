"""
Test data and fixtures for the gaze tracking system tests.
"""

import numpy as np
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class MockFaceDetection:
    """Mock face detection data for testing."""
    box: tuple = (100, 100, 200, 200)
    crop_box: tuple = (80, 80, 240, 240)
    landmarks: Any = None
    yaw: float = 0.0
    pitch: float = 0.0
    zone: str = "Test_Zone"
    confidence: float = 0.8
    face_center: tuple = (200, 200)


@dataclass
class MockTrackedFace:
    """Mock tracked face data for testing."""
    id: int = 1
    box: tuple = (100, 100, 200, 200)
    first_seen: int = 1
    last_seen: int = 100
    missing_frames: int = 0
    gaze_history: list = None
    zone_durations: Dict[str, float] = None
    current_zone: str = "Test_Zone"
    zone_start_frame: int = 1
    confidence: float = 0.8
    
    def __post_init__(self):
        if self.gaze_history is None:
            self.gaze_history = []
        if self.zone_durations is None:
            self.zone_durations = {"Test_Zone": 3.0}


@dataclass
class MockTrackingSession:
    """Mock tracking session data for testing."""
    id: int = 1
    start_frame: int = 1
    end_frame: int = 100
    total_duration: float = 3.0
    zone_durations: Dict[str, float] = None
    gaze_history: list = None
    unique_zones_visited: list = None
    avg_confidence: float = 0.8
    total_zone_transitions: int = 2
    peak_interest_zones: list = None
    
    def __post_init__(self):
        if self.zone_durations is None:
            self.zone_durations = {"Test_Zone": 3.0}
        if self.gaze_history is None:
            self.gaze_history = []
        if self.unique_zones_visited is None:
            self.unique_zones_visited = ["Test_Zone"]
        if self.peak_interest_zones is None:
            self.peak_interest_zones = [("Test_Zone", 3.0)]


def create_test_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a test frame for testing.
    
    Args:
        width: Frame width
        height: Frame height
        
    Returns:
        Test frame as numpy array
    """
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def create_test_config() -> Dict[str, Any]:
    """Create a test configuration dictionary.
    
    Returns:
        Test configuration dictionary
    """
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


def create_test_zone_mapper():
    """Create a mock zone mapper for testing."""
    class MockZoneMapper:
        def map_to_zone(self, context):
            return "Test_Zone"
        
        def get_zones(self):
            return []
        
        def get_zone_by_name(self, name):
            class MockZone:
                def __init__(self):
                    self.color = (0, 255, 0)
            return MockZone()
    
    return MockZoneMapper()


def create_test_pose_estimator():
    """Create a mock pose estimator for testing."""
    class MockPoseEstimator:
        def estimate_pose(self, landmarks, image_shape):
            class MockHeadPose:
                def __init__(self):
                    self.yaw = 0.0
                    self.pitch = 0.0
                    self.roll = 0.0
                    self.confidence = 1.0
            return MockHeadPose()
    
    return MockPoseEstimator()


def create_test_face_tracker():
    """Create a mock face tracker for testing."""
    class MockFaceTracker:
        def __init__(self):
            self.active_faces = {1: MockTrackedFace()}
            self.completed_sessions = [MockTrackingSession()]
        
        def update(self, detected_faces, frame_count):
            pass
        
        def get_active_faces(self):
            return self.active_faces
        
        def get_completed_sessions(self):
            return self.completed_sessions
        
        def add_session_callback(self, callback):
            pass
        
        def finalize_all_sessions(self):
            pass
    
    return MockFaceTracker()


def create_test_analytics_writer():
    """Create a mock analytics writer for testing."""
    class MockAnalyticsWriter:
        def __init__(self):
            self.sessions_written = 0
            self.aggregates_written = 0
        
        def write_session(self, session_data):
            self.sessions_written += 1
        
        def write_aggregate(self, aggregate_data):
            self.aggregates_written += 1
        
        def close(self):
            pass
    
    return MockAnalyticsWriter() 