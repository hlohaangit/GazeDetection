"""
Video processing component.
This module handles video I/O and coordinates the overall processing pipeline.
"""

import cv2
import numpy as np
from typing import Optional, Generator
from pathlib import Path
import logging
from core.interfaces import ProcessingResult


class VideoProcessor:
    """Handles video I/O and frame processing coordination.
    
    This class manages video file reading, frame extraction, and coordinates
    the processing pipeline for each frame.
    """
    
    def __init__(self, config: dict, frame_processor, visualizer, analytics_writer):
        """Initialize the video processor.
        
        Args:
            config: Configuration dictionary
            frame_processor: Frame processing component
            visualizer: Visualization component
            analytics_writer: Analytics writing component
        """
        self.config = config
        self.frame_processor = frame_processor
        self.visualizer = visualizer
        self.analytics_writer = analytics_writer
        self.logger = logging.getLogger(__name__)
        
        # Processing parameters
        self.frame_skip = config.get('frame_skip', 1)
        self.display_output = config.get('display_output', True)
        self.save_output = config.get('save_output', False)
        self.output_path = config.get('output_path', 'output.mp4')
    
    def process_video(self, video_path: str) -> None:
        """Process video file.
        
        Args:
            video_path: Path to the video file to process
        """
        self.logger.info(f"Processing video: {video_path}")
        
        # Open video file
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
            # Process each frame
            for frame in self._frame_generator(cap):
                frame_count += 1
                
                # Process frame (with frame skipping)
                if frame_count % self.frame_skip == 0:
                    result = self.frame_processor.process_frame(frame, frame_count)
                    
                    # Visualize results
                    if self.display_output or self.save_output:
                        visualization = self.visualizer.visualize(frame, result.tracking_data)
                        
                        if self.display_output:
                            cv2.imshow("Gaze Tracking System", visualization)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                self.logger.info("User requested quit")
                                break
                        
                        if self.save_output and out:
                            out.write(visualization)
                
                # Log progress periodically
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    self.logger.info(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
        
        except Exception as e:
            self.logger.error(f"Error processing video: {e}")
            raise
        
        finally:
            # Cleanup resources
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            
            # Finalize tracking and analytics
            self._finalize_tracking()
    
    def process_live_camera(self, camera_id: int = 0) -> None:
        """Process live camera feed.
        
        Args:
            camera_id: Camera device ID (usually 0 for default camera)
        """
        self.logger.info(f"Starting live camera processing (camera {camera_id})")
        
        # Open camera
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
                    result = self.frame_processor.process_frame(frame, frame_count)
                
                # Visualize
                if self.display_output:
                    visualization = self.visualizer.visualize(frame, result.tracking_data)
                    cv2.imshow("Live Gaze Tracking", visualization)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.logger.info("User requested quit")
                        break
                    elif key == ord('s'):
                        # Save screenshot
                        from datetime import datetime
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
    
    def _frame_generator(self, cap) -> Generator[np.ndarray, None, None]:
        """Generate frames from video capture.
        
        Args:
            cap: OpenCV VideoCapture object
            
        Yields:
            Frames as numpy arrays
        """
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            yield frame
    
    def _finalize_tracking(self) -> None:
        """Finalize all tracking and generate reports."""
        self.logger.info("Finalizing tracking sessions...")
        
        # Finalize remaining active faces
        self.frame_processor.finalize_tracking()
        
        # Get all completed sessions
        sessions = self.frame_processor.face_tracker.get_completed_sessions()
        
        self.logger.info(f"Total sessions completed: {len(sessions)}")
        
        # Generate aggregate analytics
        if sessions:
            from analytics_writer.analytics_writer import AnalyticsProcessor
            processor = AnalyticsProcessor(self.analytics_writer)
            aggregate = processor.process_sessions(sessions)
            self.analytics_writer.write_aggregate(aggregate)
        
        # Close analytics writers
        self.analytics_writer.close() 