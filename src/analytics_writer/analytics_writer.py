# analytics_writer.py
"""
Analytics module for processing tracking data and writing to various outputs.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from datetime import datetime
import json
import csv
import sqlite3
from collections import defaultdict
import numpy as np
from pathlib import Path


@dataclass
class SessionAnalytics:
    """Analytics data for a tracking session."""
    session_id: int
    timestamp: datetime
    duration: float
    zones_visited: int
    zone_transitions: int
    avg_confidence: float
    primary_zone: str
    primary_zone_duration: float
    dwell_times: Dict[str, float]
    peak_interest_zones: List[Tuple[str, float]]
    engagement_score: float
    path_complexity: float


@dataclass
class AggregateAnalytics:
    """Aggregate analytics across multiple sessions."""
    total_sessions: int
    avg_session_duration: float
    total_time_tracked: float
    zone_popularity: Dict[str, float]
    avg_zones_per_session: float
    peak_hours: List[Tuple[int, int]]  # hour, count
    conversion_zones: List[str]
    avg_engagement_score: float


class IAnalyticsWriter(ABC):
    """Interface for analytics writers."""
    
    @abstractmethod
    def write_session(self, session_data: Any) -> None:
        """Write individual session data."""
        pass
    
    @abstractmethod
    def write_aggregate(self, aggregate_data: AggregateAnalytics) -> None:
        """Write aggregate analytics."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass


