"""Tests for health monitoring functionality"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from src.utils.health_monitor import (
    HealthMonitor,
    ScanMetrics,
    SystemMetrics,
    get_health_monitor,
)


class TestScanMetrics:
    """Test ScanMetrics dataclass"""

    def test_scan_metrics_creation(self):
        """Test creating scan metrics"""
        metrics = ScanMetrics(scan_id="test-123", url="https://example.com")

        assert metrics.scan_id == "test-123"
        assert metrics.url == "https://example.com"
        assert metrics.status == "running"
        assert metrics.end_time is None
        assert metrics.duration is None


class TestSystemMetrics:
    """Test SystemMetrics dataclass"""

    def test_system_metrics_creation(self):
        """Test creating system metrics"""
        metrics = SystemMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            disk_usage_percent=75.0,
        )

        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.memory_used_mb == 1024.0
        assert metrics.disk_usage_percent == 75.0


class TestHealthMonitor:
    """Test HealthMonitor class"""

    def setup_method(self):
        """Setup for each test"""
        self.monitor = HealthMonitor(max_history=10)

    def teardown_method(self):
        """Cleanup after each test"""
        if self.monitor._monitoring:
            self.monitor.stop_monitoring()

    def test_health_monitor_initialization(self):
        """Test health monitor initialization"""
        assert self.monitor.max_history == 10
        assert len(self.monitor.scan_metrics) == 0
        assert len(self.monitor.system_metrics) == 0
        assert self.monitor.performance_stats["total_scans"] == 0
        assert not self.monitor._monitoring

    def test_start_scan(self):
        """Test starting a scan"""
        scan_id = "test-scan-123"
        url = "https://example.com"

        metrics = self.monitor.start_scan(scan_id, url)

        assert metrics.scan_id == scan_id
        assert metrics.url == url
        assert metrics.status == "running"
        assert scan_id in self.monitor.scan_metrics
        assert self.monitor.performance_stats["total_scans"] == 1

    def test_complete_scan(self):
        """Test completing a scan"""
        scan_id = "test-scan-123"
        url = "https://example.com"
        violations_count = 5

        # Start scan first
        self.monitor.start_scan(scan_id, url)

        # Complete scan
        self.monitor.complete_scan(scan_id, violations_count)

        metrics = self.monitor.scan_metrics[scan_id]
        assert metrics.status == "completed"
        assert metrics.violations_count == violations_count
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert self.monitor.performance_stats["successful_scans"] == 1
        assert self.monitor.performance_stats["total_violations"] == violations_count

    def test_fail_scan(self):
        """Test failing a scan"""
        scan_id = "test-scan-123"
        url = "https://example.com"
        error_type = "timeout_error"

        # Start scan first
        self.monitor.start_scan(scan_id, url)

        # Fail scan
        self.monitor.fail_scan(scan_id, error_type)

        metrics = self.monitor.scan_metrics[scan_id]
        assert metrics.status == "failed"
        assert metrics.error_type == error_type
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert self.monitor.performance_stats["failed_scans"] == 1
        assert self.monitor.error_counts[error_type] == 1

    @patch("src.utils.health_monitor.psutil")
    def test_collect_system_metrics(self, mock_psutil):
        """Test collecting system metrics"""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=65.0, used=1073741824
        )  # 1GB
        mock_psutil.disk_usage.return_value = MagicMock(percent=80.0)
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1000000, bytes_recv=2000000
        )

        metrics = self.monitor._collect_system_metrics()

        assert metrics.cpu_percent == 45.0
        assert metrics.memory_percent == 65.0
        assert metrics.memory_used_mb == 1024.0  # 1GB in MB
        assert metrics.disk_usage_percent == 80.0
        assert metrics.network_io["bytes_sent"] == 1000000
        assert metrics.network_io["bytes_recv"] == 2000000

    def test_get_health_status(self):
        """Test getting health status"""
        # Add some test data
        self.monitor.start_scan("scan1", "https://example.com")
        self.monitor.complete_scan("scan1", 3)

        status = self.monitor.get_health_status()

        assert "status" in status
        assert "uptime_seconds" in status
        assert "uptime_human" in status
        assert "performance" in status
        assert "recent_activity" in status
        assert "system_resources" in status

        # Check performance data
        perf = status["performance"]
        assert perf["total_scans"] == 1
        assert perf["successful_scans"] == 1
        assert perf["failed_scans"] == 0
        assert perf["total_violations_found"] == 3

    def test_get_metrics_summary(self):
        """Test getting metrics summary"""
        # Add test data
        self.monitor.start_scan("scan1", "https://example.com")
        self.monitor.complete_scan("scan1", 5)

        self.monitor.start_scan("scan2", "https://test.com")
        self.monitor.fail_scan("scan2", "timeout_error")

        summary = self.monitor.get_metrics_summary(24)

        assert summary["period_hours"] == 24
        assert summary["total_scans"] == 2
        assert summary["completed_scans"] == 1
        assert summary["failed_scans"] == 1
        assert summary["success_rate_percent"] == 50.0
        assert summary["total_violations_found"] == 5
        assert "timeout_error" in summary["error_types"]

    def test_get_metrics_summary_no_data(self):
        """Test getting metrics summary with no data"""
        summary = self.monitor.get_metrics_summary(24)

        assert summary["period_hours"] == 24
        assert summary["no_data"] is True

    def test_cleanup_old_metrics(self):
        """Test cleaning up old metrics"""
        # Add test scan with old timestamp
        scan_id = "old-scan"
        self.monitor.scan_metrics[scan_id] = ScanMetrics(
            scan_id=scan_id,
            url="https://old.com",
            start_time=time.time() - 200000,  # Very old
        )

        # Add recent scan
        recent_id = "recent-scan"
        self.monitor.start_scan(recent_id, "https://recent.com")

        assert len(self.monitor.scan_metrics) == 2

        # Cleanup old metrics (keep only last hour)
        self.monitor.cleanup_old_metrics(hours=1)

        assert len(self.monitor.scan_metrics) == 1
        assert recent_id in self.monitor.scan_metrics
        assert scan_id not in self.monitor.scan_metrics

    @patch("src.utils.health_monitor.psutil")
    def test_start_stop_monitoring(self, mock_psutil):
        """Test starting and stopping background monitoring"""
        # Mock psutil to avoid actual system calls
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=60.0, used=1073741824
        )
        mock_psutil.disk_usage.return_value = MagicMock(percent=70.0)
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1000000, bytes_recv=2000000
        )

        # Start monitoring
        self.monitor.start_monitoring(interval=1)  # 1 second interval for testing

        assert self.monitor._monitoring is True
        assert self.monitor._monitor_thread is not None
        assert self.monitor._monitor_thread.is_alive()

        # Wait a bit for metrics to be collected
        time.sleep(1.5)

        # Should have collected at least one metric
        assert len(self.monitor.system_metrics) > 0

        # Stop monitoring
        self.monitor.stop_monitoring()

        assert self.monitor._monitoring is False

    def test_determine_overall_status(self):
        """Test determining overall health status"""
        # Test healthy status
        status = self.monitor._determine_overall_status(50.0, 60.0, 98.0)
        assert status == "healthy"

        # Test ok status
        status = self.monitor._determine_overall_status(70.0, 75.0, 93.0)
        assert status == "ok"

        # Test warning status
        status = self.monitor._determine_overall_status(85.0, 80.0, 85.0)
        assert status == "warning"

        # Test critical status
        status = self.monitor._determine_overall_status(95.0, 90.0, 80.0)
        assert status == "critical"


class TestHealthMonitorSingleton:
    """Test health monitor singleton functionality"""

    def test_get_health_monitor_singleton(self):
        """Test that get_health_monitor returns same instance"""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()

        assert monitor1 is monitor2

        # Test that data persists
        monitor1.start_scan("test", "https://example.com")
        assert len(monitor2.scan_metrics) == 1


@pytest.mark.asyncio
class TestHealthMonitorIntegration:
    """Integration tests for health monitor with scanner core"""

    @patch("src.scanner.core.async_playwright")
    @patch("src.utils.health_monitor.get_health_monitor")
    async def test_scanner_health_integration(self, mock_get_monitor, mock_playwright):
        """Test that scanner core integrates with health monitor"""
        from src.scanner.core import run_axe

        # Setup mocks
        mock_monitor = MagicMock()
        mock_get_monitor.return_value = mock_monitor

        # Mock playwright
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = (
            mock_browser
        )
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Mock successful scan
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        mock_page.evaluate.return_value = {"violations": [], "passes": [{"id": "test"}]}

        # Run scan
        result = await run_axe("https://example.com")

        # Verify health monitor was called
        mock_monitor.start_scan.assert_called_once()
        mock_monitor.complete_scan.assert_called_once()

        # Verify scan result
        assert "violations" in result
        assert "passes" in result
