"""
Unit tests for the event bus.
"""

import unittest
from unittest.mock import Mock, call
from src.core.event_bus import EventBus


class TestEventBus(unittest.TestCase):
    """Test cases for the EventBus class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
    
    def test_init(self):
        """Test event bus initialization."""
        self.assertIsNotNone(self.event_bus.subscribers)
        self.assertEqual(len(self.event_bus.subscribers), 0)
    
    def test_subscribe(self):
        """Test subscribing to an event."""
        handler = Mock()
        self.event_bus.subscribe('test_event', handler)
        
        self.assertIn('test_event', self.event_bus.subscribers)
        self.assertIn(handler, self.event_bus.subscribers['test_event'])
    
    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to the same event."""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_bus.subscribe('test_event', handler1)
        self.event_bus.subscribe('test_event', handler2)
        
        self.assertEqual(len(self.event_bus.subscribers['test_event']), 2)
        self.assertIn(handler1, self.event_bus.subscribers['test_event'])
        self.assertIn(handler2, self.event_bus.subscribers['test_event'])
    
    def test_publish(self):
        """Test publishing an event."""
        handler = Mock()
        self.event_bus.subscribe('test_event', handler)
        
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
        
        handler.assert_called_once_with('test_event', test_data)
    
    def test_publish_multiple_handlers(self):
        """Test publishing an event with multiple handlers."""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_bus.subscribe('test_event', handler1)
        self.event_bus.subscribe('test_event', handler2)
        
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
        
        handler1.assert_called_once_with('test_event', test_data)
        handler2.assert_called_once_with('test_event', test_data)
    
    def test_publish_no_subscribers(self):
        """Test publishing an event with no subscribers."""
        # Should not raise an exception
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
    
    def test_publish_handler_exception(self):
        """Test publishing when a handler raises an exception."""
        def failing_handler(event_type, data):
            raise ValueError("Handler error")
        
        def working_handler(event_type, data):
            pass
        
        self.event_bus.subscribe('test_event', failing_handler)
        self.event_bus.subscribe('test_event', working_handler)
        
        # Should not raise an exception, should handle the error gracefully
        test_data = {'key': 'value'}
        self.event_bus.publish('test_event', test_data)
    
    def test_unsubscribe(self):
        """Test unsubscribing from an event."""
        handler = Mock()
        self.event_bus.subscribe('test_event', handler)
        
        # Verify handler is subscribed
        self.assertIn(handler, self.event_bus.subscribers['test_event'])
        
        # Unsubscribe
        self.event_bus.unsubscribe('test_event', handler)
        
        # Verify handler is removed
        self.assertNotIn(handler, self.event_bus.subscribers['test_event'])
    
    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that wasn't subscribed."""
        handler = Mock()
        
        # Should not raise an exception
        self.event_bus.unsubscribe('test_event', handler)
    
    def test_unsubscribe_nonexistent_event(self):
        """Test unsubscribing from a nonexistent event."""
        handler = Mock()
        
        # Should not raise an exception
        self.event_bus.unsubscribe('nonexistent_event', handler)
    
    def test_get_subscriber_count(self):
        """Test getting subscriber count for an event."""
        handler1 = Mock()
        handler2 = Mock()
        
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
        handler1 = Mock()
        handler2 = Mock()
        
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
    
    def test_multiple_event_types(self):
        """Test handling multiple different event types."""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_bus.subscribe('event1', handler1)
        self.event_bus.subscribe('event2', handler2)
        
        # Publish to event1
        self.event_bus.publish('event1', {'data': 'value1'})
        handler1.assert_called_once_with('event1', {'data': 'value1'})
        handler2.assert_not_called()
        
        # Reset mocks
        handler1.reset_mock()
        handler2.reset_mock()
        
        # Publish to event2
        self.event_bus.publish('event2', {'data': 'value2'})
        handler1.assert_not_called()
        handler2.assert_called_once_with('event2', {'data': 'value2'})


if __name__ == '__main__':
    unittest.main() 