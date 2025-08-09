"""
Event-driven communication system for the gaze tracking pipeline.
This module provides a simple event bus for loose coupling between components.
"""

from typing import Dict, List, Any, Callable
from collections import defaultdict
from .interfaces import IEventBus


class EventBus(IEventBus):
    """Simple event bus for component communication.
    
    This class enables loose coupling between components by allowing them
    to communicate through events rather than direct method calls.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all subscribers.
        
        Args:
            event_type: Type of event being published
            data: Event data to send to subscribers
        """
        for handler in self.subscribers[event_type]:
            try:
                handler(event_type, data)
            except Exception as e:
                print(f"Error in event handler for {event_type}: {e}")
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        self.subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Function to remove from subscribers
        """
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                h for h in self.subscribers[event_type] if h != handler
            ]
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Get the number of subscribers for an event type.
        
        Args:
            event_type: Type of event to check
            
        Returns:
            Number of subscribers for the event type
        """
        return len(self.subscribers.get(event_type, []))
    
    def list_event_types(self) -> List[str]:
        """Get a list of all registered event types.
        
        Returns:
            List of event types that have subscribers
        """
        return list(self.subscribers.keys()) 