# head_pose_estimator.py
"""
Head pose estimation module for calculating gaze direction from facial landmarks.
"""

from typing import Tuple, List, Optional
from abc import ABC, abstractmethod
import numpy as np
from dataclasses import dataclass


@dataclass
class HeadPose:
    """Represents head pose angles."""
    yaw: float      # Left-right rotation
    pitch: float    # Up-down rotation
    roll: float     # Tilt rotation
    confidence: float = 1.0


@dataclass
class FacialLandmarks:
    """Key facial landmarks for pose estimation."""
    nose_tip: Tuple[int, int] # (x, y)
    chin: Tuple[int, int]
    left_eye_corner: Tuple[int, int]
    right_eye_corner: Tuple[int, int]
    forehead_center: Tuple[int, int]
    left_mouth_corner: Optional[Tuple[int, int]] = None
    right_mouth_corner: Optional[Tuple[int, int]] = None


class IHeadPoseEstimator(ABC):
    """Interface for head pose estimation implementations."""
    
    @abstractmethod
    def estimate_pose(self, landmarks: object, image_shape: Tuple[int, int]) -> HeadPose:
        """Estimate head pose from landmarks."""
        pass


class MediaPipeHeadPoseEstimator(IHeadPoseEstimator):
    """Head pose estimator using MediaPipe FaceMesh landmarks."""
    
    # MediaPipe landmark indices
    NOSE_TIP_IDX = 1
    CHIN_IDX = 175
    LEFT_EYE_CORNER_IDX = 33
    RIGHT_EYE_CORNER_IDX = 263
    FOREHEAD_CENTER_IDX = 10
    LEFT_MOUTH_CORNER_IDX = 61
    RIGHT_MOUTH_CORNER_IDX = 291
    
    def __init__(self, yaw_multiplier: float = 1.5, pitch_multiplier: float = 2.0):
        self.yaw_multiplier = yaw_multiplier
        self.pitch_multiplier = pitch_multiplier
    
    def estimate_pose(self, landmarks: object, image_shape: Tuple[int, int]) -> HeadPose:
        """Estimate head pose from MediaPipe FaceMesh landmarks."""
        facial_landmarks = self._extract_landmarks(landmarks, image_shape)
        return self._calculate_pose(facial_landmarks)
    
    def _extract_landmarks(self, landmarks: object, 
                          image_shape: Tuple[int, int]) -> FacialLandmarks:
        """Extract key facial landmarks from MediaPipe results."""
        h, w = image_shape[:2]
        
        # Convert normalized coordinates to pixel coordinates. the landmarks are in [0,1] range and need to be scaled to image size.
        def to_pixel_coords(landmark):
            return (int(landmark.x * w), int(landmark.y * h))
        
        return FacialLandmarks(
            nose_tip=to_pixel_coords(landmarks.landmark[self.NOSE_TIP_IDX]),
            chin=to_pixel_coords(landmarks.landmark[self.CHIN_IDX]),
            left_eye_corner=to_pixel_coords(landmarks.landmark[self.LEFT_EYE_CORNER_IDX]),
            right_eye_corner=to_pixel_coords(landmarks.landmark[self.RIGHT_EYE_CORNER_IDX]),
            forehead_center=to_pixel_coords(landmarks.landmark[self.FOREHEAD_CENTER_IDX]),
            left_mouth_corner=to_pixel_coords(landmarks.landmark[self.LEFT_MOUTH_CORNER_IDX]),
            right_mouth_corner=to_pixel_coords(landmarks.landmark[self.RIGHT_MOUTH_CORNER_IDX])
        )
    
    def _calculate_pose(self, landmarks: FacialLandmarks) -> HeadPose:
        """Calculate head pose angles from facial landmarks."""
        # Calculate eye center
        eye_center = (
            (landmarks.left_eye_corner[0] + landmarks.right_eye_corner[0]) // 2,
            (landmarks.left_eye_corner[1] + landmarks.right_eye_corner[1]) // 2
        )
        
        # Calculate yaw (left-right turn)
        yaw_angle = self._calculate_yaw(landmarks, eye_center)
        
        # Calculate pitch (up-down tilt)
        pitch_angle = self._calculate_pitch(landmarks)
        
        # Calculate roll (head tilt)
        roll_angle = self._calculate_roll(landmarks)
        
        return HeadPose(
            yaw=yaw_angle,
            pitch=pitch_angle,
            roll=roll_angle,
            confidence=1.0  # Could be enhanced with actual confidence calculation
        )
    
    def _calculate_yaw(self, landmarks: FacialLandmarks, 
                       eye_center: Tuple[int, int]) -> float:
        """Calculate yaw angle (left-right rotation)."""
        nose_to_eye_x = landmarks.nose_tip[0] - eye_center[0]
        face_width = abs(landmarks.left_eye_corner[0] - landmarks.right_eye_corner[0])
        
        if face_width > 0:
            yaw_angle = np.degrees(np.arctan2(nose_to_eye_x, face_width / 2))
            yaw_angle *= self.yaw_multiplier
        else:
            yaw_angle = 0
        
        return np.clip(yaw_angle, -90, 90)
    
    def _calculate_pitch(self, landmarks: FacialLandmarks) -> float:
        """Calculate pitch angle (up-down rotation)."""
        face_height = abs(landmarks.forehead_center[1] - landmarks.chin[1])
        face_center_y = (landmarks.forehead_center[1] + landmarks.chin[1]) // 2
        nose_to_center_y = landmarks.nose_tip[1] - face_center_y
        
        if face_height > 0:
            pitch_angle = np.degrees(np.arctan2(nose_to_center_y, face_height / 2))
            pitch_angle *= self.pitch_multiplier
        else:
            pitch_angle = 0
        
        return np.clip(pitch_angle, -90, 90)
    
    def _calculate_roll(self, landmarks: FacialLandmarks) -> float:
        """Calculate roll angle (head tilt)."""
        eye_dy = landmarks.right_eye_corner[1] - landmarks.left_eye_corner[1]
        eye_dx = landmarks.right_eye_corner[0] - landmarks.left_eye_corner[0]
        
        if eye_dx != 0:
            roll_angle = np.degrees(np.arctan2(eye_dy, eye_dx))
        else:
            roll_angle = 0
        
        return np.clip(roll_angle, -180, 180)


class SimpleHeadPoseEstimator(IHeadPoseEstimator):
    """Simple head pose estimator for fallback scenarios."""
    
    def estimate_pose(self, landmarks: object, image_shape: Tuple[int, int]) -> HeadPose:
        """Provide default pose when detailed estimation is not available."""
        return HeadPose(yaw=0.0, pitch=0.0, roll=0.0, confidence=0.5)




class HeadPoseEstimatorFactory:
    """Factory for creating appropriate head pose estimators."""
    
    @staticmethod
    def create_estimator(estimator_type: str = "mediapipe") -> IHeadPoseEstimator:
        """Create a head pose estimator based on type."""
        if estimator_type == "mediapipe":
            return MediaPipeHeadPoseEstimator()
        elif estimator_type == "simple":
            return SimpleHeadPoseEstimator()
        else:
            raise ValueError(f"Unknown estimator type: {estimator_type}")