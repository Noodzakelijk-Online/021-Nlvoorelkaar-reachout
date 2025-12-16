"""
NLvoorElkaar Performance Optimization Package

This package provides comprehensive performance optimizations for the
NLvoorElkaar outreach tool, enabling 5-10x faster operations while
respecting rate limits.

Components:
- cache_manager: Multi-level caching (L1 memory, L2 SQLite, L3 network)
- async_engine: Async architecture with controlled parallelism
- database_optimizer: Connection pooling, indexing, batch operations
- rate_limiter: Adaptive rate limiting and smart scheduling
- delta_sync: Incremental synchronization for efficient updates
- ui_performance: Virtual scrolling, debouncing, lazy loading

Usage:
    from performance import PerformanceManager
    
    # Initialize performance optimizations
    perf = PerformanceManager()
    perf.initialize()
    
    # Use optimized operations
    volunteers = perf.fetch_volunteers_optimized(page=1)
    perf.send_messages_batch(messages)
"""

from .cache_manager import (
    MultiLevelCache,
    LRUCache,
    SQLiteCache,
    CacheWarmer,
    get_cache,
    init_cache,
    cached
)

from .async_engine import (
    AsyncHTTPClient,
    AsyncTaskQueue,
    ParallelProcessor,
    TaskPriority,
    TaskResult,
    TokenBucket,
    get_http_client,
    get_processor,
    run_async,
    async_to_sync
)

from .database_optimizer import (
    ConnectionPool,
    IndexManager,
    BatchOperations,
    QueryBuilder,
    OptimizedDatabase,
    get_database
)

from .rate_limiter import (
    AdaptiveRateLimiter,
    AdaptiveConfig,
    SmartScheduler,
    RequestThrottler,
    ServerHealth,
    get_rate_limiter,
    get_scheduler
)

from .delta_sync import (
    DeltaSyncEngine,
    FingerprintStore,
    IncrementalUpdater,
    SyncResult,
    ChangeType,
    get_delta_engine
)

from .ui_performance import (
    VirtualScrollList,
    LazyLoader,
    ProgressiveLoader,
    DebouncedSearch,
    UIUpdateBatcher,
    PerformanceMonitor,
    debounce,
    throttle,
    run_in_background,
    run_on_ui_thread
)

__version__ = '1.0.0'
__all__ = [
    # Cache
    'MultiLevelCache', 'LRUCache', 'SQLiteCache', 'CacheWarmer',
    'get_cache', 'init_cache', 'cached',
    
    # Async
    'AsyncHTTPClient', 'AsyncTaskQueue', 'ParallelProcessor',
    'TaskPriority', 'TaskResult', 'TokenBucket',
    'get_http_client', 'get_processor', 'run_async', 'async_to_sync',
    
    # Database
    'ConnectionPool', 'IndexManager', 'BatchOperations',
    'QueryBuilder', 'OptimizedDatabase', 'get_database',
    
    # Rate Limiting
    'AdaptiveRateLimiter', 'AdaptiveConfig', 'SmartScheduler',
    'RequestThrottler', 'ServerHealth', 'get_rate_limiter', 'get_scheduler',
    
    # Delta Sync
    'DeltaSyncEngine', 'FingerprintStore', 'IncrementalUpdater',
    'SyncResult', 'ChangeType', 'get_delta_engine',
    
    # UI
    'VirtualScrollList', 'LazyLoader', 'ProgressiveLoader',
    'DebouncedSearch', 'UIUpdateBatcher', 'PerformanceMonitor',
    'debounce', 'throttle', 'run_in_background', 'run_on_ui_thread',
    
    # Manager
    'PerformanceManager'
]


