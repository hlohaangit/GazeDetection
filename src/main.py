# main.py
"""
Main application for gaze tracking system.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional, Dict, Any
from pathlib import Path
import argparse
import logging
from datetime import datetime
import json
import sys

# our modules
from face_tracker.face_tracker import FaceTracker, FaceDetection, TrackedFace
from head_pose_estimator.head_pose_estimator import HeadPoseEstimatorFactory, HeadPose
from zone_mapper.zone_mapper import ZoneMapperFactory, GazeContext
from analytics_writer.analytics_writer import (
    ConsoleAnalyticsWriter, DatabaseAnalyticsWriter, JSONAnalyticsWriter,
    CompositeAnalyticsWriter, AnalyticsProcessor, AggregateAnalytics
)


class GazeTrackingSystem:
    """Main system for gaze tracking and analysis."""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = self._setup_logging()
        
        # Initialize components
        self.face_tracker = FaceTracker(
            iou_threshold=config.get('iou_threshold', 0.3),
            max_frames_missing=config.get('max_frames_missing', 20),
            min_session_duration=config.get('min_session_duration', 0.5),
            fps=config.get('fps', 30.0)
        )
        
        self.head_pose_estimator = HeadPoseEstimatorFactory.create_estimator(
            config.get('pose_estimator', 'mediapipe')
        )
        
        self.zone_mapper = ZoneMapperFactory.create_mapper(
            config.get('zone_mapper', 'bakery'),
            config.get('zone_config_path')
        )
        
        # Initialize analytics writers
        self.analytics_writer = self._setup_analytics_writers(config)
        self.analytics_processor = AnalyticsProcessor(self.analytics_writer)
        
        # Setup face tracker callback
        self.face_tracker.add_session_callback(self.analytics_writer.write_session)
        
        # Initialize MediaPipe
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=config.get('detection_confidence', 0.3)
        )
        
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=config.get('mesh_confidence', 0.3),
            min_tracking_confidence=0.5
        )
        
        # Processing parameters
        self.frame_skip = config.get('frame_skip', 1)
        self.display_output = config.get('display_output', True)
        self.save_output = config.get('save_output', False)
        self.output_path = config.get('output_path', 'output.mp4')
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        log_level = self.config.get('logging_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _setup_analytics_writers(self, config: dict):
        """Setup analytics writers based on configuration."""
        writers = []
        
        if config.get('console_output', True):
            writers.append(ConsoleAnalyticsWriter(
                verbose=config.get('verbose', True)
            ))
        
        if config.get('database_output', False):
            writers.append(DatabaseAnalyticsWriter(
                db_path=config.get('db_path', 'gaze_analytics.db')
            ))
        
        if config.get('json_output', False):
            writers.append(JSONAnalyticsWriter(
                output_dir=config.get('json_output_dir', 'analytics_output')
            ))
        
        if len(writers) == 0:
            # Default to console output
            return ConsoleAnalyticsWriter()
        elif len(writers) == 1:
            return writers[0]
        else:
            return CompositeAnalyticsWriter(writers)
    
    def process_video(self, video_path: str) -> None:
        """Process video file for gaze tracking."""
        self.logger.info(f"Processing video: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self.logger.error(f"Failed to open video: {video_path}")
            return
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.logger.info(f"Video properties: {frame_width}x{frame_height} @ {fps}fps, {total_frames} frames")
        
        # Setup video writer if saving output
        out = None
        if self.save_output:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.output_path, fourcc, fps, 
                                (frame_width, frame_height))
            self.logger.info(f"Saving output to: {self.output_path}")
        
        frame_count = 0
        
        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break
                
                frame_count += 1
                
                # Process frame
                if frame_count % self.frame_skip == 0:
                    detected_faces = self._detect_faces(frame)
                    self.face_tracker.update(detected_faces, frame_count)
                
                # Visualize results
                if self.display_output or self.save_output:
                    visualization = self._visualize_frame(frame, frame_count)
                    
                    if self.display_output:
                        cv2.imshow("Gaze Tracking System", visualization)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.logger.info("User requested quit")
                            break
                    
                    if self.save_output and out:
                        out.write(visualization)
                
                # Log progress
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    self.logger.info(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
        
        except Exception as e:
            self.logger.error(f"Error processing video: {e}")
            raise
        
        finally:
            # Cleanup
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            
            # Finalize tracking
            self._finalize_tracking()
    
    def _detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces and estimate gaze in frame."""
        detected_faces = []
        frame_height, frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        detection_results = self.face_detection.process(rgb_frame)
        
        if detection_results.detections:
            for detection in detection_results.detections:
                # Get bounding box
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * frame_width)
                y = int(bbox.ymin * frame_height)
                w = int(bbox.width * frame_width)
                h = int(bbox.height * frame_height)
                
                # Ensure coordinates are within bounds
                x = max(0, x)
                y = max(0, y)
                w = min(w, frame_width - x)
                h = min(h, frame_height - y)
                
                if w > 30 and h > 30:  # Minimum face size
                    # Process face for gaze estimation
                    face_detection = self._process_face(
                        rgb_frame, x, y, w, h, 
                        detection.score[0] if detection.score else 0.5
                    )
                    if face_detection:
                        detected_faces.append(face_detection)
        
        return detected_faces
    
    def _process_face(self, frame: np.ndarray, x: int, y: int, 
                     w: int, h: int, confidence: float) -> Optional[FaceDetection]:
        """Process individual face for gaze estimation."""
        frame_height, frame_width = frame.shape[:2]
        
        # Add padding for better FaceMesh results
        padding = int(min(w, h) * 0.3)
        x_pad = max(0, x - padding)
        y_pad = max(0, y - padding)
        w_pad = min(frame_width - x_pad, w + 2*padding)
        h_pad = min(frame_height - y_pad, h + 2*padding)
        
        # Crop face region
        face_crop = frame[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
        
        if face_crop.size > 0 and face_crop.shape[0] > 20 and face_crop.shape[1] > 20:
            # Apply FaceMesh
            mesh_results = self.face_mesh.process(face_crop)
            
            if mesh_results.multi_face_landmarks:
                landmarks = mesh_results.multi_face_landmarks[0]
                
                # Estimate head pose
                head_pose = self.head_pose_estimator.estimate_pose(
                    landmarks, face_crop.shape
                )
                
                # Map to zone
                face_center_x = x + w // 2
                face_center_y = y + h // 2
                
                gaze_context = GazeContext(
                    yaw_angle=head_pose.yaw,
                    pitch_angle=head_pose.pitch,
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
                    yaw=head_pose.yaw,
                    pitch=head_pose.pitch,
                    zone=zone,
                    confidence=confidence,
                    face_center=(face_center_x, face_center_y)
                )
            else:
                # Fallback without detailed pose
                face_center_x = x + w // 2
                face_center_y = y + h // 2
                
                gaze_context = GazeContext(
                    yaw_angle=0,
                    pitch_angle=0,
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
                    landmarks=None,
                    yaw=0,
                    pitch=0,
                    zone=zone + "_Basic",
                    confidence=confidence,
                    face_center=(face_center_x, face_center_y)
                )
        
        return None
    
    def _visualize_frame(self, frame: np.ndarray, frame_count: int) -> np.ndarray:
        """Visualize tracking results on frame."""
        vis_frame = frame.copy()
        frame_height, frame_width = frame.shape[:2]
        
        # Get active faces
        active_faces = self.face_tracker.get_active_faces()
        
        # Draw each tracked face
        for face_id, face_data in active_faces.items():
            self._draw_face(vis_frame, face_id, face_data, frame_count)
        
        # Draw zone boundaries
        self._draw_zone_boundaries(vis_frame)
        
        # Draw status information
        self._draw_status(vis_frame, frame_count, len(active_faces), 
                         len(self.face_tracker.get_completed_sessions()))
        
        return vis_frame
    
    def _draw_face(self, frame: np.ndarray, face_id: int, 
                   face_data: TrackedFace, frame_count: int) -> None:
        """Draw individual face tracking visualization."""
        x, y, w, h = face_data.box
        
        # Get zone color
        zone = self.zone_mapper.get_zone_by_name(face_data.current_zone)
        color = zone.color if zone else (0, 255, 0)
        
        # Draw bounding box
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        
        # Create info box
        info_height = 120
        info_width = max(w, 220)
        
        # Ensure info box stays within frame
        if y - info_height < 0:
            # Draw info box below face instead
            info_y_start = y + h
            info_y_end = min(y + h + info_height, frame.shape[0])
        else:
            info_y_start = y - info_height
            info_y_end = y
        
        # Draw info background
        cv2.rectangle(frame, (x, info_y_start), (x + info_width, info_y_end), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, info_y_start), (x + info_width, info_y_end), color, 2)
        
        # Prepare text
        text_y = info_y_start + 20 if info_y_start < y else info_y_start + 20
        line_height = 20
        
        # Draw information
        info_lines = [
            f"ID: {face_id}",
            f"Zone: {face_data.current_zone[:25]}",  # Truncate long zone names
            f"Duration: {(frame_count - face_data.first_seen) / self.config.get('fps', 30.0):.1f}s",
            f"Zones visited: {len(set(g.zone for g in face_data.gaze_history))}",
            f"Conf: {face_data.confidence:.2f}"
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = text_y + i * line_height
            if y_pos < info_y_end - 5:  # Ensure text fits in box
                cv2.putText(frame, line, (x + 5, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _draw_zone_boundaries(self, frame: np.ndarray) -> None:
        """Draw zone boundaries on frame."""
        frame_height, frame_width = frame.shape[:2]
        
        # Draw vertical divisions
        third_width = (frame_width // 5)*2
        cv2.line(frame, (third_width, 0), (third_width, frame_height), 
                (255, 255, 255), 1)
        # cv2.line(frame, (2*third_width, 0), (2*third_width, frame_height), 
        #         (255, 255, 255), 1)
        
        # Draw zone labels
        zones = self.zone_mapper.get_zones()
        label_y = frame_height - 20
        
        # Ensure we have zones to display
        zone_labels = [
            ("entrance", (255, 150, 100), 10),
            # ("CAKES", (100, 255, 100), third_width + 10),
            ("walkway", (100, 150, 255), 2*third_width + 10)
        ]
        
        for label, color, x_pos in zone_labels:
            cv2.putText(frame, label, (x_pos, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    def _draw_status(self, frame: np.ndarray, frame_count: int, 
                     active_count: int, completed_count: int) -> None:
        """Draw status information on frame."""
        # Draw dark background for status text
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 70), (0, 0, 0), -1)
        
        status_text = f"Frame: {frame_count} | Active: {active_count} | Completed: {completed_count}"
        cv2.putText(frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.putText(frame, "Gaze Tracking System", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add FPS if available
        if hasattr(self, '_last_frame_time'):
            current_time = cv2.getTickCount()
            fps = cv2.getTickFrequency() / (current_time - self._last_frame_time)
            cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 100, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        self._last_frame_time = cv2.getTickCount()
    
    def _finalize_tracking(self) -> None:
        """Finalize all tracking and generate reports."""
        self.logger.info("Finalizing tracking sessions...")
        
        # Finalize remaining active faces
        self.face_tracker.finalize_all_sessions()
        
        # Get all completed sessions
        sessions = self.face_tracker.get_completed_sessions()
        
        self.logger.info(f"Total sessions completed: {len(sessions)}")
        
        # Generate aggregate analytics
        if sessions:
            aggregate = self.analytics_processor.process_sessions(sessions)
            self.analytics_writer.write_aggregate(aggregate)
        
        # Close analytics writers
        self.analytics_writer.close()
        
        # Close MediaPipe
        self.face_detection.close()
        self.face_mesh.close()
    
    def process_live_camera(self, camera_id: int = 0) -> None:
        """Process live camera feed."""
        self.logger.info(f"Starting live camera processing (camera {camera_id})")
        
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            self.logger.error(f"Failed to open camera {camera_id}")
            return
        
        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        frame_count = 0
        
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    self.logger.warning("Failed to read from camera")
                    continue
                
                frame_count += 1
                
                # Process frame
                if frame_count % self.frame_skip == 0:
                    detected_faces = self._detect_faces(frame)
                    self.face_tracker.update(detected_faces, frame_count)
                
                # Visualize
                if self.display_output:
                    visualization = self._visualize_frame(frame, frame_count)
                    cv2.imshow("Live Gaze Tracking", visualization)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.logger.info("User requested quit")
                        break
                    elif key == ord('s'):
                        # Save screenshot
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = f"screenshot_{timestamp}.png"
                        cv2.imwrite(screenshot_path, visualization)
                        self.logger.info(f"Screenshot saved: {screenshot_path}")
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        
        except Exception as e:
            self.logger.error(f"Error in live camera processing: {e}")
            raise
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self._finalize_tracking()


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from file or use defaults."""
    default_config = {
        'fps': 30.0,
        'frame_skip': 1,
        'iou_threshold': 0.3,
        'max_frames_missing': 20,
        'min_session_duration': 0.5,
        'detection_confidence': 0.3,
        'mesh_confidence': 0.3,
        'pose_estimator': 'mediapipe',
        'zone_mapper': 'bakery',
        'display_output': True,
        'save_output': False,
        'console_output': True,
        'database_output': False,
        'json_output': False,
        'verbose': True,
        'logging_level': 'INFO'
    }
    
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                default_config.update(config)
                print(f"Loaded configuration from: {config_path}")
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")
    
    return default_config


def validate_input(input_path: str) -> bool:
    """Validate input path or camera ID."""
    try:
        # Check if it's a camera ID
        camera_id = int(input_path)
        # Test camera availability
        cap = cv2.VideoCapture(camera_id)
        is_valid = cap.isOpened()
        cap.release()
        return is_valid
    except ValueError:
        # It's a file path
        return Path(input_path).exists() and Path(input_path).is_file()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Gaze Tracking System - Track eye gaze patterns in physical spaces',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                    # Process video file
  %(prog)s 0                            # Use default camera
  %(prog)s video.mp4 --db --json       # Enable all outputs
  %(prog)s 0 --config myconfig.json    # Use custom configuration
        """
    )
    
    parser.add_argument('input', help='Video file path or camera ID (0 for webcam)')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--output', help='Output video path')
    parser.add_argument('--no-display', action='store_true', 
                       help='Disable display output')
    parser.add_argument('--db', action='store_true', 
                       help='Enable database output')
    parser.add_argument('--json', action='store_true', 
                       help='Enable JSON output')
    parser.add_argument('--db-path', default='gaze_analytics.db',
                       help='Database file path')
    parser.add_argument('--json-dir', default='analytics_output',
                       help='JSON output directory')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--version', action='version', 
                       version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    # Validate input
    if not validate_input(args.input):
        print(f"Error: Invalid input '{args.input}'")
        print("Please provide a valid video file path or camera ID")
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line arguments
    if args.output:
        config['save_output'] = True
        config['output_path'] = args.output
    
    if args.no_display:
        config['display_output'] = False
    
    if args.db:
        config['database_output'] = True
        config['db_path'] = args.db_path
    
    if args.json:
        config['json_output'] = True
        config['json_output_dir'] = args.json_dir
    
    if args.verbose:
        config['verbose'] = True
        config['logging_level'] = 'DEBUG'
    
    # Create output directories if needed
    if config['json_output']:
        Path(config['json_output_dir']).mkdir(exist_ok=True)
    
    # Print configuration summary
    print("\nGaze Tracking System Configuration:")
    print("-" * 40)
    print(f"Input: {args.input}")
    print(f"Display output: {config['display_output']}")
    print(f"Save output: {config['save_output']}")
    if config['save_output']:
        print(f"Output path: {config['output_path']}")
    print(f"Database output: {config['database_output']}")
    if config['database_output']:
        print(f"Database path: {config['db_path']}")
    print(f"JSON output: {config['json_output']}")
    if config['json_output']:
        print(f"JSON directory: {config['json_output_dir']}")
    print("-" * 40)
    print()
    
    # Create system
    try:
        system = GazeTrackingSystem(config)
        
        # Process input
        try:
            camera_id = int(args.input)
            system.process_live_camera(camera_id)
        except ValueError:
            # Input is a file path
            system.process_video(args.input)
            
    except Exception as e:
        print(f"\nError: {e}")
        if config.get('verbose'):
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    print("\nProcessing complete!")


if __name__ == "__main__":
    main()