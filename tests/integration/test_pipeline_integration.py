"""
Integration tests for the gaze tracking pipeline.
"""

import unittest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
from src.pipeline.gaze_tracking_pipeline import GazeTrackingPipeline
from tests.fixtures.test_data import create_test_config


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the GazeTrackingPipeline class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = create_test_config()
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            self.config_path = f.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization with configuration."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that all components are initialized
        self.assertIsNotNone(pipeline.config_manager)
        self.assertIsNotNone(pipeline.event_bus)
        self.assertIsNotNone(pipeline.face_tracker)
        self.assertIsNotNone(pipeline.pose_estimator)
        self.assertIsNotNone(pipeline.zone_mapper)
        self.assertIsNotNone(pipeline.face_detector)
        self.assertIsNotNone(pipeline.analytics_writer)
        self.assertIsNotNone(pipeline.frame_processor)
        self.assertIsNotNone(pipeline.visualizer)
        self.assertIsNotNone(pipeline.video_processor)
    
    def test_pipeline_initialization_without_config(self):
        """Test pipeline initialization without configuration file."""
        pipeline = GazeTrackingPipeline()
        
        # Should still initialize with default configuration
        self.assertIsNotNone(pipeline.config_manager)
        self.assertIsNotNone(pipeline.event_bus)
        self.assertIsNotNone(pipeline.face_tracker)
    
    def test_get_config(self):
        """Test getting configuration from pipeline."""
        pipeline = GazeTrackingPipeline(self.config_path)
        config = pipeline.get_config()
        
        # Should return the complete configuration
        self.assertIsInstance(config, dict)
        self.assertIn('system', config)
        self.assertIn('face_detection', config)
        self.assertIn('face_tracking', config)
    
    def test_update_config(self):
        """Test updating configuration in pipeline."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Update a configuration section
        updates = {'new_param': 'new_value'}
        pipeline.update_config('system', updates)
        
        # Check that the update was applied
        config = pipeline.get_config()
        self.assertEqual(config['system']['new_param'], 'new_value')
    
    def test_save_config(self):
        """Test saving configuration from pipeline."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            save_path = f.name
        
        try:
            pipeline.save_config(save_path)
            
            # Verify the file was created and contains valid JSON
            with open(save_path, 'r') as f:
                saved_config = json.load(f)
            
            self.assertIn('system', saved_config)
            self.assertIn('face_detection', saved_config)
        finally:
            if os.path.exists(save_path):
                os.unlink(save_path)
    
    def test_get_tracking_stats(self):
        """Test getting tracking statistics from pipeline."""
        pipeline = GazeTrackingPipeline(self.config_path)
        stats = pipeline.get_tracking_stats()
        
        # Should return tracking statistics
        self.assertIsInstance(stats, dict)
        self.assertIn('active_faces', stats)
        self.assertIn('completed_sessions', stats)
        self.assertIn('total_faces_tracked', stats)
        
        # Should have non-negative values
        self.assertGreaterEqual(stats['active_faces'], 0)
        self.assertGreaterEqual(stats['completed_sessions'], 0)
        self.assertGreaterEqual(stats['total_faces_tracked'], 0)
    
    def test_cleanup(self):
        """Test pipeline cleanup."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Should not raise an exception
        pipeline.cleanup()
    
    @patch('src.pipeline.gaze_tracking_pipeline.VideoProcessor')
    def test_process_video_integration(self, mock_video_processor):
        """Test video processing integration."""
        # Mock the video processor
        mock_processor_instance = Mock()
        mock_video_processor.return_value = mock_processor_instance
        
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Process a video
        video_path = "test_video.mp4"
        pipeline.process_video(video_path)
        
        # Should call video processor
        mock_processor_instance.process_video.assert_called_once_with(video_path)
    
    @patch('src.pipeline.gaze_tracking_pipeline.VideoProcessor')
    def test_process_live_camera_integration(self, mock_video_processor):
        """Test live camera processing integration."""
        # Mock the video processor
        mock_processor_instance = Mock()
        mock_video_processor.return_value = mock_processor_instance
        
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Process live camera
        camera_id = 0
        pipeline.process_live_camera(camera_id)
        
        # Should call video processor
        mock_processor_instance.process_live_camera.assert_called_once_with(camera_id)
    
    def test_component_dependencies(self):
        """Test that components have proper dependencies."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that face detector has pose estimator and zone mapper
        self.assertIsNotNone(pipeline.face_detector.pose_estimator)
        self.assertIsNotNone(pipeline.face_detector.zone_mapper)
        
        # Check that frame processor has face tracker and zone mapper
        self.assertEqual(pipeline.frame_processor.face_tracker, pipeline.face_tracker)
        self.assertEqual(pipeline.frame_processor.zone_mapper, pipeline.zone_mapper)
        
        # Check that video processor has frame processor, visualizer, and analytics writer
        self.assertEqual(pipeline.video_processor.frame_processor, pipeline.frame_processor)
        self.assertEqual(pipeline.video_processor.visualizer, pipeline.visualizer)
        self.assertEqual(pipeline.video_processor.analytics_writer, pipeline.analytics_writer)
    
    def test_event_handlers_setup(self):
        """Test that event handlers are properly set up."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that event handlers are registered
        event_types = pipeline.event_bus.list_event_types()
        self.assertIn('face_detected', event_types)
        self.assertIn('session_completed', event_types)
    
    def test_configuration_structure(self):
        """Test that configuration has the expected structure."""
        pipeline = GazeTrackingPipeline(self.config_path)
        config = pipeline.get_config()
        
        # Check all required sections
        required_sections = [
            'system', 'face_detection', 'face_tracking', 
            'pose_estimation', 'zone_mapping', 'visualization', 'analytics'
        ]
        
        for section in required_sections:
            self.assertIn(section, config, f"Missing required section: {section}")
            self.assertIsInstance(config[section], dict, f"Section {section} should be a dict")
    
    def test_analytics_writer_setup(self):
        """Test that analytics writers are properly set up."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that analytics writer is configured
        self.assertIsNotNone(pipeline.analytics_writer)
        
        # Check that face tracker has analytics callback
        # This is set up in the pipeline initialization
        self.assertTrue(hasattr(pipeline.face_tracker, '_session_callbacks'))
    
    def test_zone_mapper_configuration(self):
        """Test that zone mapper is properly configured."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that zone mapper is initialized
        self.assertIsNotNone(pipeline.zone_mapper)
        
        # Check that it has required methods
        self.assertTrue(hasattr(pipeline.zone_mapper, 'map_to_zone'))
        self.assertTrue(hasattr(pipeline.zone_mapper, 'get_zones'))
        self.assertTrue(hasattr(pipeline.zone_mapper, 'get_zone_by_name'))
    
    def test_pose_estimator_configuration(self):
        """Test that pose estimator is properly configured."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that pose estimator is initialized
        self.assertIsNotNone(pipeline.pose_estimator)
        
        # Check that it has required methods
        self.assertTrue(hasattr(pipeline.pose_estimator, 'estimate_pose'))
    
    def test_face_detector_configuration(self):
        """Test that face detector is properly configured."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that face detector is initialized
        self.assertIsNotNone(pipeline.face_detector)
        
        # Check that it has required methods
        self.assertTrue(hasattr(pipeline.face_detector, 'detect_faces'))
        self.assertTrue(hasattr(pipeline.face_detector, 'close'))
    
    def test_visualizer_configuration(self):
        """Test that visualizer is properly configured."""
        pipeline = GazeTrackingPipeline(self.config_path)
        
        # Check that visualizer is initialized
        self.assertIsNotNone(pipeline.visualizer)
        
        # Check that it has required methods
        self.assertTrue(hasattr(pipeline.visualizer, 'visualize'))
    
    def test_error_handling(self):
        """Test error handling in pipeline initialization."""
        # Test with invalid configuration
        invalid_config = {'invalid': 'config'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            invalid_config_path = f.name
        
        try:
            # Should still initialize with defaults
            pipeline = GazeTrackingPipeline(invalid_config_path)
            self.assertIsNotNone(pipeline.config_manager)
        finally:
            if os.path.exists(invalid_config_path):
                os.unlink(invalid_config_path)


if __name__ == '__main__':
    unittest.main() 