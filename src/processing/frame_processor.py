"""
Frame processing coordination component.
This module coordinates the processing of individual frames through the pipeline.
"""

import numpy as np
from typing import Dict, Any, List
from core.interfaces import ProcessingResult
from face_tracker.face_tracker import FaceDetection
from head_pose_estimator.head_pose_estimator import HeadPoseEstimatorFactory
from zone_mapper.zone_mapper import ZoneMapperFactory, GazeContext


class FrameProcessor:
    """Coordinates processing of individual frames.
    
    This class orchestrates the processing of each frame through the detection,
    tracking, and analysis pipeline.
    """
    
    def __init__(self, config: dict, face_tracker, zone_mapper, face_detector=None):
        """Initialize the frame processor.
        
        Args:
            config: Configuration dictionary
            face_tracker: Face tracking component
            zone_mapper: Zone mapping component
            face_detector: Optional face detection component
        """
        self.config = config
        self.face_tracker = face_tracker
        self.zone_mapper = zone_mapper
        self.face_detector = face_detector
        
        # Initialize pose estimator if not provided
        pose_config = config.get('pose_estimation', {})
        self.pose_estimator = HeadPoseEstimatorFactory.create_estimator(
            pose_config.get('estimator_type', 'mediapipe')
        )
    
    def process_frame(self, frame: np.ndarray, frame_count: int) -> ProcessingResult:
        """Process a single frame and return results.
        
        Args:
            frame: Input frame to process
            frame_count: Current frame number
            
        Returns:
            ProcessingResult with all frame processing data
        """
        # Detect faces in the frame
        detected_faces = self._detect_faces(frame)
        
        # Update face tracking with new detections
        self.face_tracker.update(detected_faces, frame_count)
        
        # Get current tracking state
        active_faces = self.face_tracker.get_active_faces()
        completed_sessions = self.face_tracker.get_completed_sessions()
        
        # Create processing result
        return ProcessingResult(
            frame_number=frame_count,
            detected_faces=detected_faces,
            tracking_data={
                'active_faces': active_faces,
                'completed_sessions': completed_sessions,
                'frame_count': frame_count
            }
        )
    
    def _detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces in the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            List of detected faces
        """
        if self.face_detector:
            # Use the provided face detector
            return self.face_detector.detect_faces(frame)
        else:
            # Fallback: return empty list if no detector provided
            # This allows the processor to work without a detector
            return []
    
    def get_tracking_data(self) -> Dict[str, Any]:
        """Get current tracking data.
        
        Returns:
            Dictionary with current tracking state
        """
        return {
            'active_faces': self.face_tracker.get_active_faces(),
            'completed_sessions': self.face_tracker.get_completed_sessions()
        }
    
    def finalize_tracking(self) -> None:
        """Finalize all tracking sessions.
        
        This method should be called when processing is complete to ensure
        all active faces are properly finalized.
        """
        self.face_tracker.finalize_all_sessions() 