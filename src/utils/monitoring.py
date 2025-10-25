"""
Performance monitoring utilities
"""
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data class"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    response_time_ms: float = 0.0
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'disk_io_read_mb': self.disk_io_read_mb,
            'disk_io_write_mb': self.disk_io_write_mb,
            'network_sent_mb': self.network_sent_mb,
            'network_recv_mb': self.network_recv_mb,
            'response_time_ms': self.response_time_ms,
            'active_connections': self.active_connections,
            'cache_hit_rate': self.cache_hit_rate
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 1000
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_disk_io = None
        self.last_network_io = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start continuous monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitor_loop(interval))
            logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        if self.monitoring_active and self.monitoring_task:
            self.monitoring_active = False
            self.monitoring_task.cancel()
            logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        try:
            while self.monitoring_active:
                metrics = self.collect_metrics()
                self.add_metrics(metrics)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = 0.0
            disk_write_mb = 0.0
            
            if disk_io and self.last_disk_io:
                disk_read_mb = (disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024)
                disk_write_mb = (disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024)
            
            if disk_io:
                self.last_disk_io = disk_io
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_sent_mb = 0.0
            network_recv_mb = 0.0
            
            if network_io and self.last_network_io:
                network_sent_mb = (network_io.bytes_sent - self.last_network_io.bytes_sent) / (1024 * 1024)
                network_recv_mb = (network_io.bytes_recv - self.last_network_io.bytes_recv) / (1024 * 1024)
            
            if network_io:
                self.last_network_io = network_io
            
            # Active connections (estimate)
            try:
                connections = psutil.net_connections()
                active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                active_connections = 0
            
            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                active_connections=active_connections
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return PerformanceMetrics()
    
    def add_metrics(self, metrics: PerformanceMetrics):
        """Add metrics to history"""
        self.metrics_history.append(metrics)
        
        # Limit history size
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m.active_connections for m in recent_metrics) / len(recent_metrics)
        
        # Calculate maximums
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        max_response_time = max(m.response_time_ms for m in recent_metrics)
        
        return {
            'duration_minutes': duration_minutes,
            'sample_count': len(recent_metrics),
            'averages': {
                'cpu_percent': round(avg_cpu, 2),
                'memory_percent': round(avg_memory, 2),
                'response_time_ms': round(avg_response_time, 2),
                'active_connections': round(avg_connections, 2)
            },
            'maximums': {
                'cpu_percent': round(max_cpu, 2),
                'memory_percent': round(max_memory, 2),
                'response_time_ms': round(max_response_time, 2)
            },
            'current': recent_metrics[-1].to_dict() if recent_metrics else {}
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on thresholds"""
        alerts = []
        current = self.get_current_metrics()
        
        if not current:
            return alerts
        
        # CPU alert
        if current.cpu_percent > 80:
            alerts.append({
                'type': 'cpu_high',
                'level': 'warning' if current.cpu_percent < 90 else 'critical',
                'message': f"High CPU usage: {current.cpu_percent:.1f}%",
                'value': current.cpu_percent,
                'threshold': 80
            })
        
        # Memory alert
        if current.memory_percent > 85:
            alerts.append({
                'type': 'memory_high',
                'level': 'warning' if current.memory_percent < 95 else 'critical',
                'message': f"High memory usage: {current.memory_percent:.1f}%",
                'value': current.memory_percent,
                'threshold': 85
            })
        
        # Response time alert
        if current.response_time_ms > 1000:
            alerts.append({
                'type': 'response_time_slow',
                'level': 'warning' if current.response_time_ms < 2000 else 'critical',
                'message': f"Slow response time: {current.response_time_ms:.1f}ms",
                'value': current.response_time_ms,
                'threshold': 1000
            })
        
        return alerts
    
    def export_metrics(self, filename: str, format: str = 'json'):
        """Export metrics to file"""
        try:
            if format.lower() == 'json':
                with open(filename, 'w') as f:
                    metrics_data = [m.to_dict() for m in self.metrics_history]
                    json.dump(metrics_data, f, indent=2)
            elif format.lower() == 'csv':
                import csv
                with open(filename, 'w', newline='') as f:
                    if self.metrics_history:
                        writer = csv.DictWriter(f, fieldnames=self.metrics_history[0].to_dict().keys())
                        writer.writeheader()
                        for metrics in self.metrics_history:
                            writer.writerow(metrics.to_dict())
            
            logger.info(f"Metrics exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            raise
    
    def clear_history(self):
        """Clear metrics history"""
        self.metrics_history.clear()
        logger.info("Metrics history cleared")


# Global instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Decorator for timing function execution
def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        monitor = get_performance_monitor()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Update metrics with execution time
            current_metrics = monitor.get_current_metrics()
            if current_metrics:
                current_metrics.response_time_ms = execution_time
            
            logger.debug(f"Function {func.__name__} executed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Function {func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    return wrapper


# Async version of the decorator
def monitor_async_performance(func):
    """Decorator to monitor async function performance"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        monitor = get_performance_monitor()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Update metrics with execution time
            current_metrics = monitor.get_current_metrics()
            if current_metrics:
                current_metrics.response_time_ms = execution_time
            
            logger.debug(f"Async function {func.__name__} executed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Async function {func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    return wrapper