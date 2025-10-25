"""Performance management CLI commands"""

import click
import asyncio
import json
from typing import Dict, Any

from ..performance.cache import cache_manager
from ..performance.rate_limiter import api_rate_limiter
from ..performance.connection_pool import connection_pool_manager
from ..performance.memory_optimizer import memory_optimizer


@click.group()
def performance():
    """Performance optimization commands"""
    pass


@performance.group()
def cache():
    """Cache management commands"""
    pass


@cache.command()
@click.option('--key', help='Specific cache key to check')
async def status(key):
    """Show cache status and statistics"""
    try:
        if key:
            # Check specific key
            exists = await cache_manager.exists(key)
            if exists:
                value = await cache_manager.get(key)
                click.echo(f"✅ Key '{key}' exists in cache")
                if isinstance(value, dict):
                    click.echo(json.dumps(value, indent=2))
                else:
                    click.echo(f"Value: {value}")
            else:
                click.echo(f"❌ Key '{key}' not found in cache")
        else:
            # Show general stats
            stats = await cache_manager.get_stats()
            click.echo("📊 Cache Statistics")
            click.echo("=" * 40)
            for key, value in stats.items():
                click.echo(f"{key}: {value}")
                
    except Exception as e:
        click.echo(f"❌ Cache status check failed: {e}")


@cache.command()
@click.option('--pattern', default='*', help='Pattern to match (default: *)')
@click.confirmation_option(prompt='Are you sure you want to clear cache?')
async def clear(pattern):
    """Clear cache entries matching pattern"""
    try:
        deleted = await cache_manager.clear(pattern)
        click.echo(f"✅ Cleared {deleted} cache entries matching '{pattern}'")
    except Exception as e:
        click.echo(f"❌ Cache clear failed: {e}")


@cache.command()
@click.argument('key')
async def delete(key):
    """Delete specific cache key"""
    try:
        deleted = await cache_manager.delete(key)
        if deleted:
            click.echo(f"✅ Deleted cache key '{key}'")
        else:
            click.echo(f"❌ Cache key '{key}' not found")
    except Exception as e:
        click.echo(f"❌ Cache delete failed: {e}")


@performance.group()
def ratelimit():
    """Rate limiting management"""
    pass


@ratelimit.command()
async def status():
    """Show rate limiting statistics"""
    try:
        stats = await api_rate_limiter.get_stats()
        
        click.echo("🚦 Rate Limiting Statistics")
        click.echo("=" * 40)
        click.echo(f"Total requests: {stats['total_requests']}")
        click.echo(f"Blocked requests: {stats['blocked_requests']}")
        click.echo(f"Active clients: {stats['active_clients']}")
        click.echo(f"Blocked clients: {stats['blocked_clients']}")
        click.echo(f"Burst blocks: {stats['burst_blocks']}")
        click.echo(f"Unique clients: {stats['unique_clients']}")
        
        if stats['total_requests'] > 0:
            block_rate = (stats['blocked_requests'] / stats['total_requests']) * 100
            click.echo(f"Block rate: {block_rate:.2f}%")
            
    except Exception as e:
        click.echo(f"❌ Rate limit status check failed: {e}")


@ratelimit.command()
@click.argument('client_id')
async def reset(client_id):
    """Reset rate limit for specific client"""
    try:
        success = await api_rate_limiter.reset_client(client_id)
        if success:
            click.echo(f"✅ Rate limit reset for client '{client_id}'")
        else:
            click.echo(f"❌ Failed to reset rate limit for client '{client_id}'")
    except Exception as e:
        click.echo(f"❌ Rate limit reset failed: {e}")


@performance.group()
def connections():
    """Connection pool management"""
    pass


@connections.command()
async def status():
    """Show connection pool statistics"""
    try:
        await connection_pool_manager.initialize()
        stats = await connection_pool_manager.get_pool_stats()
        
        click.echo("🔗 Connection Pool Statistics")
        click.echo("=" * 40)
        
        global_stats = stats.get('global_stats', {})
        for key, value in global_stats.items():
            click.echo(f"{key}: {value}")
        
        click.echo("\nPool Details:")
        click.echo("-" * 20)
        
        pools = stats.get('pools', {})
        for pool_name, pool_stats in pools.items():
            click.echo(f"\n{pool_name}:")
            config = pool_stats.get('config', {})
            click.echo(f"  Max connections: {config.get('max_connections', 'N/A')}")
            click.echo(f"  Max per host: {config.get('max_connections_per_host', 'N/A')}")
            click.echo(f"  Created at: {config.get('created_at', 'N/A')}")
            
            connector_stats = pool_stats.get('connector_stats', {})
            if connector_stats:
                click.echo(f"  Open connections: {connector_stats.get('open_connections', 0)}")
                click.echo(f"  Acquired connections: {connector_stats.get('acquired_connections', 0)}")
                
    except Exception as e:
        click.echo(f"❌ Connection pool status check failed: {e}")


@connections.command()
@click.argument('pool_name')
async def close_pool(pool_name):
    """Close specific connection pool"""
    try:
        success = await connection_pool_manager.close_pool(pool_name)
        if success:
            click.echo(f"✅ Closed connection pool '{pool_name}'")
        else:
            click.echo(f"❌ Pool '{pool_name}' not found")
    except Exception as e:
        click.echo(f"❌ Failed to close pool: {e}")


