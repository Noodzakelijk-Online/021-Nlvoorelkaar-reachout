"""
Database Manager for NLvoorelkaar Tool
Handles SQLite database operations and schema management
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/nlvoorelkaar.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_database()
        
    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o700)
            
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with self.get_connection() as conn:
                # Create volunteers table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS volunteers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT UNIQUE NOT NULL,
                        name TEXT,
                        description TEXT,
                        location TEXT,
                        skills TEXT,
                        categories TEXT,
                        availability TEXT,
                        contact_info TEXT,
                        profile_url TEXT,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create campaigns table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        target_categories TEXT,
                        target_location TEXT,
                        target_distance INTEGER,
                        message_template TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create contacts table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        message_sent TEXT,
                        contact_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        response_received BOOLEAN DEFAULT FALSE,
                        response_date TIMESTAMP,
                        response_content TEXT,
                        status TEXT DEFAULT 'sent',
                        notes TEXT,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')
                
                # Create blacklist table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS blacklist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT UNIQUE NOT NULL,
                        reason TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create settings table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_categories ON volunteers(categories)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_location ON volunteers(location)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_volunteer_id ON contacts(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_campaign_id ON contacts(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_date ON contacts(contact_date)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    def add_volunteer(self, volunteer_data: Dict[str, Any]) -> bool:
        """Add or update volunteer information"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO volunteers 
                    (volunteer_id, name, description, location, skills, categories, 
                     availability, contact_info, profile_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    volunteer_data.get('volunteer_id'),
                    volunteer_data.get('name'),
                    volunteer_data.get('description'),
                    volunteer_data.get('location'),
                    volunteer_data.get('skills'),
                    volunteer_data.get('categories'),
                    volunteer_data.get('availability'),
                    volunteer_data.get('contact_info'),
                    volunteer_data.get('profile_url')
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add volunteer: {e}")
            return False
            
    def get_volunteers(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get volunteers with optional filters"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM volunteers WHERE 1=1"
                params = []
                
                if filters:
                    if 'categories' in filters:
                        query += " AND categories LIKE ?"
                        params.append(f"%{filters['categories']}%")
                        
                    if 'location' in filters:
                        query += " AND location LIKE ?"
                        params.append(f"%{filters['location']}%")
                        
                    if 'not_contacted' in filters and filters['not_contacted']:
                        query += " AND volunteer_id NOT IN (SELECT volunteer_id FROM contacts)"
                        
                    if 'not_blacklisted' in filters and filters['not_blacklisted']:
                        query += " AND volunteer_id NOT IN (SELECT volunteer_id FROM blacklist)"
                        
                query += " ORDER BY updated_at DESC"
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get volunteers: {e}")
            return []
            
    def add_campaign(self, campaign_data: Dict[str, Any]) -> int:
        """Add new campaign and return campaign ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO campaigns 
                    (name, description, target_categories, target_location, 
                     target_distance, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    campaign_data.get('name'),
                    campaign_data.get('description'),
                    campaign_data.get('target_categories'),
                    campaign_data.get('target_location'),
                    campaign_data.get('target_distance'),
                    campaign_data.get('message_template')
                ))
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to add campaign: {e}")
            return None
            
    def get_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get campaigns: {e}")
            return []
            
    def add_contact(self, contact_data: Dict[str, Any]) -> bool:
        """Record a contact attempt"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO contacts 
                    (volunteer_id, campaign_id, message_sent, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    contact_data.get('volunteer_id'),
                    contact_data.get('campaign_id'),
                    contact_data.get('message_sent'),
                    contact_data.get('status', 'sent'),
                    contact_data.get('notes')
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add contact: {e}")
            return False
            
    def get_contacts(self, campaign_id: int = None) -> List[Dict[str, Any]]:
        """Get contact history"""
        try:
            with self.get_connection() as conn:
                if campaign_id:
                    cursor = conn.execute('''
                        SELECT c.*, v.name as volunteer_name, v.location as volunteer_location
                        FROM contacts c
                        LEFT JOIN volunteers v ON c.volunteer_id = v.volunteer_id
                        WHERE c.campaign_id = ?
                        ORDER BY c.contact_date DESC
                    ''', (campaign_id,))
                else:
                    cursor = conn.execute('''
                        SELECT c.*, v.name as volunteer_name, v.location as volunteer_location,
                               camp.name as campaign_name
                        FROM contacts c
                        LEFT JOIN volunteers v ON c.volunteer_id = v.volunteer_id
                        LEFT JOIN campaigns camp ON c.campaign_id = camp.id
                        ORDER BY c.contact_date DESC
                    ''')
                    
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []
            
    def add_to_blacklist(self, volunteer_id: str, reason: str = "") -> bool:
        """Add volunteer to blacklist"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO blacklist (volunteer_id, reason)
                    VALUES (?, ?)
                ''', (volunteer_id, reason))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add to blacklist: {e}")
            return False
            
    def remove_from_blacklist(self, volunteer_id: str) -> bool:
        """Remove volunteer from blacklist"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM blacklist WHERE volunteer_id = ?', (volunteer_id,))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove from blacklist: {e}")
            return False
            
    def get_blacklist(self) -> List[Dict[str, Any]]:
        """Get blacklisted volunteers"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT b.*, v.name as volunteer_name
                    FROM blacklist b
                    LEFT JOIN volunteers v ON b.volunteer_id = v.volunteer_id
                    ORDER BY b.added_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get blacklist: {e}")
            return []
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Total volunteers
                cursor = conn.execute("SELECT COUNT(*) FROM volunteers")
                stats['total_volunteers'] = cursor.fetchone()[0]
                
                # Total campaigns
                cursor = conn.execute("SELECT COUNT(*) FROM campaigns")
                stats['total_campaigns'] = cursor.fetchone()[0]
                
                # Total contacts
                cursor = conn.execute("SELECT COUNT(*) FROM contacts")
                stats['total_contacts'] = cursor.fetchone()[0]
                
                # Blacklisted volunteers
                cursor = conn.execute("SELECT COUNT(*) FROM blacklist")
                stats['blacklisted_volunteers'] = cursor.fetchone()[0]
                
                # Response rate
                cursor = conn.execute("SELECT COUNT(*) FROM contacts WHERE response_received = TRUE")
                responses = cursor.fetchone()[0]
                stats['response_rate'] = (responses / stats['total_contacts'] * 100) if stats['total_contacts'] > 0 else 0
                
                # Recent activity (last 7 days)
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM contacts 
                    WHERE contact_date >= datetime('now', '-7 days')
                ''')
                stats['recent_contacts'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
            
    def search_volunteers(self, search_term: str) -> List[Dict[str, Any]]:
        """Full-text search across volunteer data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM volunteers 
                    WHERE name LIKE ? OR description LIKE ? OR skills LIKE ? OR location LIKE ?
                    ORDER BY updated_at DESC
                ''', (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to search volunteers: {e}")
            return []
            
    def cleanup_old_data(self, days: int = 365) -> bool:
        """Clean up old data beyond retention period"""
        try:
            with self.get_connection() as conn:
                # Remove old contacts
                conn.execute('''
                    DELETE FROM contacts 
                    WHERE contact_date < datetime('now', '-{} days')
                '''.format(days))
                
                # Remove volunteers not contacted in the retention period
                conn.execute('''
                    DELETE FROM volunteers 
                    WHERE volunteer_id NOT IN (
                        SELECT DISTINCT volunteer_id FROM contacts 
                        WHERE contact_date >= datetime('now', '-{} days')
                    )
                    AND updated_at < datetime('now', '-{} days')
                '''.format(days, days))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False

