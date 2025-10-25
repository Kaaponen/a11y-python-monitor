"""Memory Optimization -moduuli

Muistin käytön optimointi ja seuranta.
Estää muistivuodot ja parantaa suorituskykyä suurissa skannauksissa.
"""

import gc
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
import weakref
from datetime import datetime, timedelta
import threading
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class MemoryStats:
    """Muistikäytön tilastot"""
    
    def __init__(self):
        self.peak_memory_mb = 0
        self.current_memory_mb = 0
        self.gc_collections = 0
        self.memory_leaks_detected = 0
        self.objects_tracked = 0
        self.cleanup_operations = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Muunna tilastot dictionary:ksi"""
        return {
            'peak_memory_mb': round(self.peak_memory_mb, 2),
            'current_memory_mb': round(self.current_memory_mb, 2),
            'gc_collections': self.gc_collections,
            'memory_leaks_detected': self.memory_leaks_detected,
            'objects_tracked': self.objects_tracked,
            'cleanup_operations': self.cleanup_operations
        }


class MemoryMonitor:
    """Muistin käytön valvonta"""
    
    def __init__(self, threshold_mb: float = 500.0, check_interval: int = 30):
        """
        Args:
            threshold_mb: Muistikynnys MB:ssä
            check_interval: Tarkistusväli sekunnissa
        """
        self.threshold_mb = threshold_mb
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.callbacks: List[Callable] = []
        
    def add_callback(self, callback: Callable[[float], None]):
        """Lisää callback muistikynnyksen ylittyessä"""
        self.callbacks.append(callback)
    
    async def start_monitoring(self):
        """Aloita muistin valvonta"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Memory monitoring started", extra={
            "threshold_mb": self.threshold_mb,
            "check_interval": self.check_interval
        })
    
    async def stop_monitoring(self):
        """Lopeta muistin valvonta"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Memory monitoring stopped")
    
    async def _monitor_loop(self):
        """Valvonta-silmukka"""
        while self.monitoring:
            try:
                memory_mb = self.get_memory_usage_mb()
                
                if memory_mb > self.threshold_mb:
                    logger.warning("Memory threshold exceeded", extra={
                        "current_memory_mb": memory_mb,
                        "threshold_mb": self.threshold_mb
                    })
                    
                    # Kutsu callbackit
                    for callback in self.callbacks:
                        try:
                            callback(memory_mb)
                        except Exception as e:
                            logger.error("Memory callback failed", extra={
                                "error": str(e)
                            })
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Memory monitoring error", extra={"error": str(e)})
                await asyncio.sleep(self.check_interval)
    
    def get_memory_usage_mb(self) -> float:
        """Hae muistikäyttö MB:ssä"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                return process.memory_info().rss / 1024 / 1024
            except Exception:
                pass
        
        # Fallback: käytä sys.getsizeof
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # macOS: bytes, Linux: KB
            if sys.platform == 'darwin':
                return usage / 1024 / 1024
            else:
                return usage / 1024
        except Exception:
            return 0.0


class ObjectTracker:
    """Objektien seuranta muistivuotojen havaitsemiseksi"""
    
    def __init__(self, max_tracked_objects: int = 1000):
        self.max_tracked_objects = max_tracked_objects
        self.tracked_objects: Dict[int, weakref.ref] = {}
        self.object_types: Dict[str, int] = {}
        self.creation_times: Dict[int, float] = {}
    
    def track_object(self, obj: Any, obj_type: str = None):
        """Seuraa objektia"""
        if len(self.tracked_objects) >= self.max_tracked_objects:
            return
        
        obj_id = id(obj)
        obj_type = obj_type or type(obj).__name__
        
        # Tarkista voidaanko objektiin luoda weak reference
        try:
            # Luo weak reference
            self.tracked_objects[obj_id] = weakref.ref(obj, self._cleanup_callback(obj_id))
            self.object_types[obj_type] = self.object_types.get(obj_type, 0) + 1
            self.creation_times[obj_id] = time.time()
        except TypeError:
            # Jotkut objektit (kuten dict, list, tuple) eivät tue weak referenceja
            # Seuraa vain tyyppiä ja kokoa näissä tapauksissa
            self.object_types[obj_type] = self.object_types.get(obj_type, 0) + 1
    
    def _cleanup_callback(self, obj_id: int):
        """Callback objektin tuhoamiselle"""
        def callback(ref):
            if obj_id in self.tracked_objects:
                del self.tracked_objects[obj_id]
            if obj_id in self.creation_times:
                del self.creation_times[obj_id]
        return callback
    
    def get_object_stats(self) -> Dict[str, Any]:
        """Hae objektitilastot"""
        current_time = time.time()
        old_objects = 0
        
        for obj_id, creation_time in self.creation_times.items():
            if current_time - creation_time > 300:  # 5 minuuttia
                old_objects += 1
        
        return {
            'tracked_objects': len(self.tracked_objects),
            'object_types': dict(self.object_types),
            'old_objects': old_objects,
            'potential_leaks': old_objects if old_objects > 10 else 0
        }


