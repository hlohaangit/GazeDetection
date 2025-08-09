"""
Unit tests for the visualizer component.
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch
from src.visualization.visualizer import GazeTrackingVisualizer
from tests.fixtures.test_data import (
    create_test_frame, create_test_config, create_test_zone_mapper,
    MockTrackedFace
)


class TestGazeTrackingVisualizer(unittest.TestCase):
    """Test cases for the GazeTrackingVisualizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = create_test_config()['visualization']
        self.zone_mapper = create_test_zone_mapper()
        self.visualizer = GazeTrackingVisualizer(self.config, self.zone_mapper)
        self.test_frame = create_test_frame(640, 480)
    
    def test_init(self):
        """Test visualizer initialization."""
        self.assertEqual(self.visualizer.config, self.config)
        self.assertEqual(self.visualizer.zone_mapper, self.zone_mapper)
        self.assertTrue(self.visualizer.display_output)
        self.assertFalse(self.visualizer.save_output)
    
    def test_visualize_empty_data(self):
        """Test visualization with empty tracking data."""
        data = {
            'frame_count': 1,
            'active_faces': {},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should return a frame with the same shape
        self.assertEqual(result.shape, self.test_frame.shape)
        self.assertIsInstance(result, np.ndarray)
    
    def test_visualize_with_faces(self):
        """Test visualization with tracked faces."""
        tracked_face = MockTrackedFace()
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should return a frame with the same shape
        self.assertEqual(result.shape, self.test_frame.shape)
        self.assertIsInstance(result, np.ndarray)
    
    def test_visualize_with_multiple_faces(self):
        """Test visualization with multiple tracked faces."""
        face1 = MockTrackedFace(id=1, box=(50, 50, 100, 100))
        face2 = MockTrackedFace(id=2, box=(200, 200, 150, 150))
        
        data = {
            'frame_count': 100,
            'active_faces': {1: face1, 2: face2},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should return a frame with the same shape
        self.assertEqual(result.shape, self.test_frame.shape)
        self.assertIsInstance(result, np.ndarray)
    
    def test_visualize_with_completed_sessions(self):
        """Test visualization with completed sessions."""
        tracked_face = MockTrackedFace()
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': [Mock()]  # Mock session
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should return a frame with the same shape
        self.assertEqual(result.shape, self.test_frame.shape)
        self.assertIsInstance(result, np.ndarray)
    
    def test_draw_face(self):
        """Test drawing individual face visualization."""
        face_data = MockTrackedFace()
        frame = self.test_frame.copy()
        
        # Should not raise an exception
        self.visualizer._draw_face(frame, 1, face_data, 100)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_draw_face_with_info_box_above(self):
        """Test drawing face with info box positioned above."""
        face_data = MockTrackedFace(box=(100, 200, 100, 100))  # Face below top
        frame = self.test_frame.copy()
        
        # Should not raise an exception
        self.visualizer._draw_face(frame, 1, face_data, 100)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_draw_face_with_info_box_below(self):
        """Test drawing face with info box positioned below."""
        face_data = MockTrackedFace(box=(100, 50, 100, 100))  # Face near top
        frame = self.test_frame.copy()
        
        # Should not raise an exception
        self.visualizer._draw_face(frame, 1, face_data, 100)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_draw_zone_boundaries(self):
        """Test drawing zone boundaries."""
        frame = self.test_frame.copy()
        
        # Should not raise an exception
        self.visualizer._draw_zone_boundaries(frame)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_draw_status(self):
        """Test drawing status information."""
        frame = self.test_frame.copy()
        
        # Should not raise an exception
        self.visualizer._draw_status(frame, 100, 2, 5)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_draw_status_with_fps(self):
        """Test drawing status with FPS calculation."""
        frame = self.test_frame.copy()
        
        # Set up FPS calculation
        self.visualizer._last_frame_time = 0
        
        # Should not raise an exception
        self.visualizer._draw_status(frame, 100, 2, 5)
        
        # Frame should still have the same shape
        self.assertEqual(frame.shape, self.test_frame.shape)
    
    def test_visualize_different_frame_sizes(self):
        """Test visualization with different frame sizes."""
        sizes = [(320, 240), (1280, 720), (1920, 1080)]
        
        for width, height in sizes:
            frame = create_test_frame(width, height)
            data = {
                'frame_count': 1,
                'active_faces': {},
                'completed_sessions': []
            }
            
            result = self.visualizer.visualize(frame, data)
            self.assertEqual(result.shape, frame.shape)
    
    def test_visualize_with_long_zone_name(self):
        """Test visualization with long zone names."""
        tracked_face = MockTrackedFace(
            current_zone="Very_Long_Zone_Name_That_Should_Be_Truncated_For_Display"
        )
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should not raise an exception and should handle long zone names
        self.assertEqual(result.shape, self.test_frame.shape)
    
    def test_visualize_with_zero_confidence(self):
        """Test visualization with zero confidence face."""
        tracked_face = MockTrackedFace(confidence=0.0)
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should handle zero confidence gracefully
        self.assertEqual(result.shape, self.test_frame.shape)
    
    def test_visualize_with_large_face_box(self):
        """Test visualization with face box larger than frame."""
        tracked_face = MockTrackedFace(box=(0, 0, 1000, 1000))  # Larger than frame
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': []
        }
        
        result = self.visualizer.visualize(self.test_frame, data)
        
        # Should handle oversized boxes gracefully
        self.assertEqual(result.shape, self.test_frame.shape)
    
    def test_config_overrides(self):
        """Test that configuration overrides work correctly."""
        config = {
            'display_output': False,
            'save_output': True,
            'output_path': 'custom_output.mp4'
        }
        
        visualizer = GazeTrackingVisualizer(config, self.zone_mapper)
        
        self.assertFalse(visualizer.display_output)
        self.assertTrue(visualizer.save_output)
    
    def test_zone_mapper_integration(self):
        """Test integration with zone mapper."""
        # Mock zone mapper that returns a zone with color
        mock_zone = Mock()
        mock_zone.color = (255, 0, 0)  # Red color
        
        zone_mapper = Mock()
        zone_mapper.get_zone_by_name.return_value = mock_zone
        
        visualizer = GazeTrackingVisualizer(self.config, zone_mapper)
        
        tracked_face = MockTrackedFace()
        data = {
            'frame_count': 100,
            'active_faces': {1: tracked_face},
            'completed_sessions': []
        }
        
        result = visualizer.visualize(self.test_frame, data)
        
        # Should use the zone mapper to get zone information
        zone_mapper.get_zone_by_name.assert_called_with(tracked_face.current_zone)
        self.assertEqual(result.shape, self.test_frame.shape)


if __name__ == '__main__':
    unittest.main() 