class ConsoleAnalyticsWriter(IAnalyticsWriter):
    """Write analytics to console output."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.session_count = 0
    
    def write_session(self, session_data: Any) -> None:
        print(len(session_data.zone_durations),"-- zome durations")
        print(len(session_data.gaze_history),"-- gaze history")
        """Write session data to console."""
        self.session_count += 1
        
        print("\n" + "="*60)
        print(f"FACE TRACKING SESSION COMPLETED - ID: {session_data.id}")
        print("="*60)
        print(f"Total Duration: {session_data.total_duration:.2f} seconds")
        print(f"Frames: {session_data.start_frame} to {session_data.end_frame}")
        print(f"Average Confidence: {session_data.avg_confidence:.2f}")
        print(f"\nZones Visited: {', '.join(session_data.unique_zones_visited)}")
        
        if session_data.total_duration > 0:
            print("\nTime Spent in Each Zone:")
            sorted_zones = sorted(session_data.zone_durations.items(), 
                                key=lambda x: x[1], reverse=True)
            for zone, duration in sorted_zones:
                percentage = (duration / session_data.total_duration) * 100
                print(f"  {zone}: {duration:.2f}s ({percentage:.1f}%)")
        
        if self.verbose and session_data.peak_interest_zones:
            print("\nPeak Interest Zones:")
            for zone, duration in session_data.peak_interest_zones[:3]:
                print(f"  - {zone}: {duration:.2f}s")
        
        print("="*60 + "\n")
    
    def write_aggregate(self, aggregate_data: AggregateAnalytics) -> None:
        """Write aggregate data to console."""
        print("\n" + "="*60)
        print("OVERALL STATISTICS")
        print("="*60)
        print(f"Total Sessions: {aggregate_data.total_sessions}")
        print(f"Average Session Duration: {aggregate_data.avg_session_duration:.2f}s")
        print(f"Total Time Tracked: {aggregate_data.total_time_tracked:.2f}s")
        print(f"Average Zones per Session: {aggregate_data.avg_zones_per_session:.1f}")
        print(f"Average Engagement Score: {aggregate_data.avg_engagement_score:.2f}")
        
        print("\nZone Popularity (by total time):")
        sorted_zones = sorted(aggregate_data.zone_popularity.items(), 
                            key=lambda x: x[1], reverse=True)
        for zone, duration in sorted_zones:
            percentage = (duration / aggregate_data.total_time_tracked) * 100
            print(f"  {zone}: {duration:.2f}s ({percentage:.1f}%)")
        
        if aggregate_data.peak_hours:
            print("\nPeak Hours:")
            for hour, count in aggregate_data.peak_hours[:5]:
                print(f"  {hour:02d}:00 - {count} sessions")
    
    def close(self) -> None:
        """No cleanup needed for console output."""
        pass


class DatabaseAnalyticsWriter(IAnalyticsWriter):
    """Write analytics to SQLite database."""
    
    def __init__(self, db_path: str = "gaze_analytics.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                start_frame INTEGER,
                end_frame INTEGER,
                duration REAL,
                zones_visited INTEGER,
                zone_transitions INTEGER,
                avg_confidence REAL,
                primary_zone TEXT,
                primary_zone_duration REAL,
                engagement_score REAL,
                path_complexity REAL
            )
        ''')
        
        # Zone durations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zone_durations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                zone_name TEXT,
                duration REAL,
                percentage REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Gaze history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gaze_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                frame INTEGER,
                zone TEXT,
                yaw REAL,
                pitch REAL,
                position_x INTEGER,
                position_y INTEGER,
                confidence REAL,
                timestamp REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Aggregate statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aggregate_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_sessions INTEGER,
                avg_session_duration REAL,
                total_time_tracked REAL,
                avg_zones_per_session REAL,
                avg_engagement_score REAL
            )
        ''')
        
        self.conn.commit()
    
    def write_session(self, session_data: Any) -> None:
        """Write session data to database."""
        cursor = self.conn.cursor()
        
        # Calculate analytics
        analytics = self._calculate_session_analytics(session_data)
        
        # Insert main session data
        cursor.execute('''
            INSERT INTO sessions (
                session_id, start_frame, end_frame, duration, zones_visited,
                zone_transitions, avg_confidence, primary_zone, primary_zone_duration,
                engagement_score, path_complexity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data.id,
            session_data.start_frame,
            session_data.end_frame,
            session_data.total_duration,
            len(session_data.unique_zones_visited),
            session_data.total_zone_transitions,
            session_data.avg_confidence,
            analytics.primary_zone,
            analytics.primary_zone_duration,
            analytics.engagement_score,
            analytics.path_complexity
        ))
        
        # Insert zone durations
        for zone, duration in session_data.zone_durations.items():
            percentage = (duration / session_data.total_duration * 100 
                         if session_data.total_duration > 0 else 0)
            cursor.execute('''
                INSERT INTO zone_durations (session_id, zone_name, duration, percentage)
                VALUES (?, ?, ?, ?)
            ''', (session_data.id, zone, duration, percentage))
        
        # Insert gaze history (sample every 10th record to reduce size)
        for i, gaze in enumerate(session_data.gaze_history):
            if i % 10 == 0:  # Sample rate
                cursor.execute('''
                    INSERT INTO gaze_history (
                        session_id, frame, zone, yaw, pitch, 
                        position_x, position_y, confidence, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_data.id,
                    gaze.frame,
                    gaze.zone,
                    gaze.yaw,
                    gaze.pitch,
                    gaze.position[0],
                    gaze.position[1],
                    gaze.confidence,
                    gaze.timestamp
                ))
        
        self.conn.commit()
    
    def _calculate_session_analytics(self, session_data: Any) -> SessionAnalytics:
        """Calculate detailed analytics for a session."""
        # Find primary zone
        if session_data.zone_durations:
            primary_zone = max(session_data.zone_durations.items(), 
                             key=lambda x: x[1])
        else:
            primary_zone = ("Unknown", 0)
        
        # Calculate engagement score (0-1)
        engagement_score = self._calculate_engagement_score(session_data)
        
        # Calculate path complexity
        path_complexity = (session_data.total_zone_transitions / 
                          max(len(session_data.unique_zones_visited), 1))
        
        return SessionAnalytics(
            session_id=session_data.id,
            timestamp=datetime.now(),
            duration=session_data.total_duration,
            zones_visited=len(session_data.unique_zones_visited),
            zone_transitions=session_data.total_zone_transitions,
            avg_confidence=session_data.avg_confidence,
            primary_zone=primary_zone[0],
            primary_zone_duration=primary_zone[1],
            dwell_times=session_data.zone_durations,
            peak_interest_zones=session_data.peak_interest_zones,
            engagement_score=engagement_score,
            path_complexity=path_complexity
        )
    
    def _calculate_engagement_score(self, session_data: Any) -> float:
        """Calculate engagement score based on various factors."""
        factors = []
        
        # Duration factor (normalize to 0-1, assuming 60s is high engagement)
        duration_score = min(session_data.total_duration / 60, 1.0)
        factors.append(duration_score * 0.3)
        
        # Zone exploration factor
        exploration_score = min(len(session_data.unique_zones_visited) / 5, 1.0)
        factors.append(exploration_score * 0.2)
        
        # Confidence factor
        factors.append(session_data.avg_confidence * 0.2)
        
        # Dwell time concentration (how focused was the attention)
        if session_data.zone_durations and session_data.total_duration > 0:
            durations = list(session_data.zone_durations.values())
            concentration = max(durations) / session_data.total_duration
            factors.append(concentration * 0.3)
        else:
            factors.append(0)
        
        return sum(factors)
    
    def write_aggregate(self, aggregate_data: AggregateAnalytics) -> None:
        """Write aggregate statistics to database."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO aggregate_stats (
                total_sessions, avg_session_duration, total_time_tracked,
                avg_zones_per_session, avg_engagement_score
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            aggregate_data.total_sessions,
            aggregate_data.avg_session_duration,
            aggregate_data.total_time_tracked,
            aggregate_data.avg_zones_per_session,
            aggregate_data.avg_engagement_score
        ))
        
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()


