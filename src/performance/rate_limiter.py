"""API Rate Limiting -moduuli

Rajoittaa API-kutsujen määrää aikayksikköä kohden.
Estää palvelun ylikuormituksen ja varmistaa tasaisen suorituskyvyn.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
from collections import defaultdict, deque
import json

from ..utils.exceptions import SecurityError
from ..utils.monitoring import PerformanceMonitor

logger = logging.getLogger(__name__)


class RateLimitExceeded(SecurityError):
    """Rate limit ylitetty"""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, error_type="rate_limit")
        self.retry_after = retry_after


class APIRateLimiter:
    """Edistynyt API rate limiter useilla aikaikkunoilla"""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        burst_limit: int = 20,
        burst_window: int = 10,
    ):
        """
        Alustaa rate limiterin

        Args:
            requests_per_minute: Pyyntöjä minuutissa
            requests_per_hour: Pyyntöjä tunnissa
            requests_per_day: Pyyntöjä päivässä
            burst_limit: Burst-rajoitus
            burst_window: Burst-ikkuna sekunnissa
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
        self.burst_window = burst_window

        # Asiakaskohtaiset tiedot
        self.client_requests: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                "minute": deque(),
                "hour": deque(),
                "day": deque(),
                "burst": deque(),
            }
        )

        # Asiakaskohtaiset blokkaustiedot
        self.blocked_clients: Dict[str, Dict[str, Any]] = {}

        # Tilastot
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "unique_clients": 0,
            "burst_blocks": 0,
        }

        self.monitor = PerformanceMonitor()

        logger.info(
            "APIRateLimiter initialized",
            extra={
                "requests_per_minute": requests_per_minute,
                "requests_per_hour": requests_per_hour,
                "requests_per_day": requests_per_day,
                "burst_limit": burst_limit,
            },
        )

    def _cleanup_old_requests(self, client_id: str, current_time: float):
        """Poista vanhat pyynnöt dequeista"""
        client_data = self.client_requests[client_id]

        # Minuutin ikkuna
        minute_cutoff = current_time - 60
        while client_data["minute"] and client_data["minute"][0] < minute_cutoff:
            client_data["minute"].popleft()

        # Tunnin ikkuna
        hour_cutoff = current_time - 3600
        while client_data["hour"] and client_data["hour"][0] < hour_cutoff:
            client_data["hour"].popleft()

        # Päivän ikkuna
        day_cutoff = current_time - 86400
        while client_data["day"] and client_data["day"][0] < day_cutoff:
            client_data["day"].popleft()

        # Burst-ikkuna
        burst_cutoff = current_time - self.burst_window
        while client_data["burst"] and client_data["burst"][0] < burst_cutoff:
            client_data["burst"].popleft()

    def _is_client_blocked(
        self, client_id: str, current_time: float
    ) -> Tuple[bool, Optional[int]]:
        """Tarkista onko asiakas estetty"""
        if client_id not in self.blocked_clients:
            return False, None

        block_info = self.blocked_clients[client_id]

        # Tarkista onko esto vielä voimassa
        if current_time >= block_info["expires_at"]:
            del self.blocked_clients[client_id]
            logger.info(
                "Client unblocked",
                extra={
                    "client_id": client_id,
                    "block_duration": block_info["duration"],
                },
            )
            return False, None

        retry_after = int(block_info["expires_at"] - current_time)
        return True, retry_after

    def _block_client(
        self, client_id: str, current_time: float, reason: str, duration: int = 300
    ):
        """Estä asiakas määräajaksi"""
        self.blocked_clients[client_id] = {
            "blocked_at": current_time,
            "expires_at": current_time + duration,
            "reason": reason,
            "duration": duration,
        }

        logger.warning(
            "Client blocked",
            extra={"client_id": client_id, "reason": reason, "duration": duration},
        )

    async def check_rate_limit(
        self, client_id: str, endpoint: str = "default"
    ) -> Dict[str, Any]:
        """
        Tarkista rate limit asiakkaalle

        Args:
            client_id: Asiakkaan tunniste (IP, user ID, jne.)
            endpoint: API-endpoint

        Returns:
            Rate limit tiedot

        Raises:
            RateLimitExceeded: Jos rate limit ylitetty
        """
        current_time = time.time()

        with self.monitor.measure_time("rate_limit_check"):
            # Tarkista onko asiakas estetty
            is_blocked, retry_after = self._is_client_blocked(client_id, current_time)
            if is_blocked:
                self.stats["blocked_requests"] += 1
                raise RateLimitExceeded(
                    f"Client {client_id} is temporarily blocked",
                    retry_after=retry_after,
                )

            # Siivoa vanhat pyynnöt
            self._cleanup_old_requests(client_id, current_time)

            client_data = self.client_requests[client_id]

            # Tarkista burst-raja
            if len(client_data["burst"]) >= self.burst_limit:
                self.stats["burst_blocks"] += 1
                self._block_client(client_id, current_time, "burst_limit", 60)
                raise RateLimitExceeded(
                    f"Burst limit exceeded: {self.burst_limit} requests in {self.burst_window}s",
                    retry_after=60,
                )

            # Tarkista minuuttiraja
            if len(client_data["minute"]) >= self.requests_per_minute:
                self._block_client(client_id, current_time, "minute_limit", 60)
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                    retry_after=60,
                )

            # Tarkista tuntiraja
            if len(client_data["hour"]) >= self.requests_per_hour:
                self._block_client(client_id, current_time, "hour_limit", 300)
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                    retry_after=300,
                )

            # Tarkista päiväraja
            if len(client_data["day"]) >= self.requests_per_day:
                self._block_client(client_id, current_time, "day_limit", 3600)
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.requests_per_day} requests per day",
                    retry_after=3600,
                )

            # Lisää pyyntö kaikkiin ikkunoihin
            for window in client_data.values():
                window.append(current_time)

            # Päivitä tilastot
            self.stats["total_requests"] += 1
            if client_id not in [data for data in self.client_requests.keys()]:
                self.stats["unique_clients"] += 1

            # Laske jäljellä olevat pyynnöt
            remaining = {
                "minute": self.requests_per_minute - len(client_data["minute"]),
                "hour": self.requests_per_hour - len(client_data["hour"]),
                "day": self.requests_per_day - len(client_data["day"]),
                "burst": self.burst_limit - len(client_data["burst"]),
            }

            logger.debug(
                "Rate limit check passed",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "remaining": remaining,
                },
            )

            return {
                "allowed": True,
                "remaining": remaining,
                "reset_times": {
                    "minute": current_time + 60,
                    "hour": current_time + 3600,
                    "day": current_time + 86400,
                },
            }

    async def get_stats(self) -> Dict[str, Any]:
        """Hae rate limiting tilastot"""
        current_time = time.time()

        # Laske aktiiviset asiakkaat (pyynnöt viimeisen tunnin aikana)
        active_clients = 0
        for client_data in self.client_requests.values():
            if client_data["hour"]:
                active_clients += 1

        # Laske estetyt asiakkaat
        blocked_count = len(self.blocked_clients)

        return {
            **self.stats,
            "active_clients": active_clients,
            "blocked_clients": blocked_count,
            "current_time": current_time,
        }

    async def reset_client(self, client_id: str) -> bool:
        """Nollaa asiakkaan rate limit tiedot"""
        try:
            if client_id in self.client_requests:
                del self.client_requests[client_id]

            if client_id in self.blocked_clients:
                del self.blocked_clients[client_id]

            logger.info("Client rate limit reset", extra={"client_id": client_id})
            return True

        except Exception as e:
            logger.error(
                "Failed to reset client rate limit",
                extra={"client_id": client_id, "error": str(e)},
            )
            return False


