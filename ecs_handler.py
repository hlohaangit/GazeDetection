import json
import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import cv2
import numpy as np
from flask import Flask, request, jsonify, Response
import requests

# Import our gaze tracking system
import sys
sys.path.append('/app/src')
from main import GazeTrackingSystem, load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

class ECSGazeProcessor:
    """ECS-based gaze detection processor for live streams."""
    
    def __init__(self):
        self.config = load_config()
        self.config.update({
            'display_output': False,
            'save_output': False,
            'json_output': True,
            'json_output_dir': '/app/analytics_output',
            'database_output': False,
            'console_output': True
        })
        
        self.system = None
        self.processing_thread = None
        self.is_processing = False
        self.current_stream_url = None
        self.analytics_buffer = []
        self.last_analytics_time = None
        
        # Initialize the gaze tracking system
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize the gaze tracking system."""
        try:
            logger.info("Initializing gaze tracking system...")
            self.system = GazeTrackingSystem(self.config)
            logger.info("Gaze tracking system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize gaze tracking system: {e}")
            raise
    
    def start_stream_processing(self, stream_url: str) -> Dict[str, Any]:
        """Start processing a live stream."""
        if self.is_processing:
            return {
                'status': 'error',
                'message': 'Already processing a stream. Stop current stream first.'
            }
        
        try:
            logger.info(f"Starting stream processing: {stream_url}")
            
            # Test stream connection
            if not self._test_stream_connection(stream_url):
                return {
                    'status': 'error',
                    'message': 'Cannot connect to stream URL'
                }
            
            self.current_stream_url = stream_url
            self.is_processing = True
            self.analytics_buffer = []
            self.last_analytics_time = time.time()
            
            # Start processing in a separate thread
            self.processing_thread = threading.Thread(
                target=self._process_stream,
                args=(stream_url,),
                daemon=True
            )
            self.processing_thread.start()
            
            return {
                'status': 'success',
                'message': f'Started processing stream: {stream_url}',
                'stream_url': stream_url,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting stream processing: {e}")
            self.is_processing = False
            return {
                'status': 'error',
                'message': f'Failed to start processing: {str(e)}'
            }
    
    def stop_stream_processing(self) -> Dict[str, Any]:
        """Stop current stream processing."""
        if not self.is_processing:
            return {
                'status': 'error',
                'message': 'No stream currently processing'
            }
        
        try:
            logger.info("Stopping stream processing...")
            self.is_processing = False
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=10)
            
            # Finalize analytics
            self._finalize_analytics()
            
            return {
                'status': 'success',
                'message': 'Stream processing stopped',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error stopping stream processing: {e}")
            return {
                'status': 'error',
                'message': f'Failed to stop processing: {str(e)}'
            }
    
    def _test_stream_connection(self, stream_url: str) -> bool:
        """Test if we can connect to the stream."""
        try:
            # Handle YouTube URLs specially
            if 'youtube.com' in stream_url or 'youtu.be' in stream_url:
                logger.warning("YouTube URLs may not work directly with OpenCV. Consider using a direct video file or RTSP stream.")
                # Try anyway, but warn user
                return True
            
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                logger.warning(f"Could not open stream: {stream_url}")
                return False
            
            # Try to read a frame
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                logger.info(f"Successfully connected to stream: {stream_url}")
                return True
            else:
                logger.warning(f"Could not read frame from stream: {stream_url}")
                return False
            
        except Exception as e:
            logger.error(f"Stream connection test failed: {e}")
            return False
    
    def _process_stream(self, stream_url: str):
        """Process the live stream in a separate thread."""
        cap = None
        frame_count = 0
        
        try:
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                logger.error(f"Failed to open stream: {stream_url}")
                return
            
            logger.info(f"Successfully connected to stream: {stream_url}")
            
            while self.is_processing:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame from stream")
                    time.sleep(1)
                    continue
                
                frame_count += 1
                
                # Process frame
                if frame_count % self.config.get('frame_skip', 1) == 0:
                    self._process_frame(frame, frame_count)
                
                # Generate analytics periodically
                current_time = time.time()
                if current_time - self.last_analytics_time > 5:  # Every 5 seconds
                    self._generate_analytics()
                    self.last_analytics_time = current_time
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
        
        finally:
            if cap:
                cap.release()
            self.is_processing = False
            logger.info("Stream processing thread ended")
    
    def _process_frame(self, frame: np.ndarray, frame_count: int):
        """Process a single frame."""
        try:
            # Detect faces and track gaze
            detected_faces = self.system._detect_faces(frame)
            self.system.face_tracker.update(detected_faces, frame_count)
            
            # Store frame analytics
            if detected_faces:
                frame_analytics = {
                    'timestamp': datetime.now().isoformat(),
                    'frame_count': frame_count,
                    'faces_detected': len(detected_faces),
                    'gaze_data': [
                        {
                            'face_id': i,
                            'zone': face.zone,
                            'confidence': face.confidence,
                            'yaw': face.yaw,
                            'pitch': face.pitch
                        }
                        for i, face in enumerate(detected_faces)
                    ]
                }
                self.analytics_buffer.append(frame_analytics)
                
        except Exception as e:
            logger.error(f"Error processing frame {frame_count}: {e}")
    
    def _generate_analytics(self):
        """Generate and store analytics."""
        if not self.analytics_buffer:
            return
        
        try:
            # Get active faces
            active_faces = self.system.face_tracker.get_active_faces()
            
            analytics = {
                'timestamp': datetime.now().isoformat(),
                'stream_url': self.current_stream_url,
                'active_faces': len(active_faces),
                'recent_frames': len(self.analytics_buffer),
                'face_details': [
                    {
                        'face_id': face_id,
                        'current_zone': face_data.current_zone,
                        'session_duration': (time.time() - face_data.first_seen) / self.config.get('fps', 30.0),
                        'zones_visited': len(set(g.zone for g in face_data.gaze_history))
                    }
                    for face_id, face_data in active_faces.items()
                ],
                'recent_gaze_data': self.analytics_buffer[-10:]  # Last 10 frames
            }
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analytics_file = f"/app/analytics_output/analytics_{timestamp}.json"
            
            with open(analytics_file, 'w') as f:
                json.dump(analytics, f, indent=2)
            
            # Clear buffer (keep last 50 frames)
            self.analytics_buffer = self.analytics_buffer[-50:]
            
            logger.info(f"Generated analytics: {analytics_file}")
            
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
    
    def _finalize_analytics(self):
        """Finalize analytics when stopping."""
        try:
            # Get completed sessions
            sessions = self.system.face_tracker.get_completed_sessions()
            
            if sessions:
                final_analytics = {
                    'timestamp': datetime.now().isoformat(),
                    'stream_url': self.current_stream_url,
                    'total_sessions': len(sessions),
                    'session_summary': [
                        {
                            'session_id': session.session_id,
                            'duration': session.duration,
                            'zones_visited': len(set(g.zone for g in session.gaze_history)),
                            'total_gazes': len(session.gaze_history)
                        }
                        for session in sessions
                    ]
                }
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_file = f"/app/analytics_output/final_analytics_{timestamp}.json"
                
                with open(final_file, 'w') as f:
                    json.dump(final_analytics, f, indent=2)
                
                logger.info(f"Finalized analytics: {final_file}")
        
        except Exception as e:
            logger.error(f"Error finalizing analytics: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processing status."""
        active_faces = self.system.face_tracker.get_active_faces() if self.system else {}
        
        return {
            'is_processing': self.is_processing,
            'stream_url': self.current_stream_url,
            'active_faces': len(active_faces),
            'analytics_buffer_size': len(self.analytics_buffer),
            'last_analytics_time': self.last_analytics_time,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recent_analytics(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent analytics data."""
        return {
            'recent_analytics': self.analytics_buffer[-limit:],
            'timestamp': datetime.now().isoformat()
        }

# Initialize the processor
processor = ECSGazeProcessor()

# Flask routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'gaze-detection-ecs'
    })

@app.route('/start', methods=['POST'])
def start_processing():
    """Start processing a stream."""
    try:
        data = request.get_json()
        stream_url = data.get('stream_url')
        
        if not stream_url:
            return jsonify({
                'status': 'error',
                'message': 'stream_url is required'
            }), 400
        
        result = processor.start_stream_processing(stream_url)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in start endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/stop', methods=['POST'])
def stop_processing():
    """Stop current stream processing."""
    try:
        result = processor.stop_stream_processing()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in stop endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get current processing status."""
    try:
        status = processor.get_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/analytics', methods=['GET'])
def get_analytics():
    """Get recent analytics data."""
    try:
        limit = request.args.get('limit', 10, type=int)
        analytics = processor.get_recent_analytics(limit)
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error in analytics endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    try:
        return jsonify(processor.config)
        
    except Exception as e:
        logger.error(f"Error in config endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting ECS Gaze Detection Service...")
    app.run(host='0.0.0.0', port=8080, debug=False) 