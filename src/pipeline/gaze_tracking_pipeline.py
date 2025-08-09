"""
Main pipeline for the modular gaze tracking system.
This module orchestrates all components and provides the main interface.
"""

import logging
from typing import Optional
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from face_detection.face_detector import MediaPipeFaceDetector
from face_tracker.face_tracker import FaceTracker
from head_pose_estimator.head_pose_estimator import HeadPoseEstimatorFactory
from zone_mapper.zone_mapper import ZoneMapperFactory
from visualization.visualizer import GazeTrackingVisualizer
from processing.frame_processor import FrameProcessor
from processing.video_processor import VideoProcessor
from analytics_writer.analytics_writer import (
    ConsoleAnalyticsWriter, DatabaseAnalyticsWriter, JSONAnalyticsWriter,
    CompositeAnalyticsWriter
)


class GazeTrackingPipeline:
    """Main pipeline orchestrating all components.
    
    This class serves as the main entry point for the gaze tracking system.
    It initializes all components, manages their dependencies, and provides
    a clean interface for processing videos and live camera feeds.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the gaze tracking pipeline.
        
        Args:
            config_path: Optional path to configuration JSON file
        """
        # Initialize core components
        self.config_manager = ConfigManager(config_path)
        self.event_bus = EventBus()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize all components with dependency injection
        self._initialize_components()
        
        # Setup event handlers for component communication
        self._setup_event_handlers()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration.
        
        Returns:
            Configured logger instance
        """
        log_level = self.config_manager.get_config('system').get('logging_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Initialize all pipeline components with proper dependencies."""
        # Get component configurations
        face_tracking_config = self.config_manager.get_config('face_tracking')
        pose_config = self.config_manager.get_config('pose_estimation')
        zone_config = self.config_manager.get_config('zone_mapping')
        analytics_config = self.config_manager.get_config('analytics')
        viz_config = self.config_manager.get_config('visualization')
        face_detection_config = self.config_manager.get_config('face_detection')
        
        # Initialize face tracking component
        self.face_tracker = FaceTracker(
            iou_threshold=face_tracking_config.get('iou_threshold', 0.3),
            max_frames_missing=face_tracking_config.get('max_frames_missing', 20),
            min_session_duration=face_tracking_config.get('min_session_duration', 0.5),
            fps=self.config_manager.get_config('system').get('fps', 30.0)
        )
        
        # Initialize pose estimator
        self.pose_estimator = HeadPoseEstimatorFactory.create_estimator(
            pose_config.get('estimator_type', 'mediapipe')
        )
        
        # Initialize zone mapper
        self.zone_mapper = ZoneMapperFactory.create_mapper(
            zone_config.get('mapper_type', 'bakery'),
            zone_config.get('config_path')
        )
        
        # Initialize face detector with dependencies
        self.face_detector = MediaPipeFaceDetector(
            face_detection_config,
            pose_estimator=self.pose_estimator,
            zone_mapper=self.zone_mapper
        )
        
        # Initialize analytics writers
        self.analytics_writer = self._setup_analytics_writers(analytics_config)
        
        # Setup face tracker callback for analytics
        self.face_tracker.add_session_callback(self.analytics_writer.write_session)
        
        # Initialize frame processor
        self.frame_processor = FrameProcessor(
            self.config_manager.get_all_config(),
            self.face_tracker,
            self.zone_mapper,
            self.face_detector
        )
        
        # Initialize visualizer
        self.visualizer = GazeTrackingVisualizer(viz_config, self.zone_mapper)
        
        # Initialize video processor
        self.video_processor = VideoProcessor(
            self.config_manager.get_all_config(),
            self.frame_processor,
            self.visualizer,
            self.analytics_writer
        )
    
    def _setup_analytics_writers(self, config: dict):
        """Setup analytics writers based on configuration.
        
        Args:
            config: Analytics configuration dictionary
            
        Returns:
            Configured analytics writer (single or composite)
        """
        writers = []
        
        # Add console writer if enabled
        if config.get('console_output', True):
            writers.append(ConsoleAnalyticsWriter(
                verbose=config.get('verbose', True)
            ))
        
        # Add database writer if enabled
        if config.get('database_output', False):
            writers.append(DatabaseAnalyticsWriter(
                db_path=config.get('db_path', 'gaze_analytics.db')
            ))
        
        # Add JSON writer if enabled
        if config.get('json_output', False):
            writers.append(JSONAnalyticsWriter(
                output_dir=config.get('json_output_dir', 'analytics_output')
            ))
        
        # Return appropriate writer based on configuration
        if len(writers) == 0:
            return ConsoleAnalyticsWriter()
        elif len(writers) == 1:
            return writers[0]
        else:
            return CompositeAnalyticsWriter(writers)
    
    def _setup_event_handlers(self):
        """Setup event handlers for component communication."""
        # Subscribe to face detection events
        self.event_bus.subscribe('face_detected', self._on_face_detected)
        self.event_bus.subscribe('session_completed', self._on_session_completed)
    
    def _on_face_detected(self, event_type: str, data):
        """Handle face detection events.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        self.logger.debug(f"Face detected: {data}")
    
    def _on_session_completed(self, event_type: str, data):
        """Handle session completion events.
        
        Args:
            event_type: Type of event
            data: Event data containing session information
        """
        self.logger.info(f"Session completed: {data.id}")
    
    def process_video(self, video_path: str) -> None:
        """Process a video file.
        
        Args:
            video_path: Path to the video file to process
        """
        self.logger.info(f"Starting video processing: {video_path}")
        self.video_processor.process_video(video_path)
    
    def process_live_camera(self, camera_id: int = 0) -> None:
        """Process live camera feed.
        
        Args:
            camera_id: Camera device ID (usually 0 for default camera)
        """
        self.logger.info(f"Starting live camera processing (camera {camera_id})")
        self.video_processor.process_live_camera(camera_id)
    
    def get_config(self) -> dict:
        """Get current configuration.
        
        Returns:
            Complete configuration dictionary
        """
        return self.config_manager.get_all_config()
    
    def update_config(self, section: str, updates: dict) -> None:
        """Update configuration for a section.
        
        Args:
            section: Configuration section to update
            updates: Dictionary of updates to apply
        """
        self.config_manager.update_config(section, updates)
    
    def save_config(self, config_path: str) -> None:
        """Save current configuration to file.
        
        Args:
            config_path: Path where to save the configuration
        """
        self.config_manager.save_config(config_path)
    
    def get_tracking_stats(self) -> dict:
        """Get current tracking statistics.
        
        Returns:
            Dictionary with current tracking statistics
        """
        active_faces = self.face_tracker.get_active_faces()
        completed_sessions = self.face_tracker.get_completed_sessions()
        
        return {
            'active_faces': len(active_faces),
            'completed_sessions': len(completed_sessions),
            'total_faces_tracked': len(completed_sessions) + len(active_faces)
        }
    
    def cleanup(self) -> None:
        """Clean up resources and close components."""
        self.logger.info("Cleaning up pipeline resources...")
        
        # Close face detector
        if hasattr(self, 'face_detector'):
            self.face_detector.close()
        
        # Close analytics writer
        if hasattr(self, 'analytics_writer'):
            self.analytics_writer.close()
        
        self.logger.info("Pipeline cleanup complete") 