class JSONAnalyticsWriter(IAnalyticsWriter):
    """Write analytics to JSON files."""
    
    def __init__(self, output_dir: str = "analytics_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.sessions = []
    
    def write_session(self, session_data: Any) -> None:
        """Write session data to JSON."""
        session_dict = {
            'id': session_data.id,
            'timestamp': datetime.now().isoformat(),
            'start_frame': session_data.start_frame,
            'end_frame': session_data.end_frame,
            'total_duration': session_data.total_duration,
            'zone_durations': session_data.zone_durations,
            'unique_zones_visited': session_data.unique_zones_visited,
            'avg_confidence': session_data.avg_confidence,
            'total_zone_transitions': session_data.total_zone_transitions,
            'peak_interest_zones': session_data.peak_interest_zones
        }
        
        self.sessions.append(session_dict)
        
        # Write individual session file
        session_file = self.output_dir / f"session_{session_data.id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_dict, f, indent=2)
    
    def write_aggregate(self, aggregate_data: AggregateAnalytics) -> None:
        """Write aggregate data to JSON."""
        aggregate_dict = asdict(aggregate_data)
        aggregate_dict['timestamp'] = datetime.now().isoformat()
        
        # Write aggregate file
        aggregate_file = self.output_dir / "aggregate_analytics.json"
        with open(aggregate_file, 'w') as f:
            json.dump(aggregate_dict, f, indent=2)
        
        # Write all sessions file
        all_sessions_file = self.output_dir / "all_sessions.json"
        with open(all_sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)
    
    def close(self) -> None:
        """No cleanup needed for JSON writer."""
        pass


class CompositeAnalyticsWriter(IAnalyticsWriter):
    """Composite writer that writes to multiple outputs."""
    
    def __init__(self, writers: List[IAnalyticsWriter]):
        self.writers = writers
    
    def write_session(self, session_data: Any) -> None:
        """Write session data to all writers."""
        for writer in self.writers:
            writer.write_session(session_data)
    
    def write_aggregate(self, aggregate_data: AggregateAnalytics) -> None:
        """Write aggregate data to all writers."""
        for writer in self.writers:
            writer.write_aggregate(aggregate_data)
    
    def close(self) -> None:
        """Close all writers."""
        for writer in self.writers:
            writer.close()


class AnalyticsProcessor:
    """Process tracking sessions and generate analytics."""
    
    def __init__(self, writer: IAnalyticsWriter):
        self.writer = writer
    
    def process_sessions(self, sessions: List[Any]) -> AggregateAnalytics:
        """Process multiple sessions and generate aggregate analytics."""
        if not sessions:
            return self._empty_aggregate()
        
        # Calculate aggregate metrics
        total_sessions = len(sessions)
        total_time = sum(s.total_duration for s in sessions)
        avg_duration = total_time / total_sessions
        
        # Zone popularity
        zone_totals = defaultdict(float)
        for session in sessions:
            for zone, duration in session.zone_durations.items():
                zone_totals[zone] += duration
        
        # Average zones per session
        avg_zones = np.mean([len(s.unique_zones_visited) for s in sessions])
        
        # Calculate engagement scores
        engagement_scores = []
        for session in sessions:
            score = self._calculate_session_engagement(session)
            engagement_scores.append(score)
        avg_engagement = np.mean(engagement_scores) if engagement_scores else 0
        
        # Peak hours (simplified - would need actual timestamps)
        peak_hours = self._calculate_peak_hours(sessions)
        
        # Conversion zones (zones with longest dwell times)
        conversion_zones = sorted(zone_totals.keys(), 
                                key=lambda z: zone_totals[z], 
                                reverse=True)[:3]
        
        return AggregateAnalytics(
            total_sessions=total_sessions,
            avg_session_duration=avg_duration,
            total_time_tracked=total_time,
            zone_popularity=dict(zone_totals),
            avg_zones_per_session=avg_zones,
            peak_hours=peak_hours,
            conversion_zones=conversion_zones,
            avg_engagement_score=avg_engagement
        )
    
    def _calculate_session_engagement(self, session: Any) -> float:
        """Calculate engagement score for a session."""
        # Similar to DatabaseAnalyticsWriter implementation
        factors = []
        
        duration_score = min(session.total_duration / 60, 1.0)
        factors.append(duration_score * 0.3)
        
        exploration_score = min(len(session.unique_zones_visited) / 5, 1.0)
        factors.append(exploration_score * 0.2)
        
        factors.append(session.avg_confidence * 0.2)
        
        if session.zone_durations and session.total_duration > 0:
            durations = list(session.zone_durations.values())
            concentration = max(durations) / session.total_duration
            factors.append(concentration * 0.3)
        else:
            factors.append(0)
        
        return sum(factors)
    
    def _calculate_peak_hours(self, sessions: List[Any]) -> List[Tuple[int, int]]:
        """Calculate peak hours from sessions."""
        # This is a simplified implementation
        # In practice, you'd use actual timestamps
        hour_counts = defaultdict(int)
        
        for i, session in enumerate(sessions):
            # Simulate hour based on session index
            hour = (9 + i) % 24  # Assuming starting at 9 AM
            hour_counts[hour] += 1
        
        # Sort by count and return top 5
        sorted_hours = sorted(hour_counts.items(), 
                            key=lambda x: x[1], 
                            reverse=True)
        return sorted_hours[:5]
    
    def _empty_aggregate(self) -> AggregateAnalytics:
        """Return empty aggregate analytics."""
        return AggregateAnalytics(
            total_sessions=0,
            avg_session_duration=0,
            total_time_tracked=0,
            zone_popularity={},
            avg_zones_per_session=0,
            peak_hours=[],
            conversion_zones=[],
            avg_engagement_score=0
        )