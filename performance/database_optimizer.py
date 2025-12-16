"""
Database Optimizer
Implements connection pooling, advanced indexing, and batch operations
for maximum database performance.
"""

import sqlite3
import threading
import queue
import time
import logging
from typing import Any, Optional, Dict, List, Tuple, Callable, Iterator
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for query performance monitoring"""
    query_count: int = 0
    total_time_ms: float = 0
    avg_time_ms: float = 0
    slow_queries: int = 0
    cache_hits: int = 0
    
    def record(self, duration_ms: float, slow_threshold: float = 100) -> None:
        self.query_count += 1
        self.total_time_ms += duration_ms
        self.avg_time_ms = self.total_time_ms / self.query_count
        if duration_ms > slow_threshold:
            self.slow_queries += 1


class ConnectionPool:
    """
    SQLite Connection Pool
    
    Maintains a pool of database connections for reuse,
    avoiding the overhead of creating new connections.
    
    Features:
    - Thread-safe connection management
    - Automatic connection health checks
    - Connection timeout handling
    - Statistics tracking
    """
    
    def __init__(
        self,
        db_path: str,
        pool_size: int = 10,
        timeout: float = 30.0,
        check_same_thread: bool = False
    ):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.check_same_thread = check_same_thread
        
        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created = 0
        self._in_use = 0
        self.stats = QueryStats()
        
        # Pre-create connections
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Pre-create connections for the pool"""
        for _ in range(min(3, self.pool_size)):  # Start with 3 connections
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimizations"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=self.check_same_thread,
            isolation_level=None  # Autocommit mode for better performance
        )
        
        # Enable optimizations
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
        conn.execute('PRAGMA synchronous=NORMAL')  # Faster writes
        conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
        conn.execute('PRAGMA temp_store=MEMORY')  # Temp tables in memory
        conn.execute('PRAGMA mmap_size=268435456')  # 256MB memory-mapped I/O
        
        conn.row_factory = sqlite3.Row
        
        with self._lock:
            self._created += 1
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM table")
        """
        conn = None
        try:
            # Try to get from pool
            try:
                conn = self._pool.get(timeout=self.timeout)
            except queue.Empty:
                # Pool exhausted, create new if under limit
                with self._lock:
                    if self._created < self.pool_size:
                        conn = self._create_connection()
                    else:
                        raise RuntimeError("Connection pool exhausted")
            
            with self._lock:
                self._in_use += 1
            
            # Health check
            try:
                conn.execute('SELECT 1')
            except sqlite3.Error:
                conn = self._create_connection()
            
            yield conn
            
        finally:
            if conn:
                with self._lock:
                    self._in_use -= 1
                try:
                    self._pool.put_nowait(conn)
                except queue.Full:
                    conn.close()
    
    def execute(
        self,
        query: str,
        params: Tuple = (),
        fetch: bool = True
    ) -> Optional[List[Dict]]:
        """Execute query and return results"""
        start_time = time.monotonic()
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            
            if fetch:
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                result = None
        
        duration = (time.monotonic() - start_time) * 1000
        self.stats.record(duration)
        
        if duration > 100:
            logger.warning(f"Slow query ({duration:.1f}ms): {query[:100]}")
        
        return result
    
    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """Execute query with multiple parameter sets"""
        start_time = time.monotonic()
        
        with self.get_connection() as conn:
            conn.execute('BEGIN TRANSACTION')
            try:
                cursor = conn.executemany(query, params_list)
                conn.execute('COMMIT')
                affected = cursor.rowcount
            except Exception as e:
                conn.execute('ROLLBACK')
                raise
        
        duration = (time.monotonic() - start_time) * 1000
        self.stats.record(duration)
        
        return affected
    
    def close_all(self) -> None:
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
    
    @property
    def pool_status(self) -> Dict[str, int]:
        """Get pool status"""
        return {
            'created': self._created,
            'in_use': self._in_use,
            'available': self._pool.qsize(),
            'max_size': self.pool_size
        }


class IndexManager:
    """
    Database Index Manager
    
    Creates and manages indexes for optimal query performance.
    """
    
    # Recommended indexes for the NLvoorElkaar tool
    RECOMMENDED_INDEXES = [
        # Volunteer table indexes
        ('idx_volunteers_location', 'volunteers', 'location'),
        ('idx_volunteers_active', 'volunteers', 'is_active'),
        ('idx_volunteers_last_seen', 'volunteers', 'last_seen DESC'),
        ('idx_volunteers_skills', 'volunteers', 'skills'),
        ('idx_volunteers_compound', 'volunteers', 'is_active, location, last_seen DESC'),
        ('idx_volunteers_search', 'volunteers', 'name COLLATE NOCASE, location'),
        
        # Messages table indexes
        ('idx_messages_status', 'messages', 'status'),
        ('idx_messages_scheduled', 'messages', 'scheduled_time'),
        ('idx_messages_recipient', 'messages', 'recipient_id'),
        ('idx_messages_compound', 'messages', 'status, scheduled_time'),
        
        # Blacklist table indexes
        ('idx_blacklist_profile', 'blacklist', 'profile_id'),
        ('idx_blacklist_expires', 'blacklist', 'expires_at'),
        
        # Reminders table indexes
        ('idx_reminders_due', 'reminders', 'scheduled_date'),
        ('idx_reminders_status', 'reminders', 'status'),
        
        # Cache table indexes
        ('idx_cache_expires', 'cache', 'expires_at'),
        ('idx_cache_hits', 'cache', 'hits DESC'),
        
        # Sync table indexes
        ('idx_sync_timestamp', 'sync_log', 'sync_timestamp DESC'),
    ]
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
    
    def create_all_indexes(self) -> Dict[str, bool]:
        """Create all recommended indexes"""
        results = {}
        
        for index_name, table, columns in self.RECOMMENDED_INDEXES:
            try:
                success = self.create_index(index_name, table, columns)
                results[index_name] = success
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")
                results[index_name] = False
        
        return results
    
    def create_index(
        self,
        index_name: str,
        table: str,
        columns: str,
        unique: bool = False
    ) -> bool:
        """Create a single index"""
        unique_str = 'UNIQUE' if unique else ''
        query = f'''
            CREATE {unique_str} INDEX IF NOT EXISTS {index_name}
            ON {table} ({columns})
        '''
        
        try:
            self.pool.execute(query, fetch=False)
            logger.info(f"Created index: {index_name}")
            return True
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e):
                logger.debug(f"Table {table} doesn't exist yet, skipping index")
            else:
                logger.error(f"Error creating index {index_name}: {e}")
            return False
    
    def drop_index(self, index_name: str) -> bool:
        """Drop an index"""
        try:
            self.pool.execute(f'DROP INDEX IF EXISTS {index_name}', fetch=False)
            return True
        except Exception as e:
            logger.error(f"Error dropping index {index_name}: {e}")
            return False
    
    def analyze_tables(self) -> None:
        """Run ANALYZE to update query planner statistics"""
        self.pool.execute('ANALYZE', fetch=False)
        logger.info("Database analyzed for query optimization")
    
    def get_index_info(self) -> List[Dict]:
        """Get information about existing indexes"""
        query = '''
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type = 'index' AND sql IS NOT NULL
        '''
        return self.pool.execute(query)
    
    def get_table_stats(self, table: str) -> Dict[str, Any]:
        """Get statistics for a table"""
        count_query = f'SELECT COUNT(*) as count FROM {table}'
        size_query = f'''
            SELECT page_count * page_size as size_bytes
            FROM pragma_page_count(), pragma_page_size()
        '''
        
        try:
            count_result = self.pool.execute(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            return {
                'table': table,
                'row_count': count
            }
        except Exception as e:
            return {'table': table, 'error': str(e)}


class BatchOperations:
    """
    Batch Operations Manager
    
    Provides efficient batch insert, update, and delete operations.
    """
    
    def __init__(self, pool: ConnectionPool, batch_size: int = 1000):
        self.pool = pool
        self.batch_size = batch_size
    
    def batch_insert(
        self,
        table: str,
        columns: List[str],
        data: List[Tuple],
        on_conflict: str = 'IGNORE'
    ) -> int:
        """
        Insert multiple rows efficiently
        
        Args:
            table: Table name
            columns: Column names
            data: List of tuples with values
            on_conflict: Conflict resolution (IGNORE, REPLACE, ABORT)
        
        Returns:
            Number of rows affected
        """
        if not data:
            return 0
        
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        query = f'''
            INSERT OR {on_conflict} INTO {table} ({columns_str})
            VALUES ({placeholders})
        '''
        
        total_affected = 0
        
        # Process in batches
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            affected = self.pool.execute_many(query, batch)
            total_affected += affected
            
            logger.debug(f"Inserted batch {i // self.batch_size + 1}: {affected} rows")
        
        return total_affected
    
    def batch_update(
        self,
        table: str,
        set_columns: List[str],
        where_column: str,
        data: List[Tuple]
    ) -> int:
        """
        Update multiple rows efficiently
        
        Args:
            table: Table name
            set_columns: Columns to update
            where_column: Column for WHERE clause
            data: List of tuples (set_values..., where_value)
        
        Returns:
            Number of rows affected
        """
        if not data:
            return 0
        
        set_str = ', '.join([f'{col} = ?' for col in set_columns])
        query = f'UPDATE {table} SET {set_str} WHERE {where_column} = ?'
        
        total_affected = 0
        
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            affected = self.pool.execute_many(query, batch)
            total_affected += affected
        
        return total_affected
    
    def batch_delete(
        self,
        table: str,
        where_column: str,
        values: List[Any]
    ) -> int:
        """
        Delete multiple rows efficiently
        
        Args:
            table: Table name
            where_column: Column for WHERE clause
            values: Values to match for deletion
        
        Returns:
            Number of rows deleted
        """
        if not values:
            return 0
        
        # Use IN clause for efficiency
        total_deleted = 0
        
        for i in range(0, len(values), self.batch_size):
            batch = values[i:i + self.batch_size]
            placeholders = ', '.join(['?' for _ in batch])
            query = f'DELETE FROM {table} WHERE {where_column} IN ({placeholders})'
            
            result = self.pool.execute(query, tuple(batch), fetch=False)
            # Note: SQLite doesn't return rowcount for DELETE with execute
            total_deleted += len(batch)
        
        return total_deleted
    
    def batch_upsert(
        self,
        table: str,
        columns: List[str],
        data: List[Tuple],
        conflict_columns: List[str],
        update_columns: List[str]
    ) -> int:
        """
        Insert or update multiple rows (upsert)
        
        Args:
            table: Table name
            columns: All column names
            data: List of tuples with values
            conflict_columns: Columns that define uniqueness
            update_columns: Columns to update on conflict
        
        Returns:
            Number of rows affected
        """
        if not data:
            return 0
        
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        conflict_str = ', '.join(conflict_columns)
        update_str = ', '.join([f'{col} = excluded.{col}' for col in update_columns])
        
        query = f'''
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_str})
            DO UPDATE SET {update_str}
        '''
        
        total_affected = 0
        
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            affected = self.pool.execute_many(query, batch)
            total_affected += affected
        
        return total_affected


class QueryBuilder:
    """
    Fluent Query Builder
    
    Provides a clean API for building complex queries.
    """
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self._reset()
    
    def _reset(self) -> None:
        """Reset query state"""
        self._table = None
        self._select = ['*']
        self._where = []
        self._params = []
        self._order = []
        self._limit = None
        self._offset = None
        self._joins = []
    
    def table(self, table: str) -> 'QueryBuilder':
        """Set table name"""
        self._table = table
        return self
    
    def select(self, *columns: str) -> 'QueryBuilder':
        """Set columns to select"""
        self._select = list(columns) if columns else ['*']
        return self
    
    def where(self, column: str, operator: str, value: Any) -> 'QueryBuilder':
        """Add WHERE condition"""
        self._where.append(f'{column} {operator} ?')
        self._params.append(value)
        return self
    
    def where_in(self, column: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE IN condition"""
        placeholders = ', '.join(['?' for _ in values])
        self._where.append(f'{column} IN ({placeholders})')
        self._params.extend(values)
        return self
    
    def where_like(self, column: str, pattern: str) -> 'QueryBuilder':
        """Add WHERE LIKE condition"""
        self._where.append(f'{column} LIKE ?')
        self._params.append(pattern)
        return self
    
    def order_by(self, column: str, direction: str = 'ASC') -> 'QueryBuilder':
        """Add ORDER BY clause"""
        self._order.append(f'{column} {direction}')
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """Set LIMIT"""
        self._limit = limit
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """Set OFFSET"""
        self._offset = offset
        return self
    
    def join(self, table: str, on: str, join_type: str = 'INNER') -> 'QueryBuilder':
        """Add JOIN clause"""
        self._joins.append(f'{join_type} JOIN {table} ON {on}')
        return self
    
    def build(self) -> Tuple[str, Tuple]:
        """Build the SQL query"""
        if not self._table:
            raise ValueError("Table not specified")
        
        parts = [f"SELECT {', '.join(self._select)} FROM {self._table}"]
        
        if self._joins:
            parts.extend(self._joins)
        
        if self._where:
            parts.append(f"WHERE {' AND '.join(self._where)}")
        
        if self._order:
            parts.append(f"ORDER BY {', '.join(self._order)}")
        
        if self._limit:
            parts.append(f"LIMIT {self._limit}")
        
        if self._offset:
            parts.append(f"OFFSET {self._offset}")
        
        query = ' '.join(parts)
        params = tuple(self._params)
        
        return query, params
    
    def get(self) -> List[Dict]:
        """Execute query and return results"""
        query, params = self.build()
        result = self.pool.execute(query, params)
        self._reset()
        return result
    
    def first(self) -> Optional[Dict]:
        """Get first result"""
        self._limit = 1
        results = self.get()
        return results[0] if results else None
    
    def count(self) -> int:
        """Get count of matching rows"""
        self._select = ['COUNT(*) as count']
        result = self.first()
        self._reset()
        return result['count'] if result else 0
    
    def exists(self) -> bool:
        """Check if any matching rows exist"""
        return self.count() > 0
    
    def paginate(self, page: int, per_page: int = 50) -> Dict[str, Any]:
        """Get paginated results"""
        # Get total count
        total = self.count()
        
        # Get page data
        self._limit = per_page
        self._offset = (page - 1) * per_page
        data = self.get()
        
        return {
            'data': data,
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }


class OptimizedDatabase:
    """
    High-level optimized database interface
    
    Combines all optimization features into a single interface.
    """
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool = ConnectionPool(db_path, pool_size)
        self.indexes = IndexManager(self.pool)
        self.batch = BatchOperations(self.pool)
    
    def initialize(self) -> None:
        """Initialize database with optimizations"""
        # Create indexes
        self.indexes.create_all_indexes()
        
        # Analyze tables
        self.indexes.analyze_tables()
        
        logger.info("Database initialized with optimizations")
    
    def query(self) -> QueryBuilder:
        """Get a new query builder"""
        return QueryBuilder(self.pool)
    
    def execute(self, query: str, params: Tuple = ()) -> List[Dict]:
        """Execute raw query"""
        return self.pool.execute(query, params)
    
    def insert(self, table: str, data: Dict) -> int:
        """Insert single row"""
        columns = list(data.keys())
        values = tuple(data.values())
        
        result = self.batch.batch_insert(table, columns, [values])
        return result
    
    def insert_many(self, table: str, data: List[Dict]) -> int:
        """Insert multiple rows"""
        if not data:
            return 0
        
        columns = list(data[0].keys())
        values = [tuple(d.values()) for d in data]
        
        return self.batch.batch_insert(table, columns, values)
    
    def update(self, table: str, data: Dict, where: Dict) -> int:
        """Update rows"""
        set_parts = [f'{k} = ?' for k in data.keys()]
        where_parts = [f'{k} = ?' for k in where.keys()]
        
        query = f'''
            UPDATE {table}
            SET {', '.join(set_parts)}
            WHERE {' AND '.join(where_parts)}
        '''
        
        params = tuple(data.values()) + tuple(where.values())
        self.pool.execute(query, params, fetch=False)
        return 1
    
    def delete(self, table: str, where: Dict) -> int:
        """Delete rows"""
        where_parts = [f'{k} = ?' for k in where.keys()]
        query = f"DELETE FROM {table} WHERE {' AND '.join(where_parts)}"
        
        self.pool.execute(query, tuple(where.values()), fetch=False)
        return 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'pool': self.pool.pool_status,
            'queries': {
                'count': self.pool.stats.query_count,
                'avg_time_ms': self.pool.stats.avg_time_ms,
                'slow_queries': self.pool.stats.slow_queries
            }
        }
    
    def vacuum(self) -> None:
        """Optimize database file"""
        self.pool.execute('VACUUM', fetch=False)
        logger.info("Database vacuumed")
    
    def close(self) -> None:
        """Close all connections"""
        self.pool.close_all()


# Global instance
_db_instance: Optional[OptimizedDatabase] = None


def get_database(db_path: str = 'data/nlvoorelkaar.db') -> OptimizedDatabase:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = OptimizedDatabase(db_path)
        _db_instance.initialize()
    return _db_instance
