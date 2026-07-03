"""
Scheduler Service
Automated daily synchronization scheduler with monitoring and management
"""

import asyncio
import threading
import time
import logging
import re
import sqlite3
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    import schedule
except ImportError:
    schedule = None

from .sync_service import SyncService, SyncReport

class ScheduleStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    task_id: str
    name: str
    schedule_time: str
    function: Callable
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    status: ScheduleStatus
    run_count: int
    error_count: int
    last_error: Optional[str]

class SchedulerService:
    """
    Automated scheduler service for daily synchronization and maintenance tasks
    
    Features:
    - Daily synchronization scheduling
    - Task monitoring and management
    - Error handling and retry logic
    - Performance tracking
    - Flexible scheduling configuration
    """
    
    def __init__(self, sync_service: SyncService):
        self.sync_service = sync_service
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Scheduler state
        self.scheduler_thread = None
        self.scheduler_status = ScheduleStatus.STOPPED
        self.scheduled_tasks = {}
        self.task_history = []
        
        # Configuration
        self.config = {
            'daily_sync_time': '02:00',
            'maintenance_time': '03:00',
            'backup_time': '01:00',
            'max_retry_attempts': 3,
            'retry_delay_minutes': 30,
            'task_timeout_minutes': 120,
            'enable_notifications': True
        }
        
        # Initialize default tasks
        self._initialize_default_tasks()

    def _error_label(self, error: Optional[object]) -> Optional[str]:
        """Reduce scheduler errors to a non-sensitive class-style label."""
        if error is None:
            return None
        if isinstance(error, BaseException):
            return type(error).__name__
        text = str(error).strip()
        if not text:
            return None
        prefix = text.split(":", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", prefix) and len(prefix) <= 120:
            return prefix
        return "Error"

    def _schedule_available(self) -> bool:
        """Return whether the schedule dependency is available."""
        if schedule is not None:
            return True
        self.logger.warning("Schedule package is unavailable. Install `schedule` for scheduler features.")
        return False
    
    def _initialize_default_tasks(self):
        """Initialize default scheduled tasks"""
        try:
            if not self._schedule_available():
                return
            # Daily synchronization task
            self.add_scheduled_task(
                task_id='daily_sync',
                name='Daily Volunteer Database Synchronization',
                schedule_time=self.config['daily_sync_time'],
                function=self._run_daily_sync
            )
            
            # Daily maintenance task
            self.add_scheduled_task(
                task_id='daily_maintenance',
                name='Daily Database Maintenance',
                schedule_time=self.config['maintenance_time'],
                function=self._run_daily_maintenance
            )
            
            # Daily backup task
            self.add_scheduled_task(
                task_id='daily_backup',
                name='Daily Database Backup',
                schedule_time=self.config['backup_time'],
                function=self._run_daily_backup
            )
            
            self.logger.info("Initialized default scheduled tasks")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, re.error) as e:
            self.logger.error("Error initializing default tasks: %s", type(e).__name__)
    
    def add_scheduled_task(self, task_id: str, name: str, schedule_time: str, function: Callable):
        """Add a new scheduled task"""
        try:
            if not self._schedule_available():
                return

            task = ScheduledTask(
                task_id=task_id,
                name=name,
                schedule_time=schedule_time,
                function=function,
                last_run=None,
                next_run=self._calculate_next_run_time(schedule_time),
                status=ScheduleStatus.STOPPED,
                run_count=0,
                error_count=0,
                last_error=None
            )
            
            self.scheduled_tasks[task_id] = task
            
            # Add to schedule and tag by task id so updates/removals are precise.
            schedule.every().day.at(schedule_time).do(self._execute_task, task_id).tag(task_id)
            
            self.logger.info(f"Added scheduled task: {name} at {schedule_time}")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, re.error) as e:
            self.logger.error("Error adding scheduled task: %s", type(e).__name__)
    
    def start_scheduler(self):
        """Start the scheduler service"""
        try:
            if not self._schedule_available():
                self.scheduler_status = ScheduleStatus.ERROR
                return
            if self.scheduler_status == ScheduleStatus.RUNNING:
                self.logger.warning("Scheduler is already running")
                return
            
            self.scheduler_status = ScheduleStatus.RUNNING
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            # Update task statuses
            for task in self.scheduled_tasks.values():
                task.status = ScheduleStatus.RUNNING
            
            self.logger.info("Scheduler service started successfully")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, OSError, asyncio.CancelledError) as e:
            self.logger.error("Error starting scheduler: %s", type(e).__name__)
            self.scheduler_status = ScheduleStatus.ERROR
    
    def stop_scheduler(self):
        """Stop the scheduler service"""
        try:
            self.scheduler_status = ScheduleStatus.STOPPED
            
            # Update task statuses
            for task in self.scheduled_tasks.values():
                task.status = ScheduleStatus.STOPPED

            if self._schedule_available():
                # Clear schedule
                schedule.clear()
            
            self.logger.info("Scheduler service stopped")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, OSError) as e:
            self.logger.error("Error stopping scheduler: %s", type(e).__name__)
    
    def pause_scheduler(self):
        """Pause the scheduler service"""
        try:
            self.scheduler_status = ScheduleStatus.PAUSED
            
            # Update task statuses
            for task in self.scheduled_tasks.values():
                task.status = ScheduleStatus.PAUSED
            
            self.logger.info("Scheduler service paused")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, OSError) as e:
            self.logger.error("Error pausing scheduler: %s", type(e).__name__)
    
    def resume_scheduler(self):
        """Resume the scheduler service"""
        try:
            if self.scheduler_status != ScheduleStatus.PAUSED:
                self.logger.warning("Scheduler is not paused")
                return
            
            self.scheduler_status = ScheduleStatus.RUNNING
            
            # Update task statuses
            for task in self.scheduled_tasks.values():
                task.status = ScheduleStatus.RUNNING
            
            self.logger.info("Scheduler service resumed")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, OSError) as e:
            self.logger.error("Error resuming scheduler: %s", type(e).__name__)
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        if not self._schedule_available():
            self.logger.warning("Cannot run scheduler loop without schedule dependency")
            return
        self.logger.info("Scheduler loop started")
        
        while self.scheduler_status in [ScheduleStatus.RUNNING, ScheduleStatus.PAUSED]:
            try:
                if self.scheduler_status == ScheduleStatus.RUNNING:
                    schedule.run_pending()
                
                time.sleep(60)  # Check every minute
                
            except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, OSError, asyncio.CancelledError) as e:
                self.logger.error("Error in scheduler loop: %s", type(e).__name__)
                self.scheduler_status = ScheduleStatus.ERROR
                break
        
        self.logger.info("Scheduler loop ended")
    
    def _execute_task(self, task_id: str):
        """Execute a scheduled task with error handling and retry logic"""
        if task_id not in self.scheduled_tasks:
            self.logger.error(f"Task {task_id} not found")
            return
        
        task = self.scheduled_tasks[task_id]
        
        try:
            self.logger.info(f"Executing scheduled task: {task.name}")
            
            # Update task status
            task.last_run = datetime.now()
            task.next_run = self._calculate_next_run_time(task.schedule_time)
            
            # Execute task with timeout
            result = asyncio.run(self._execute_task_with_timeout(task))
            
            if result:
                task.run_count += 1
                self.logger.info(f"Task {task.name} completed successfully")
                
                # Record successful execution
                self._record_task_execution(task_id, True, None)
            else:
                raise RuntimeError("Task execution failed")
                
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, sqlite3.DatabaseError) as e:
            error_msg = type(e).__name__
            task.error_count += 1
            task.last_error = error_msg
            
            self.logger.error("Task %s failed: %s", task.name, error_msg)
            
            # Record failed execution
            self._record_task_execution(task_id, False, error_msg)
            
            # Attempt retry if configured
            if task.error_count <= self.config['max_retry_attempts']:
                self._schedule_retry(task_id)
    
    async def _execute_task_with_timeout(self, task: ScheduledTask) -> bool:
        """Execute task with timeout protection"""
        try:
            timeout_seconds = self.config['task_timeout_minutes'] * 60
            
            # Execute task function
            if asyncio.iscoroutinefunction(task.function):
                result = await asyncio.wait_for(task.function(), timeout=timeout_seconds)
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, task.function),
                    timeout=timeout_seconds
                )
            
            return result is not False  # Consider None as success
            
        except asyncio.TimeoutError:
            self.logger.error(f"Task {task.name} timed out after {self.config['task_timeout_minutes']} minutes")
            return False
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, sqlite3.DatabaseError) as e:
            self.logger.error("Task %s execution error: %s", task.name, type(e).__name__)
            return False
    
    def _schedule_retry(self, task_id: str):
        """Schedule a retry for a failed task"""
        try:
            if not self._schedule_available():
                return
            task = self.scheduled_tasks[task_id]
            retry_time = datetime.now() + timedelta(minutes=self.config['retry_delay_minutes'])
            
            self.logger.info(f"Scheduling retry for task {task.name} at {retry_time}")
            
            # Schedule one-time retry and keep a dedicated retry tag.
            schedule.every().day.at(retry_time.strftime('%H:%M')).do(
                self._execute_retry, task_id
            ).tag(f"retry_{task_id}")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error scheduling retry: %s", type(e).__name__)
    
    def _execute_retry(self, task_id: str):
        """Execute a retry attempt"""
        try:
            self.logger.info(f"Executing retry for task {task_id}")

            if self._schedule_available():
                # Remove retry tag
                schedule.clear(f"retry_{task_id}")
            
            # Execute task
            self._execute_task(task_id)
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error executing retry: %s", type(e).__name__)
    
    def _record_task_execution(self, task_id: str, success: bool, error_msg: Optional[str]):
        """Record task execution in history"""
        try:
            execution_record = {
                'task_id': task_id,
                'task_name': self.scheduled_tasks[task_id].name,
                'execution_time': datetime.now().isoformat(),
                'success': success,
                'error_message': self._error_label(error_msg),
                'duration': None  # Could be enhanced to track duration
            }
            
            self.task_history.append(execution_record)
            
            # Keep only last 1000 records
            if len(self.task_history) > 1000:
                self.task_history = self.task_history[-1000:]
                
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, sqlite3.DatabaseError) as e:
            self.logger.error("Error recording task execution: %s", type(e).__name__)
    
    def _calculate_next_run_time(self, schedule_time: str) -> datetime:
        """Calculate next run time for a scheduled task"""
        try:
            now = datetime.now()
            time_parts = schedule_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)
            
            return next_run
            
        except (AttributeError, ValueError, TypeError, KeyError, RuntimeError) as e:
            self.logger.error("Error calculating next run time: %s", type(e).__name__)
            return datetime.now() + timedelta(days=1)
    
    async def _run_daily_sync(self) -> bool:
        """Execute daily synchronization"""
        try:
            self.logger.info("Starting daily synchronization task")
            
            sync_report = await self.sync_service.perform_daily_sync()
            
            if sync_report.success:
                self.logger.info("Daily synchronization completed successfully")
                return True
            else:
                self.logger.error("Daily synchronization failed")
                return False
                
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, sqlite3.DatabaseError) as e:
            self.logger.error("Daily sync task error: %s", type(e).__name__)
            return False
    
    def _run_daily_maintenance(self) -> bool:
        """Execute daily maintenance tasks"""
        try:
            self.logger.info("Starting daily maintenance task")
            
            # Database optimization
            self.sync_service.db_manager.optimize_database()
            
            # Clean old records
            self._clean_old_records()
            
            # Generate integrity report
            integrity_report = self.sync_service.get_database_integrity_report()
            
            if integrity_report.get('data_quality_score', 0) < 80:
                self.logger.warning(f"Data quality score is low: {integrity_report.get('data_quality_score', 0)}%")
            
            self.logger.info("Daily maintenance completed successfully")
            return True
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, sqlite3.DatabaseError) as e:
            self.logger.error("Daily maintenance task error: %s", type(e).__name__)
            return False
    
    def _run_daily_backup(self) -> bool:
        """Execute daily backup task"""
        try:
            self.logger.info("Starting daily backup task")
            
            backup_id = self.sync_service.backup_manager.create_backup("daily_scheduled")
            
            if backup_id:
                self.logger.info(f"Daily backup completed: {backup_id}")
                return True
            else:
                self.logger.error("Daily backup failed")
                return False
                
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Daily backup task error: %s", type(e).__name__)
            return False
    
    def _clean_old_records(self):
        """Clean old records from database"""
        try:
            # Clean old sync reports (keep last 90 days)
            cutoff_date = datetime.now() - timedelta(days=90)
            self.sync_service.db_manager.clean_old_sync_reports(cutoff_date)
            
            # Clean old task history (keep last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            self.task_history = [
                record for record in self.task_history
                if datetime.fromisoformat(record['execution_time']) >= cutoff_date
            ]
            
            self.logger.info("Old records cleaned successfully")
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, IndexError, TypeError) as e:
            self.logger.error("Error cleaning old records: %s", type(e).__name__)
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status"""
        try:
            status = {
                'scheduler_status': self.scheduler_status.value,
                'total_tasks': len(self.scheduled_tasks),
                'running_tasks': len([t for t in self.scheduled_tasks.values() if t.status == ScheduleStatus.RUNNING]),
                'failed_tasks': len([t for t in self.scheduled_tasks.values() if t.error_count > 0]),
                'next_task': None,
                'uptime': None,
                'config': self.config
            }
            
            # Find next scheduled task
            next_tasks = sorted(
                [(task.task_id, task.next_run) for task in self.scheduled_tasks.values() if task.next_run],
                key=lambda x: x[1]
            )
            
            if next_tasks:
                next_task_id, next_run_time = next_tasks[0]
                status['next_task'] = {
                    'task_id': next_task_id,
                    'task_name': self.scheduled_tasks[next_task_id].name,
                    'next_run': next_run_time.isoformat(),
                    'time_until_run': str(next_run_time - datetime.now())
                }
            
            return status
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError, IndexError) as e:
            self.logger.error("Error getting scheduler status: %s", type(e).__name__)
            return {}
    
    def get_task_details(self, task_id: str) -> Optional[Dict]:
        """Get detailed information about a specific task"""
        try:
            if task_id not in self.scheduled_tasks:
                return None
            
            task = self.scheduled_tasks[task_id]
            
            return {
                'task_id': task.task_id,
                'name': task.name,
                'schedule_time': task.schedule_time,
                'status': task.status.value,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'last_error': task.last_error,
                'success_rate': (task.run_count - task.error_count) / max(task.run_count, 1) * 100
            }
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error getting task details: %s", type(e).__name__)
            return None
    
    def get_task_history(self, task_id: Optional[str] = None, days: int = 7) -> List[Dict]:
        """Get task execution history"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            history = []
            for record in self.task_history:
                execution_time = datetime.fromisoformat(record['execution_time'])
                
                if execution_time >= cutoff_date:
                    if task_id is None or record['task_id'] == task_id:
                        history.append(record)
            
            return sorted(history, key=lambda x: x['execution_time'], reverse=True)
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error getting task history: %s", type(e).__name__)
            return []
    
    def run_task_now(self, task_id: str) -> bool:
        """Run a specific task immediately"""
        try:
            if task_id not in self.scheduled_tasks:
                self.logger.error(f"Task {task_id} not found")
                return False
            
            self.logger.info(f"Running task {task_id} immediately")
            self._execute_task(task_id)
            return True
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error running task immediately: %s", type(e).__name__)
            return False
    
    def update_task_schedule(self, task_id: str, new_schedule_time: str) -> bool:
        """Update the schedule time for a task"""
        try:
            if not self._schedule_available():
                return False
            if task_id not in self.scheduled_tasks:
                self.logger.error(f"Task {task_id} not found")
                return False
            
            task = self.scheduled_tasks[task_id]
            old_time = task.schedule_time
            
            # Update task schedule
            task.schedule_time = new_schedule_time
            task.next_run = self._calculate_next_run_time(new_schedule_time)
            
            # Update schedule
            schedule.clear(task_id)
            schedule.every().day.at(new_schedule_time).do(self._execute_task, task_id).tag(task_id)
            
            self.logger.info(f"Updated task {task.name} schedule from {old_time} to {new_schedule_time}")
            return True
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error updating task schedule: %s", type(e).__name__)
            return False
    
    def get_performance_metrics(self) -> Dict:
        """Get scheduler performance metrics"""
        try:
            total_executions = len(self.task_history)
            successful_executions = len([r for r in self.task_history if r['success']])
            
            metrics = {
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'failed_executions': total_executions - successful_executions,
                'success_rate': (successful_executions / max(total_executions, 1)) * 100,
                'average_daily_executions': 0,
                'task_performance': {}
            }
            
            # Calculate average daily executions
            if self.task_history:
                oldest_record = min(self.task_history, key=lambda x: x['execution_time'])
                oldest_date = datetime.fromisoformat(oldest_record['execution_time'])
                days_active = max((datetime.now() - oldest_date).days, 1)
                metrics['average_daily_executions'] = total_executions / days_active
            
            # Task-specific performance
            for task_id, task in self.scheduled_tasks.items():
                task_executions = [r for r in self.task_history if r['task_id'] == task_id]
                task_successes = [r for r in task_executions if r['success']]
                
                metrics['task_performance'][task_id] = {
                    'name': task.name,
                    'total_executions': len(task_executions),
                    'successful_executions': len(task_successes),
                    'success_rate': (len(task_successes) / max(len(task_executions), 1)) * 100,
                    'last_execution': task_executions[0]['execution_time'] if task_executions else None
                }
            
            return metrics
            
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as e:
            self.logger.error("Error getting performance metrics: %s", type(e).__name__)
            return {}
