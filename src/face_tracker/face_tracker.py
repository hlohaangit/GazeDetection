from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from abc import ABC, abstractmethod


@dataclass
class GazeRecord:
    """Record of a single gaze measurement."""
    frame: int
    zone: str
    yaw: float
    pitch: float
    position: Tuple[int, int]
    confidence: float
    timestamp: Optional[float] = None


@dataclass
class FaceDetection:
    """Represents a detected face in a single frame."""
    box: Tuple[int, int, int, int]  # x, y, w, h
    crop_box: Optional[Tuple[int, int, int, int]] = None
    landmarks: Optional[object] = None
    yaw: float = 0.0
    pitch: float = 0.0
    zone: str = "Unknown"
    confidence: float = 0.0
    face_center: Optional[Tuple[int, int]] = None


@dataclass
class TrackedFace:
    """Represents a face being tracked across multiple frames."""
    id: int
    box: Tuple[int, int, int, int]
    first_seen: int
    last_seen: int
    missing_frames: int = 0
    gaze_history: List[GazeRecord] = field(default_factory=list)
    zone_durations: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    current_zone: str = "Unknown"
    zone_start_frame: int = 0
    confidence: float = 0.0


@dataclass
class TrackingSession:
    """Completed tracking session for a face."""
    id: int
    start_frame: int
    end_frame: int
    total_duration: float
    zone_durations: Dict[str, float]
    gaze_history: List[GazeRecord]
    unique_zones_visited: List[str]
    avg_confidence: float
    total_zone_transitions: int = 0
    peak_interest_zones: List[Tuple[str, float]] = field(default_factory=list)


class ITracker(ABC):
    """Interface for face tracking implementations."""
    
    @abstractmethod
    def update(self, detected_faces: List[FaceDetection], frame_count: int) -> None:
        """Update tracking with new detections."""
        pass
    
    @abstractmethod
    def get_active_faces(self) -> Dict[int, TrackedFace]:
        """Get currently tracked faces."""
        pass
    
    @abstractmethod
    def get_completed_sessions(self) -> List[TrackingSession]:
        """Get completed tracking sessions."""
        pass


