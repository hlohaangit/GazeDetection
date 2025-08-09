"""
Unit tests for the frame processor component.
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch
from src.processing.frame_processor import FrameProcessor
from src.core.interfaces import ProcessingResult
from tests.fixtures.test_data import (
    create_test_frame, create_test_config, create_test_face_tracker,
    create_test_zone_mapper, MockFaceDetection
)


class TestFrameProcessor(unittest.TestCase):
    """Test cases for the FrameProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = create_test_config()
        self.face_tracker = create_test_face_tracker()
        self.zone_mapper = create_test_zone_mapper()
        self.frame_processor = FrameProcessor(
            self.config, self.face_tracker, self.zone_mapper
        )
        self.test_frame = create_test_frame(640, 480)
    
    def test_init(self):
        """Test frame processor initialization."""
        self.assertEqual(self.frame_processor.config, self.config)
        self.assertEqual(self.frame_processor.face_tracker, self.face_tracker)
        self.assertEqual(self.frame_processor.zone_mapper, self.zone_mapper)
        self.assertIsNone(self.frame_processor.face_detector)
        self.assertIsNotNone(self.frame_processor.pose_estimator)
    
    def test_init_with_face_detector(self):
        """Test initialization with a face detector."""
        face_detector = Mock()
        frame_processor = FrameProcessor(
            self.config, self.face_tracker, self.zone_mapper, face_detector
        )
        
        self.assertEqual(frame_processor.face_detector, face_detector)
    
    def test_process_frame(self):
        """Test processing a single frame."""
        frame_count = 100
        
        result = self.frame_processor.process_frame(self.test_frame, frame_count)
        
        # Should return a ProcessingResult
        self.assertIsInstance(result, ProcessingResult)
        self.assertEqual(result.frame_number, frame_count)
        self.assertIsInstance(result.detected_faces, list)
        self.assertIsInstance(result.tracking_data, dict)
        
        # Should contain expected tracking data
        self.assertIn('active_faces', result.tracking_data)
        self.assertIn('completed_sessions', result.tracking_data)
        self.assertIn('frame_count', result.tracking_data)
    
    def test_process_frame_with_face_detector(self):
        """Test processing frame with a face detector."""
        # Mock face detector
        face_detector = Mock()
        detected_faces = [MockFaceDetection()]
        face_detector.detect_faces.return_value = detected_faces
        
        frame_processor = FrameProcessor(
            self.config, self.face_tracker, self.zone_mapper, face_detector
        )
        
        result = frame_processor.process_frame(self.test_frame, 100)
        
        # Should call face detector
        face_detector.detect_faces.assert_called_once_with(self.test_frame)
        
        # Should update face tracker
        self.face_tracker.update.assert_called_once_with(detected_faces, 100)
        
        # Should return processing result
        self.assertIsInstance(result, ProcessingResult)
        self.assertEqual(result.detected_faces, detected_faces)
    
    def test_process_frame_without_face_detector(self):
        """Test processing frame without a face detector."""
        result = self.frame_processor.process_frame(self.test_frame, 100)
        
        # Should return empty detected faces list
        self.assertEqual(result.detected_faces, [])
        
        # Should still update face tracker with empty list
        self.face_tracker.update.assert_called_once_with([], 100)
    
    def test_get_tracking_data(self):
        """Test getting current tracking data."""
        tracking_data = self.frame_processor.get_tracking_data()
        
        self.assertIsInstance(tracking_data, dict)
        self.assertIn('active_faces', tracking_data)
        self.assertIn('completed_sessions', tracking_data)
        
        # Should get data from face tracker
        self.assertEqual(tracking_data['active_faces'], self.face_tracker.get_active_faces())
        self.assertEqual(tracking_data['completed_sessions'], self.face_tracker.get_completed_sessions())
    
    def test_finalize_tracking(self):
        """Test finalizing tracking sessions."""
        self.frame_processor.finalize_tracking()
        
        # Should call face tracker's finalize method
        self.face_tracker.finalize_all_sessions.assert_called_once()
    
    def test_process_frame_multiple_frames(self):
        """Test processing multiple frames."""
        frame_counts = [1, 10, 100, 1000]
        
        for frame_count in frame_counts:
            result = self.frame_processor.process_frame(self.test_frame, frame_count)
            
            self.assertEqual(result.frame_number, frame_count)
            self.assertIsInstance(result, ProcessingResult)
    
    def test_process_frame_different_sizes(self):
        """Test processing frames of different sizes."""
        sizes = [(320, 240), (1280, 720), (1920, 1080)]
        
        for width, height in sizes:
            frame = create_test_frame(width, height)
            result = self.frame_processor.process_frame(frame, 1)
            
            self.assertIsInstance(result, ProcessingResult)
            self.assertEqual(result.frame_number, 1)
    
    def test_process_frame_with_face_detector_exception(self):
        """Test processing frame when face detector raises an exception."""
        # Mock face detector that raises an exception
        face_detector = Mock()
        face_detector.detect_faces.side_effect = Exception("Detection error")
        
        frame_processor = FrameProcessor(
            self.config, self.face_tracker, self.zone_mapper, face_detector
        )
        
        # Should handle the exception gracefully
        with self.assertRaises(Exception):
            frame_processor.process_frame(self.test_frame, 100)
    
    def test_process_frame_with_tracker_exception(self):
        """Test processing frame when face tracker raises an exception."""
        # Mock face tracker that raises an exception
        self.face_tracker.update.side_effect = Exception("Tracking error")
        
        # Should handle the exception gracefully
        with self.assertRaises(Exception):
            self.frame_processor.process_frame(self.test_frame, 100)
    
    def test_pose_estimator_initialization(self):
        """Test that pose estimator is properly initialized."""
        pose_estimator = self.frame_processor.pose_estimator
        self.assertIsNotNone(pose_estimator)
        
        # Should have estimate_pose method
        self.assertTrue(hasattr(pose_estimator, 'estimate_pose'))
    
    def test_config_integration(self):
        """Test that configuration is properly used."""
        # Test with different pose estimator types
        config_with_simple = self.config.copy()
        config_with_simple['pose_estimation']['estimator_type'] = 'simple'
        
        frame_processor = FrameProcessor(
            config_with_simple, self.face_tracker, self.zone_mapper
        )
        
        self.assertIsNotNone(frame_processor.pose_estimator)
    
    def test_processing_result_structure(self):
        """Test that ProcessingResult has the correct structure."""
        result = self.frame_processor.process_frame(self.test_frame, 100)
        
        # Check required attributes
        self.assertIsInstance(result.frame_number, int)
        self.assertIsInstance(result.detected_faces, list)
        self.assertIsInstance(result.tracking_data, dict)
        self.assertIsNone(result.visualization)  # Should be None by default
    
    def test_tracking_data_structure(self):
        """Test that tracking data has the correct structure."""
        result = self.frame_processor.process_frame(self.test_frame, 100)
        tracking_data = result.tracking_data
        
        # Check required keys
        required_keys = ['active_faces', 'completed_sessions', 'frame_count']
        for key in required_keys:
            self.assertIn(key, tracking_data)
        
        # Check types
        self.assertIsInstance(tracking_data['active_faces'], dict)
        self.assertIsInstance(tracking_data['completed_sessions'], list)
        self.assertIsInstance(tracking_data['frame_count'], int)
    
    def test_face_detector_integration(self):
        """Test integration with face detector."""
        # Mock face detector with specific return values
        face_detector = Mock()
        detected_faces = [
            MockFaceDetection(confidence=0.8),
            MockFaceDetection(confidence=0.9)
        ]
        face_detector.detect_faces.return_value = detected_faces
        
        frame_processor = FrameProcessor(
            self.config, self.face_tracker, self.zone_mapper, face_detector
        )
        
        result = frame_processor.process_frame(self.test_frame, 100)
        
        # Should return the detected faces
        self.assertEqual(len(result.detected_faces), 2)
        self.assertEqual(result.detected_faces, detected_faces)
        
        # Should pass detected faces to tracker
        self.face_tracker.update.assert_called_once_with(detected_faces, 100)


if __name__ == '__main__':
    unittest.main() 