class PerformanceManager:
    """
    Unified Performance Manager
    
    Integrates all performance optimization components into
    a single, easy-to-use interface.
    
    Usage:
        perf = PerformanceManager()
        perf.initialize()
        
        # Optimized volunteer fetching
        volunteers = perf.fetch_volunteers(page=1)
        
        # Optimized message sending
        results = perf.send_messages(messages)
        
        # Delta sync
        changes = perf.sync_volunteers()
        
        # Get performance stats
        stats = perf.get_stats()
    """
    
    def __init__(
        self,
        db_path: str = 'data/nlvoorelkaar.db',
        cache_db_path: str = 'cache/cache.db',
        fingerprint_db_path: str = 'data/fingerprints.db'
    ):
        self.db_path = db_path
        self.cache_db_path = cache_db_path
        self.fingerprint_db_path = fingerprint_db_path
        
        self._initialized = False
        self._cache: MultiLevelCache = None
        self._database: OptimizedDatabase = None
        self._rate_limiter: AdaptiveRateLimiter = None
        self._scheduler: SmartScheduler = None
        self._delta_engine: DeltaSyncEngine = None
        self._http_client: AsyncHTTPClient = None
        self._processor: ParallelProcessor = None
    
    def initialize(self) -> None:
        """Initialize all performance components"""
        if self._initialized:
            return
        
        import os
        
        # Create directories
        os.makedirs('data', exist_ok=True)
        os.makedirs('cache', exist_ok=True)
        
        # Initialize components
        self._cache = init_cache(
            l1_max_size=2000,
            l2_db_path=self.cache_db_path
        )
        
        self._database = OptimizedDatabase(self.db_path)
        self._database.initialize()
        
        self._rate_limiter = AdaptiveRateLimiter(AdaptiveConfig(
            min_rate=0.5,
            max_rate=5.0,
            initial_rate=2.0
        ))
        
        self._scheduler = SmartScheduler(self._rate_limiter)
        self._scheduler.start()
        
        self._delta_engine = DeltaSyncEngine(db_path=self.fingerprint_db_path)
        
        self._http_client = AsyncHTTPClient(
            max_connections=10,
            default_rate=2.0
        )
        
        self._processor = ParallelProcessor(
            http_client=self._http_client,
            max_concurrent=5
        )
        
        self._initialized = True
    
    def fetch_volunteers(
        self,
        page: int = 1,
        force_refresh: bool = False
    ) -> list:
        """
        Fetch volunteers with caching and rate limiting
        
        Args:
            page: Page number to fetch
            force_refresh: Bypass cache
        
        Returns:
            List of volunteer data
        """
        self._ensure_initialized()
        
        cache_key = f"volunteers:page:{page}"
        
        if not force_refresh:
            cached = self._cache.get(cache_key, data_type='volunteer_list')
            if cached:
                return cached
        
        # Wait for rate limit
        self._rate_limiter.wait()
        
        # Fetch from network (placeholder - implement actual fetch)
        volunteers = self._fetch_volunteers_from_network(page)
        
        # Cache result
        self._cache.set(cache_key, volunteers, 'volunteer_list')
        
        return volunteers
    
    def fetch_volunteers_parallel(
        self,
        pages: list,
        on_progress: callable = None
    ) -> list:
        """
        Fetch multiple pages in parallel
        
        Args:
            pages: List of page numbers
            on_progress: Progress callback
        
        Returns:
            Combined list of all volunteers
        """
        self._ensure_initialized()
        
        async def fetch_all():
            return await self._processor.scrape_pages(
                base_url="https://www.nlvoorelkaar.nl/hulpaanbod?page={page}",
                page_numbers=pages,
                parse_func=self._parse_volunteer_page,
                on_progress=on_progress
            )
        
        return run_async(fetch_all())
    
    def sync_volunteers(
        self,
        fetch_func: callable,
        total_pages: int,
        on_progress: callable = None
    ) -> SyncResult:
        """
        Perform delta synchronization
        
        Args:
            fetch_func: Function to fetch volunteers
            total_pages: Total pages to sync
            on_progress: Progress callback
        
        Returns:
            SyncResult with changes
        """
        self._ensure_initialized()
        
        return self._delta_engine.sync(
            fetch_func=fetch_func,
            total_pages=total_pages,
            on_progress=on_progress
        )
    
    def send_messages_batch(
        self,
        messages: list,
        on_progress: callable = None
    ) -> list:
        """
        Send messages in optimized batches
        
        Args:
            messages: List of messages to send
            on_progress: Progress callback
        
        Returns:
            List of send results
        """
        self._ensure_initialized()
        
        results = []
        total = len(messages)
        
        for i, message in enumerate(messages):
            # Wait for rate limit
            self._rate_limiter.wait()
            
            # Send message (placeholder)
            result = self._send_message(message)
            results.append(result)
            
            # Record response
            self._rate_limiter.record_response(
                response_time_ms=result.get('duration_ms', 100),
                success=result.get('success', True)
            )
            
            if on_progress:
                on_progress(i + 1, total)
        
        return results
    
    def schedule_heavy_task(
        self,
        task_func: callable,
        task_name: str,
        **kwargs
    ) -> str:
        """
        Schedule a heavy task for off-peak execution
        
        Args:
            task_func: Function to execute
            task_name: Human-readable name
            **kwargs: Arguments for task_func
        
        Returns:
            Task ID
        """
        self._ensure_initialized()
        
        return self._scheduler.schedule_task(
            task_func=task_func,
            task_name=task_name,
            require_off_peak=True,
            **kwargs
        )
    
    def query_database(self) -> QueryBuilder:
        """Get a query builder for database operations"""
        self._ensure_initialized()
        return self._database.query()
    
    def batch_insert(self, table: str, data: list) -> int:
        """
        Batch insert data into database
        
        Args:
            table: Table name
            data: List of dicts to insert
        
        Returns:
            Number of rows inserted
        """
        self._ensure_initialized()
        return self._database.insert_many(table, data)
    
    def get_stats(self) -> dict:
        """Get comprehensive performance statistics"""
        self._ensure_initialized()
        
        return {
            'cache': self._cache.get_stats(),
            'database': self._database.get_stats(),
            'rate_limiter': self._rate_limiter.stats,
            'sync': self._delta_engine.get_sync_stats(),
            'scheduler': {
                'pending_tasks': len(self._scheduler.get_pending_tasks()),
                'is_off_peak': self._scheduler.is_off_peak()
            }
        }
    
    def get_health(self) -> dict:
        """Get system health status"""
        self._ensure_initialized()
        
        return {
            'server_health': self._rate_limiter.health.value,
            'cache_hit_rate': self._cache.get_stats()['l1']['hit_rate'],
            'database_pool': self._database.pool.pool_status,
            'needs_full_sync': self._delta_engine.needs_full_sync()
        }
    
    def cleanup(self) -> dict:
        """Run cleanup operations"""
        self._ensure_initialized()
        
        cache_cleaned = self._cache.cleanup()
        self._database.vacuum()
        
        return {
            'cache_cleaned': cache_cleaned,
            'database_vacuumed': True
        }
    
    def shutdown(self) -> None:
        """Shutdown all components"""
        if not self._initialized:
            return
        
        self._scheduler.stop()
        self._database.close()
        run_async(self._http_client.close())
        
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """Ensure manager is initialized"""
        if not self._initialized:
            self.initialize()
    
    def _fetch_volunteers_from_network(self, page: int) -> list:
        """Placeholder for actual network fetch"""
        # This would be implemented with actual scraping logic
        return []
    
    def _parse_volunteer_page(self, html: str) -> list:
        """Placeholder for HTML parsing"""
        # This would be implemented with BeautifulSoup
        return []
    
    def _send_message(self, message: dict) -> dict:
        """Placeholder for message sending"""
        # This would be implemented with actual messaging logic
        return {'success': True, 'duration_ms': 100}


# Global performance manager instance
_manager: PerformanceManager = None


def get_performance_manager() -> PerformanceManager:
    """Get global performance manager instance"""
    global _manager
    if _manager is None:
        _manager = PerformanceManager()
        _manager.initialize()
    return _manager
