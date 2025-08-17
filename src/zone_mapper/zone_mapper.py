# zone_mapper.py
"""
Zone mapping module for determining gaze zones based on head pose and position.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json


@dataclass
class Zone:
    """Represents a physical zone in the monitored space."""
    name: str
    display_name: str
    bounds: Optional[Tuple[int, int, int, int]] = None  # x1, y1, x2, y2
    color: Tuple[int, int, int] = (0, 255, 0)  # BGR color
    category: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class GazeContext:
    """Context information for zone mapping."""
    yaw_angle: float
    pitch_angle: float
    face_center_x: int
    face_center_y: int
    frame_width: int # Width of the video frame
    frame_height: int # Height of the video frame
    confidence: float = 1.0


class IZoneMapper(ABC):
    """Interface for zone mapping implementations."""
    
    @abstractmethod
    def map_to_zone(self, context: GazeContext) -> str:
        """Map gaze context to a zone name."""
        pass
    
    @abstractmethod
    def get_zones(self) -> List[Zone]:
        """Get all defined zones."""
        pass


class BakeryZoneMapper(IZoneMapper):
    """Zone mapper specifically for bakery layout."""
    
    def __init__(self):
        self.zones = self._initialize_zones()
        self.position_thresholds = {
            'left': 0.33
        }
        self.gaze_thresholds = {
            'forward_min': -25,
            'forward_max': 25
        }
    
    def _initialize_zones(self) -> List[Zone]:
        """Initialize bakery-specific zones."""
        return [
            Zone(
                name="Left_sandwich_and_croissant_shelves",
                display_name="PASTRY/SANDWICH",
                color=(255, 150, 100),  # Orange
                category="food_display"
            ),
            Zone(
                name="Cake_Display",
                display_name="CAKES",
                color=(100, 255, 100),  # Green
                category="food_display"
            ),
            Zone(
                name="Cookie_Shelves",
                display_name="COOKIES",
                # bounds=(0, 0, 100, 100),  # Example bounds
                color=(100, 150, 255),  # Blue
                category="food_display"
            ),
            Zone(
                name="Right_sandwich_and_bread_shelves",
                display_name="BREAD",
                color=(255, 100, 255),  # Purple
                category="food_display"
            ),
            Zone(
                name="Entrance",
                display_name="ENTRANCE",
                color=(200, 200, 200),  # Gray
                category="navigation"
            ),
            Zone(
                name="Unknown",
                display_name="UNKNOWN",
                color=(128, 128, 128),  # Gray
                category="other"
            )
        ]
    
    def map_to_zone(self, context: GazeContext) -> str:
        """Map gaze context to a bakery zone."""
        position = self._determine_position(context)
        direction = self._determine_direction(context)
        
        # Use mapping logic
        zone_name = self._apply_mapping_rules(position, direction, context)
        
        return zone_name
    
    def _determine_position(self, context: GazeContext) -> str:
        """Determine person's position in the frame."""
        relative_x = context.face_center_x / context.frame_width
        
        if relative_x < self.position_thresholds['left']:
            return "left"
        else:
            return "right"
    
    def _determine_direction(self, context: GazeContext) -> str:
        """Determine gaze direction based on yaw angle."""
        if self.gaze_thresholds['forward_min'] <= context.yaw_angle <= self.gaze_thresholds['forward_max']:
            return "forward"
        elif context.yaw_angle > self.gaze_thresholds['forward_max']:
            return "right"
        else:
            return "left"
    
    def _apply_mapping_rules(self, position: str, direction: str, 
                            context: GazeContext) -> str:
        """Apply zone mapping rules based on position and direction."""
        # Define mapping rules
        zone_mapping = {
            # From left position (entrance area)
            ("left", "forward"): "Left_sandwich_and_croissant_shelves",
            ("left", "right"): "Cake_Display",
            ("left", "left"): "Entrance",
            
            # # From center position
            # ("center", "left"): "Left_sandwich_and_croissant_shelves",
            # ("center", "forward"): self._determine_center_forward_zone(context),
            # ("center", "right"): self._determine_center_right_zone(context),
            
            # From right position
            ("right", "left"): self._determine_right_left_zone(context),
            ("right", "forward"): self._determine_right_forward_zone(context),
            ("right", "right"): "Right_sandwich_and_bread_shelves",
        }
        
        return zone_mapping.get((position, direction), f"Unknown_{position}_{direction}") 
    
    # def _determine_center_forward_zone(self, context: GazeContext) -> str:
    #     """Determine zone when looking forward from center."""
    #     if context.face_center_y < context.frame_height * 0.45:
    #         return "Cake_Display"
    #     else:
    #         return "Left_sandwich_and_croissant_shelves"
    
    # def _determine_center_right_zone(self, context: GazeContext) -> str:
    #     """Determine zone when looking right from center."""
    #     if context.face_center_y < context.frame_height * 0.45:
    #         return "Cookie_Shelves"
    #     else:
    #         return "Right_sandwich_and_bread_shelves"
    
    def _determine_right_left_zone(self, context: GazeContext) -> str:
        """Determine zone when looking left from right position."""
        if context.face_center_y < context.frame_height * 0.45:
            return "Cake_Display"
        else:
            return "Left_sandwich_and_croissant_shelves"
    
    def _determine_right_forward_zone(self, context: GazeContext) -> str:
        """Determine zone when looking forward from right position."""
        if context.face_center_y < context.frame_height * 0.45:
            return "Cookie_Shelves"
        else:
            return "Right_sandwich_and_bread_shelves"
    
    def get_zones(self) -> List[Zone]:
        """Get all defined zones."""
        return self.zones.copy()
    
    def get_zone_by_name(self, name: str) -> Optional[Zone]:
        """Get a specific zone by name."""
        for zone in self.zones:
            if zone.name == name:
                return zone
        return None


