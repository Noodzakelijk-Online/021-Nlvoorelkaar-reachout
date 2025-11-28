"""
Asynchronous Task Manager for NLvoorelkaar Tool
Handles background operations with progress tracking and cancellation
"""

import asyncio
import threading
import queue
import time
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class TaskProgress:
    """Task progress information"""
    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0
    
    def update(self, current: int = None, total: int = None, message: str = None):
        """Update progress information"""
        if current is not None:
            self.current = current
        if total is not None:
            self.total = total
        if message is not None:
            self.message = message
            
        if self.total > 0:
            self.percentage = (self.current / self.total) * 100
        else:
            self.percentage = 0.0

@dataclass
class Task:
    """Asynchronous task definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    function: Callable = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Any = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    callback: Optional[Callable] = None
    cancellation_token: threading.Event = field(default_factory=threading.Event)
    
    def cancel(self):
        """Cancel the task"""
        self.cancellation_token.set()
        self.status = TaskStatus.CANCELLED
        
    def is_cancelled(self) -> bool:
        """Check if task is cancelled"""
        return self.cancellation_token.is_set()

class AsyncTaskManager:
    """Manages asynchronous tasks with progress tracking"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_queue = queue.Queue()
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        self._shutdown = False
        
        # Start task processor
        self.processor_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self.processor_thread.start()
        
    def add_task(self, 
                 name: str,
                 function: Callable,
                 args: tuple = (),
                 kwargs: dict = None,
                 description: str = "",
                 callback: Callable = None) -> str:
        """Add a new task to the queue"""
        task = Task(
            name=name,
            description=description,
            function=function,
            args=args,
            kwargs=kwargs or {},
            callback=callback
        )
        
        self.tasks[task.id] = task
        self.task_queue.put(task.id)
        
        logger.info(f"Task added: {name} ({task.id})")
        self._notify_progress_callbacks(task)
        
        return task.id
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.cancel()
            
            # If task is running, we need to wait for it to check cancellation
            if task_id in self.running_tasks:
                logger.info(f"Cancelling running task: {task.name}")
            else:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
            self._notify_completion_callbacks(task)
            return True
        return False
        
    def pause_task(self, task_id: str) -> bool:
        """Pause a specific task (if supported by the task function)"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.PAUSED
                return True
        return False
        
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PAUSED:
                task.status = TaskStatus.RUNNING
                return True
        return False
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
        
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return list(self.tasks.values())
        
    def get_running_tasks(self) -> List[Task]:
        """Get currently running tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]
        
    def get_pending_tasks(self) -> List[Task]:
        """Get pending tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
        
    def clear_completed_tasks(self):
        """Clear completed, failed, and cancelled tasks"""
        to_remove = []
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                to_remove.append(task_id)
                
        for task_id in to_remove:
            del self.tasks[task_id]
            
    def add_progress_callback(self, callback: Callable):
        """Add progress update callback"""
        self.progress_callbacks.append(callback)
        
    def add_completion_callback(self, callback: Callable):
        """Add task completion callback"""
        self.completion_callbacks.append(callback)
        
    def _process_tasks(self):
        """Process tasks from the queue"""
        while not self._shutdown:
            try:
                # Check if we can start new tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    time.sleep(0.1)
                    continue
                    
                # Get next task
                try:
                    task_id = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                if task_id not in self.tasks:
                    continue
                    
                task = self.tasks[task_id]
                
                # Skip cancelled tasks
                if task.is_cancelled():
                    continue
                    
                # Start task in new thread
                thread = threading.Thread(
                    target=self._execute_task,
                    args=(task,),
                    daemon=True
                )
                
                self.running_tasks[task_id] = thread
                thread.start()
                
            except Exception as e:
                logger.error(f"Error in task processor: {e}")
                
    def _execute_task(self, task: Task):
        """Execute a single task"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            logger.info(f"Starting task: {task.name}")
            self._notify_progress_callbacks(task)
            
            # Create progress updater
            def update_progress(current: int = None, total: int = None, message: str = None):
                if not task.is_cancelled():
                    task.progress.update(current, total, message)
                    self._notify_progress_callbacks(task)
                    
            # Add progress updater to kwargs
            task.kwargs['progress_callback'] = update_progress
            task.kwargs['cancellation_token'] = task.cancellation_token
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task.function):
                # Handle async functions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    task.result = loop.run_until_complete(
                        task.function(*task.args, **task.kwargs)
                    )
                finally:
                    loop.close()
            else:
                # Handle sync functions
                task.result = task.function(*task.args, **task.kwargs)
                
            # Check if task was cancelled during execution
            if task.is_cancelled():
                task.status = TaskStatus.CANCELLED
            else:
                task.status = TaskStatus.COMPLETED
                
            task.completed_at = datetime.now()
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            logger.error(f"Task failed: {task.name} - {e}")
            
        finally:
            # Remove from running tasks
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
                
            # Call completion callback
            self._notify_completion_callbacks(task)
            
            # Call task-specific callback
            if task.callback:
                try:
                    task.callback(task)
                except Exception as e:
                    logger.error(f"Error in task callback: {e}")
                    
    def _notify_progress_callbacks(self, task: Task):
        """Notify progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
                
    def _notify_completion_callbacks(self, task: Task):
        """Notify completion callbacks"""
        for callback in self.completion_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
                
    def shutdown(self):
        """Shutdown the task manager"""
        self._shutdown = True
        
        # Cancel all pending and running tasks
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.cancel()
                
        # Wait for processor thread to finish
        if self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5.0)

# Task wrapper functions for common operations
class TaskWrappers:
    """Common task wrapper functions"""
    
    @staticmethod
    def scrape_volunteers(scraper, search_params, progress_callback=None, cancellation_token=None):
        """Wrapper for volunteer scraping with progress tracking"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Starting volunteer search...")
                
            volunteers = []
            page = 1
            max_pages = search_params.get('max_pages', 50)
            
            while page <= max_pages:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_set():
                    break
                    
                if progress_callback:
                    progress_callback(
                        page - 1, 
                        max_pages, 
                        f"Scraping page {page}..."
                    )
                    
                # Scrape page
                page_volunteers = scraper.search_volunteers_page(search_params, page)
                
                if not page_volunteers:
                    break
                    
                volunteers.extend(page_volunteers)
                page += 1
                
                # Small delay to be respectful
                time.sleep(1)
                
            if progress_callback:
                progress_callback(
                    max_pages, 
                    max_pages, 
                    f"Found {len(volunteers)} volunteers"
                )
                
            return volunteers
            
        except Exception as e:
            logger.error(f"Error in scrape_volunteers task: {e}")
            raise
            
    @staticmethod
    def send_messages(scraper, message_data, progress_callback=None, cancellation_token=None):
        """Wrapper for sending messages with progress tracking"""
        try:
            volunteers = message_data['volunteers']
            message_template = message_data['message_template']
            campaign_id = message_data.get('campaign_id')
            
            sent_count = 0
            failed_count = 0
            
            for i, volunteer in enumerate(volunteers):
                # Check for cancellation
                if cancellation_token and cancellation_token.is_set():
                    break
                    
                if progress_callback:
                    progress_callback(
                        i,
                        len(volunteers),
                        f"Sending message to {volunteer.get('name', 'volunteer')}..."
                    )
                    
                try:
                    # Personalize message
                    personalized_message = message_template.replace(
                        '{name}', volunteer.get('name', 'there')
                    ).replace(
                        '{location}', volunteer.get('location', 'your area')
                    )
                    
                    # Send message
                    success = scraper.send_message(
                        volunteer['volunteer_id'],
                        personalized_message
                    )
                    
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                    # Delay between messages
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error sending message to {volunteer.get('volunteer_id')}: {e}")
                    failed_count += 1
                    
            if progress_callback:
                progress_callback(
                    len(volunteers),
                    len(volunteers),
                    f"Completed: {sent_count} sent, {failed_count} failed"
                )
                
            return {
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_count': len(volunteers)
            }
            
        except Exception as e:
            logger.error(f"Error in send_messages task: {e}")
            raise
            
    @staticmethod
    def backup_data(backup_manager, backup_name=None, progress_callback=None, cancellation_token=None):
        """Wrapper for data backup with progress tracking"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Starting backup...")
                
            # Check for cancellation
            if cancellation_token and cancellation_token.is_set():
                return None
                
            if progress_callback:
                progress_callback(25, 100, "Preparing backup...")
                
            # Create backup
            backup_path = backup_manager.create_backup(backup_name)
            
            if progress_callback:
                progress_callback(75, 100, "Verifying backup...")
                
            # Verify backup
            if backup_path and backup_manager.verify_backup(backup_path):
                if progress_callback:
                    progress_callback(100, 100, "Backup completed successfully")
                return backup_path
            else:
                raise Exception("Backup verification failed")
                
        except Exception as e:
            logger.error(f"Error in backup_data task: {e}")
            raise