@performance.group()
def memory():
    """Memory optimization management"""
    pass


@memory.command()
async def status():
    """Show memory usage and optimization statistics"""
    try:
        info = memory_optimizer.get_memory_info()
        
        click.echo("💾 Memory Statistics")
        click.echo("=" * 40)
        click.echo(f"Current memory: {info['current_memory_mb']:.2f} MB")
        click.echo(f"Memory limit: {info['memory_limit_mb']:.2f} MB")
        click.echo(f"Usage: {info['usage_percent']:.1f}%")
        
        stats = info.get('stats', {})
        click.echo(f"\nOptimization Stats:")
        click.echo(f"  Peak memory: {stats.get('peak_memory_mb', 0):.2f} MB")
        click.echo(f"  GC collections: {stats.get('gc_collections', 0)}")
        click.echo(f"  Cleanup operations: {stats.get('cleanup_operations', 0)}")
        click.echo(f"  Objects tracked: {stats.get('objects_tracked', 0)}")
        
        system_memory = info.get('system_memory', {})
        if system_memory:
            click.echo(f"\nSystem Memory:")
            click.echo(f"  Total: {system_memory.get('total_mb', 0):.2f} MB")
            click.echo(f"  Available: {system_memory.get('available_mb', 0):.2f} MB")
            click.echo(f"  Used: {system_memory.get('percent_used', 0):.1f}%")
        
        recent_cleanups = info.get('recent_cleanups', [])
        if recent_cleanups:
            click.echo(f"\nRecent Cleanups:")
            for cleanup in recent_cleanups[-3:]:
                freed_mb = cleanup.get('freed_mb', 0)
                cleanup_type = cleanup.get('type', 'unknown')
                click.echo(f"  {cleanup_type}: {freed_mb:.2f} MB freed")
                
    except Exception as e:
        click.echo(f"❌ Memory status check failed: {e}")


@memory.command()
async def cleanup():
    """Force memory cleanup"""
    try:
        memory_optimizer.force_cleanup()
        click.echo("✅ Memory cleanup completed")
    except Exception as e:
        click.echo(f"❌ Memory cleanup failed: {e}")


@memory.command()
async def start():
    """Start memory optimization"""
    try:
        await memory_optimizer.start()
        click.echo("✅ Memory optimizer started")
    except Exception as e:
        click.echo(f"❌ Failed to start memory optimizer: {e}")


@memory.command()
async def stop():
    """Stop memory optimization"""
    try:
        await memory_optimizer.stop()
        click.echo("✅ Memory optimizer stopped")
    except Exception as e:
        click.echo(f"❌ Failed to stop memory optimizer: {e}")


@performance.command()
async def overview():
    """Show overall performance overview"""
    try:
        click.echo("🚀 Performance Overview")
        click.echo("=" * 50)
        
        # Cache stats
        try:
            cache_stats = await cache_manager.get_stats()
            click.echo(f"\n📦 Cache:")
            click.echo(f"  Hit rate: {cache_stats.get('hit_rate', 0)}%")
            click.echo(f"  Total hits: {cache_stats.get('hits', 0)}")
            click.echo(f"  Total misses: {cache_stats.get('misses', 0)}")
        except Exception:
            click.echo(f"\n📦 Cache: Not available")
        
        # Rate limit stats
        try:
            rate_stats = await api_rate_limiter.get_stats()
            click.echo(f"\n🚦 Rate Limiting:")
            click.echo(f"  Total requests: {rate_stats.get('total_requests', 0)}")
            click.echo(f"  Blocked requests: {rate_stats.get('blocked_requests', 0)}")
            click.echo(f"  Active clients: {rate_stats.get('active_clients', 0)}")
        except Exception:
            click.echo(f"\n🚦 Rate Limiting: Not available")
        
        # Memory stats
        try:
            memory_info = memory_optimizer.get_memory_info()
            click.echo(f"\n💾 Memory:")
            click.echo(f"  Current usage: {memory_info['current_memory_mb']:.2f} MB")
            click.echo(f"  Usage percentage: {memory_info['usage_percent']:.1f}%")
            click.echo(f"  GC collections: {memory_info['stats'].get('gc_collections', 0)}")
        except Exception:
            click.echo(f"\n💾 Memory: Not available")
        
        # Connection pools
        try:
            await connection_pool_manager.initialize()
            pool_stats = await connection_pool_manager.get_pool_stats()
            global_stats = pool_stats.get('global_stats', {})
            click.echo(f"\n🔗 Connection Pools:")
            click.echo(f"  Total requests: {global_stats.get('total_requests', 0)}")
            click.echo(f"  Active connections: {global_stats.get('active_connections', 0)}")
            click.echo(f"  Reuse rate: {global_stats.get('reuse_rate', 0)}%")
        except Exception:
            click.echo(f"\n🔗 Connection Pools: Not available")
            
    except Exception as e:
        click.echo(f"❌ Performance overview failed: {e}")


# Async command wrapper
def async_command(f):
    """Decorator to run async commands"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Apply async wrapper to all async commands
for command in [
    status, clear, delete, 
    ratelimit.commands['status'], ratelimit.commands['reset'],
    connections.commands['status'],
    memory.commands['status'], memory.commands['cleanup'], 
    memory.commands['start'], memory.commands['stop'],
    overview
]:
    if hasattr(command, 'callback'):
        command.callback = async_command(command.callback)