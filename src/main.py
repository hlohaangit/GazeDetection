# main.py
"""
Main entry point for the modular gaze tracking system.
This file provides the command-line interface for the gaze tracking system.
"""

import argparse
import sys
from pathlib import Path
from pipeline.gaze_tracking_pipeline import GazeTrackingPipeline


def validate_input(input_path: str) -> bool:
    """Validate input path or camera ID.
    
    Args:
        input_path: Path to video file or camera ID
        
    Returns:
        True if input is valid, False otherwise
    """
    try:
        # Check if it's a camera ID
        camera_id = int(input_path)
        # Test camera availability
        import cv2
        cap = cv2.VideoCapture(camera_id)
        is_valid = cap.isOpened()
        cap.release()
        return is_valid
    except ValueError:
        # It's a file path
        return Path(input_path).exists() and Path(input_path).is_file()


def main():
    """Main entry point for the gaze tracking system."""
    parser = argparse.ArgumentParser(
        description='Modular Gaze Tracking System - Track eye gaze patterns in physical spaces',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                    # Process video file
  %(prog)s 0                            # Use default camera
  %(prog)s video.mp4 --config myconfig.json    # Use custom configuration
  %(prog)s 0 --save-config myconfig.json       # Save current config
        """
    )
    
    parser.add_argument('input', help='Video file path or camera ID (0 for webcam)')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--save-config', help='Save current configuration to file')
    parser.add_argument('--version', action='version', 
                       version='%(prog)s 2.0.0')
    
    args = parser.parse_args()
    
    # Validate input
    if not validate_input(args.input):
        print(f"Error: Invalid input '{args.input}'")
        print("Please provide a valid video file path or camera ID")
        sys.exit(1)
    
    # Create pipeline
    try:
        pipeline = GazeTrackingPipeline(args.config)
        
        # Print configuration summary
        config = pipeline.get_config()
        print("\nModular Gaze Tracking System Configuration:")
        print("-" * 50)
        print(f"Input: {args.input}")
        print(f"Display output: {config['visualization']['display_output']}")
        print(f"Save output: {config['visualization']['save_output']}")
        print(f"Database output: {config['analytics']['database_output']}")
        print(f"JSON output: {config['analytics']['json_output']}")
        print(f"Logging level: {config['system']['logging_level']}")
        print("-" * 50)
        print()
        
        # Save configuration if requested
        if args.save_config:
            pipeline.save_config(args.save_config)
            print(f"Configuration saved to: {args.save_config}")
            return
        
        # Process input
        try:
            camera_id = int(args.input)
            pipeline.process_live_camera(camera_id)
        except ValueError:
            # Input is a file path
            pipeline.process_video(args.input)
            
    except Exception as e:
        print(f"\nError: {e}")
        if config.get('system', {}).get('logging_level') == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup resources
        if 'pipeline' in locals():
            pipeline.cleanup()
    
    print("\nProcessing complete!")


if __name__ == "__main__":
    main()