"""
Simple unit tests for the event bus.
"""

import unittest
import sys
from pathlib import Path

# Add src to Python path
src_dir = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from core.event_bus import EventBus


class TestEventBusSimple(unittest.TestCase):
    """Simple test cases for the EventBus class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
    
    def test_init(self):
        """Test event bus initialization."""
        self.assertIsNotNone(self.event_bus.subscribers)
        self.assertEqual(len(self.event_bus.subscribers), 0)
    
    def test_subscribe(self):
        """Test subscribing to an event."""
        handler = lambda event_type, data: None
        self.event_bus.subscribe('test_event', handler)
        
        self.assertIn('test_event', self.event_bus.subscribers)
        self.assertIn(handler, self.event_bus.subscribers['test_event'])
    
    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to the same event."""
        handler1 = lambda event_type, data: None
        handler2 = lambda event_type, data: None
        
        self.event_bus.subscribe('test_event', handler1)
        self.event_bus.subscribe('test_event', handler2)
        
        self.assertEqual(len(self.event_bus.subscribers['test_event']), 2)
        self.assertIn(handler1, self.event_bus.subscribers['test_event'])
        self.assertIn(handler2, self.event_bus.subscribers['test_event'])
    
    def test_publish(self):
        """Test publishing an event."""
        called = False
        def handler(event_type, data):
            nonlocal called
            called = True
        
        self.event_bus.subscribe('test_event', handler)
        
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
        
        self.assertTrue(called)
    
    def test_publish_no_subscribers(self):
        """Test publishing an event with no subscribers."""
        # Should not raise an exception
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
    
    def test_unsubscribe(self):
        """Test unsubscribing from an event."""
        handler = lambda event_type, data: None
        self.event_bus.subscribe('test_event', handler)
        
        # Verify handler is subscribed
        self.assertIn(handler, self.event_bus.subscribers['test_event'])
        
        # Unsubscribe
        self.event_bus.unsubscribe('test_event', handler)
        
        # Verify handler is removed
        self.assertNotIn(handler, self.event_bus.subscribers['test_event'])
    
    def test_get_subscriber_count(self):
        """Test getting subscriber count for an event."""
        handler1 = lambda event_type, data: None
        handler2 = lambda event_type, data: None
        
        self.event_bus.subscribe('test_event', handler1)
        self.event_bus.subscribe('test_event', handler2)
        
        count = self.event_bus.get_subscriber_count('test_event')
        self.assertEqual(count, 2)
    
    def test_get_subscriber_count_nonexistent_event(self):
        """Test getting subscriber count for a nonexistent event."""
        count = self.event_bus.get_subscriber_count('nonexistent_event')
        self.assertEqual(count, 0)
    
    def test_list_event_types(self):
        """Test listing all event types."""
        handler1 = lambda event_type, data: None
        handler2 = lambda event_type, data: None
        
        self.event_bus.subscribe('event1', handler1)
        self.event_bus.subscribe('event2', handler2)
        
        event_types = self.event_bus.list_event_types()
        self.assertIn('event1', event_types)
        self.assertIn('event2', event_types)
        self.assertEqual(len(event_types), 2)
    
    def test_list_event_types_empty(self):
        """Test listing event types when no events are registered."""
        event_types = self.event_bus.list_event_types()
        self.assertEqual(len(event_types), 0)


if __name__ == '__main__':
    unittest.main() 