class ConfigurableZoneMapper(IZoneMapper):
    """Zone mapper that can be configured from a JSON file."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.zones = self._parse_zones(self.config['zones'])
        self.rules = self.config.get('mapping_rules', {})
    
    def _load_config(self, config_path: str) -> Dict:
        """Load zone configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _parse_zones(self, zones_config: List[Dict]) -> List[Zone]:
        """Parse zones from configuration."""
        zones = []
        for zone_cfg in zones_config:
            zone = Zone(
                name=zone_cfg['name'],
                display_name=zone_cfg.get('display_name', zone_cfg['name']),
                bounds=tuple(zone_cfg['bounds']) if 'bounds' in zone_cfg else None,
                color=tuple(zone_cfg.get('color', [0, 255, 0])),
                category=zone_cfg.get('category'),
                metadata=zone_cfg.get('metadata')
            )
            zones.append(zone)
        return zones
    
    def map_to_zone(self, context: GazeContext) -> str:
        """Map gaze context to a zone using configured rules."""
        # This is a simplified implementation
        # In practice, you'd implement more sophisticated rule parsing
        for zone in self.zones:
            if zone.bounds:
                x1, y1, x2, y2 = zone.bounds
                if (x1 <= context.face_center_x <= x2 and 
                    y1 <= context.face_center_y <= y2):
                    return zone.name
        
        return "Unknown"
    
    def get_zones(self) -> List[Zone]:
        """Get all defined zones."""
        return self.zones.copy()


class ZoneMapperFactory:
    """Factory for creating zone mappers."""
    
    @staticmethod
    def create_mapper(mapper_type: str = "bakery", 
                     config_path: Optional[str] = None) -> IZoneMapper:
        """Create a zone mapper based on type."""
        if mapper_type == "bakery":
            return BakeryZoneMapper()
        elif mapper_type == "configurable" and config_path:
            print('need to implement zone mapper from config')
        else:
            raise ValueError(f"Unknown mapper type: {mapper_type} or missing config")