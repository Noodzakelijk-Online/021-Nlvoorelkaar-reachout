"""
Adaptive Rate Limiter and Smart Scheduler
Automatically adjusts request rates based on server response
and schedules heavy operations during optimal times.
"""

import time
import threading
import logging
from typing import Optional, Dict, Callable, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import statistics
import json
import os

logger = logging.getLogger(__name__)


class ServerHealth(Enum):
    """Server health status"""
    EXCELLENT = "excellent"  # Fast responses, no errors
    GOOD = "good"           # Normal responses
    DEGRADED = "degraded"   # Slow responses
    STRESSED = "stressed"   # Very slow, some errors
    CRITICAL = "critical"   # Rate limited or errors


@dataclass
class ResponseMetrics:
    """Metrics from a single response"""
    timestamp: float
    response_time_ms: float
    status_code: int
    success: bool
    rate_limited: bool = False


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive rate limiting"""
    # Base rates
    min_rate: float = 0.5      # Minimum requests per second
    max_rate: float = 5.0      # Maximum requests per second
    initial_rate: float = 2.0  # Starting rate
    
    # Response time thresholds (ms)
    excellent_threshold: float = 200
    good_threshold: float = 500
    degraded_threshold: float = 1000
    stressed_threshold: float = 2000
    
    # Adjustment factors
    increase_factor: float = 1.2   # Speed up by 20%
    decrease_factor: float = 0.5   # Slow down by 50%
    
    # Window settings
    window_size: int = 20          # Number of responses to consider
    adjustment_interval: float = 5.0  # Seconds between adjustments


class AdaptiveRateLimiter:
    """
    Adaptive Rate Limiter
    
    Automatically adjusts request rate based on server response times
    and error rates. Speeds up when server is healthy, slows down
    when stressed.
    
    Features:
    - Real-time rate adjustment
    - Server health monitoring
    - Circuit breaker pattern
    - Rate limit detection
    - Statistics tracking
    """
    
    def __init__(self, config: Optional[AdaptiveConfig] = None):
        self.config = config or AdaptiveConfig()
        self.current_rate = self.config.initial_rate
        
        self._metrics: deque = deque(maxlen=self.config.window_size)
        self._lock = threading.Lock()
        self._last_request = 0.0
        self._last_adjustment = time.monotonic()
        self._consecutive_errors = 0
        self._circuit_open = False
        self._circuit_open_until = 0.0
        
        # Statistics
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.rate_adjustments = 0
    
    def wait(self) -> float:
        """
        Wait for rate limit, returns actual wait time
        
        Usage:
            wait_time = limiter.wait()
            response = make_request()
            limiter.record_response(response)
        """
        with self._lock:
            # Check circuit breaker
            if self._circuit_open:
                if time.monotonic() < self._circuit_open_until:
                    wait_time = self._circuit_open_until - time.monotonic()
                    logger.warning(f"Circuit open, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    self._circuit_open = False
                else:
                    self._circuit_open = False
            
            # Calculate required wait
            now = time.monotonic()
            min_interval = 1.0 / self.current_rate
            elapsed = now - self._last_request
            
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                time.sleep(wait_time)
                self.total_wait_time += wait_time
            else:
                wait_time = 0
            
            self._last_request = time.monotonic()
            self.total_requests += 1
            
            return wait_time
    
    def record_response(
        self,
        response_time_ms: float,
        status_code: int = 200,
        success: bool = True
    ) -> None:
        """Record response metrics for rate adjustment"""
        rate_limited = status_code == 429
        
        metric = ResponseMetrics(
            timestamp=time.monotonic(),
            response_time_ms=response_time_ms,
            status_code=status_code,
            success=success,
            rate_limited=rate_limited
        )
        
        with self._lock:
            self._metrics.append(metric)
            
            # Handle errors
            if not success or rate_limited:
                self._consecutive_errors += 1
                
                if rate_limited:
                    self._handle_rate_limit()
                elif self._consecutive_errors >= 3:
                    self._open_circuit(30)  # 30 second cooldown
            else:
                self._consecutive_errors = 0
            
            # Adjust rate periodically
            if time.monotonic() - self._last_adjustment > self.config.adjustment_interval:
                self._adjust_rate()
    
    def _handle_rate_limit(self) -> None:
        """Handle rate limit response"""
        # Immediately reduce rate
        self.current_rate = max(
            self.config.min_rate,
            self.current_rate * 0.3  # Reduce to 30%
        )
        
        # Open circuit for cooldown
        self._open_circuit(60)  # 60 second cooldown
        
        logger.warning(f"Rate limited! Reduced rate to {self.current_rate:.2f}/s")
    
    def _open_circuit(self, duration: float) -> None:
        """Open circuit breaker"""
        self._circuit_open = True
        self._circuit_open_until = time.monotonic() + duration
        logger.info(f"Circuit breaker open for {duration}s")
    
    def _adjust_rate(self) -> None:
        """Adjust rate based on recent metrics"""
        if len(self._metrics) < 5:
            return
        
        self._last_adjustment = time.monotonic()
        health = self._assess_health()
        old_rate = self.current_rate
        
        if health == ServerHealth.EXCELLENT:
            # Speed up
            self.current_rate = min(
                self.config.max_rate,
                self.current_rate * self.config.increase_factor
            )
        elif health == ServerHealth.GOOD:
            # Slight increase
            self.current_rate = min(
                self.config.max_rate,
                self.current_rate * 1.05
            )
        elif health == ServerHealth.DEGRADED:
            # Slight decrease
            self.current_rate = max(
                self.config.min_rate,
                self.current_rate * 0.9
            )
        elif health == ServerHealth.STRESSED:
            # Significant decrease
            self.current_rate = max(
                self.config.min_rate,
                self.current_rate * self.config.decrease_factor
            )
        elif health == ServerHealth.CRITICAL:
            # Emergency slowdown
            self.current_rate = self.config.min_rate
        
        if old_rate != self.current_rate:
            self.rate_adjustments += 1
            logger.info(f"Rate adjusted: {old_rate:.2f} -> {self.current_rate:.2f}/s ({health.value})")
    
    def _assess_health(self) -> ServerHealth:
        """Assess server health based on metrics"""
        if not self._metrics:
            return ServerHealth.GOOD
        
        recent = list(self._metrics)
        
        # Check for rate limits
        rate_limited = sum(1 for m in recent if m.rate_limited)
        if rate_limited > 0:
            return ServerHealth.CRITICAL
        
        # Check error rate
        errors = sum(1 for m in recent if not m.success)
        error_rate = errors / len(recent)
        if error_rate > 0.3:
            return ServerHealth.CRITICAL
        elif error_rate > 0.1:
            return ServerHealth.STRESSED
        
        # Check response times
        response_times = [m.response_time_ms for m in recent if m.success]
        if not response_times:
            return ServerHealth.DEGRADED
        
        avg_time = statistics.mean(response_times)
        
        if avg_time < self.config.excellent_threshold:
            return ServerHealth.EXCELLENT
        elif avg_time < self.config.good_threshold:
            return ServerHealth.GOOD
        elif avg_time < self.config.degraded_threshold:
            return ServerHealth.DEGRADED
        elif avg_time < self.config.stressed_threshold:
            return ServerHealth.STRESSED
        else:
            return ServerHealth.CRITICAL
    
    @property
    def health(self) -> ServerHealth:
        """Get current server health assessment"""
        with self._lock:
            return self._assess_health()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self._lock:
            recent = list(self._metrics)
            
            if recent:
                response_times = [m.response_time_ms for m in recent if m.success]
                avg_response = statistics.mean(response_times) if response_times else 0
                success_rate = sum(1 for m in recent if m.success) / len(recent)
            else:
                avg_response = 0
                success_rate = 1.0
            
            return {
                'current_rate': self.current_rate,
                'health': self._assess_health().value,
                'total_requests': self.total_requests,
                'total_wait_time': self.total_wait_time,
                'rate_adjustments': self.rate_adjustments,
                'avg_response_ms': avg_response,
                'success_rate': success_rate,
                'circuit_open': self._circuit_open
            }


class SmartScheduler:
    """
    Smart Task Scheduler
    
    Schedules heavy operations during optimal times
    (off-peak hours, low server load).
    
    Features:
    - Time-based scheduling
    - Load-aware scheduling
    - Priority queuing
    - Automatic rescheduling on failure
    """
    
    # Off-peak hours (local time)
    OFF_PEAK_HOURS = list(range(22, 24)) + list(range(0, 7))  # 22:00 - 07:00
    
    def __init__(self, rate_limiter: Optional[AdaptiveRateLimiter] = None):
        self.rate_limiter = rate_limiter
        self._scheduled_tasks: List[Dict] = []
        self._lock = threading.Lock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
    
    def is_off_peak(self) -> bool:
        """Check if current time is off-peak"""
        return datetime.now().hour in self.OFF_PEAK_HOURS
    
    def is_good_time_for_heavy_task(self) -> bool:
        """Check if it's a good time for heavy operations"""
        # Off-peak hours
        if self.is_off_peak():
            return True
        
        # Check server health
        if self.rate_limiter:
            health = self.rate_limiter.health
            if health in [ServerHealth.EXCELLENT, ServerHealth.GOOD]:
                return True
        
        return False
    
    def get_next_off_peak(self) -> datetime:
        """Get next off-peak time window"""
        now = datetime.now()
        
        if self.is_off_peak():
            return now
        
        # Find next off-peak hour
        if now.hour < 22:
            # Today at 22:00
            return now.replace(hour=22, minute=0, second=0, microsecond=0)
        else:
            # Tomorrow at 00:00
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def schedule_task(
        self,
        task_func: Callable,
        task_name: str,
        priority: int = 5,
        require_off_peak: bool = False,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Schedule a task for execution
        
        Args:
            task_func: Function to execute
            task_name: Human-readable task name
            priority: Priority (1-10, lower = higher priority)
            require_off_peak: Only run during off-peak hours
            max_retries: Maximum retry attempts
            **kwargs: Arguments to pass to task_func
        
        Returns:
            Task ID
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = {
            'id': task_id,
            'name': task_name,
            'func': task_func,
            'kwargs': kwargs,
            'priority': priority,
            'require_off_peak': require_off_peak,
            'max_retries': max_retries,
            'retries': 0,
            'status': 'pending',
            'created_at': datetime.now(),
            'scheduled_for': self.get_next_off_peak() if require_off_peak else datetime.now()
        }
        
        with self._lock:
            self._scheduled_tasks.append(task)
            self._scheduled_tasks.sort(key=lambda t: (t['priority'], t['scheduled_for']))
        
        logger.info(f"Scheduled task: {task_name} (ID: {task_id})")
        return task_id
    
    def schedule_full_sync(self, sync_func: Callable, **kwargs) -> str:
        """Schedule a full database sync (heavy operation)"""
        return self.schedule_task(
            sync_func,
            "Full Database Sync",
            priority=3,
            require_off_peak=True,
            max_retries=3,
            **kwargs
        )
    
    def schedule_batch_messages(self, send_func: Callable, **kwargs) -> str:
        """Schedule batch message sending"""
        return self.schedule_task(
            send_func,
            "Batch Message Sending",
            priority=5,
            require_off_peak=False,
            max_retries=2,
            **kwargs
        )
    
    def start(self) -> None:
        """Start the scheduler"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info("Smart scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Smart scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                self._process_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _process_tasks(self) -> None:
        """Process pending tasks"""
        now = datetime.now()
        
        with self._lock:
            tasks_to_run = [
                t for t in self._scheduled_tasks
                if t['status'] == 'pending'
                and t['scheduled_for'] <= now
                and (not t['require_off_peak'] or self.is_off_peak())
            ]
        
        for task in tasks_to_run:
            self._execute_task(task)
    
    def _execute_task(self, task: Dict) -> None:
        """Execute a single task"""
        task['status'] = 'running'
        logger.info(f"Executing task: {task['name']} (ID: {task['id']})")
        
        try:
            result = task['func'](**task['kwargs'])
            task['status'] = 'completed'
            task['completed_at'] = datetime.now()
            task['result'] = result
            logger.info(f"Task completed: {task['name']}")
            
        except Exception as e:
            task['retries'] += 1
            
            if task['retries'] < task['max_retries']:
                # Reschedule with delay
                delay = 2 ** task['retries'] * 60  # Exponential backoff
                task['scheduled_for'] = datetime.now() + timedelta(seconds=delay)
                task['status'] = 'pending'
                logger.warning(f"Task failed, rescheduling: {task['name']} ({e})")
            else:
                task['status'] = 'failed'
                task['error'] = str(e)
                logger.error(f"Task failed permanently: {task['name']} ({e})")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        with self._lock:
            for task in self._scheduled_tasks:
                if task['id'] == task_id:
                    return {
                        'id': task['id'],
                        'name': task['name'],
                        'status': task['status'],
                        'retries': task['retries'],
                        'scheduled_for': task['scheduled_for'].isoformat(),
                        'error': task.get('error')
                    }
        return None
    
    def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks"""
        with self._lock:
            return [
                {
                    'id': t['id'],
                    'name': t['name'],
                    'priority': t['priority'],
                    'scheduled_for': t['scheduled_for'].isoformat()
                }
                for t in self._scheduled_tasks
                if t['status'] == 'pending'
            ]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self._lock:
            for task in self._scheduled_tasks:
                if task['id'] == task_id and task['status'] == 'pending':
                    task['status'] = 'cancelled'
                    logger.info(f"Task cancelled: {task['name']}")
                    return True
        return False


class RequestThrottler:
    """
    Simple request throttler for specific endpoints
    
    Use when you need guaranteed rate limits without adaptation.
    """
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self._request_times: deque = deque(maxlen=requests_per_minute)
        self._lock = threading.Lock()
    
    def throttle(self) -> float:
        """
        Throttle requests to stay within limit
        
        Returns:
            Wait time in seconds
        """
        with self._lock:
            now = time.monotonic()
            
            # Remove old requests (older than 1 minute)
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()
            
            # Check if at limit
            if len(self._request_times) >= self.requests_per_minute:
                # Wait until oldest request expires
                wait_time = 60 - (now - self._request_times[0])
                if wait_time > 0:
                    time.sleep(wait_time)
            
            self._request_times.append(time.monotonic())
            return 0
    
    @property
    def remaining(self) -> int:
        """Get remaining requests in current window"""
        with self._lock:
            now = time.monotonic()
            valid = sum(1 for t in self._request_times if now - t <= 60)
            return max(0, self.requests_per_minute - valid)


# Global instances
_rate_limiter: Optional[AdaptiveRateLimiter] = None
_scheduler: Optional[SmartScheduler] = None


def get_rate_limiter() -> AdaptiveRateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdaptiveRateLimiter()
    return _rate_limiter


def get_scheduler() -> SmartScheduler:
    """Get global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SmartScheduler(get_rate_limiter())
    return _scheduler
