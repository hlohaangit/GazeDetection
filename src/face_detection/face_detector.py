"""
Modular face detection component.
This module provides a clean interface for face detection using MediaPipe.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional
from core.interfaces import IFaceDetector
from face_tracker.face_tracker import FaceDetection
from head_pose_estimator.head_pose_estimator import HeadPoseEstimatorFactory
from zone_mapper.zone_mapper import GazeContext


class MediaPipeFaceDetector(IFaceDetector):
    """Face detector using MediaPipe.
    
    This class encapsulates all MediaPipe face detection logic and provides
    a clean interface for detecting faces in video frames.
    """
    
    def __init__(self, config: dict, pose_estimator=None, zone_mapper=None):
        """Initialize the MediaPipe face detector.
        
        Args:
            config: Configuration dictionary for face detection
            pose_estimator: Optional pose estimator for gaze analysis
            zone_mapper: Optional zone mapper for gaze zone determination
        """
        self.config = config
        self.pose_estimator = pose_estimator
        self.zone_mapper = zone_mapper
        
        # Initialize MediaPipe components
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        
        # Create face detection model
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=config.get('model_selection', 1),
            min_detection_confidence=config.get('detection_confidence', 0.3)
        )
        
        # Create face mesh model for detailed landmarks
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=config.get('mesh_confidence', 0.3),
            min_tracking_confidence=0.5
        )
    
    def detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces in the given frame.
        
        Args:
            frame: Input frame as numpy array (BGR format)
            
        Returns:
            List of detected faces with their properties
        """
        detected_faces = []
        frame_height, frame_width = frame.shape[:2]
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces using MediaPipe
        detection_results = self.face_detection.process(rgb_frame)
        
        if detection_results.detections:
            for detection in detection_results.detections:
                face_detection = self._process_detection(
                    detection, rgb_frame, frame_width, frame_height
                )
                if face_detection:
                    detected_faces.append(face_detection)
        
        return detected_faces
    
    def _process_detection(self, detection, rgb_frame: np.ndarray, 
                          frame_width: int, frame_height: int) -> Optional[FaceDetection]:
        """Process individual face detection.
        
        Args:
            detection: MediaPipe detection result
            rgb_frame: Input frame in RGB format
            frame_width: Width of the frame
            frame_height: Height of the frame
            
        Returns:
            FaceDetection object if processing successful, None otherwise
        """
        # Extract bounding box coordinates
        bbox = detection.location_data.relative_bounding_box
        x = int(bbox.xmin * frame_width)
        y = int(bbox.ymin * frame_height)
        w = int(bbox.width * frame_width)
        h = int(bbox.height * frame_height)
        
        # Ensure coordinates are within frame bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame_width - x)
        h = min(h, frame_height - y)
        
        # Check minimum face size
        if w > 30 and h > 30:
            confidence = detection.score[0] if detection.score else 0.5
            return self._create_face_detection(
                rgb_frame, x, y, w, h, confidence, frame_width, frame_height
            )
        
        return None
    
    def _create_face_detection(self, rgb_frame: np.ndarray, x: int, y: int, 
                              w: int, h: int, confidence: float,
                              frame_width: int, frame_height: int) -> FaceDetection:
        """Create FaceDetection object with pose estimation.
        
        Args:
            rgb_frame: Input frame in RGB format
            x, y, w, h: Bounding box coordinates
            confidence: Detection confidence score
            frame_width, frame_height: Frame dimensions
            
        Returns:
            FaceDetection object with all properties
        """
        # Add padding for better FaceMesh results
        padding = int(min(w, h) * 0.3)
        x_pad = max(0, x - padding)
        y_pad = max(0, y - padding)
        w_pad = min(frame_width - x_pad, w + 2*padding)
        h_pad = min(frame_height - y_pad, h + 2*padding)
        
        # Crop face region
        face_crop = rgb_frame[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
        
        # Check if crop is valid
        if face_crop.size > 0 and face_crop.shape[0] > 20 and face_crop.shape[1] > 20:
            # Apply FaceMesh for detailed landmarks
            mesh_results = self.face_mesh.process(face_crop)
            
            if mesh_results.multi_face_landmarks:
                landmarks = mesh_results.multi_face_landmarks[0]
                face_center_x = x + w // 2
                face_center_y = y + h // 2
                
                # Estimate pose if estimator is available
                yaw, pitch = 0, 0
                if self.pose_estimator:
                    head_pose = self.pose_estimator.estimate_pose(landmarks, face_crop.shape)
                    yaw = head_pose.yaw
                    pitch = head_pose.pitch
                
                # Determine zone if mapper is available
                zone = "Unknown"
                if self.zone_mapper:
                    gaze_context = GazeContext(
                        yaw_angle=yaw,
                        pitch_angle=pitch,
                        face_center_x=face_center_x,
                        face_center_y=face_center_y,
                        frame_width=frame_width,
                        frame_height=frame_height,
                        confidence=confidence
                    )
                    zone = self.zone_mapper.map_to_zone(gaze_context)
                
                return FaceDetection(
                    box=(x, y, w, h),
                    crop_box=(x_pad, y_pad, w_pad, h_pad),
                    landmarks=landmarks,
                    yaw=yaw,
                    pitch=pitch,
                    zone=zone,
                    confidence=confidence,
                    face_center=(face_center_x, face_center_y)
                )
        
        # Fallback without detailed pose estimation
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # Determine zone if mapper is available
        zone = "Unknown_Basic"
        if self.zone_mapper:
            gaze_context = GazeContext(
                yaw_angle=0,
                pitch_angle=0,
                face_center_x=face_center_x,
                face_center_y=face_center_y,
                frame_width=frame_width,
                frame_height=frame_height,
                confidence=confidence
            )
            zone = self.zone_mapper.map_to_zone(gaze_context) + "_Basic"
        
        return FaceDetection(
            box=(x, y, w, h),
            crop_box=(x_pad, y_pad, w_pad, h_pad),
            landmarks=None,
            yaw=0,
            pitch=0,
            zone=zone,
            confidence=confidence,
            face_center=(face_center_x, face_center_y)
        )
    
    def close(self) -> None:
        """Clean up MediaPipe resources."""
        self.face_detection.close()
        self.face_mesh.close() 