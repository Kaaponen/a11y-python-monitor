"""Health monitoring and metrics collection for the accessibility scanner"""

import time
import asyncio
import psutil
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from .logger import get_logger


logger = get_logger(__name__)


@dataclass
class ScanMetrics:
    """Metrics for individual scans"""

    scan_id: str
    url: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    violations_count: int = 0
    status: str = "running"  # running, completed, failed
    error_type: Optional[str] = None


@dataclass
class SystemMetrics:
    """System resource metrics"""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_io: Dict[str, int] = field(default_factory=dict)


class HealthMonitor:
    """Comprehensive health monitoring and metrics collection"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.scan_metrics: Dict[str, ScanMetrics] = {}
        self.system_metrics: deque = deque(maxlen=max_history)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.performance_stats = {
            "total_scans": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "avg_scan_duration": 0.0,
            "total_violations": 0,
            "uptime_start": time.time(),
        }
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        logger.info(
            "Health monitor initialized",
            extra={
                "max_history": max_history,
                "uptime_start": self.performance_stats["uptime_start"],
            },
        )

    def start_monitoring(self, interval: int = 30):
        """Start background system monitoring"""
        if self._monitoring:
            logger.warning("Health monitoring already running")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_system, args=(interval,), daemon=True
        )
        self._monitor_thread.start()

        logger.info("Health monitoring started", extra={"interval_seconds": interval})

    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        logger.info("Health monitoring stopped")

    def _monitor_system(self, interval: int):
        """Background system monitoring loop"""
        while self._monitoring:
            try:
                metrics = self._collect_system_metrics()

                with self._lock:
                    self.system_metrics.append(metrics)

                # Log warning if resources are high
                if metrics.cpu_percent > 80:
                    logger.warning(
                        "High CPU usage detected",
                        extra={"cpu_percent": metrics.cpu_percent},
                    )

                if metrics.memory_percent > 85:
                    logger.warning(
                        "High memory usage detected",
                        extra={
                            "memory_percent": metrics.memory_percent,
                            "memory_used_mb": metrics.memory_used_mb,
                        },
                    )

                time.sleep(interval)

            except Exception as e:
                logger.error("Error in system monitoring", exc_info=True)
                time.sleep(interval)

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_io={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                },
            )
        except Exception as e:
            logger.error("Failed to collect system metrics", exc_info=True)
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_mb=0,
                disk_usage_percent=0,
            )

    def start_scan(self, scan_id: str, url: str) -> ScanMetrics:
        """Record the start of a scan"""
        metrics = ScanMetrics(scan_id=scan_id, url=url, start_time=time.time())

        with self._lock:
            self.scan_metrics[scan_id] = metrics
            self.performance_stats["total_scans"] += 1

        logger.info(
            "Scan started",
            extra={
                "scan_id": scan_id,
                "url": url,
                "total_scans": self.performance_stats["total_scans"],
            },
        )

        return metrics

    def complete_scan(self, scan_id: str, violations_count: int = 0):
        """Record successful scan completion"""
        with self._lock:
            if scan_id in self.scan_metrics:
                metrics = self.scan_metrics[scan_id]
                metrics.end_time = time.time()
                metrics.duration = metrics.end_time - metrics.start_time
                metrics.violations_count = violations_count
                metrics.status = "completed"

                self.performance_stats["successful_scans"] += 1
                self.performance_stats["total_violations"] += violations_count

                # Update average duration
                total_completed = self.performance_stats["successful_scans"]
                if total_completed > 0:
                    total_duration = sum(
                        m.duration
                        for m in self.scan_metrics.values()
                        if m.status == "completed" and m.duration
                    )
                    self.performance_stats["avg_scan_duration"] = (
                        total_duration / total_completed
                    )

                logger.info(
                    "Scan completed",
                    extra={
                        "scan_id": scan_id,
                        "duration": metrics.duration,
                        "violations_count": violations_count,
                        "url": metrics.url,
                    },
                )

    def fail_scan(self, scan_id: str, error_type: str):
        """Record scan failure"""
        with self._lock:
            if scan_id in self.scan_metrics:
                metrics = self.scan_metrics[scan_id]
                metrics.end_time = time.time()
                metrics.duration = metrics.end_time - metrics.start_time
                metrics.status = "failed"
                metrics.error_type = error_type

                self.performance_stats["failed_scans"] += 1
                self.error_counts[error_type] += 1

                logger.warning(
                    "Scan failed",
                    extra={
                        "scan_id": scan_id,
                        "duration": metrics.duration,
                        "error_type": error_type,
                        "url": metrics.url,
                        "total_failures": self.performance_stats["failed_scans"],
                    },
                )

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        with self._lock:
            current_time = time.time()
            uptime = current_time - self.performance_stats["uptime_start"]

            # Recent scans (last hour)
            hour_ago = current_time - 3600
            recent_scans = [
                m for m in self.scan_metrics.values() if m.start_time > hour_ago
            ]

            # Recent system metrics (last 10 minutes)
            ten_min_ago = current_time - 600
            recent_system = [
                m for m in self.system_metrics if m.timestamp > ten_min_ago
            ]

            # Calculate averages
            avg_cpu = 0
            avg_memory = 0
            if recent_system:
                avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system)
                avg_memory = sum(m.memory_percent for m in recent_system) / len(
                    recent_system
                )

            # Success rate
            total_scans = self.performance_stats["total_scans"]
            success_rate = 0
            if total_scans > 0:
                success_rate = (
                    self.performance_stats["successful_scans"] / total_scans
                ) * 100

            return {
                "status": self._determine_overall_status(
                    avg_cpu, avg_memory, success_rate
                ),
                "uptime_seconds": uptime,
                "uptime_human": str(timedelta(seconds=int(uptime))),
                "performance": {
                    "total_scans": total_scans,
                    "successful_scans": self.performance_stats["successful_scans"],
                    "failed_scans": self.performance_stats["failed_scans"],
                    "success_rate_percent": round(success_rate, 2),
                    "avg_scan_duration": round(
                        self.performance_stats["avg_scan_duration"], 2
                    ),
                    "total_violations_found": self.performance_stats[
                        "total_violations"
                    ],
                },
                "recent_activity": {
                    "scans_last_hour": len(recent_scans),
                    "active_scans": len(
                        [m for m in self.scan_metrics.values() if m.status == "running"]
                    ),
                },
                "system_resources": {
                    "avg_cpu_percent_10min": round(avg_cpu, 1),
                    "avg_memory_percent_10min": round(avg_memory, 1),
                    "monitoring_active": self._monitoring,
                },
                "error_breakdown": dict(self.error_counts),
                "timestamp": current_time,
            }

    def _determine_overall_status(
        self, avg_cpu: float, avg_memory: float, success_rate: float
    ) -> str:
        """Determine overall health status"""
        if avg_cpu > 90 or avg_memory > 95:
            return "critical"
        elif avg_cpu > 80 or avg_memory > 85 or success_rate < 90:
            return "warning"
        elif success_rate > 95:
            return "healthy"
        else:
            return "ok"

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary for specified time period"""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)

            # Filter metrics by time period
            period_scans = [
                m
                for m in self.scan_metrics.values()
                if m.start_time > cutoff_time and m.status in ["completed", "failed"]
            ]

            if not period_scans:
                return {"period_hours": hours, "no_data": True}

            completed_scans = [m for m in period_scans if m.status == "completed"]
            failed_scans = [m for m in period_scans if m.status == "failed"]

            # Calculate statistics
            total_duration = sum(m.duration for m in completed_scans if m.duration)
            avg_duration = (
                total_duration / len(completed_scans) if completed_scans else 0
            )

            total_violations = sum(m.violations_count for m in completed_scans)
            avg_violations = (
                total_violations / len(completed_scans) if completed_scans else 0
            )

            return {
                "period_hours": hours,
                "total_scans": len(period_scans),
                "completed_scans": len(completed_scans),
                "failed_scans": len(failed_scans),
                "success_rate_percent": (len(completed_scans) / len(period_scans))
                * 100,
                "avg_duration_seconds": round(avg_duration, 2),
                "total_violations_found": total_violations,
                "avg_violations_per_scan": round(avg_violations, 1),
                "error_types": {
                    error_type: len(
                        [m for m in failed_scans if m.error_type == error_type]
                    )
                    for error_type in set(
                        m.error_type for m in failed_scans if m.error_type
                    )
                },
            }

    def cleanup_old_metrics(self, hours: int = 168):  # Default: 1 week
        """Clean up old scan metrics to prevent memory bloat"""
        cutoff_time = time.time() - (hours * 3600)

        with self._lock:
            old_scan_ids = [
                scan_id
                for scan_id, metrics in self.scan_metrics.items()
                if metrics.start_time < cutoff_time
            ]

            for scan_id in old_scan_ids:
                del self.scan_metrics[scan_id]

            if old_scan_ids:
                logger.info(
                    "Cleaned up old metrics",
                    extra={"removed_scans": len(old_scan_ids), "cutoff_hours": hours},
                )


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def initialize_health_monitoring(start_background: bool = True, interval: int = 30):
    """Initialize and optionally start health monitoring"""
    monitor = get_health_monitor()
    if start_background:
        monitor.start_monitoring(interval)
    return monitor
