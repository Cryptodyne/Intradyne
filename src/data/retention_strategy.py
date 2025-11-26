"""
Adaptive Data Retention Strategy
Intelligently manages historical data based on importance and age
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import logging

class DataRetentionStrategy:
    """
    Adaptive data retention with intelligent compression.
    Keeps important data longer, compresses old data.
    """
    
    def __init__(self, max_raw_samples: int = 1000, 
                 max_compressed_samples: int = 10000):
        """
        Initialize retention strategy.
        
        Args:
            max_raw_samples: Max high-resolution samples
            max_compressed_samples: Max compressed samples
        """
        self.max_raw_samples = max_raw_samples
        self.max_compressed_samples = max_compressed_samples
        
        # Data storage
        self.raw_data = deque(maxlen=max_raw_samples)
        self.compressed_data = deque(maxlen=max_compressed_samples)
        
        # Importance tracking
        self.important_indices = set()
        
        self.logger = logging.getLogger("DataRetention")
    
    def add_data(self, data: Dict, importance: float = 0.5):
        """
        Add data point with importance score.
        
        Args:
            data: Data point to store
            importance: Importance score (0-1)
        """
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        
        # Add importance score
        data['importance'] = importance
        
        # Add to raw data
        self.raw_data.append(data)
        
        # Mark as important if high score
        if importance > 0.8:
            self.important_indices.add(len(self.raw_data) - 1)
        
        # Compress old data if needed
        if len(self.raw_data) >= self.max_raw_samples * 0.9:
            self._compress_old_data()
    
    def _compress_old_data(self):
        """Compress oldest raw data"""
        # Take oldest 20% of data
        compress_count = int(len(self.raw_data) * 0.2)
        
        if compress_count == 0:
            return
        
        # Extract data to compress
        to_compress = []
        for i in range(compress_count):
            if len(self.raw_data) > 0:
                data = self.raw_data.popleft()
                
                # Keep important data in raw form
                if data.get('importance', 0) > 0.8:
                    self.raw_data.append(data)
                else:
                    to_compress.append(data)
        
        # Compress data (aggregate)
        if to_compress:
            compressed = self._aggregate_data(to_compress)
            self.compressed_data.append(compressed)
            self.logger.info(f"Compressed {len(to_compress)} samples into 1")
    
    def _aggregate_data(self, data_points: List[Dict]) -> Dict:
        """Aggregate multiple data points"""
        if not data_points:
            return {}
        
        # Extract numeric fields
        numeric_fields = {}
        for point in data_points:
            for key, value in point.items():
                if isinstance(value, (int, float)) and key != 'importance':
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(value)
        
        # Aggregate
        aggregated = {
            'timestamp_start': data_points[0]['timestamp'],
            'timestamp_end': data_points[-1]['timestamp'],
            'count': len(data_points),
            'compressed': True
        }
        
        for key, values in numeric_fields.items():
            aggregated[f'{key}_mean'] = np.mean(values)
            aggregated[f'{key}_min'] = np.min(values)
            aggregated[f'{key}_max'] = np.max(values)
            aggregated[f'{key}_std'] = np.std(values)
        
        return aggregated
    
    def get_recent_data(self, n: int = 100) -> List[Dict]:
        """Get n most recent raw data points"""
        return list(self.raw_data)[-n:]
    
    def get_all_data(self) -> Dict:
        """Get all data (raw + compressed)"""
        return {
            'raw': list(self.raw_data),
            'compressed': list(self.compressed_data),
            'total_samples': len(self.raw_data) + len(self.compressed_data)
        }
    
    def get_stats(self) -> Dict:
        """Get retention statistics"""
        return {
            'raw_samples': len(self.raw_data),
            'compressed_samples': len(self.compressed_data),
            'total_samples': len(self.raw_data) + len(self.compressed_data),
            'important_samples': len(self.important_indices),
            'compression_ratio': len(self.compressed_data) / max(1, len(self.raw_data)),
            'max_raw': self.max_raw_samples,
            'max_compressed': self.max_compressed_samples
        }


class AdaptiveRetentionManager:
    """
    Manages multiple data streams with adaptive retention.
    Different retention policies for different data types.
    """
    
    def __init__(self):
        self.streams: Dict[str, DataRetentionStrategy] = {}
        self.policies: Dict[str, Dict] = {}
        self.logger = logging.getLogger("AdaptiveRetention")
    
    def create_stream(self, name: str, policy: str = 'standard'):
        """
        Create data stream with retention policy.
        
        Args:
            name: Stream name
            policy: 'aggressive', 'standard', 'conservative'
        """
        # Define policies
        policies = {
            'aggressive': {
                'max_raw': 500,
                'max_compressed': 5000
            },
            'standard': {
                'max_raw': 1000,
                'max_compressed': 10000
            },
            'conservative': {
                'max_raw': 2000,
                'max_compressed': 20000
            }
        }
        
        config = policies.get(policy, policies['standard'])
        
        self.streams[name] = DataRetentionStrategy(
            max_raw_samples=config['max_raw'],
            max_compressed_samples=config['max_compressed']
        )
        
        self.policies[name] = policy
        self.logger.info(f"Created stream '{name}' with {policy} policy")
    
    def add_data(self, stream_name: str, data: Dict, importance: float = 0.5):
        """Add data to stream"""
        if stream_name not in self.streams:
            self.create_stream(stream_name)
        
        self.streams[stream_name].add_data(data, importance)
    
    def get_stream_data(self, stream_name: str, recent: int = 100) -> List[Dict]:
        """Get recent data from stream"""
        if stream_name not in self.streams:
            return []
        
        return self.streams[stream_name].get_recent_data(recent)
    
    def get_all_stats(self) -> Dict:
        """Get statistics for all streams"""
        stats = {}
        
        for name, stream in self.streams.items():
            stats[name] = stream.get_stats()
            stats[name]['policy'] = self.policies.get(name, 'unknown')
        
        return stats
    
    def print_status(self):
        """Print retention status"""
        stats = self.get_all_stats()
        
        print("\n" + "="*70)
        print("ADAPTIVE DATA RETENTION STATUS")
        print("="*70)
        
        total_raw = 0
        total_compressed = 0
        
        for name, stream_stats in stats.items():
            print(f"\n📊 Stream: {name} ({stream_stats['policy']})")
            print(f"   Raw Samples: {stream_stats['raw_samples']:,}/{stream_stats['max_raw']:,}")
            print(f"   Compressed: {stream_stats['compressed_samples']:,}/{stream_stats['max_compressed']:,}")
            print(f"   Important: {stream_stats['important_samples']:,}")
            print(f"   Compression Ratio: {stream_stats['compression_ratio']:.2f}x")
            
            total_raw += stream_stats['raw_samples']
            total_compressed += stream_stats['compressed_samples']
        
        print(f"\n📈 Total:")
        print(f"   Raw: {total_raw:,}")
        print(f"   Compressed: {total_compressed:,}")
        print(f"   Total: {total_raw + total_compressed:,}")
        
        print("="*70)


class TimeBasedRetention:
    """
    Time-based retention with automatic aging.
    Different granularity for different time periods.
    """
    
    def __init__(self):
        # Retention periods
        self.high_res_period = timedelta(hours=24)  # Last 24h: 1-min data
        self.medium_res_period = timedelta(days=7)  # Last 7d: 5-min data
        self.low_res_period = timedelta(days=30)    # Last 30d: 1-hour data
        
        # Data storage by resolution
        self.high_res_data = deque(maxlen=1440)  # 24h * 60min
        self.medium_res_data = deque(maxlen=2016)  # 7d * 24h * 12 (5min)
        self.low_res_data = deque(maxlen=720)  # 30d * 24h
        
        self.logger = logging.getLogger("TimeBasedRetention")
    
    def add_data(self, data: Dict):
        """Add data with automatic aging"""
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        
        # Add to high-res
        self.high_res_data.append(data)
        
        # Age old data
        self._age_data()
    
    def _age_data(self):
        """Move old data to lower resolutions"""
        now = datetime.now()
        
        # Check high-res data
        while self.high_res_data:
            oldest = self.high_res_data[0]
            age = now - oldest['timestamp']
            
            if age > self.high_res_period:
                # Move to medium-res
                data = self.high_res_data.popleft()
                self.medium_res_data.append(data)
            else:
                break
        
        # Check medium-res data
        while self.medium_res_data:
            oldest = self.medium_res_data[0]
            age = now - oldest['timestamp']
            
            if age > self.medium_res_period:
                # Move to low-res
                data = self.medium_res_data.popleft()
                self.low_res_data.append(data)
            else:
                break
    
    def get_data(self, period: str = 'all') -> List[Dict]:
        """Get data by period"""
        if period == 'high':
            return list(self.high_res_data)
        elif period == 'medium':
            return list(self.medium_res_data)
        elif period == 'low':
            return list(self.low_res_data)
        else:  # all
            return (list(self.high_res_data) + 
                   list(self.medium_res_data) + 
                   list(self.low_res_data))
    
    def get_stats(self) -> Dict:
        """Get retention statistics"""
        return {
            'high_res': {
                'count': len(self.high_res_data),
                'period': '24 hours',
                'granularity': '1 minute'
            },
            'medium_res': {
                'count': len(self.medium_res_data),
                'period': '7 days',
                'granularity': '5 minutes'
            },
            'low_res': {
                'count': len(self.low_res_data),
                'period': '30 days',
                'granularity': '1 hour'
            },
            'total': len(self.high_res_data) + len(self.medium_res_data) + len(self.low_res_data)
        }
