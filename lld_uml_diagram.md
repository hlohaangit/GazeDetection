# Gaze Tracking System - Low Level Design UML Diagram

## Class Diagram

```mermaid
---
config:
  layout: elk
---
classDiagram
   class GazeTrackingSystem {
       -face_tracker: FaceTracker
       -head_pose_estimator: IHeadPoseEstimator
       -zone_mapper: IZoneMapper
       -analytics_writer: IAnalyticsWriter
       +process_video(path: str)
       +process_live_camera(id: int)
   }
   class IHeadPoseEstimator {
       <<interface>>
       +estimate_pose(landmarks, shape) HeadPose
   }
   class IZoneMapper {
       <<interface>>
       +map_to_zone(context: GazeContext) str
       +get_zones() List~Zone~
   }
   class IAnalyticsWriter {
       <<interface>>
       +write_session(session_data)
       +write_aggregate(aggregate_data)
       +close()
   }
   class FaceTracker {
       -active_faces: Dict
       -completed_sessions: List
       +update(faces: List~FaceDetection~, frame: int)
       +finalize_all_sessions()
   }
   class MediaPipeHeadPoseEstimator {
       +estimate_pose(landmarks, shape) HeadPose
   }
   class BakeryZoneMapper {
       -zones: List~Zone~
       +map_to_zone(context: GazeContext) str
       +get_zones() List~Zone~
   }
   class ConsoleAnalyticsWriter {
       +write_session(session_data)
       +write_aggregate(aggregate_data)
   }
   class DatabaseAnalyticsWriter {
       -db_path: str
       +write_session(session_data)
       +write_aggregate(aggregate_data)
   }
   class FaceDetection {
       <<dataclass>>
       +box: Tuple
       +zone: str
       +confidence: float
   }
   class TrackingSession {
       <<dataclass>>
       +id: int
       +total_duration: float
       +zone_durations: Dict
   }
   class HeadPoseEstimatorFactory {
       +create_estimator(type: str)$ IHeadPoseEstimator
   }
   class ZoneMapperFactory {
       +create_mapper(type: str)$ IZoneMapper
   }
   GazeTrackingSystem --> FaceTracker : uses
   GazeTrackingSystem --> IHeadPoseEstimator : uses
   GazeTrackingSystem --> IZoneMapper : uses
   GazeTrackingSystem --> IAnalyticsWriter : uses
   MediaPipeHeadPoseEstimator ..|> IHeadPoseEstimator : implements
   BakeryZoneMapper ..|> IZoneMapper : implements
   ConsoleAnalyticsWriter ..|> IAnalyticsWriter : implements
   DatabaseAnalyticsWriter ..|> IAnalyticsWriter : implements
   HeadPoseEstimatorFactory ..> IHeadPoseEstimator : creates
   ZoneMapperFactory ..> IZoneMapper : creates
   FaceTracker --> FaceDetection : processes
   FaceTracker --> TrackingSession : produces
   class MediaPipe {
       <<external>>
       +FaceDetection
       +FaceMesh
   }
   class OpenCV {
       <<external>>
       +VideoCapture
       +VideoWriter
   }
   GazeTrackingSystem --> MediaPipe : uses
   GazeTrackingSystem --> OpenCV : uses

```

## Component Diagram

