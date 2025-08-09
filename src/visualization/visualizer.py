"""
Modular visualization component.
This module provides clean visualization of gaze tracking results.
"""

import cv2
import numpy as np
from typing import Dict, Any, List
from core.interfaces import IVisualizer
from face_tracker.face_tracker import TrackedFace


class GazeTrackingVisualizer(IVisualizer):
    """Visualizer for gaze tracking results.
    
    This class handles all visualization aspects of the gaze tracking system,
    including drawing face bounding boxes, zone boundaries, and status information.
    """
    
    def __init__(self, config: dict, zone_mapper):
        """Initialize the visualizer.
        
        Args:
            config: Configuration dictionary for visualization
            zone_mapper: Zone mapper for zone information
        """
        self.config = config
        self.zone_mapper = zone_mapper
        self.display_output = config.get('display_output', True)
        self.save_output = config.get('save_output', False)
    
    def visualize(self, frame: np.ndarray, data: Dict[str, Any]) -> np.ndarray:
        """Create visualization of tracking data on the frame.
        
        Args:
            frame: Input frame to draw on
            data: Tracking and detection data to visualize
            
        Returns:
            Frame with visualization overlays
        """
        vis_frame = frame.copy()
        frame_count = data.get('frame_count', 0)
        active_faces = data.get('active_faces', {})
        completed_sessions = data.get('completed_sessions', [])
        
        # Draw each tracked face
        for face_id, face_data in active_faces.items():
            self._draw_face(vis_frame, face_id, face_data, frame_count)
        
        # Draw zone boundaries
        self._draw_zone_boundaries(vis_frame)
        
        # Draw status information
        self._draw_status(vis_frame, frame_count, len(active_faces), 
                         len(completed_sessions))
        
        return vis_frame
    
    def _draw_face(self, frame: np.ndarray, face_id: int, 
                   face_data: TrackedFace, frame_count: int) -> None:
        """Draw individual face tracking visualization.
        
        Args:
            frame: Frame to draw on
            face_id: Unique identifier for the face
            face_data: Tracking data for the face
            frame_count: Current frame number
        """
        x, y, w, h = face_data.box
        
        # Get zone color for the face
        zone = self.zone_mapper.get_zone_by_name(face_data.current_zone)
        color = zone.color if zone else (0, 255, 0)
        
        # Draw bounding box around the face
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        
        # Create info box dimensions
        info_height = 120
        info_width = max(w, 220)
        
        # Position info box above or below face
        if y - info_height < 0:
            # Draw info box below face if not enough space above
            info_y_start = y + h
            info_y_end = min(y + h + info_height, frame.shape[0])
        else:
            # Draw info box above face
            info_y_start = y - info_height
            info_y_end = y
        
        # Draw info box background
        cv2.rectangle(frame, (x, info_y_start), (x + info_width, info_y_end), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, info_y_start), (x + info_width, info_y_end), color, 2)
        
        # Calculate text position
        text_y = info_y_start + 20 if info_y_start < y else info_y_start + 20
        line_height = 20
        
        # Prepare information lines
        duration_seconds = (frame_count - face_data.first_seen) / 30.0
        zones_visited = len(set(g.zone for g in face_data.gaze_history))
        
        info_lines = [
            f"ID: {face_id}",
            f"Zone: {face_data.current_zone[:25]}",  # Truncate long zone names
            f"Duration: {duration_seconds:.1f}s",
            f"Zones visited: {zones_visited}",
            f"Conf: {face_data.confidence:.2f}"
        ]
        
        # Draw each line of information
        for i, line in enumerate(info_lines):
            y_pos = text_y + i * line_height
            if y_pos < info_y_end - 5:  # Ensure text fits in box
                cv2.putText(frame, line, (x + 5, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _draw_zone_boundaries(self, frame: np.ndarray) -> None:
        """Draw zone boundaries on frame.
        
        Args:
            frame: Frame to draw zone boundaries on
        """
        frame_height, frame_width = frame.shape[:2]
        
        # Draw vertical division lines
        third_width = (frame_width // 5) * 2
        cv2.line(frame, (third_width, 0), (third_width, frame_height), 
                (255, 255, 255), 1)
        
        # Draw zone labels at the bottom
        label_y = frame_height - 20
        
        # Define zone labels with their colors and positions
        zone_labels = [
            ("entrance", (255, 150, 100), 10),
            ("walkway", (100, 150, 255), 2*third_width + 10)
        ]
        
        # Draw each zone label
        for label, color, x_pos in zone_labels:
            cv2.putText(frame, label, (x_pos, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    def _draw_status(self, frame: np.ndarray, frame_count: int, 
                     active_count: int, completed_count: int) -> None:
        """Draw status information on frame.
        
        Args:
            frame: Frame to draw status on
            frame_count: Current frame number
            active_count: Number of active faces
            completed_count: Number of completed sessions
        """
        # Draw dark background for status text
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 70), (0, 0, 0), -1)
        
        # Create status text
        status_text = f"Frame: {frame_count} | Active: {active_count} | Completed: {completed_count}"
        cv2.putText(frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw system title
        cv2.putText(frame, "Gaze Tracking System", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add FPS information if available
        if hasattr(self, '_last_frame_time'):
            current_time = cv2.getTickCount()
            fps = cv2.getTickFrequency() / (current_time - self._last_frame_time)
            cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 100, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Update frame time for FPS calculation
        self._last_frame_time = cv2.getTickCount() 