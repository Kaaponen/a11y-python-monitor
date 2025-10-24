"""Rate limiting and request security controls"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.logger import get_logger
from ..utils.exceptions import SecurityError

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    cooldown_seconds: int = 300  # 5 minutes
    max_concurrent_scans: int = 5


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry"""
    requests: deque
    last_request: float
    blocked_until: Optional[float] = None
    total_requests: int = 0
    blocked_requests: int = 0


class RateLimiter:
    """Advanced rate limiter with multiple time windows and burst protection"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.entries: Dict[str, RateLimitEntry] = defaultdict(self._create_entry)
        self.active_scans: Dict[str, float] = {}  # client_id -> start_time
        self._lock = threading.Lock()
        
        logger.info("Rate limiter initialized", extra={
            "requests_per_minute": self.config.requests_per_minute,
            "requests_per_hour": self.config.requests_per_hour,
            "burst_limit": self.config.burst_limit,
            "max_concurrent_scans": self.config.max_concurrent_scans
        })
    
    def _create_entry(self) -> RateLimitEntry:
        """Create new rate limit entry"""
        return RateLimitEntry(
            requests=deque(),
            last_request=0,
            total_requests=0,
            blocked_requests=0
        )
    
    def check_rate_limit(self, client_id: str, operation: str = "scan") -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits
        
        Args:
            client_id: Unique identifier for client (IP, user ID, etc.)
            operation: Type of operation being performed
            
        Returns:
            Tuple of (allowed, reason_if_blocked)
        """
        current_time = time.time()
        
        with self._lock:
            entry = self.entries[client_id]
            
            # Check if currently blocked
            if entry.blocked_until and current_time < entry.blocked_until:
                remaining = entry.blocked_until - current_time
                reason = f"Rate limit exceeded. Blocked for {remaining:.0f} more seconds"
                logger.warning("Rate limit block active", extra={
                    "client_id": client_id,
                    "operation": operation,
                    "remaining_seconds": remaining
                })
                return False, reason
            
            # Clear expired block
            if entry.blocked_until and current_time >= entry.blocked_until:
                entry.blocked_until = None
                logger.info("Rate limit block expired", extra={
                    "client_id": client_id
                })
            
            # Clean old requests (older than 1 hour)
            cutoff_time = current_time - 3600
            while entry.requests and entry.requests[0] < cutoff_time:
                entry.requests.popleft()
            
            # Check concurrent scans limit
            if operation == "scan":
                # Clean expired active scans (older than 5 minutes)
                expired_scans = [
                    cid for cid, start_time in self.active_scans.items()
                    if current_time - start_time > 300
                ]
                for cid in expired_scans:
                    del self.active_scans[cid]
                
                if len(self.active_scans) >= self.config.max_concurrent_scans:
                    reason = f"Too many concurrent scans: {len(self.active_scans)}/{self.config.max_concurrent_scans}"
                    logger.warning("Concurrent scan limit exceeded", extra={
                        "client_id": client_id,
                        "active_scans": len(self.active_scans),
                        "max_allowed": self.config.max_concurrent_scans
                    })
                    return False, reason
            
            # Check minute limit
            minute_ago = current_time - 60
            minute_requests = sum(1 for req_time in entry.requests if req_time > minute_ago)
            
            if minute_requests >= self.config.requests_per_minute:
                self._apply_rate_limit_penalty(entry, current_time, "minute_limit")
                reason = f"Rate limit: {minute_requests}/{self.config.requests_per_minute} requests per minute"
                logger.warning("Minute rate limit exceeded", extra={
                    "client_id": client_id,
                    "requests_this_minute": minute_requests,
                    "limit": self.config.requests_per_minute
                })
                return False, reason
            
            # Check hour limit
            hour_requests = len(entry.requests)
            if hour_requests >= self.config.requests_per_hour:
                self._apply_rate_limit_penalty(entry, current_time, "hour_limit")
                reason = f"Rate limit: {hour_requests}/{self.config.requests_per_hour} requests per hour"
                logger.warning("Hour rate limit exceeded", extra={
                    "client_id": client_id,
                    "requests_this_hour": hour_requests,
                    "limit": self.config.requests_per_hour
                })
                return False, reason
            
            # Check burst protection
            if self._is_burst_attack(entry, current_time):
                self._apply_rate_limit_penalty(entry, current_time, "burst_attack")
                reason = f"Burst attack detected. Requests too frequent."
                logger.warning("Burst attack detected", extra={
                    "client_id": client_id,
                    "operation": operation
                })
                return False, reason
            
            # Request allowed - record it
            entry.requests.append(current_time)
            entry.last_request = current_time
            entry.total_requests += 1
            
            if operation == "scan":
                self.active_scans[client_id] = current_time
            
            logger.debug("Rate limit check passed", extra={
                "client_id": client_id,
                "operation": operation,
                "minute_requests": minute_requests + 1,
                "hour_requests": hour_requests + 1
            })
            
            return True, None
    
    def _is_burst_attack(self, entry: RateLimitEntry, current_time: float) -> bool:
        """Check if request pattern indicates burst attack"""
        if len(entry.requests) < self.config.burst_limit:
            return False
        
        # Check if last N requests were too close together
        recent_requests = list(entry.requests)[-self.config.burst_limit:]
        time_span = current_time - recent_requests[0]
        
        # If burst_limit requests in less than 10 seconds, it's likely an attack
        return time_span < 10
    
    def _apply_rate_limit_penalty(self, entry: RateLimitEntry, current_time: float, reason: str):
        """Apply rate limiting penalty"""
        entry.blocked_until = current_time + self.config.cooldown_seconds
        entry.blocked_requests += 1
        
        logger.warning("Rate limit penalty applied", extra={
            "reason": reason,
            "cooldown_seconds": self.config.cooldown_seconds,
            "blocked_until": entry.blocked_until
        })
    
    def complete_scan(self, client_id: str):
        """Mark scan as completed for client"""
        with self._lock:
            if client_id in self.active_scans:
                del self.active_scans[client_id]
                logger.debug("Scan completed", extra={
                    "client_id": client_id,
                    "active_scans_remaining": len(self.active_scans)
                })
    
    def get_rate_limit_status(self, client_id: str) -> Dict[str, any]:
        """Get current rate limit status for client"""
        current_time = time.time()
        
        with self._lock:
            entry = self.entries[client_id]
            
            # Clean old requests
            cutoff_time = current_time - 3600
            while entry.requests and entry.requests[0] < cutoff_time:
                entry.requests.popleft()
            
            minute_ago = current_time - 60
            minute_requests = sum(1 for req_time in entry.requests if req_time > minute_ago)
            
            status = {
                'client_id': client_id,
                'requests_this_minute': minute_requests,
                'requests_this_hour': len(entry.requests),
                'minute_limit': self.config.requests_per_minute,
                'hour_limit': self.config.requests_per_hour,
                'minute_remaining': self.config.requests_per_minute - minute_requests,
                'hour_remaining': self.config.requests_per_hour - len(entry.requests),
                'is_blocked': entry.blocked_until and current_time < entry.blocked_until,
                'blocked_until': entry.blocked_until,
                'total_requests': entry.total_requests,
                'blocked_requests': entry.blocked_requests,
                'active_scans': len(self.active_scans),
                'max_concurrent_scans': self.config.max_concurrent_scans
            }
            
            if status['is_blocked']:
                status['block_remaining_seconds'] = entry.blocked_until - current_time
            
            return status
    
    def cleanup_old_entries(self, max_age_hours: int = 24):
        """Clean up old rate limit entries"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        with self._lock:
            old_clients = [
                client_id for client_id, entry in self.entries.items()
                if entry.last_request < cutoff_time
            ]
            
            for client_id in old_clients:
                del self.entries[client_id]
            
            if old_clients:
                logger.info("Cleaned up old rate limit entries", extra={
                    "removed_clients": len(old_clients),
                    "max_age_hours": max_age_hours
                })


class RequestSecurityMiddleware:
    """Security middleware for request validation"""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.suspicious_user_agents = {
            'bot', 'crawler', 'spider', 'scraper', 'scanner',
            'curl', 'wget', 'python-requests', 'go-http-client'
        }
        
    def validate_request_headers(self, headers: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate request headers for security
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            Tuple of (valid, reason_if_invalid)
        """
        user_agent = headers.get('User-Agent', '').lower()
        
        # Check for suspicious user agents
        for suspicious in self.suspicious_user_agents:
            if suspicious in user_agent:
                logger.warning("Suspicious user agent detected", extra={
                    "user_agent": headers.get('User-Agent', ''),
                    "suspicious_pattern": suspicious
                })
                return False, f"Suspicious user agent pattern: {suspicious}"
        
        # Check for overly long headers (potential attack)
        for header_name, header_value in headers.items():
            if len(header_value) > 8192:  # 8KB limit
                logger.warning("Oversized header detected", extra={
                    "header_name": header_name,
                    "header_length": len(header_value)
                })
                return False, f"Header too long: {header_name}"
        
        return True, None
    
    def get_client_id(self, request_info: Dict[str, str]) -> str:
        """
        Generate client ID for rate limiting
        
        Args:
            request_info: Request information (IP, user agent, etc.)
            
        Returns:
            Unique client identifier
        """
        # Use IP address as primary identifier
        client_ip = request_info.get('remote_addr', 'unknown')
        user_agent = request_info.get('user_agent', '')
        
        # Create composite ID for more granular tracking
        return f"{client_ip}:{hash(user_agent) % 10000}"


# Global instances
_default_rate_limiter: Optional[RateLimiter] = None
_security_middleware: Optional[RequestSecurityMiddleware] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _default_rate_limiter
    if _default_rate_limiter is None:
        _default_rate_limiter = RateLimiter()
    return _default_rate_limiter


def get_security_middleware() -> RequestSecurityMiddleware:
    """Get global security middleware instance"""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = RequestSecurityMiddleware(get_rate_limiter())
    return _security_middleware