"""
Unit tests for the configuration manager.
"""

import unittest
import tempfile
import json
import os
from unittest.mock import patch, mock_open
from src.core.config_manager import ConfigManager
from tests.fixtures.test_data import create_test_config


class TestConfigManager(unittest.TestCase):
    """Test cases for the ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
    
    def test_init_without_config_file(self):
        """Test initialization without a config file."""
        config_manager = ConfigManager()
        self.assertIsNotNone(config_manager.config)
        self.assertIn('system', config_manager.config)
        self.assertIn('face_detection', config_manager.config)
    
    def test_init_with_config_file(self):
        """Test initialization with a config file."""
        test_config = {
            'system': {'fps': 60.0},
            'face_detection': {'detection_confidence': 0.5}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name
        
        try:
            config_manager = ConfigManager(config_path)
            self.assertEqual(config_manager.get_config('system')['fps'], 60.0)
            self.assertEqual(config_manager.get_config('face_detection')['detection_confidence'], 0.5)
        finally:
            os.unlink(config_path)
    
    def test_init_with_invalid_config_file(self):
        """Test initialization with an invalid config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_path = f.name
        
        try:
            # Should not raise an exception, should use defaults
            config_manager = ConfigManager(config_path)
            self.assertIsNotNone(config_manager.config)
        finally:
            os.unlink(config_path)
    
    def test_get_config(self):
        """Test getting configuration for a specific section."""
        config = self.config_manager.get_config('system')
        self.assertIsInstance(config, dict)
        self.assertIn('fps', config)
        self.assertIn('frame_skip', config)
    
    def test_get_config_nonexistent_section(self):
        """Test getting configuration for a nonexistent section."""
        config = self.config_manager.get_config('nonexistent_section')
        self.assertEqual(config, {})
    
    def test_get_component_config(self):
        """Test getting component-specific configuration."""
        config = self.config_manager.get_component_config('face_detection')
        self.assertIsInstance(config, dict)
        self.assertIn('detection_confidence', config)
    
    def test_get_all_config(self):
        """Test getting all configuration."""
        all_config = self.config_manager.get_all_config()
        self.assertIsInstance(all_config, dict)
        self.assertIn('system', all_config)
        self.assertIn('face_detection', all_config)
        self.assertIn('face_tracking', all_config)
    
    def test_update_config(self):
        """Test updating configuration for a section."""
        updates = {'new_param': 'new_value'}
        self.config_manager.update_config('system', updates)
        
        config = self.config_manager.get_config('system')
        self.assertIn('new_param', config)
        self.assertEqual(config['new_param'], 'new_value')
    
    def test_update_config_new_section(self):
        """Test updating configuration for a new section."""
        new_section = {'param1': 'value1', 'param2': 'value2'}
        self.config_manager.update_config('new_section', new_section)
        
        config = self.config_manager.get_config('new_section')
        self.assertEqual(config['param1'], 'value1')
        self.assertEqual(config['param2'], 'value2')
    
    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            self.config_manager.save_config(config_path)
            
            # Verify the file was created and contains valid JSON
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
            
            self.assertIn('system', saved_config)
            self.assertIn('face_detection', saved_config)
        finally:
            os.unlink(config_path)
    
    def test_save_config_error(self):
        """Test saving configuration with an error."""
        # Try to save to a directory that doesn't exist
        invalid_path = '/nonexistent/directory/config.json'
        
        # Should not raise an exception, should handle the error gracefully
        self.config_manager.save_config(invalid_path)
    
    def test_merge_configs(self):
        """Test merging configuration dictionaries."""
        default = {
            'section1': {'param1': 'default1', 'param2': 'default2'},
            'section2': {'param3': 'default3'}
        }
        override = {
            'section1': {'param1': 'override1', 'param4': 'new4'},
            'section3': {'param5': 'new5'}
        }
        
        self.config_manager._merge_configs(default, override)
        
        # Check that existing values were overridden
        self.assertEqual(default['section1']['param1'], 'override1')
        # Check that existing values were preserved
        self.assertEqual(default['section1']['param2'], 'default2')
        # Check that new values were added
        self.assertEqual(default['section1']['param4'], 'new4')
        self.assertEqual(default['section3']['param5'], 'new5')
    
    def test_default_config_structure(self):
        """Test that default configuration has the expected structure."""
        config = self.config_manager.get_all_config()
        
        # Check all required sections exist
        required_sections = [
            'system', 'face_detection', 'face_tracking', 
            'pose_estimation', 'zone_mapping', 'visualization', 'analytics'
        ]
        
        for section in required_sections:
            self.assertIn(section, config, f"Missing required section: {section}")
            self.assertIsInstance(config[section], dict, f"Section {section} should be a dict")


if __name__ == '__main__':
    unittest.main() 