# Globaali rate limiter instance
api_rate_limiter = APIRateLimiter()


def rate_limit(
    requests_per_minute: int = None,
    client_id_func: Callable = None,
    endpoint_name: str = None,
):
    """
    Decorator API rate limitingiin

    Args:
        requests_per_minute: Pyyntöjä minuutissa (ylittää globaalin)
        client_id_func: Funktio asiakkaan tunnistamiseen
        endpoint_name: Endpoint:n nimi
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Määritä asiakas
            if client_id_func:
                client_id = client_id_func(*args, **kwargs)
            else:
                # Oleta että ensimmäinen argumentti on client_id tai IP
                client_id = args[0] if args else "anonymous"

            endpoint = endpoint_name or func.__name__

            # Tarkista rate limit
            try:
                await api_rate_limiter.check_rate_limit(client_id, endpoint)
            except RateLimitExceeded as e:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_id": client_id,
                        "endpoint": endpoint,
                        "function": func.__name__,
                    },
                )
                raise

            # Suorita funktio
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class AdaptiveRateLimiter:
    """Adaptiivinen rate limiter joka säätää rajoja kuormituksen mukaan"""

    def __init__(
        self,
        base_requests_per_minute: int = 60,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
    ):
        """
        Args:
            base_requests_per_minute: Perusraja minuutissa
            cpu_threshold: CPU-kynnys prosentteina
            memory_threshold: Muistikäytön kynnys prosentteina
        """
        self.base_requests_per_minute = base_requests_per_minute
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.current_limit = base_requests_per_minute

        # Järjestelmätiedot
        try:
            import psutil

            self.psutil_available = True
        except ImportError:
            self.psutil_available = False
            logger.warning("psutil not available, adaptive rate limiting disabled")

        self.adjustment_history = deque(maxlen=10)

    async def get_system_load(self) -> Dict[str, float]:
        """Hae järjestelmän kuormitustiedot"""
        if not self.psutil_available:
            return {"cpu_percent": 0, "memory_percent": 0}

        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent

            return {"cpu_percent": cpu_percent, "memory_percent": memory_percent}
        except Exception as e:
            logger.error("Failed to get system load", extra={"error": str(e)})
            return {"cpu_percent": 0, "memory_percent": 0}

    async def adjust_rate_limit(self) -> int:
        """Säädä rate limitiä järjestelmäkuormituksen mukaan"""
        system_load = await self.get_system_load()

        cpu_load = system_load["cpu_percent"]
        memory_load = system_load["memory_percent"]

        # Laske säätökerroin
        adjustment_factor = 1.0

        if cpu_load > self.cpu_threshold:
            adjustment_factor *= (100 - cpu_load) / 100

        if memory_load > self.memory_threshold:
            adjustment_factor *= (100 - memory_load) / 100

        # Sovella säätö
        new_limit = int(self.base_requests_per_minute * adjustment_factor)
        new_limit = max(new_limit, 1)  # Vähintään 1 pyyntö minuutissa

        if new_limit != self.current_limit:
            self.adjustment_history.append(
                {
                    "timestamp": time.time(),
                    "old_limit": self.current_limit,
                    "new_limit": new_limit,
                    "cpu_load": cpu_load,
                    "memory_load": memory_load,
                }
            )

            logger.info(
                "Rate limit adjusted",
                extra={
                    "old_limit": self.current_limit,
                    "new_limit": new_limit,
                    "cpu_load": cpu_load,
                    "memory_load": memory_load,
                },
            )

            self.current_limit = new_limit

        return self.current_limit


# Apufunktioita eri skenaarioille


async def check_scan_rate_limit(client_ip: str, scan_type: str):
    """Tarkista skannauksen rate limit"""
    endpoint = f"scan_{scan_type}"
    return await api_rate_limiter.check_rate_limit(client_ip, endpoint)


async def check_api_rate_limit(client_id: str, endpoint: str):
    """Tarkista API:n rate limit"""
    return await api_rate_limiter.check_rate_limit(client_id, endpoint)


def extract_client_ip(*args, **kwargs) -> str:
    """Poimi asiakkaan IP-osoite argumenteista"""
    # Flask request objektista
    if "request" in kwargs:
        request = kwargs["request"]
        return getattr(request, "remote_addr", "unknown")

    # Suoraan argumenteista
    if args and isinstance(args[0], str):
        return args[0]

    return "anonymous"
