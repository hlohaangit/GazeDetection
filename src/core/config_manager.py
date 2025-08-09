"""
Configuration management for the gaze tracking system.
This module provides centralized configuration management with section-based access.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from .interfaces import IConfigManager


class ConfigManager(IConfigManager):
    """Manages configuration for all system components.
    
    This class provides a centralized way to manage configuration across
    all components of the gaze tracking system. It supports loading from
    JSON files and provides section-based access to configuration parameters.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Optional path to configuration JSON file
        """
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Complete configuration dictionary
        """
        # Default configuration with all system parameters
        default_config = {
            'system': {
                'fps': 30.0,
                'frame_skip': 1,
                'logging_level': 'INFO'
            },
            'face_detection': {
                'detection_confidence': 0.3,
                'mesh_confidence': 0.3,
                'model_selection': 1
            },
            'face_tracking': {
                'iou_threshold': 0.3,
                'max_frames_missing': 20,
                'min_session_duration': 0.5
            },
            'pose_estimation': {
                'estimator_type': 'mediapipe',
                'yaw_multiplier': 1.5,
                'pitch_multiplier': 2.0
            },
            'zone_mapping': {
                'mapper_type': 'bakery',
                'config_path': None
            },
            'visualization': {
                'display_output': True,
                'save_output': False,
                'output_path': 'output.mp4'
            },
            'analytics': {
                'console_output': True,
                'database_output': False,
                'json_output': False,
                'db_path': 'gaze_analytics.db',
                'json_output_dir': 'analytics_output',
                'verbose': True
            }
        }
        
        # Load configuration from file if provided
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge with defaults
                    self._merge_configs(default_config, file_config)
                    print(f"Loaded configuration from: {config_path}")
            except Exception as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration")
        
        return default_config
    
    def _merge_configs(self, default: Dict, override: Dict) -> None:
        """Recursively merge configuration dictionaries.
        
        This method ensures that nested configuration structures are properly
        merged, with override values taking precedence over defaults.
        
        Args:
            default: Default configuration dictionary
            override: Override configuration dictionary
        """
        for key, value in override.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._merge_configs(default[key], value)
            else:
                # Override or add new configuration
                default[key] = value
    
    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section.
        
        Args:
            section: Configuration section name (e.g., 'system', 'face_detection')
            
        Returns:
            Dictionary of configuration parameters for the section
        """
        return self.config.get(section, {})
    
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """Get configuration for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Dictionary of component-specific configuration
        """
        return self.config.get(component_name, {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration.
        
        Returns:
            Complete configuration dictionary
        """
        return self.config
    
    def update_config(self, section: str, updates: Dict[str, Any]) -> None:
        """Update configuration for a specific section.
        
        Args:
            section: Configuration section to update
            updates: Dictionary of updates to apply
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section].update(updates)
    
    def save_config(self, config_path: str) -> None:
        """Save current configuration to file.
        
        Args:
            config_path: Path where to save the configuration
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to: {config_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}") 