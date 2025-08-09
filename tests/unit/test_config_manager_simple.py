"""
Simple unit tests for the configuration manager.
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path

# Add src to Python path
src_dir = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from core.config_manager import ConfigManager


class TestConfigManagerSimple(unittest.TestCase):
    """Simple test cases for the ConfigManager class."""
    
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


if __name__ == '__main__':
    unittest.main() 