"""
Core interfaces for the modular gaze tracking system.
These interfaces define the contracts that all components must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result from processing a single frame."""
    frame_number: int
    detected_faces: List[Any]
    tracking_data: Dict[str, Any]
    visualization: Optional[np.ndarray] = None


class IFaceDetector(ABC):
    """Interface for face detection implementations.
    
    This interface ensures that all face detectors follow the same contract,
    making them interchangeable in the pipeline.
    """
    
    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[Any]:
        """Detect faces in the given frame.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            List of detected faces with their properties
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Clean up resources when done."""
        pass


class IPoseEstimator(ABC):
    """Interface for pose estimation implementations.
    
    This interface allows different pose estimation methods to be used
    interchangeably (MediaPipe, OpenCV, custom models, etc.).
    """
    
    @abstractmethod
    def estimate_pose(self, landmarks: Any, image_shape: tuple) -> Any:
        """Estimate pose from facial landmarks.
        
        Args:
            landmarks: Facial landmarks from detection
            image_shape: Shape of the input image
            
        Returns:
            Pose estimation result with yaw, pitch, roll angles
        """
        pass


class IVisualizer(ABC):
    """Interface for visualization implementations.
    
    This interface allows different visualization styles and methods
    to be used without changing the core processing logic.
    """
    
    @abstractmethod
    def visualize(self, frame: np.ndarray, data: Dict[str, Any]) -> np.ndarray:
        """Create visualization of the given data on the frame.
        
        Args:
            frame: Input frame to draw on
            data: Tracking and detection data to visualize
            
        Returns:
            Frame with visualization overlays
        """
        pass


class IConfigManager(ABC):
    """Interface for configuration management.
    
    This interface provides a consistent way to access configuration
    across all components of the system.
    """
    
    @abstractmethod
    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section.
        
        Args:
            section: Configuration section name
            
        Returns:
            Dictionary of configuration parameters
        """
        pass
    
    @abstractmethod
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """Get configuration for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Dictionary of component-specific configuration
        """
        pass


class IEventBus(ABC):
    """Interface for event-driven communication.
    
    This interface enables loose coupling between components
    through event-based communication.
    """
    
    @abstractmethod
    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all subscribers.
        
        Args:
            event_type: Type of event being published
            data: Event data to send to subscribers
        """
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        pass 