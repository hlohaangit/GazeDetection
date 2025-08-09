# Modular Gaze Tracking System

This is a refactored version of the gaze tracking system with a modular, maintainable architecture.

## Architecture Overview

The system is now organized into clear, separate modules with well-defined interfaces:

```
src/
├── core/                    # Core interfaces and utilities
│   ├── interfaces.py       # Abstract base classes
│   ├── config_manager.py   # Configuration management
│   └── event_bus.py        # Event-driven communication
├── face_detection/         # Face detection components
│   └── face_detector.py    # MediaPipe face detector
├── visualization/          # Visualization components
│   └── visualizer.py       # Gaze tracking visualizer
├── processing/             # Processing components
│   ├── frame_processor.py  # Frame processing coordination
│   └── video_processor.py  # Video I/O and processing
├── pipeline/               # Main pipeline
│   └── gaze_tracking_pipeline.py  # Main orchestrator
└── main.py                 # Entry point
```

## Key Improvements

### 1. **Separation of Concerns**
Each component has a single responsibility:
- **Face Detection**: Handles only face detection logic
- **Visualization**: Handles only drawing and display
- **Processing**: Coordinates frame processing
- **Configuration**: Manages all system settings

### 2. **Interface-Based Design**
All components implement well-defined interfaces:
- `IFaceDetector`: For face detection implementations
- `IVisualizer`: For visualization implementations
- `IConfigManager`: For configuration management
- `IEventBus`: For event-driven communication

### 3. **Dependency Injection**
Components receive their dependencies rather than creating them:
```python
# Instead of creating dependencies internally
self.face_detector = MediaPipeFaceDetector(
    config, 
    pose_estimator=self.pose_estimator,
    zone_mapper=self.zone_mapper
)
```

### 4. **Configuration Management**
Centralized configuration with section-based access:
```python
config = config_manager.get_config('face_detection')
confidence = config.get('detection_confidence', 0.3)
```

### 5. **Event-Driven Communication**
Components can communicate through events:
```python
event_bus.publish('face_detected', face_data)
event_bus.subscribe('session_completed', handler)
```

## Usage

### Basic Usage
```bash
# Process a video file
python src/main.py video.mp4

# Use live camera
python src/main.py 0

# Use custom configuration
python src/main.py video.mp4 --config config_modular.json

# Save current configuration
python src/main.py 0 --save-config my_config.json
```

### Configuration
The system uses a hierarchical configuration structure:

```json
{
  "system": {
    "fps": 30.0,
    "frame_skip": 1,
    "logging_level": "INFO"
  },
  "face_detection": {
    "detection_confidence": 0.3,
    "mesh_confidence": 0.3
  },
  "visualization": {
    "display_output": true,
    "save_output": false
  },
  "analytics": {
    "console_output": true,
    "database_output": true,
    "json_output": true
  }
}
```

## Benefits

### 1. **Testability**
Each component can be unit tested independently:
```python
def test_face_detector():
    detector = MediaPipeFaceDetector(config)
    faces = detector.detect_faces(test_frame)
    assert len(faces) > 0
```

### 2. **Extensibility**
Easy to add new components by implementing interfaces:
```python
class CustomFaceDetector(IFaceDetector):
    def detect_faces(self, frame):
        # Custom detection logic
        pass
```

### 3. **Maintainability**
Clear separation makes it easy to:
- Fix bugs in specific components
- Add new features without affecting others
- Understand the system structure

### 4. **Reusability**
Components can be reused in different contexts:
```python
# Use face detector in a different application
detector = MediaPipeFaceDetector(config)
faces = detector.detect_faces(frame)
```

### 5. **Performance**
Easier to optimize individual components:
- Profile specific components
- Replace slow components with faster alternatives
- Parallelize independent components

## Component Details

### Core Components

#### `ConfigManager`
- Loads configuration from JSON files
- Provides section-based access to settings
- Supports configuration merging and validation

#### `EventBus`
- Enables loose coupling between components
- Supports publish/subscribe pattern
- Handles error isolation

### Processing Components

#### `FrameProcessor`
- Coordinates frame processing pipeline
- Manages dependencies between components
- Provides clean processing interface

#### `VideoProcessor`
- Handles video I/O operations
- Manages frame extraction and output writing
- Coordinates visualization and processing

### Detection Components

#### `MediaPipeFaceDetector`
- Implements `IFaceDetector` interface
- Handles MediaPipe face detection and mesh
- Integrates pose estimation and zone mapping

### Visualization Components

#### `GazeTrackingVisualizer`
- Implements `IVisualizer` interface
- Handles all drawing operations
- Manages display and output generation

## Migration from Old System

The old monolithic `GazeTrackingSystem` class has been broken down into:

1. **Face Detection Logic** → `MediaPipeFaceDetector`
2. **Visualization Logic** → `GazeTrackingVisualizer`
3. **Video Processing** → `VideoProcessor`
4. **Configuration** → `ConfigManager`
5. **Coordination** → `GazeTrackingPipeline`

## Future Enhancements

This modular architecture enables:

1. **Plugin System**: Easy to add new detectors, visualizers, or processors
2. **Distributed Processing**: Components can run on different machines
3. **Real-time Streaming**: Event-driven architecture supports streaming
4. **Multiple Output Formats**: Easy to add new analytics writers
5. **A/B Testing**: Easy to compare different component implementations

## Testing

Each component can be tested independently:

```python
# Test configuration manager
def test_config_manager():
    config = ConfigManager("test_config.json")
    assert config.get_config('system')['fps'] == 30.0

# Test face detector
def test_face_detector():
    detector = MediaPipeFaceDetector(config)
    faces = detector.detect_faces(test_frame)
    assert isinstance(faces, list)

# Test visualizer
def test_visualizer():
    visualizer = GazeTrackingVisualizer(config, zone_mapper)
    result = visualizer.visualize(frame, data)
    assert result.shape == frame.shape
```

This modular architecture makes the system more maintainable, testable, and extensible while preserving all the original functionality. 