class FaceTracker(ITracker):
    """Track individual faces with unique IDs and gaze history."""
    
    def __init__(self, 
                 iou_threshold: float = 0.3,
                 max_frames_missing: int = 20,
                 min_session_duration: float = 0.5,
                 fps: float = 30.0):
        self.next_id = 0
        self.active_faces: Dict[int, TrackedFace] = {}
        self.completed_sessions: List[TrackingSession] = []
        self.iou_threshold = iou_threshold
        self.max_frames_missing = max_frames_missing
        self.min_session_duration = min_session_duration
        self.fps = fps
        self._session_callbacks = []
        
    def add_session_callback(self, callback):
        """Add callback to be called when a session is completed."""
        self._session_callbacks.append(callback)
        
    def calculate_iou(self, box1: Tuple[int, int, int, int], 
                      box2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union between two boxes."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0
    
    def update(self, detected_faces: List[FaceDetection], frame_count: int) -> None:
        """Update tracking with new detections."""
        # Mark all existing faces as potentially missing
        for face_id in self.active_faces:
            self.active_faces[face_id].missing_frames += 1
        
        # Match detected faces to existing tracked faces
        matched: Set[int] = set()
        for detection in detected_faces:
            best_match_id = self._find_best_match(detection, matched)
            
            if best_match_id is not None:
                matched.add(best_match_id)
                self._update_face(best_match_id, detection, frame_count)
            else:
                self._create_new_face(detection, frame_count)
        
        # Check for faces that have left the frame
        self._remove_lost_faces()
    
    def _find_best_match(self, detection: FaceDetection, 
                        matched: Set[int]) -> Optional[int]:
        """Find the best matching existing face for a detection."""
        best_match_id = None
        best_iou = 0
        
        for face_id, face_data in self.active_faces.items():
            if face_id in matched:
                continue
                
            iou = self.calculate_iou(detection.box, face_data.box)
            if iou > best_iou and iou > self.iou_threshold:
                best_iou = iou
                best_match_id = face_id
        
        return best_match_id
    
    def _create_new_face(self, detection: FaceDetection, frame_count: int) -> None:
        """Create a new tracked face."""
        face_id = self.next_id
        self.next_id += 1
        
        tracked_face = TrackedFace(
            id=face_id,
            box=detection.box,
            first_seen=frame_count,
            last_seen=frame_count,
            current_zone=detection.zone,
            zone_start_frame=frame_count,
            confidence=detection.confidence
        )
        
        self.active_faces[face_id] = tracked_face
        self._add_gaze_record(face_id, detection, frame_count)
    
    def _update_face(self, face_id: int, detection: FaceDetection, 
                     frame_count: int) -> None:
        """Update existing tracked face."""
        face_data = self.active_faces[face_id]
        
        # Check if zone changed
        if face_data.current_zone != detection.zone:
            # Calculate duration in previous zone
            duration = (frame_count - face_data.zone_start_frame) / self.fps
            face_data.zone_durations[face_data.current_zone] += duration
            
            # Update to new zone
            face_data.current_zone = detection.zone
            face_data.zone_start_frame = frame_count
        
        # Update face data
        face_data.box = detection.box
        face_data.last_seen = frame_count
        face_data.missing_frames = 0
        face_data.confidence = detection.confidence
        
        # Add gaze record
        self._add_gaze_record(face_id, detection, frame_count)
    
    def _add_gaze_record(self, face_id: int, detection: FaceDetection, 
                         frame_count: int) -> None:
        """Add a gaze record to face history."""
        gaze_record = GazeRecord(
            frame=frame_count,
            zone=detection.zone,
            yaw=detection.yaw,
            pitch=detection.pitch,
            position=detection.face_center or (0, 0),
            confidence=detection.confidence,
            timestamp=frame_count / self.fps
        )
        self.active_faces[face_id].gaze_history.append(gaze_record)
    
    def _remove_lost_faces(self) -> None:
        """Remove faces that have been missing for too long."""
        faces_to_remove = []
        
        for face_id, face_data in self.active_faces.items():
            if face_data.missing_frames > self.max_frames_missing:
                self._finalize_face_session(face_id)
                faces_to_remove.append(face_id)
        
        for face_id in faces_to_remove:
            del self.active_faces[face_id]
    
    def _finalize_face_session(self, face_id: int) -> None:
        """Finalize tracking session for a face that has left."""
        face_data = self.active_faces[face_id]
        
        # Add duration for the last zone
        duration = (face_data.last_seen - face_data.zone_start_frame) / self.fps
        face_data.zone_durations[face_data.current_zone] += duration
        
        # Calculate total duration
        total_frames = face_data.last_seen - face_data.first_seen
        total_duration = total_frames / self.fps
        
        # Skip very brief detections
        if total_duration < self.min_session_duration or len(face_data.gaze_history) < 2:
            return
        
        # Calculate zone transitions
        zone_transitions = self._calculate_zone_transitions(face_data.gaze_history)
        
        # Identify peak interest zones (top 3 by duration)
        sorted_zones = sorted(face_data.zone_durations.items(), 
                            key=lambda x: x[1], reverse=True)
        peak_zones = sorted_zones[:3]
        
        # Create session summary
        session = TrackingSession(
            id=face_id,
            start_frame=face_data.first_seen,
            end_frame=face_data.last_seen,
            total_duration=total_duration,
            zone_durations=dict(face_data.zone_durations),
            gaze_history=face_data.gaze_history,
            unique_zones_visited=list(set(g.zone for g in face_data.gaze_history)),
            avg_confidence=np.mean([g.confidence for g in face_data.gaze_history]),
            total_zone_transitions=len(zone_transitions),
            peak_interest_zones=peak_zones
        )
        
        self.completed_sessions.append(session)
        
        # Notify callbacks
        for callback in self._session_callbacks:
            callback(session)
    
    def _calculate_zone_transitions(self, gaze_history: List[GazeRecord]) -> List[Tuple[str, str]]:
        """Calculate zone transitions from gaze history."""
        transitions = []
        for i in range(1, len(gaze_history)):
            if gaze_history[i].zone != gaze_history[i-1].zone:
                transitions.append((
                    gaze_history[i-1].zone,
                    gaze_history[i].zone
                ))
        return transitions
    
    def get_active_faces(self) -> Dict[int, TrackedFace]:
        """Get currently tracked faces."""
        return self.active_faces.copy()
    
    def get_completed_sessions(self) -> List[TrackingSession]:
        """Get completed tracking sessions."""
        return self.completed_sessions.copy()
    
    def finalize_all_sessions(self) -> None:
        """Finalize all remaining active faces."""
        for face_id in list(self.active_faces.keys()):
            self._finalize_face_session(face_id)