```mermaid
graph TB
    subgraph "Gaze Tracking System"
        subgraph "Core System"
            Main[GazeTrackingSystem]
            Config[Configuration]
        end
        
        subgraph "Face Processing Pipeline"
            FaceDetector[MediaPipe Face Detection]
            FaceMesh[MediaPipe Face Mesh]
            HeadPose[Head Pose Estimator]
            ZoneMapper[Zone Mapper]
        end
        
        subgraph "Tracking & Analytics"
            FaceTracker[Face Tracker]
            AnalyticsProcessor[Analytics Processor]
        end
        
        subgraph "Output Writers"
            Console[Console Writer]
        end
        
        subgraph "Data Models"
            FaceDetection[Face Detection]
            TrackedFace[Tracked Face]
            Session[Tracking Session]
            Analytics[Analytics Data]
        end
    end
    
    %% Data Flow
    Video[Video Input] --> Main
    Main --> FaceDetector
    FaceDetector --> FaceMesh
    FaceMesh --> HeadPose
    HeadPose --> ZoneMapper
    ZoneMapper --> FaceTracker
    FaceTracker --> AnalyticsProcessor
    AnalyticsProcessor --> OutputWriters
    
    %% Output Writers
    AnalyticsProcessor --> Console
    
    %% Configuration
    Config --> Main
    Config --> FaceTracker
    Config --> ZoneMapper
    Config --> OutputWriters
```

## Sequence Diagram for Video Processing

```mermaid
sequenceDiagram
   participant V as Video Source
   participant M as Main System
   participant MP as MediaPipe
   participant FT as FaceTracker
   participant HPE as HeadPoseEstimator
   participant ZM as ZoneMapper
   participant AW as AnalyticsWriter

   %% Video Processing Loop
   Note over V,AW: Video Processing Loop (per frame)
   
   V->>M: Frame data
   M->>MP: Process frame
   MP->>MP: Detect faces
   MP-->>M: Detection results
   
   %% For each detected face
   Note over M,ZM: For each detected face
   
   M->>M: Extract face region
   M->>MP: Process face mesh
   MP-->>M: Facial landmarks
   
   M->>HPE: estimate_pose(landmarks)
   HPE->>HPE: Calculate yaw/pitch
   HPE-->>M: HeadPose object
   
   M->>ZM: map_to_zone(GazeContext)
   ZM->>ZM: Apply mapping rules
   ZM-->>M: Zone name
   
   M->>M: Create FaceDetection
   %%Note right of M: FaceDetection contains:<br/>- box coordinates<br/>- head pose<br/>- zone<br/>- confidence

   M->>FT: update(List[FaceDetection])
   FT->>FT: Match to existing faces, keep track of faces
   
   

   %% Face leaves frame
   Note over FT,AW: When face leaves frame
   
   FT->>FT: Detect missing faces and end session

   %%Note right of FT: TrackingSession contains:<br/>- total_duration<br/>- zone_durations<br/>- gaze_history<br/>- unique_zones
   
   FT->>AW: write_session(TrackingSession)
   
   AW->>AW: Format output


   %% Aggregate Analytics
   Note over M,AW: End of processing
   
   M->>FT: finalize_all_sessions()
   FT->>AW: Remaining sessions
   M->>M: Calculate aggregates
   M->>AW: write_aggregate(AggregateAnalytics)
   AW->>AW: close()

   %% Legend
   Note over V,AW: Data Classes Flow:<br/>Frame → FaceDetection → TrackedFace → TrackingSession → AnalyticsWriters
```

## Key Design Patterns Used

1. **Factory Pattern**: `HeadPoseEstimatorFactory` and `ZoneMapperFactory`
2. **Strategy Pattern**: Different implementations of `IHeadPoseEstimator` and `IZoneMapper`
3. **Observer Pattern**: Session callbacks in `FaceTracker`
4. **Template Method**: Base processing pipeline in `GazeTrackingSystem`
5. **Data Transfer Objects**: `FaceDetection`, `TrackedFace`, `GazeRecord`, etc.

## System Architecture Highlights

- **Modular Design**: Clear separation of concerns with dedicated modules for each responsibility
- **Interface-based Design**: Uses abstract interfaces for extensibility
- **Configuration-driven**: System behavior controlled via JSON configuration
- **Multi-output Support**: Analytics can be written to console, database, and JSON simultaneously
- **Real-time Processing**: Supports both video files and live camera feeds
- **Extensible Zone Mapping**: Easy to add new zone configurations for different physical spaces
