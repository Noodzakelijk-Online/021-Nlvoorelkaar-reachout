"""
Async Engine with Controlled Parallelism
Implements high-performance async operations while respecting rate limits.
"""

import asyncio
import aiohttp
import time
import logging
from typing import (
    Any, Optional, Dict, List, Callable, TypeVar, 
    Coroutine, AsyncIterator, Union
)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskResult:
    """Result of an async task"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    retries: int = 0


@dataclass
class RequestStats:
    """Statistics for request tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time_ms: float = 0
    avg_time_ms: float = 0
    requests_per_second: float = 0
    
    def record(self, duration_ms: float, success: bool) -> None:
        self.total_requests += 1
        self.total_time_ms += duration_ms
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.avg_time_ms = self.total_time_ms / self.total_requests


class TokenBucket:
    """
    Token Bucket Rate Limiter
    
    Allows bursts while maintaining average rate limit.
    More efficient than simple delays.
    """
    
    def __init__(
        self,
        rate: float = 1.0,      # tokens per second
        capacity: int = 10,     # max burst size
    ):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary
        
        Returns:
            Wait time in seconds
        """
        async with self._lock:
            now = time.monotonic()
            
            # Add tokens based on time passed
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # Wait if not enough tokens
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
                return wait_time
            
            self.tokens -= tokens
            return 0
    
    def update_rate(self, new_rate: float) -> None:
        """Dynamically update rate limit"""
        self.rate = new_rate


class SemaphorePool:
    """
    Pool of semaphores for different endpoints
    
    Allows different rate limits for different operations.
    """
    
    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
    
    def get_semaphore(self, name: str, limit: int = 5) -> asyncio.Semaphore:
        """Get or create semaphore for endpoint"""
        with self._lock:
            if name not in self._semaphores:
                self._semaphores[name] = asyncio.Semaphore(limit)
            return self._semaphores[name]
    
    def get_bucket(
        self,
        name: str,
        rate: float = 1.0,
        capacity: int = 10
    ) -> TokenBucket:
        """Get or create token bucket for endpoint"""
        with self._lock:
            if name not in self._buckets:
                self._buckets[name] = TokenBucket(rate, capacity)
            return self._buckets[name]


class AsyncHTTPClient:
    """
    High-performance async HTTP client with rate limiting
    
    Features:
    - Connection pooling
    - Automatic retries with exponential backoff
    - Rate limiting per endpoint
    - Request coalescing
    - Statistics tracking
    """
    
    def __init__(
        self,
        max_connections: int = 10,
        max_connections_per_host: int = 5,
        timeout: int = 30,
        default_rate: float = 2.0,  # requests per second
        max_retries: int = 3
    ):
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.timeout = timeout
        self.default_rate = default_rate
        self.max_retries = max_retries
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore_pool = SemaphorePool()
        self.stats = RequestStats()
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections_per_host,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Connection': 'keep-alive'
                }
            )
        return self._session
    
    async def get(
        self,
        url: str,
        endpoint_name: str = 'default',
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> TaskResult:
        """
        Make GET request with rate limiting and retries
        """
        return await self._request(
            'GET', url, endpoint_name,
            params=params, headers=headers, priority=priority
        )
    
    async def post(
        self,
        url: str,
        endpoint_name: str = 'default',
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> TaskResult:
        """
        Make POST request with rate limiting and retries
        """
        return await self._request(
            'POST', url, endpoint_name,
            data=data, json=json, headers=headers, priority=priority
        )
    
    async def _request(
        self,
        method: str,
        url: str,
        endpoint_name: str,
        **kwargs
    ) -> TaskResult:
        """Internal request method with full functionality"""
        start_time = time.monotonic()
        priority = kwargs.pop('priority', TaskPriority.NORMAL)
        
        # Get rate limiter for endpoint
        bucket = self._semaphore_pool.get_bucket(
            endpoint_name,
            rate=self.default_rate,
            capacity=5
        )
        semaphore = self._semaphore_pool.get_semaphore(endpoint_name, 5)
        
        # Request coalescing - deduplicate identical requests
        request_key = f"{method}:{url}:{kwargs}"
        async with self._lock:
            if request_key in self._pending_requests:
                # Wait for existing request
                return await self._pending_requests[request_key]
            
            # Create future for this request
            future = asyncio.get_event_loop().create_future()
            self._pending_requests[request_key] = future
        
        try:
            result = await self._execute_request(
                method, url, bucket, semaphore, **kwargs
            )
            future.set_result(result)
            return result
        except Exception as e:
            error_result = TaskResult(
                success=False,
                error=str(e),
                duration_ms=(time.monotonic() - start_time) * 1000
            )
            future.set_result(error_result)
            return error_result
        finally:
            async with self._lock:
                self._pending_requests.pop(request_key, None)
    
    async def _execute_request(
        self,
        method: str,
        url: str,
        bucket: TokenBucket,
        semaphore: asyncio.Semaphore,
        **kwargs
    ) -> TaskResult:
        """Execute request with retries"""
        start_time = time.monotonic()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Wait for rate limit
                await bucket.acquire()
                
                # Acquire semaphore for concurrent limit
                async with semaphore:
                    session = await self._get_session()
                    
                    async with session.request(method, url, **kwargs) as response:
                        # Handle rate limit response
                        if response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', 60))
                            logger.warning(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        response.raise_for_status()
                        
                        # Get response data
                        content_type = response.headers.get('Content-Type', '')
                        if 'application/json' in content_type:
                            data = await response.json()
                        else:
                            data = await response.text()
                        
                        duration = (time.monotonic() - start_time) * 1000
                        self.stats.record(duration, True)
                        
                        return TaskResult(
                            success=True,
                            data=data,
                            duration_ms=duration,
                            retries=attempt
                        )
            
            except aiohttp.ClientError as e:
                last_error = str(e)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) + (time.monotonic() % 1)
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error: {e}")
                break
        
        duration = (time.monotonic() - start_time) * 1000
        self.stats.record(duration, False)
        
        return TaskResult(
            success=False,
            error=last_error,
            duration_ms=duration,
            retries=self.max_retries
        )
    
    async def batch_get(
        self,
        urls: List[str],
        endpoint_name: str = 'default',
        max_concurrent: int = 5,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[TaskResult]:
        """
        Fetch multiple URLs with controlled concurrency
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        total = len(urls)
        completed = 0
        
        async def fetch_one(url: str) -> TaskResult:
            nonlocal completed
            async with semaphore:
                result = await self.get(url, endpoint_name)
                completed += 1
                if on_progress:
                    on_progress(completed, total)
                return result
        
        tasks = [fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to TaskResults
        return [
            r if isinstance(r, TaskResult) else TaskResult(success=False, error=str(r))
            for r in results
        ]
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()


class AsyncTaskQueue:
    """
    Priority-based async task queue
    
    Features:
    - Priority scheduling
    - Concurrent execution with limits
    - Progress tracking
    - Cancellation support
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._queues: Dict[TaskPriority, asyncio.Queue] = {
            priority: asyncio.Queue()
            for priority in TaskPriority
        }
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._completed = 0
        self._total = 0
        self._lock = asyncio.Lock()
    
    async def add_task(
        self,
        coro: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None
    ) -> None:
        """Add task to queue"""
        async with self._lock:
            self._total += 1
        await self._queues[priority].put((task_id, coro))
    
    async def add_tasks(
        self,
        coros: List[Coroutine],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> None:
        """Add multiple tasks to queue"""
        for i, coro in enumerate(coros):
            await self.add_task(coro, priority, f"task_{i}")
    
    async def start(
        self,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_complete: Optional[Callable[[str, Any], None]] = None
    ) -> None:
        """Start processing tasks"""
        self._running = True
        
        async def worker():
            while self._running:
                # Check queues in priority order
                for priority in TaskPriority:
                    queue = self._queues[priority]
                    if not queue.empty():
                        task_id, coro = await queue.get()
                        try:
                            result = await coro
                            if on_complete:
                                on_complete(task_id, result)
                        except Exception as e:
                            logger.error(f"Task {task_id} failed: {e}")
                        finally:
                            async with self._lock:
                                self._completed += 1
                            if on_progress:
                                on_progress(self._completed, self._total)
                            queue.task_done()
                        break
                else:
                    # All queues empty, wait a bit
                    await asyncio.sleep(0.1)
        
        # Start workers
        self._workers = [
            asyncio.create_task(worker())
            for _ in range(self.max_workers)
        ]
    
    async def wait_completion(self) -> None:
        """Wait for all tasks to complete"""
        for queue in self._queues.values():
            await queue.join()
    
    async def stop(self) -> None:
        """Stop all workers"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
    
    @property
    def progress(self) -> tuple:
        """Get current progress"""
        return (self._completed, self._total)


class ParallelProcessor:
    """
    High-level parallel processing for common operations
    
    Provides easy-to-use methods for parallel scraping,
    message sending, and data processing.
    """
    
    def __init__(
        self,
        http_client: Optional[AsyncHTTPClient] = None,
        max_concurrent: int = 5
    ):
        self.http_client = http_client or AsyncHTTPClient()
        self.max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    async def scrape_pages(
        self,
        base_url: str,
        page_numbers: List[int],
        parse_func: Callable[[str], List[Dict]],
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict]:
        """
        Scrape multiple pages in parallel
        
        Args:
            base_url: URL template with {page} placeholder
            page_numbers: List of page numbers to scrape
            parse_func: Function to parse HTML into data
            on_progress: Progress callback (current, total, message)
        
        Returns:
            Combined list of all scraped items
        """
        all_items = []
        total = len(page_numbers)
        
        async def scrape_page(page: int) -> List[Dict]:
            url = base_url.format(page=page)
            result = await self.http_client.get(url, 'volunteer_list')
            
            if result.success:
                items = parse_func(result.data)
                return items
            return []
        
        # Process in batches
        for i in range(0, total, self.max_concurrent):
            batch = page_numbers[i:i + self.max_concurrent]
            tasks = [scrape_page(page) for page in batch]
            results = await asyncio.gather(*tasks)
            
            for items in results:
                all_items.extend(items)
            
            if on_progress:
                on_progress(min(i + self.max_concurrent, total), total, 
                           f"Scraped {len(all_items)} items")
        
        return all_items
    
    async def fetch_profiles(
        self,
        profile_urls: List[str],
        parse_func: Callable[[str], Dict],
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict]:
        """
        Fetch multiple volunteer profiles in parallel
        """
        profiles = []
        total = len(profile_urls)
        
        results = await self.http_client.batch_get(
            profile_urls,
            'volunteer_profile',
            max_concurrent=self.max_concurrent,
            on_progress=lambda c, t: on_progress(c, t, f"Fetched {c} profiles") if on_progress else None
        )
        
        for result in results:
            if result.success:
                profile = parse_func(result.data)
                if profile:
                    profiles.append(profile)
        
        return profiles
    
    async def process_items(
        self,
        items: List[T],
        process_func: Callable[[T], Any],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Process items in parallel using thread pool
        
        Useful for CPU-bound operations like parsing.
        """
        loop = asyncio.get_event_loop()
        results = []
        total = len(items)
        completed = 0
        
        async def process_one(item: T) -> Any:
            nonlocal completed
            result = await loop.run_in_executor(
                self._executor,
                process_func,
                item
            )
            completed += 1
            if on_progress:
                on_progress(completed, total)
            return result
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_process(item: T) -> Any:
            async with semaphore:
                return await process_one(item)
        
        tasks = [bounded_process(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def close(self) -> None:
        """Clean up resources"""
        await self.http_client.close()
        self._executor.shutdown(wait=False)


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine from sync code
    
    Handles event loop creation and cleanup.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    finally:
        # Clean up pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to convert async function to sync
    
    Usage:
        @async_to_sync
        async def my_async_func():
            return await something()
        
        # Can now call synchronously
        result = my_async_func()
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        return run_async(func(*args, **kwargs))
    return wrapper


# Global instances
_http_client: Optional[AsyncHTTPClient] = None
_processor: Optional[ParallelProcessor] = None


def get_http_client() -> AsyncHTTPClient:
    """Get global HTTP client instance"""
    global _http_client
    if _http_client is None:
        _http_client = AsyncHTTPClient()
    return _http_client


def get_processor(max_concurrent: int = 5) -> ParallelProcessor:
    """Get global parallel processor instance"""
    global _processor
    if _processor is None:
        _processor = ParallelProcessor(
            http_client=get_http_client(),
            max_concurrent=max_concurrent
        )
    return _processor