class MemoryOptimizer:
    """Muistin optimointi ja hallinta"""
    
    def __init__(self,
                 gc_threshold: int = 700,
                 auto_gc: bool = True,
                 memory_limit_mb: float = 1000.0,
                 cleanup_interval: int = 60):
        """
        Args:
            gc_threshold: GC-kynnys objekteille
            auto_gc: Automaattinen garbage collection
            memory_limit_mb: Muistiraja MB:ssä
            cleanup_interval: Siivouksen aikaväli sekunnissa
        """
        self.gc_threshold = gc_threshold
        self.auto_gc = auto_gc
        self.memory_limit_mb = memory_limit_mb
        self.cleanup_interval = cleanup_interval
        
        self.stats = MemoryStats()
        self.monitor = MemoryMonitor(memory_limit_mb * 0.8)  # 80% raja
        self.object_tracker = ObjectTracker()
        
        # Siivouksen historia
        self.cleanup_history: List[Dict[str, Any]] = []
        
        # Cache puhdistajat
        self.cache_cleaners: List[Callable] = []
        
        # Automaattinen siivous
        self.cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Aseta GC-kynnykset
        if self.auto_gc:
            gc.set_threshold(gc_threshold, gc_threshold // 10, gc_threshold // 10)
        
        # Lisää memory monitor callback
        self.monitor.add_callback(self._on_memory_threshold)
        
        logger.info("MemoryOptimizer initialized", extra={
            "gc_threshold": gc_threshold,
            "auto_gc": auto_gc,
            "memory_limit_mb": memory_limit_mb
        })
    
    async def start(self):
        """Aloita muistin optimointi"""
        if self._running:
            return
        
        self._running = True
        
        # Aloita valvonta
        await self.monitor.start_monitoring()
        
        # Aloita automaattinen siivous
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Memory optimizer started")
    
    async def stop(self):
        """Pysäytä muistin optimointi"""
        self._running = False
        
        await self.monitor.stop_monitoring()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Memory optimizer stopped")
    
    def _on_memory_threshold(self, memory_mb: float):
        """Callback muistikynnyksen ylittyessä"""
        logger.warning("Memory threshold exceeded, starting cleanup", extra={
            "memory_mb": memory_mb,
            "threshold_mb": self.memory_limit_mb
        })
        
        # Synkroninen siivous
        self.force_cleanup()
    
    async def _cleanup_loop(self):
        """Automaattinen siivous-silmukka"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", extra={"error": str(e)})
    
    def force_cleanup(self):
        """Pakottaa välittömän muistisiivouksen"""
        start_memory = self.monitor.get_memory_usage_mb()
        
        # Suorita garbage collection
        collected = gc.collect()
        self.stats.gc_collections += 1
        
        # Tyhjennä cache:t
        for cleaner in self.cache_cleaners:
            try:
                cleaner()
            except Exception as e:
                logger.error("Cache cleaner failed", extra={"error": str(e)})
        
        end_memory = self.monitor.get_memory_usage_mb()
        freed_mb = start_memory - end_memory
        
        cleanup_info = {
            'timestamp': datetime.now().isoformat(),
            'start_memory_mb': start_memory,
            'end_memory_mb': end_memory,
            'freed_mb': freed_mb,
            'objects_collected': collected,
            'type': 'forced'
        }
        
        self.cleanup_history.append(cleanup_info)
        self.stats.cleanup_operations += 1
        
        logger.info("Forced memory cleanup completed", extra=cleanup_info)
    
    async def cleanup_memory(self):
        """Asynkroninen muistisiivous"""
        start_memory = self.monitor.get_memory_usage_mb()
        
        # Päivitä tilastot
        self.stats.current_memory_mb = start_memory
        if start_memory > self.stats.peak_memory_mb:
            self.stats.peak_memory_mb = start_memory
        
        # Tarkista tarvitaanko siivousta
        if start_memory < self.memory_limit_mb * 0.7:  # 70% raja
            return
        
        # Suorita siivous
        collected = gc.collect()
        self.stats.gc_collections += 1
        
        # Tyhjennä cache:t
        for cleaner in self.cache_cleaners:
            try:
                if asyncio.iscoroutinefunction(cleaner):
                    await cleaner()
                else:
                    cleaner()
            except Exception as e:
                logger.error("Async cache cleaner failed", extra={"error": str(e)})
        
        end_memory = self.monitor.get_memory_usage_mb()
        freed_mb = start_memory - end_memory
        
        cleanup_info = {
            'timestamp': datetime.now().isoformat(),
            'start_memory_mb': start_memory,
            'end_memory_mb': end_memory,
            'freed_mb': freed_mb,
            'objects_collected': collected,
            'type': 'automatic'
        }
        
        self.cleanup_history.append(cleanup_info)
        self.stats.cleanup_operations += 1
        
        # Rajoita historian pituutta
        if len(self.cleanup_history) > 100:
            self.cleanup_history = self.cleanup_history[-50:]
        
        logger.debug("Memory cleanup completed", extra=cleanup_info)
    
    def add_cache_cleaner(self, cleaner: Callable):
        """Lisää cache-puhdistaja"""
        self.cache_cleaners.append(cleaner)
    
    def track_object(self, obj: Any, obj_type: str = None):
        """Seuraa objektia muistivuotojen havaitsemiseksi"""
        self.object_tracker.track_object(obj, obj_type)
        self.stats.objects_tracked += 1
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Hae kattavat muistitiedot"""
        current_memory = self.monitor.get_memory_usage_mb()
        
        # GC-tilastot
        gc_stats = {}
        if hasattr(gc, 'get_stats'):
            gc_stats = gc.get_stats()
        
        # Objektitilastot
        object_stats = self.object_tracker.get_object_stats()
        
        # Järjestelmätiedot
        system_memory = {}
        if PSUTIL_AVAILABLE:
            try:
                vm = psutil.virtual_memory()
                system_memory = {
                    'total_mb': vm.total / 1024 / 1024,
                    'available_mb': vm.available / 1024 / 1024,
                    'percent_used': vm.percent
                }
            except Exception:
                pass
        
        return {
            'current_memory_mb': current_memory,
            'memory_limit_mb': self.memory_limit_mb,
            'usage_percent': (current_memory / self.memory_limit_mb) * 100,
            'stats': self.stats.to_dict(),
            'gc_stats': gc_stats,
            'object_stats': object_stats,
            'system_memory': system_memory,
            'recent_cleanups': self.cleanup_history[-5:] if self.cleanup_history else []
        }
    
    def optimize_for_large_scan(self):
        """Optimoi muisti suurelle skannaukselle"""
        logger.info("Optimizing memory for large scan")
        
        # Aggressive cleanup
        self.force_cleanup()
        
        # Väliaikaisesti matalammat kynnykset
        original_threshold = gc.get_threshold()[0]
        gc.set_threshold(original_threshold // 2)
        
        return original_threshold
    
    def restore_normal_optimization(self, original_threshold: int):
        """Palauta normaalit optimointiasetukset"""
        gc.set_threshold(original_threshold)
        logger.info("Memory optimization restored to normal")


# Globaali memory optimizer instance
memory_optimizer = MemoryOptimizer()


# Decorator muistinkäytön optimointiin
def optimize_memory(track_objects: bool = False):
    """
    Decorator funktioiden muistinkäytön optimointiin
    
    Args:
        track_objects: Seuraa objektien luomista
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_memory = memory_optimizer.monitor.get_memory_usage_mb()
            
            try:
                result = await func(*args, **kwargs)
                
                if track_objects and result:
                    memory_optimizer.track_object(result, f"result_{func.__name__}")
                
                return result
                
            finally:
                end_memory = memory_optimizer.monitor.get_memory_usage_mb()
                memory_used = end_memory - start_memory
                
                if memory_used > 50:  # Jos käytti yli 50MB
                    logger.info("High memory usage detected", extra={
                        "function": func.__name__,
                        "memory_used_mb": memory_used,
                        "start_memory_mb": start_memory,
                        "end_memory_mb": end_memory
                    })
                    
                    # Pakota siivous jos tarpeellista
                    if end_memory > memory_optimizer.memory_limit_mb * 0.8:
                        memory_optimizer.force_cleanup()
        
        def sync_wrapper(*args, **kwargs):
            start_memory = memory_optimizer.monitor.get_memory_usage_mb()
            
            try:
                result = func(*args, **kwargs)
                
                if track_objects and result:
                    memory_optimizer.track_object(result, f"result_{func.__name__}")
                
                return result
                
            finally:
                end_memory = memory_optimizer.monitor.get_memory_usage_mb()
                memory_used = end_memory - start_memory
                
                if memory_used > 50:
                    logger.info("High memory usage detected", extra={
                        "function": func.__name__,
                        "memory_used_mb": memory_used
                    })
                    
                    if end_memory > memory_optimizer.memory_limit_mb * 0.8:
                        memory_optimizer.force_cleanup()
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Apufunktiot

async def get_memory_stats() -> Dict[str, Any]:
    """Hae muistitilastot"""
    return memory_optimizer.get_memory_info()


def cleanup_memory_now():
    """Pakottaa välittömän muistisiivouksen"""
    memory_optimizer.force_cleanup()


def track_scan_result(result: Any, scan_type: str):
    """Seuraa skannauksen tulosta"""
    memory_optimizer.track_object(result, f"scan_result_{scan_type}")